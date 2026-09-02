"""
app.py - Desktop-Grade Global Business Directory Extractor
Powered by Streamlit, DuckDB, Overture Maps S3, and GeonamesCache.
Features global cascading location selectors, multi-category stacking,
keyword clubbing, and full directory extraction without website filters.
"""

import logging
import re
import time
from typing import List, Optional, Tuple
import pandas as pd
import streamlit as st

# Import local engines
from geocoder import geocode_location_details
from location_service import get_location_service
from overture_fetcher import fetch_overture_places

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("global_extractor_app")

# Set Page Config
st.set_page_config(
    page_title="Global Business Directory Extractor",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for sleek, premium Apple / macOS Human Interface Guidelines aesthetic
st.markdown("""
<style>
    /* 1. Typography: Apple System Fonts & Clean Weights */
    html, body, [class*="css"], [class*="st-"], div, span, button, input, select, textarea {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }
    
    h1, h2, h3, h4, h5, h6, .main-title {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
        font-weight: 600 !important;
        color: #1D1D1F !important;
        letter-spacing: -0.02em !important;
    }
    
    p, label, span, .subtitle {
        font-weight: 400 !important;
        color: #424245 !important;
    }

    /* 2. Window Chrome & Desktop Canvas Feel */
    #MainMenu { visibility: hidden; }
    header { visibility: hidden; }
    footer { visibility: hidden; }
    
    .block-container {
        padding-top: 1.8rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 96% !important;
    }

    [data-testid="stAppViewContainer"] {
        background-color: #FBFBFD !important;
    }

    [data-testid="stSidebar"] {
        background-color: #F5F5F7 !important;
        border-right: 1px solid #E5E5EA !important;
    }

    /* 3. Header & Badges */
    .main-title {
        font-size: 2.2rem !important;
        margin-bottom: 0.25rem !important;
    }
    .subtitle {
        font-size: 1.02rem !important;
        color: #6E6E73 !important;
        line-height: 1.5 !important;
        margin-bottom: 1.4rem !important;
    }
    .badge-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        margin-bottom: 0.85rem;
    }
    .badge {
        display: inline-block;
        padding: 0.28rem 0.72rem;
        font-size: 0.78rem;
        font-weight: 500;
        border-radius: 9999px;
        background-color: #FFFFFF;
        color: #1D1D1F;
        border: 1px solid #F5F5F7;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.03);
    }
    .badge-highlight {
        background-color: #E8F2FF !important;
        color: #0071E3 !important;
        border-color: #CCE3FF !important;
    }

    /* 4. Metric Cards: Soft Floating Geometry */
    .metric-card {
        background: #FFFFFF !important;
        border: 1px solid #F5F5F7 !important;
        border-radius: 14px !important;
        padding: 1.2rem 0.9rem !important;
        text-align: center !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04) !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .metric-card:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.06) !important;
    }
    .metric-value {
        font-size: 1.95rem !important;
        font-weight: 600 !important;
        color: #1D1D1F !important;
        line-height: 1.2 !important;
    }
    .metric-label {
        font-size: 0.74rem !important;
        color: #86868B !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        margin-top: 0.35rem !important;
        font-weight: 600 !important;
    }

    /* 5. Pill Buttons with Smooth Lift */
    .stButton > button {
        border-radius: 20px !important;
        font-weight: 500 !important;
        font-size: 0.92rem !important;
        padding: 0.55rem 1.4rem !important;
        border: none !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 5px 14px rgba(0, 0, 0, 0.08) !important;
    }
    .stButton > button:active {
        transform: translateY(0px) !important;
    }
    .stButton > button[kind="primary"] {
        background: #0071E3 !important;
        color: #FFFFFF !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #0077ED !important;
        box-shadow: 0 6px 16px rgba(0, 113, 227, 0.28) !important;
    }

    .stDownloadButton > button {
        border-radius: 20px !important;
        font-weight: 500 !important;
        font-size: 0.92rem !important;
        padding: 0.55rem 1.4rem !important;
        border: none !important;
        background: #0071E3 !important;
        color: #FFFFFF !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }
    .stDownloadButton > button:hover {
        background: #0077ED !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(0, 113, 227, 0.28) !important;
    }

    /* 6. Soft Geometry for Containers, Tables & Widgets */
    [data-testid="stDataFrame"], [data-testid="stTable"], .stDataFrame {
        border-radius: 14px !important;
        overflow: hidden !important;
        border: 1px solid #F5F5F7 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04) !important;
        background-color: #FFFFFF !important;
    }

    div[data-testid="stExpander"], div[data-testid="stStatusWidget"], div[data-testid="stAlert"] {
        border-radius: 14px !important;
        border: 1px solid #F5F5F7 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04) !important;
        background-color: #FFFFFF !important;
    }

    /* 7. Input Elements & Selectboxes */
    [data-testid="stSidebar"] [data-baseweb="select"],
    [data-testid="stSidebar"] [data-baseweb="input"],
    [data-testid="stSidebar"] .stTextInput input,
    .stTextInput input,
    [data-baseweb="select"] > div {
        border-radius: 12px !important;
        border: 1px solid #E5E5EA !important;
        background-color: #FFFFFF !important;
    }
</style>
""", unsafe_allow_html=True)


def slugify(text: str) -> str:
    """Converts a string to a filesystem-safe lowercase slug."""
    if not text:
        return "all"
    return re.sub(r"[^a-zA-Z0-9_-]", "_", text.strip().lower()).strip("_")


# Initialize Location Service
loc_service = get_location_service()
all_countries = loc_service.get_countries()
all_categories = loc_service.get_all_categories()


# Cached Engines
@st.cache_data(show_spinner=False, ttl=3600)
def cached_geocode_location(query: str, buffer_ratio: float) -> dict:
    """Caches global geocoding queries."""
    return geocode_location_details(query, buffer_ratio=buffer_ratio)


@st.cache_data(show_spinner=False, ttl=1800)
def cached_query_overture(
    bbox: Tuple[float, float, float, float],
    categories_tuple: Tuple[str, ...],
    keyword: str,
    all_categories: bool
) -> pd.DataFrame:
    """Caches DuckDB S3 queries for places in a bbox and category."""
    cat_list = list(categories_tuple) if categories_tuple else None
    kw = keyword.strip() if keyword else None
    return fetch_overture_places(
        bbox=bbox,
        categories=cat_list,
        keyword=kw,
        all_categories=all_categories,
        limit=None
    )


# ---------------- SIDEBAR: GLOBAL CASCADING & CATEGORY SELECTORS ----------------
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/globe.png", width=60)
    st.title("Search Parameters")
    st.markdown("Global directory extraction powered by DuckDB & Overture Maps.")

    # 1. Geographic Location
    st.subheader("1. Geographic Location")
    default_country_idx = all_countries.index("United States") if "United States" in all_countries else 0
    selected_country = st.selectbox(
        "Country",
        options=all_countries,
        index=default_country_idx,
        help="Select any country globally (250+ countries)."
    )

    # State / Region Selector (Cascades dynamically from Country)
    states_list, state_code_map = loc_service.get_states_for_country(selected_country)
    if not states_list:
        states_list = ["All Regions"]

    default_state_idx = 0
    if selected_country == "United States" and "Texas" in states_list:
        default_state_idx = states_list.index("Texas")

    selected_state = st.selectbox(
        "State / Province / Region",
        options=states_list,
        index=default_state_idx,
        help="Dynamically populated based on the selected country."
    )

    # City Selector (Cascades dynamically from State)
    cities_list = loc_service.get_cities_for_state(
        country_name=selected_country,
        state_name=selected_state,
        state_to_code=state_code_map
    )

    city_mode = st.radio("City Selection Mode", ["Choose from City List", "Type Custom City"], horizontal=True)

    if city_mode == "Choose from City List" and cities_list:
        default_city_idx = 0
        if "Austin" in cities_list:
            default_city_idx = cities_list.index("Austin")
        elif "Toronto" in cities_list:
            default_city_idx = cities_list.index("Toronto")
        elif "London" in cities_list:
            default_city_idx = cities_list.index("London")

        selected_city = st.selectbox(
            "City",
            options=cities_list,
            index=default_city_idx,
            help="Major cities (pop > 15,000) within the selected region."
        )
    else:
        selected_city = st.text_input(
            "Enter City Name",
            value=cities_list[0] if cities_list else "Austin",
            placeholder="e.g., Austin, Melbourne, Munich, Kyoto",
            help="Type any city or town name."
        )

    # Spatial Boundary Scope
    st.subheader("2. Spatial Boundary Scope")
    scope_option = st.radio(
        "Search Coverage Area",
        options=["Strict City Limits Only", "Include Surrounding Metro / Suburbs (+20%)"],
        index=0,
        help="Strict limits restricts queries to exact municipal bounds. Surrounding Metro expands bounds to capture suburbs."
    )
    buffer_ratio = 0.20 if "Surrounding" in scope_option else 0.0

    # 3. Category & Keyword Selector
    st.subheader("3. Business Categories")
    select_all_cats = st.checkbox(
        "🌐 Select All Categories (Extract Entire City)",
        value=False,
        help="Check to extract all commercial businesses across all industries inside the bounding box."
    )

    if select_all_cats:
        st.info("ℹ️ **Extracting all business categories** without restriction.")
        selected_categories: List[str] = []
        keyword_input = ""
    else:
        # Category Keyword Clubbing Input
        keyword_input = st.text_input(
            "🔍 Keyword Search (Clubbing)",
            value="",
            placeholder="e.g., restaurant, contractor, salon, medical",
            help="Wildcard search matching primary and alternate categories. e.g. 'restaurant' automatically clubs thai_restaurant, italian_restaurant, etc."
        )

        # Multi-select Dropdown
        default_cats = ["restaurant"] if not keyword_input and "restaurant" in all_categories else []
        selected_categories = st.multiselect(
            "📂 Multi-Select Specific Categories",
            options=all_categories,
            default=default_cats,
            help="Stack multiple standardized categories at once (e.g. plumber + electrician)."
        )

    st.markdown("---")
    st.caption("⚡ **Fast Streaming Pipeline**: Nominatim Geocoding + DuckDB S3 Parquet Streaming (2–5 seconds).")


# ---------------- MAIN DASHBOARD ----------------
st.markdown('<div class="main-title">🌍 Global Business Directory Extractor</div>', unsafe_allow_html=True)

st.markdown("""
<div class="badge-container">
    <span class="badge badge-highlight">⚡ 2–5s Streaming</span>
    <span class="badge">🌐 250+ Countries</span>
    <span class="badge">📚 2,117 Overture Categories</span>
    <span class="badge">🔍 Keyword Clubbing</span>
    <span class="badge">📂 Multi-Category Stacking</span>
    <span class="badge">🚀 100% Free / Zero API Keys</span>
</div>
<div class="subtitle">Extract verified business directories with phone numbers, websites, native emails, physical street addresses, and exact coordinates.</div>
""", unsafe_allow_html=True)

# Build formatted location query string
formatted_location = loc_service.format_location_query(
    city=selected_city,
    state=selected_state if selected_state != "All Regions" else None,
    country=selected_country
)

# Determine Category Display Text
if select_all_cats:
    category_summary = "All Categories (Full Directory)"
    cat_slug_for_file = "all_categories"
elif keyword_input.strip() and selected_categories:
    category_summary = f"Keyword: '{keyword_input.strip()}' + {len(selected_categories)} selected categories"
    cat_slug_for_file = f"{slugify(keyword_input)}_{slugify(selected_categories[0])}"
elif keyword_input.strip():
    category_summary = f"Keyword: '{keyword_input.strip()}' (Clubbing)"
    cat_slug_for_file = slugify(keyword_input)
elif selected_categories:
    category_summary = f"Categories: {', '.join(selected_categories[:3])}" + (f" (+{len(selected_categories)-3} more)" if len(selected_categories) > 3 else "")
    cat_slug_for_file = "_".join([slugify(c) for c in selected_categories[:3]])
else:
    category_summary = "All Categories (Default)"
    cat_slug_for_file = "all"

# Run Controls
col_btn, col_info = st.columns([1.2, 4])
with col_btn:
    run_clicked = st.button("🚀 Extract Businesses", type="primary", use_container_width=True)

with col_info:
    st.info(
        f"📍 Location: **{formatted_location}** | "
        f"🏷️ Target: **{category_summary}** | "
        f"🎯 Scope: **{'Metro Area (+20%)' if buffer_ratio > 0 else 'Strict City Limits'}**"
    )

# Session State Persistence
if "global_places_df" not in st.session_state:
    st.session_state.global_places_df = None
if "last_query_meta" not in st.session_state:
    st.session_state.last_query_meta = {}


# ---------------- STREAMLINED EXECUTION PIPELINE ----------------
if run_clicked:
    if not selected_city or not selected_city.strip():
        st.error("Please enter or select a target city.")
        st.stop()

    start_time = time.time()
    status_box = st.status("Executing Extraction Pipeline...", expanded=True)

    try:
        # Phase 1: Geocoding
        status_box.write(f"📍 **Phase 1: Resolving spatial coordinates for '{formatted_location}'...**")
        loc_details = cached_geocode_location(formatted_location, buffer_ratio=buffer_ratio)
        bbox = loc_details["bounding_box"]
        display_address = loc_details["display_name"]
        
        status_box.write(
            f"✅ **Location Resolved**: `{display_address}`\n\n"
            f"📐 **Bounding Box**: `[{bbox[0]:.4f}, {bbox[1]:.4f}, {bbox[2]:.4f}, {bbox[3]:.4f}]`"
        )

        # Phase 2: DuckDB S3 Parquet Streaming
        status_box.write(f"🦆 **Phase 2: Streaming places from AWS S3 via DuckDB ({category_summary})...**")
        t0 = time.time()
        
        categories_tuple = tuple(selected_categories) if selected_categories else ()
        places_df = cached_query_overture(
            bbox=bbox,
            categories_tuple=categories_tuple,
            keyword=keyword_input,
            all_categories=select_all_cats
        )
        s3_duration = round(time.time() - t0, 2)

        total_extracted = len(places_df)
        total_time = round(time.time() - start_time, 2)

        if total_extracted == 0:
            status_box.update(label="Extraction Complete (0 results)", state="complete", expanded=False)
            st.warning(
                f"No businesses found in **{formatted_location}** for **{category_summary}**. "
                "Try enabling 'Include Surrounding Metro' in the sidebar or broadening your category criteria."
            )
            st.session_state.global_places_df = None
            st.stop()

        status_box.write(f"🎉 **Streaming Completed**: Extracted **{total_extracted:,}** physical businesses in **{s3_duration}s**.")
        status_box.update(label=f"Completed! {total_extracted:,} businesses extracted in {total_time}s", state="complete", expanded=False)

        # Persist results to session
        st.session_state.global_places_df = places_df
        st.session_state.last_query_meta = {
            "country": selected_country,
            "state": selected_state,
            "city": selected_city,
            "category_label": category_summary,
            "cat_slug": cat_slug_for_file,
            "total": total_extracted,
            "duration": total_time,
            "display_name": display_address,
            "center_lat": loc_details["latitude"],
            "center_lon": loc_details["longitude"],
        }

    except Exception as e:
        status_box.update(label="Extraction Error", state="error", expanded=True)
        st.error(f"❌ Error during extraction: {e}")
        logger.exception("Extraction failed:")
        st.stop()


# ---------------- RESULTS PRESENTATION & KPI CARDS ----------------
if st.session_state.global_places_df is not None and not st.session_state.global_places_df.empty:
    df = st.session_state.global_places_df
    meta = st.session_state.last_query_meta

    total_count = len(df)
    with_phone = df["phone"].apply(lambda x: len(str(x).strip()) > 3).sum()
    with_website = df["website"].apply(lambda x: len(str(x).strip()) > 3).sum()
    with_email = df["email"].apply(lambda x: len(str(x).strip()) > 3).sum()
    with_address = df["street_address"].apply(lambda x: len(str(x).strip()) > 0).sum()

    st.markdown("---")
    st.subheader("📊 Extraction Metrics")

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{total_count:,}</div>'
            '<div class="metric-label">Total Businesses</div></div>',
            unsafe_allow_html=True
        )
    with col2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{with_phone:,}</div>'
            '<div class="metric-label">Phones</div></div>',
            unsafe_allow_html=True
        )
    with col3:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{with_website:,}</div>'
            '<div class="metric-label">Websites</div></div>',
            unsafe_allow_html=True
        )
    with col4:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{with_email:,}</div>'
            '<div class="metric-label">Native Emails</div></div>',
            unsafe_allow_html=True
        )
    with col5:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{with_address:,}</div>'
            '<div class="metric-label">Physical Addresses</div></div>',
            unsafe_allow_html=True
        )
    with col6:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{meta.get("duration", 0)}s</div>'
            '<div class="metric-label">Pipeline Time</div></div>',
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs for Data View and Map View
    tab_data, tab_map = st.tabs(["📋 Directory Data Table", "🗺️ Geographic Coordinate Map"])

    with tab_data:
        # Table Filter Controls
        f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns([1.5, 1.5, 1.5, 1.5, 3])
        with f_col1:
            filt_phone = st.checkbox("Only with Phone", value=False)
        with f_col2:
            filt_website = st.checkbox("Only with Website", value=False)
        with f_col3:
            filt_email = st.checkbox("Only with Email", value=False)
        with f_col4:
            filt_addr = st.checkbox("Only with Address", value=False)
        with f_col5:
            search_name = st.text_input("Search Business Name", placeholder="Filter by name...", label_visibility="collapsed")

        # Apply Filters
        view_df = df.copy()
        if filt_phone:
            view_df = view_df[view_df["phone"].str.strip().str.len() > 3]
        if filt_website:
            view_df = view_df[view_df["website"].str.strip().str.len() > 3]
        if filt_email:
            view_df = view_df[view_df["email"].str.strip().str.len() > 3]
        if filt_addr:
            view_df = view_df[view_df["street_address"].str.strip().str.len() > 0]
        if search_name.strip():
            view_df = view_df[view_df["name"].str.contains(search_name.strip(), case=False, na=False)]

        st.caption(f"Showing **{len(view_df):,}** of **{total_count:,}** extracted businesses")

        # Interactive Dataframe with rich columns
        display_columns = [
            "name", "category", "phone", "website", "email",
            "street_address", "locality", "postcode", "region", "country"
        ]
        available_cols = [c for c in display_columns if c in view_df.columns]

        st.dataframe(
            view_df[available_cols],
            use_container_width=True,
            height=450,
            column_config={
                "name": st.column_config.TextColumn("Business Name", width="medium"),
                "category": st.column_config.TextColumn("Category", width="small"),
                "phone": st.column_config.TextColumn("Phone", width="small"),
                "website": st.column_config.LinkColumn("Website", width="medium"),
                "email": st.column_config.TextColumn("Email", width="medium"),
                "street_address": st.column_config.TextColumn("Street Address", width="medium"),
                "locality": st.column_config.TextColumn("City / Locality", width="small"),
                "postcode": st.column_config.TextColumn("Postal Code", width="small"),
                "region": st.column_config.TextColumn("State / Region", width="small"),
                "country": st.column_config.TextColumn("Country Code", width="small"),
            }
        )

        # Standard Export File Naming: {country}_{state}_{city}_{category}.csv
        filename_country = slugify(meta.get("country", "country"))
        filename_state = slugify(meta.get("state", "state"))
        filename_city = slugify(meta.get("city", "city"))
        filename_cat = slugify(meta.get("cat_slug", "directory"))
        export_filename = f"{filename_country}_{filename_state}_{filename_city}_{filename_cat}.csv"

        # CSV Download
        csv_bytes = view_df[available_cols].to_csv(index=False).encode("utf-8")
        
        col_dl, col_blank = st.columns([2.5, 4])
        with col_dl:
            st.download_button(
                label=f"📥 Download CSV ({export_filename})",
                data=csv_bytes,
                file_name=export_filename,
                mime="text/csv",
                type="primary",
                use_container_width=True
            )

    with tab_map:
        if "latitude" in df.columns and "longitude" in df.columns:
            map_data = df.dropna(subset=["latitude", "longitude"]).copy()
            # Ensure numeric coordinates
            map_data["latitude"] = pd.to_numeric(map_data["latitude"], errors="coerce")
            map_data["longitude"] = pd.to_numeric(map_data["longitude"], errors="coerce")
            map_data = map_data.dropna(subset=["latitude", "longitude"])

            if not map_data.empty:
                st.caption(f"Displaying **{len(map_data):,}** geographic points across {meta.get('city', 'the city')}:")
                st.map(map_data, latitude="latitude", longitude="longitude", size=18)
            else:
                st.info("No valid latitude/longitude coordinates available to map.")
        else:
            st.info("Coordinates not present in dataset.")
