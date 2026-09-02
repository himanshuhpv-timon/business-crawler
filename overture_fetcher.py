"""
overture_fetcher.py - High-Performance Streaming DuckDB Query Engine for Overture Maps
Extracts physical business records directly from public Overture Maps S3 Parquet partitions.
Supports flexible multi-category selection, keyword clubbing, and full directory extraction.
"""

import logging
from typing import List, Optional, Tuple, Union
import duckdb
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_OVERTURE_RELEASE = "2026-08-19.0"
FALLBACK_RELEASES = ["2026-08-19.0", "2026-07-22.0", "2024-07-22.0"]


def init_duckdb_s3_connection() -> duckdb.DuckDBPyConnection:
    """
    Initializes an in-memory DuckDB connection configured for streaming S3 parquet files.
    """
    logger.info("Initializing DuckDB with httpfs and spatial extensions...")
    conn = duckdb.connect(database=":memory:")
    
    # Load required extensions
    conn.execute("INSTALL httpfs; LOAD httpfs;")
    try:
        conn.execute("INSTALL spatial; LOAD spatial;")
    except Exception as e:
        logger.warning(f"Spatial extension load notice: {e}")

    # Configure public S3 settings for us-west-2
    conn.execute("SET s3_region = 'us-west-2';")
    conn.execute("SET s3_url_style = 'path';")
    try:
        conn.execute("CREATE SECRET overture_s3 (TYPE S3, PROVIDER CONFIG);")
    except Exception:
        pass

    return conn


def get_available_s3_release(conn: duckdb.DuckDBPyConnection, preferred_release: str = DEFAULT_OVERTURE_RELEASE) -> str:
    """
    Verifies that the target release exists in the S3 bucket; falls back if necessary.
    """
    test_releases = [preferred_release] + [r for r in FALLBACK_RELEASES if r != preferred_release]
    
    for rel in test_releases:
        try:
            test_path = f"s3://overturemaps-us-west-2/release/{rel}/theme=places/type=place/*"
            res = conn.execute(f"SELECT count(*) FROM glob('{test_path}')").fetchone()
            if res and res[0] > 0:
                logger.info(f"Using verified Overture release on S3: '{rel}' ({res[0]} partitions)")
                return rel
        except Exception as e:
            logger.debug(f"Release '{rel}' check notice: {e}")
            continue

    logger.warning(f"Defaulting to preferred release: '{preferred_release}'.")
    return preferred_release


def build_category_filter_clause(
    categories: Optional[Union[str, List[str]]] = None,
    keyword: Optional[str] = None,
    all_categories: bool = False
) -> str:
    """
    Dynamically constructs SQL WHERE clauses for category filtering:
    - If all_categories is True: returns '1=1'
    - If keyword is provided: lower(categories.primary) LIKE '%kw%' OR list_contains(categories.alternate, 'kw')
    - If categories list is provided: categories.primary IN ('c1', 'c2')
    - Combines multiple criteria with OR logic.
    """
    if all_categories:
        logger.info("Category filter: ALL categories selected (1=1).")
        return "1=1"

    clauses: List[str] = []

    # 1. Specific Category Multi-Select Clause
    if categories:
        if isinstance(categories, str):
            cat_list = [c.strip().lower() for c in categories.split(",") if c.strip()]
        else:
            cat_list = [c.strip().lower() for c in categories if c.strip()]

        if cat_list:
            cleaned_cats = [c.replace("'", "''") for c in cat_list]
            cat_tuples = ", ".join([f"'{c}'" for c in cleaned_cats])
            clauses.append(f"lower(categories.primary) IN ({cat_tuples})")

    # 2. Keyword Search Clubbing Clause
    # Automatically clubs e.g. 'thai_restaurant', 'chinese_restaurant' or alternate category references
    if keyword and keyword.strip():
        clean_kw = keyword.strip().lower().replace("'", "''")
        clauses.append(
            f"("
            f"lower(categories.primary) LIKE '%{clean_kw}%' OR "
            f"(categories.alternate IS NOT NULL AND list_contains(categories.alternate, '{clean_kw}'))"
            f")"
        )

    if not clauses:
        logger.info("No specific category or keyword provided; matching all categories.")
        return "1=1"

    # Combine criteria with OR (matches if it satisfies either the multiselect OR the keyword)
    combined = " OR ".join(clauses)
    return f"({combined})"


def fetch_overture_places(
    bbox: Tuple[float, float, float, float],
    categories: Optional[Union[str, List[str]]] = None,
    keyword: Optional[str] = None,
    all_categories: bool = False,
    release: str = DEFAULT_OVERTURE_RELEASE,
    limit: Optional[int] = None,
    conn: Optional[duckdb.DuckDBPyConnection] = None
) -> pd.DataFrame:
    """
    Streams and extracts physical business records from the public Overture Maps Places dataset.
    Completely removes legacy website filters and returns all matching physical entities.

    Parameters:
        bbox (Tuple[float, float, float, float]): (xmin, ymin, xmax, ymax)
        categories (Optional[Union[str, List[str]]]): Multi-select list or string of categories.
        keyword (Optional[str]): Wildcard search keyword for primary & alternate category clubbing.
        all_categories (bool): If True, disables category filtering and extracts all businesses.
        release (str): S3 dataset release version tag.
        limit (Optional[int]): Optional maximum record cap (None = unlimited).
        conn (Optional[duckdb.DuckDBPyConnection]): Existing connection if any.

    Returns:
        pd.DataFrame: Contains columns:
            ['name', 'category', 'phone', 'website', 'email', 'street_address',
             'locality', 'postcode', 'region', 'country', 'latitude', 'longitude']
    """
    close_conn = False
    if conn is None:
        conn = init_duckdb_s3_connection()
        close_conn = True

    try:
        xmin, ymin, xmax, ymax = bbox
        category_filter_clause = build_category_filter_clause(
            categories=categories,
            keyword=keyword,
            all_categories=all_categories
        )

        logger.info(
            f"Querying Overture Places within "
            f"bbox=[xmin:{xmin:.4f}, ymin:{ymin:.4f}, xmax:{xmax:.4f}, ymax:{ymax:.4f}] | "
            f"Category Filter: {category_filter_clause}"
        )

        active_release = get_available_s3_release(conn, preferred_release=release)
        parquet_source = f"s3://overturemaps-us-west-2/release/{active_release}/theme=places/type=place/*"
        limit_clause = f"LIMIT {limit}" if limit and limit > 0 else ""

        # Rich Schema Extraction:
        # NO website filter (returns businesses with or without website)
        # Robust array element extraction phones[1], websites[1], emails[1], addresses[1]
        query = f"""
        SELECT 
            names.primary AS name,
            categories.primary AS category,
            phones[1] AS phone,
            websites[1] AS website,
            emails[1] AS email,
            addresses[1].freeform AS street_address,
            addresses[1].locality AS locality,
            addresses[1].postcode AS postcode,
            addresses[1].region AS region,
            addresses[1].country AS country,
            CAST((bbox.ymin + bbox.ymax) / 2.0 AS DOUBLE) AS latitude,
            CAST((bbox.xmin + bbox.xmax) / 2.0 AS DOUBLE) AS longitude
        FROM read_parquet('{parquet_source}', hive_partitioning=1)
        WHERE 
            -- Spatial Bounding Box Filter
            bbox.xmin <= {xmax} AND bbox.xmax >= {xmin}
            AND bbox.ymin <= {ymax} AND bbox.ymax >= {ymin}
            -- Dynamic Category Filter (all, multi-select, and/or keyword)
            AND ({category_filter_clause})
            -- Entity must have a primary name
            AND names.primary IS NOT NULL
            AND trim(names.primary) != ''
        {limit_clause};
        """

        logger.info("Executing DuckDB S3 Parquet streaming query...")
        df = conn.execute(query).df()
        logger.info(f"Query completed: extracted {len(df)} businesses.")

        # Clean string columns and handle NULL/NaN robustly without dropping rows
        string_cols = [
            "name", "category", "phone", "website", "email",
            "street_address", "locality", "postcode", "region", "country"
        ]
        for col in string_cols:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.strip()
                df[col] = df[col].replace({"nan": "", "None": "", "<NA>": "", "NULL": ""})

        # Drop duplicate records based on identical names and coordinates
        if not df.empty:
            df.drop_duplicates(subset=["name", "latitude", "longitude"], inplace=True)
            df.reset_index(drop=True, inplace=True)

        return df

    finally:
        if close_conn:
            try:
                conn.close()
            except Exception:
                pass


if __name__ == "__main__":
    test_bbox = (-97.94, 30.13, -97.56, 30.52)
    print("1. Testing keyword clubbing with 'restaurant'...")
    res_kw = fetch_overture_places(bbox=test_bbox, keyword="restaurant", limit=5)
    print(f"Result count: {len(res_kw)}")
    print(res_kw[["name", "category", "phone", "website", "street_address"]])

    print("\n2. Testing multi-select with ['plumber', 'electrician']...")
    res_multi = fetch_overture_places(bbox=test_bbox, categories=["plumber", "electrician"], limit=5)
    print(f"Result count: {len(res_multi)}")
    print(res_multi[["name", "category", "phone", "website", "street_address"]])
