"""
app.py - High-Performance Global Business Directory Extractor
Powered by Streamlit, DuckDB, Overture Maps S3, and GeoNamesCache.
Features global cascading location selectors, multi-category stacking,
keyword clubbing, offline 0ms geocoding, and unlimited record extraction.
Styled with a warm, minimalist, high-end design inspired by modern executive dashboards.
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

# Page Configuration
st.set_page_config(
    page_title="Directory • Global Business Extractor",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Modern, Minimalist, Warm Executive Aesthetic (No Apple Blue)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* 1. Global Typography & Warm Porcelain Canvas */
    html, body, [class*="css"], [class*="st-"], div, span, button, input, select, textarea {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    body, [data-testid="stAppViewContainer"] {
        background-color: #F7F7FA !important;
        color: #18181B !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-weight: 700 !important;
        color: #18181B !important;
        letter-spacing: -0.025em !important;
    }

    p, label, span {
        color: #52525B !important;
    }

    /* 2. Hide Clutter & Lock Static Sidebar */
    #MainMenu { visibility: hidden !important; display: none !important; }
    header { visibility: hidden !important; display: none !important; }
    footer { visibility: hidden !important; display: none !important; }

    [data-testid="collapsedControl"],
    button[data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapseButton"],
    button[kind="header"],
    [data-testid="stSidebarHeader"] button {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
    }

    [data-testid="stSidebar"] {
        display: block !important;
        visibility: visible !important;
        transform: none !important;
        margin-left: 0 !important;
        min-width: 320px !important;
        max-width: 380px !important;
        background-color: #FFFFFF !important;
        border-right: 1px solid #ECECEF !important;
        box-shadow: 2px 0 20px rgba(0, 0, 0, 0.02) !important;
    }

    [data-testid="stSidebarContent"] {
        visibility: visible !important;
        display: block !important;
        padding-top: 1.5rem !important;
        padding-bottom: 2.5rem !important;
    }

    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        padding-left: 2.2rem !important;
        padding-right: 2.2rem !important;
        max-width: 98% !important;
    }

    /* 3. Hero Header Section */
    .hero-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 1rem;
        margin-bottom: 1.8rem;
    }

    .hero-title-group {
        display: flex;
        flex-direction: column;
    }

    .hero-badge-row {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-bottom: 0.4rem;
    }

    .hero-tag {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: #FFFFFF;
        border: 1px solid #ECECEF;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        color: #71717A;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.02);
    }

    .hero-tag .dot-terracotta {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #E0583B;
    }

    .hero-tag .dot-green {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background-color: #10B981;
    }

    .hero-title {
        font-size: 2.4rem !important;
        font-weight: 800 !important;
        color: #18181B !important;
        letter-spacing: -0.03em !important;
        line-height: 1.15 !important;
        margin: 0 !important;
    }

    .hero-title span {
        color: #E0583B !important;
    }

    .hero-subtitle {
        font-size: 1.02rem !important;
        color: #71717A !important;
        margin-top: 0.35rem !important;
        font-weight: 400 !important;
    }

    /* 4. Action Banner & Target Chips */
    .target-banner {
        background: #FFFFFF;
        border: 1px solid #ECECEF;
        border-radius: 20px;
        padding: 1rem 1.4rem;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.025);
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .chip-container {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.6rem;
    }

    .param-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: #F4F4F7;
        border: 1px solid #EBEBED;
        padding: 0.35rem 0.85rem;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 500;
        color: #27272A;
    }

    .param-chip strong {
        color: #18181B;
        font-weight: 700;
    }

    /* 5. Terracotta Primary Buttons & Obsidian Download Buttons */
    .stButton > button {
        border-radius: 9999px !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
        padding: 0.62rem 1.8rem !important;
        border: none !important;
        background-color: #E0583B !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 14px rgba(224, 88, 59, 0.28) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }

    .stButton > button:hover {
        background-color: #D44A2D !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(224, 88, 59, 0.4) !important;
    }

    .stButton > button:active {
        transform: translateY(0px) !important;
    }

    .stDownloadButton > button {
        border-radius: 9999px !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        padding: 0.62rem 1.8rem !important;
        border: none !important;
        background-color: #18181B !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }

    .stDownloadButton > button:hover {
        background-color: #27272A !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.25) !important;
    }

    /* 6. Executive Metric Cards (Financial Dashboard Style) */
    .metric-card-modern {
        background: #FFFFFF !important;
        border: 1px solid #ECECEF !important;
        border-radius: 20px !important;
        padding: 1.3rem 1.1rem !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.03) !important;
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        position: relative;
        overflow: hidden;
    }

    .metric-card-modern:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.06) !important;
        border-color: #E2E2E6 !important;
    }

    .metric-header-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.6rem;
    }

    .metric-icon-circle {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background-color: #F7F7FA;
        border: 1px solid #EBEBED;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.95rem;
    }

    .metric-subbadge {
        font-size: 0.7rem;
        font-weight: 600;
        color: #E0583B;
        background: rgba(224, 88, 59, 0.08);
        padding: 0.15rem 0.55rem;
        border-radius: 9999px;
    }

    .metric-number {
        font-size: 2.1rem !important;
        font-weight: 800 !important;
        color: #18181B !important;
        line-height: 1.15 !important;
        letter-spacing: -0.03em !important;
        margin-bottom: 0.3rem !important;
    }

    .metric-title {
        font-size: 0.72rem !important;
        color: #71717A !important;
        text-transform: uppercase !important;
        letter-spacing: 0.07em !important;
        font-weight: 600 !important;
    }

    /* 7. Rounded Containers, DataTables & Inputs */
    [data-testid="stDataFrame"], [data-testid="stTable"], .stDataFrame {
        border-radius: 20px !important;
        overflow: hidden !important;
        border: 1px solid #ECECEF !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.03) !important;
        background-color: #FFFFFF !important;
    }

    div[data-testid="stExpander"], div[data-testid="stStatusWidget"], div[data-testid="stAlert"] {
        border-radius: 18px !important;
        border: 1px solid #ECECEF !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.02) !important;
        background-color: #FFFFFF !important;
    }

    /* Sidebar Form Controls */
    [data-testid="stSidebar"] [data-baseweb="select"],
    [data-testid="stSidebar"] [data-baseweb="input"],
    [data-testid="stSidebar"] .stTextInput input,
    .stTextInput input,
    [data-baseweb="select"] > div {
        border-radius: 12px !important;
        border: 1px solid #E2E2E6 !important;
        background-color: #FFFFFF !important;
        color: #18181B !important;
    }

    /* Checkbox & Radio Accents in Terracotta */
    [data-testid="stCheckbox"] [aria-checked="true"] {
        background-color: #E0583B !important;
        border-color: #E0583B !important;
    }

    /* Responsive Grid */
    @media (max-width: 992px) {
        .hero-title { font-size: 1.9rem !important; }
        [data-testid="column"] {
            min-width: 46% !important;
            flex: 1 1 46% !important;
            margin-bottom: 0.6rem !important;
        }
    }

    @media (max-width: 768px) {
        [data-testid="stAppViewContainer"] {
            display: flex !important;
            flex-direction: column !important;
        }
        [data-testid="stSidebar"] {
            position: relative !important;
            width: 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
            height: auto !important;
            border-right: none !important;
            border-bottom: 1px solid #ECECEF !important;
            box-shadow: none !important;
        }
        [data-testid="column"] {
            min-width: 100% !important;
            flex: 1 1 100% !important;
            margin-bottom: 0.6rem !important;
        }
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
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
    st.markdown("### 🧭 Search Filters")
    st.caption("Global directory pipeline powered by DuckDB & Overture Maps.")

    # 1. Geographic Location
    st.markdown("#### 1. Location Parameters")
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
        "State / Region",
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

    city_mode = st.radio("City Mode", ["Standard City List", "Custom City Input"], horizontal=True)

    if city_mode == "Standard City List" and cities_list:
        default_city_idx = 0
        if "Austin" in cities_list:
            default_city_idx = cities_list.index("Austin")
        elif "Toronto" in cities_list:
            default_city_idx = cities_list.index("Toronto")
        elif "London" in cities_list:
            default_city_idx = cities_list.index("London")

        selected_city = st.selectbox(
            "Target City",
            options=cities_list,
            index=default_city_idx,
            help="Major cities (pop > 15,000) within the selected region."
        )
    else:
        selected_city = st.text_input(
            "Target City",
            value=cities_list[0] if cities_list else "Austin",
            placeholder="e.g., Austin, Bhopal, Munich, Kyoto",
            help="Type any city or town name."
        )

    # Spatial Boundary Scope
    st.markdown("#### 2. Spatial Scope")
    scope_option = st.radio(
        "Boundary Radius",
        options=["Strict City Limits", "Include Metro / Suburbs (+20%)"],
        index=0,
        help="Strict limits restricts queries to municipal bounds. Metro expands bounds to capture surrounding suburbs."
    )
    buffer_ratio = 0.20 if "Metro" in scope_option else 0.0

    # 3. Category & Keyword Selector
    st.markdown("#### 3. Business Industry")
    select_all_cats = st.checkbox(
        "🌐 Extract All Categories (Full City)",
        value=False,
        help="Extract all commercial businesses across all industries inside the bounding box."
    )

    if select_all_cats:
        st.info("ℹ️ All 2,117 business categories enabled.")
        selected_categories: List[str] = []
        keyword_input = ""
    else:
        keyword_input = st.text_input(
            "🔍 Keyword Search (Clubbing)",
            value="",
            placeholder="e.g., restaurant, contractor, clinic",
            help="Wildcard search matching primary & alternate categories (e.g. 'restaurant' clubs thai_restaurant, italian_restaurant, etc.)."
        )

        default_cats = ["restaurant"] if not keyword_input and "restaurant" in all_categories else []
        selected_categories = st.multiselect(
            "📂 Multi-Select Categories",
            options=all_categories,
            default=default_cats,
            help="Stack multiple standardized categories at once (e.g. plumber + electrician)."
        )

    st.markdown("---")
    st.caption("⚡ **Zero API Keys**: DuckDB direct S3 Parquet streaming. Unlimited records.")


# ---------------- MAIN DASHBOARD HERO ----------------
# Build formatted location query string
formatted_location = loc_service.format_location_query(
    city=selected_city,
    state=selected_state if selected_state != "All Regions" else None,
    country=selected_country
)

# Determine Category Display Text
if select_all_cats:
    category_summary = "All Categories (Full City)"
    cat_slug_for_file = "all_categories"
elif keyword_input.strip() and selected_categories:
    category_summary = f"Keyword '{keyword_input.strip()}' + {len(selected_categories)} categories"
    cat_slug_for_file = f"{slugify(keyword_input)}_{slugify(selected_categories[0])}"
elif keyword_input.strip():
    category_summary = f"Keyword '{keyword_input.strip()}'"
    cat_slug_for_file = slugify(keyword_input)
elif selected_categories:
    category_summary = f"{', '.join(selected_categories[:2])}" + (f" (+{len(selected_categories)-2} more)" if len(selected_categories) > 2 else "")
    cat_slug_for_file = "_".join([slugify(c) for c in selected_categories[:2]])
else:
    category_summary = "All Categories"
    cat_slug_for_file = "all"

# Hero Header with Modern Warm Layout
st.markdown(f"""
<div class="hero-header">
    <div class="hero-title-group">
        <div class="hero-badge-row">
            <span class="hero-tag"><span class="dot-terracotta"></span> Cloud Parquet Engine</span>
            <span class="hero-tag"><span class="dot-green"></span> S3 Active</span>
            <span class="hero-tag">250+ Countries</span>
        </div>
        <h1 class="hero-title">Business Directory <span>Crawler</span></h1>
        <div class="hero-subtitle">High-speed geospatial business extraction directly from Overture Maps via DuckDB.</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Target Parameter Bar & Run Action
target_col_chips, target_col_btn = st.columns([3.6, 1.4])
with target_col_chips:
    st.markdown(f"""
    <div class="chip-container" style="padding-top: 0.35rem;">
        <span class="param-chip">📍 <strong>{formatted_location}</strong></span>
        <span class="param-chip">🏷️ <strong>{category_summary}</strong></span>
        <span class="param-chip">🎯 <strong>{'Metro (+20%)' if buffer_ratio > 0 else 'Strict Limits'}</strong></span>
    </div>
    """, unsafe_allow_html=True)

with target_col_btn:
    run_clicked = st.button("🚀 Extract Businesses →", type="primary", use_container_width=True)

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
        # Phase 1: Geocoding (Offline First)
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
                "Try enabling 'Include Metro / Suburbs (+20%)' or broadening your category criteria."
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


# ---------------- RESULTS PRESENTATION & METRIC CARDS ----------------
if st.session_state.global_places_df is not None and not st.session_state.global_places_df.empty:
    df = st.session_state.global_places_df
    meta = st.session_state.last_query_meta

    total_count = len(df)
    with_phone = df["phone"].apply(lambda x: len(str(x).strip()) > 3).sum()
    with_website = df["website"].apply(lambda x: len(str(x).strip()) > 3).sum()
    with_email = df["email"].apply(lambda x: len(str(x).strip()) > 3).sum()
    with_address = df["street_address"].apply(lambda x: len(str(x).strip()) > 0).sum()

    st.markdown("<br>", unsafe_allow_html=True)

    # 6 Modern Executive Metric Cards
    col1, col2, col3, col4, col5, col6 = st.columns(6)

    with col1:
        st.markdown(f"""
        <div class="metric-card-modern">
            <div class="metric-header-row">
                <span class="metric-icon-circle">🏢</span>
                <span class="metric-subbadge">100%</span>
            </div>
            <div class="metric-number">{total_count:,}</div>
            <div class="metric-title">Total Places</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        phone_pct = round((with_phone / total_count * 100), 1) if total_count > 0 else 0
        st.markdown(f"""
        <div class="metric-card-modern">
            <div class="metric-header-row">
                <span class="metric-icon-circle">📞</span>
                <span class="metric-subbadge">{phone_pct}%</span>
            </div>
            <div class="metric-number">{with_phone:,}</div>
            <div class="metric-title">Direct Phones</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        web_pct = round((with_website / total_count * 100), 1) if total_count > 0 else 0
        st.markdown(f"""
        <div class="metric-card-modern">
            <div class="metric-header-row">
                <span class="metric-icon-circle">🌐</span>
                <span class="metric-subbadge">{web_pct}%</span>
            </div>
            <div class="metric-number">{with_website:,}</div>
            <div class="metric-title">Websites</div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div class="metric-card-modern">
            <div class="metric-header-row">
                <span class="metric-icon-circle">✉️</span>
                <span class="metric-subbadge">Native</span>
            </div>
            <div class="metric-number">{with_email:,}</div>
            <div class="metric-title">Native Emails</div>
        </div>
        """, unsafe_allow_html=True)

    with col5:
        addr_pct = round((with_address / total_count * 100), 1) if total_count > 0 else 0
        st.markdown(f"""
        <div class="metric-card-modern">
            <div class="metric-header-row">
                <span class="metric-icon-circle">📍</span>
                <span class="metric-subbadge">{addr_pct}%</span>
            </div>
            <div class="metric-number">{with_address:,}</div>
            <div class="metric-title">Street Addresses</div>
        </div>
        """, unsafe_allow_html=True)

    with col6:
        st.markdown(f"""
        <div class="metric-card-modern">
            <div class="metric-header-row">
                <span class="metric-icon-circle">⚡</span>
                <span class="metric-subbadge">Cloud</span>
            </div>
            <div class="metric-number">{meta.get("duration", 0)}s</div>
            <div class="metric-title">Pipeline Time</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Tabs for Data View and Map View
    tab_data, tab_map = st.tabs(["📋 Directory Dataset", "🗺️ Geographic Map"])

    with tab_data:
        # Clean Filter Controls
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
            search_name = st.text_input("Filter by name", placeholder="Type business name...", label_visibility="collapsed")

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

        # CSV Download in Obsidian Pill Button
        csv_bytes = view_df[available_cols].to_csv(index=False).encode("utf-8")
        
        col_dl, col_blank = st.columns([2.5, 4])
        with col_dl:
            st.download_button(
                label=f"📥 Download Dataset ({export_filename})",
                data=csv_bytes,
                file_name=export_filename,
                mime="text/csv",
                type="primary",
                use_container_width=True
            )

    with tab_map:
        if "latitude" in df.columns and "longitude" in df.columns:
            map_data = df.dropna(subset=["latitude", "longitude"]).copy()
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
