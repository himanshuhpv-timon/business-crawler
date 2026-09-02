"""
app.py - High-Performance Global Business Directory Extractor
Features global cascading location selectors, multi-city extraction,
select-all-cities mode, multi-category stacking, keyword clubbing,
offline 0ms geocoding, real-time keystroke filtering, and unlimited record extraction.
Styled with a high-contrast Neo-Minimalist Black & Electric Yellow aesthetic on Pure White.
"""

import logging
import re
import time
from typing import List, Optional, Tuple
import pandas as pd
import streamlit as st

# Real-time keystroke search
try:
    from st_keyup import st_keyup
except ImportError:
    st_keyup = None

# Import local engines
from geocoder import geocode_location_details
from location_service import get_location_service
from overture_fetcher import fetch_overture_places

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("global_extractor_app")

# Page Configuration
st.set_page_config(
    page_title="Business Directory Crawler",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="auto"
)

# Custom CSS for Pure White Canvas + Jet Black & Electric Yellow Accents
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

    /* 1. Global Typography: Target text elements, NEVER override icon fonts */
    html, body, p, h1, h2, h3, h4, h5, h6, label, input, button, select, textarea {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
    }

    /* Protect Streamlit icon ligatures from font corruption */
    [data-testid*="Icon"], .material-symbols-rounded, .material-icons, [data-testid="stStatusWidget"] svg, [data-testid="stExpander"] svg {
        font-family: 'Material Symbols Rounded', 'Material Icons' !important;
    }

    /* Pure White Canvas */
    body, [data-testid="stAppViewContainer"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }

    h1, h2, h3, h4, h5, h6 {
        font-weight: 800 !important;
        color: #000000 !important;
        letter-spacing: -0.03em !important;
    }

    /* 2. Transparent Header to preserve mobile sidebar toggle */
    header[data-testid="stHeader"] {
        background: transparent !important;
        color: transparent !important;
        height: 2.8rem !important;
        z-index: 99999 !important;
    }
    header [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    #MainMenu,
    footer,
    [data-testid="manage-app-button"],
    .viewerBadge_container__1QSob {
        display: none !important;
        visibility: hidden !important;
    }

    /* Desktop View (>= 769px): Permanently Open Static Sidebar */
    @media (min-width: 769px) {
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
            border-right: 1.5px solid #F3F4F6 !important;
            box-shadow: 4px 0 20px rgba(0, 0, 0, 0.02) !important;
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
    }

    /* 3. Hero Header Section */
    .hero-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 1rem;
        margin-bottom: 1.6rem;
    }

    .hero-title-group {
        display: flex;
        flex-direction: column;
    }

    .hero-badge-row {
        display: flex;
        align-items: center;
        gap: 0.6rem;
        margin-bottom: 0.5rem;
    }

    .hero-tag {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        background: #000000 !important;
        color: #FFFFFF !important;
        padding: 0.28rem 0.8rem;
        border-radius: 9999px;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.03em;
    }

    .hero-tag * {
        color: #FFFFFF !important;
    }

    .hero-tag .dot-yellow {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background-color: #FFE600 !important;
    }

    .hero-tag-outline {
        display: inline-flex;
        align-items: center;
        border: 1.5px solid #E5E7EB;
        background: #FFFFFF;
        padding: 0.28rem 0.8rem;
        border-radius: 9999px;
        font-size: 0.74rem;
        font-weight: 700;
        color: #000000;
    }

    .hero-title {
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        color: #000000 !important;
        letter-spacing: -0.04em !important;
        line-height: 1.15 !important;
        margin: 0 !important;
    }

    .hero-title .highlight-yellow {
        background-color: #FFE600 !important;
        color: #000000 !important;
        padding: 0.1rem 0.6rem !important;
        border-radius: 8px !important;
        display: inline-block !important;
    }

    .hero-subtitle {
        font-size: 1.05rem !important;
        color: #6B7280 !important;
        margin-top: 0.4rem !important;
        font-weight: 500 !important;
    }

    /* 4. Target Parameter Bar */
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
        background: #F9FAFB;
        border: 1.5px solid #E5E7EB;
        padding: 0.4rem 0.95rem;
        border-radius: 9999px;
        font-size: 0.84rem;
        font-weight: 600;
        color: #000000;
    }

    .param-chip strong {
        color: #000000;
        font-weight: 800;
    }

    /* 5. High-Impact Action Buttons: Strictly Force Bright Visible Text */
    .stButton > button {
        border-radius: 9999px !important;
        font-weight: 800 !important;
        font-size: 0.95rem !important;
        padding: 0.68rem 1.9rem !important;
        border: 2px solid #000000 !important;
        background-color: #FFE600 !important;
        color: #000000 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    }

    .stButton > button * {
        color: #000000 !important;
        font-weight: 800 !important;
    }

    .stButton > button:hover {
        background-color: #000000 !important;
        color: #FFE600 !important;
        border-color: #000000 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2) !important;
    }

    .stButton > button:hover * {
        color: #FFE600 !important;
        font-weight: 800 !important;
    }

    /* Sidebar Category Suggestion Pills */
    [data-testid="stSidebar"] div[data-testid="column"] .stButton > button {
        border-radius: 9999px !important;
        font-size: 0.74rem !important;
        font-weight: 700 !important;
        padding: 0.22rem 0.55rem !important;
        min-height: 28px !important;
        height: auto !important;
        border: 1.5px solid #000000 !important;
        background-color: #FFFFFF !important;
        color: #000000 !important;
        box-shadow: none !important;
        white-space: nowrap !important;
        margin-bottom: 0.35rem !important;
    }

    [data-testid="stSidebar"] div[data-testid="column"] .stButton > button * {
        font-size: 0.74rem !important;
        color: #000000 !important;
        font-weight: 700 !important;
    }

    [data-testid="stSidebar"] div[data-testid="column"] .stButton > button:hover {
        background-color: #FFE600 !important;
        color: #000000 !important;
        border-color: #000000 !important;
        transform: translateY(-1px) !important;
    }

    [data-testid="stSidebar"] div[data-testid="column"] .stButton > button:hover * {
        color: #000000 !important;
    }

    /* Bottom Download Button with Ample Sizing and High Contrast */
    .stDownloadButton > button {
        border-radius: 9999px !important;
        font-weight: 800 !important;
        font-size: 0.95rem !important;
        padding: 0.72rem 2.2rem !important;
        border: 2px solid #000000 !important;
        background-color: #000000 !important;
        color: #FFE600 !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        white-space: nowrap !important;
    }

    .stDownloadButton > button * {
        color: #FFE600 !important;
        font-weight: 800 !important;
        white-space: nowrap !important;
    }

    .stDownloadButton > button:hover {
        background-color: #FFE600 !important;
        color: #000000 !important;
        border-color: #000000 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 22px rgba(0, 0, 0, 0.2) !important;
    }

    .stDownloadButton > button:hover * {
        color: #000000 !important;
        font-weight: 800 !important;
    }

    /* 6. Clean Single-Line Metric Cards */
    .metric-card-modern {
        background: #FFFFFF !important;
        border: 1.5px solid #E5E7EB !important;
        border-radius: 18px !important;
        padding: 1.15rem 0.85rem !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03) !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        position: relative;
        overflow: hidden;
    }

    .metric-card-modern:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 24px rgba(0, 0, 0, 0.06) !important;
        border-color: #000000 !important;
    }

    .metric-header-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 0.5rem;
    }

    .metric-icon-circle {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        background-color: #000000 !important;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-size: 0.95rem;
    }

    .metric-icon-circle * {
        color: #FFE600 !important;
    }

    .metric-subbadge {
        font-size: 0.72rem;
        font-weight: 800;
        color: #000000 !important;
        background: #FFE600 !important;
        padding: 0.15rem 0.55rem;
        border-radius: 9999px;
        letter-spacing: 0.02em;
    }

    /* Metric Numbers: Strictly 1 line, zero wrapping */
    .metric-number {
        font-size: clamp(1.2rem, 1.6vw, 1.7rem) !important;
        font-weight: 800 !important;
        color: #000000 !important;
        line-height: 1.15 !important;
        letter-spacing: -0.02em !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        margin-bottom: 0.25rem !important;
    }

    .metric-title {
        font-size: 0.69rem !important;
        color: #4B5563 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        font-weight: 700 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
    }

    /* 7. Result Banner: Bright White & Yellow Text on Solid Black */
    .result-banner {
        background: #000000 !important;
        color: #FFFFFF !important;
        border-radius: 14px;
        padding: 0.85rem 1.4rem;
        display: flex;
        align-items: center;
        gap: 0.85rem;
        font-size: 0.95rem;
        margin-top: 0.5rem;
        margin-bottom: 1.3rem;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
    }

    .result-banner * {
        color: #FFFFFF !important;
    }

    .result-banner strong {
        color: #FFE600 !important;
        font-weight: 800 !important;
    }

    .result-banner .banner-badge {
        background: #FFE600 !important;
        color: #000000 !important;
        font-weight: 800 !important;
        font-size: 0.74rem;
        padding: 0.22rem 0.7rem;
        border-radius: 9999px;
        letter-spacing: 0.05em;
    }

    /* 8. Controls & Inputs */
    [data-testid="stSidebar"] [data-baseweb="select"],
    [data-testid="stSidebar"] [data-baseweb="input"],
    [data-testid="stSidebar"] .stTextInput input,
    .stTextInput input,
    [data-baseweb="select"] > div {
        border-radius: 12px !important;
        border: 1.5px solid #E5E7EB !important;
        background-color: #FFFFFF !important;
        color: #000000 !important;
        font-weight: 500 !important;
    }

    [data-testid="stSidebar"] [data-baseweb="select"]:focus-within,
    [data-testid="stSidebar"] .stTextInput input:focus,
    .stTextInput input:focus {
        border-color: #000000 !important;
        box-shadow: 0 0 0 3px rgba(255, 230, 0, 0.3) !important;
    }

    /* Dataframe & Tables */
    [data-testid="stDataFrame"], [data-testid="stTable"], .stDataFrame {
        border-radius: 18px !important;
        overflow: hidden !important;
        border: 1.5px solid #E5E7EB !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03) !important;
        background-color: #FFFFFF !important;
    }

    /* Responsive Grid */
    @media (max-width: 992px) {
        .hero-title { font-size: 2rem !important; }
        [data-testid="column"] {
            min-width: 46% !important;
            flex: 1 1 46% !important;
            margin-bottom: 0.6rem !important;
        }
    }

    @media (max-width: 768px) {
        /* Mobile: Show sleek floating Filters button */
        [data-testid="collapsedControl"] {
            display: inline-flex !important;
            visibility: visible !important;
            pointer-events: auto !important;
            position: fixed !important;
            top: 0.85rem !important;
            left: 0.85rem !important;
            z-index: 999999 !important;
            background-color: #000000 !important;
            color: #FFE600 !important;
            border: 2px solid #000000 !important;
            border-radius: 9999px !important;
            box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25) !important;
            padding: 0.35rem 0.85rem !important;
            align-items: center !important;
            gap: 0.3rem !important;
        }

        [data-testid="collapsedControl"] button {
            background: transparent !important;
            color: #FFE600 !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 !important;
            display: inline-flex !important;
            align-items: center !important;
        }

        [data-testid="collapsedControl"] svg {
            color: #FFE600 !important;
            fill: #FFE600 !important;
        }

        [data-testid="collapsedControl"] button::after {
            content: " Filters";
            font-weight: 800;
            font-size: 0.82rem;
            color: #FFE600 !important;
            margin-left: 0.35rem;
        }

        /* Show drawer close button inside sidebar on mobile */
        [data-testid="stSidebarCollapseButton"],
        button[data-testid="stSidebarCollapseButton"],
        [data-testid="stSidebarHeader"] button {
            display: flex !important;
            visibility: visible !important;
            pointer-events: auto !important;
            background-color: #F3F4F6 !important;
            color: #000000 !important;
            border-radius: 9999px !important;
        }

        /* Mobile: When sidebar is collapsed, slide 100% off screen (Zero peeking) */
        section[data-testid="stSidebar"][aria-expanded="false"] {
            transform: translateX(-100vw) !important;
            visibility: hidden !important;
            pointer-events: none !important;
            display: none !important;
        }

        /* Mobile: When sidebar is expanded, smoothly overlay as a drawer */
        section[data-testid="stSidebar"][aria-expanded="true"] {
            display: block !important;
            visibility: visible !important;
            pointer-events: auto !important;
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            height: 100vh !important;
            width: 85vw !important;
            max-width: 350px !important;
            min-width: 260px !important;
            transform: none !important;
            margin-left: 0 !important;
            z-index: 9999999 !important;
            box-shadow: 10px 0 40px rgba(0, 0, 0, 0.35) !important;
            background-color: #FFFFFF !important;
            overflow-y: auto !important;
        }

        /* Metric Cards: Clean 2-column grid on phones */
        [data-testid="column"]:has(.metric-card-modern) {
            min-width: calc(50% - 0.4rem) !important;
            max-width: calc(50% - 0.4rem) !important;
            flex: 1 1 calc(50% - 0.4rem) !important;
            margin-bottom: 0.4rem !important;
        }

        .metric-card-modern {
            padding: 0.85rem 0.65rem !important;
        }

        .metric-number {
            font-size: 1.35rem !important;
        }

        /* Mobile Action Buttons: Full width for easy thumb tapping */
        .stButton > button,
        .stDownloadButton > button {
            width: 100% !important;
            text-align: center !important;
            justify-content: center !important;
        }

        .hero-title {
            font-size: 1.85rem !important;
            line-height: 1.2 !important;
        }

        .hero-subtitle {
            font-size: 0.88rem !important;
        }

        .block-container {
            padding-top: 4.2rem !important;
            padding-left: 0.9rem !important;
            padding-right: 0.9rem !important;
        }

        /* Hide bottom badges/watermark on mobile */
        [data-testid="manage-app-button"],
        .viewerBadge_container__1QSob {
            display: none !important;
            visibility: hidden !important;
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
    """Caches places streaming queries for a bbox and category."""
    cat_list = list(categories_tuple) if categories_tuple else None
    kw = keyword.strip() if keyword else None
    return fetch_overture_places(
        bbox=bbox,
        categories=cat_list,
        keyword=kw,
        all_categories=all_categories,
        limit=None
    )


# ---------------- SIDEBAR: LOCATION & INDUSTRY CONFIGURATION ----------------
with st.sidebar:
    st.markdown("### 🧭 Search Filters")

    # 1. Geographic Location
    st.markdown("#### 1. Geographic Location")
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

    # 2. City Selection: Select All Cities or Multiple Cities
    cities_list = loc_service.get_cities_for_state(
        country_name=selected_country,
        state_name=selected_state,
        state_to_code=state_code_map
    )

    st.markdown("#### 2. City Selection")
    select_all_cities = st.checkbox(
        f"⚡ Select All Cities in {selected_state} ({len(cities_list)} cities)",
        value=False,
        help=f"Extract businesses across all {len(cities_list)} major cities in {selected_state}."
    )

    if select_all_cities:
        selected_cities = cities_list
        st.info(f"ℹ️ All **{len(cities_list)}** cities in **{selected_state}** selected.")
    else:
        default_city_selection = []
        if "Austin" in cities_list:
            default_city_selection = ["Austin"]
        elif "Bhopal" in cities_list:
            default_city_selection = ["Bhopal"]
        elif "Toronto" in cities_list:
            default_city_selection = ["Toronto"]
        elif "London" in cities_list:
            default_city_selection = ["London"]
        elif cities_list:
            default_city_selection = [cities_list[0]]

        selected_cities = st.multiselect(
            "Select Cities (Single or Multiple)",
            options=cities_list,
            default=default_city_selection,
            help="Choose one or more cities to extract simultaneously."
        )

    # Spatial Boundary Scope
    st.markdown("#### 3. Boundary Scope")
    scope_option = st.radio(
        "Coverage Area",
        options=["Strict City Limits", "Include Metro / Suburbs (+20%)"],
        index=0,
        help="Strict limits restricts queries to municipal bounds. Metro expands bounds to capture suburbs."
    )
    buffer_ratio = 0.20 if "Metro" in scope_option else 0.0

    # 4. Business Industry (3 Dedicated Sections)
    st.markdown("#### 4. Business Industry")

    # Section 1: All Categories
    st.markdown("##### 1. All Categories")
    select_all_cats = st.checkbox(
        "⚡ Extract All Categories (Full City Directory)",
        value=False,
        help="Extract all commercial businesses across all industries inside the bounding box."
    )

    if select_all_cats:
        st.info("ℹ️ Complete directory extraction enabled across all 2,117 business categories.")
        selected_categories: List[str] = []
        keyword_input = ""
    else:
        # Section 2: Primary Category Selector (Multiple)
        st.markdown("##### 2. Primary Category Selector (Multiple)")
        if "primary_categories_selection" not in st.session_state:
            st.session_state.primary_categories_selection = ["restaurant"] if "restaurant" in all_categories else []

        selected_primary = st.multiselect(
            "Select specific primary categories:",
            options=all_categories,
            default=st.session_state.primary_categories_selection,
            help="Choose one or more specific standard categories (e.g. dentist, auto_repair_shop)."
        )

        # Section 3: Keyword Search (Clubbed Categories)
        st.markdown("##### 3. Keyword Search (Clubbed Categories)")
        keyword_input = ""
        if st_keyup is not None:
            try:
                keyword_input = st_keyup(
                    label="Search generic keyword to club related categories:",
                    value="",
                    placeholder="e.g., restaurant, contractor, clinic, dental",
                    debounce=150,
                    key="keyword_search_clubbing"
                )
            except Exception:
                keyword_input = st.text_input(
                    "Search generic keyword to club related categories:",
                    value="",
                    placeholder="e.g., restaurant, contractor, clinic, dental"
                )
        else:
            keyword_input = st.text_input(
                "Search generic keyword to club related categories:",
                value="",
                placeholder="e.g., restaurant, contractor, clinic, dental"
            )

        # Ongoing Evaluation: If a generic term is searched, take ALL matching primary categories
        clubbed_categories: List[str] = []
        if keyword_input and keyword_input.strip():
            kw_clean = keyword_input.strip().lower()
            matching_primary = [c for c in all_categories if kw_clean in c.lower()]
            exact = [c for c in matching_primary if c.lower() == kw_clean]
            starts = [c for c in matching_primary if c.lower().startswith(kw_clean) and c not in exact]
            contains = [c for c in matching_primary if c not in exact and c not in starts]
            sorted_matches = exact + starts + contains

            if sorted_matches:
                st.caption(f"💡 Found **{len(sorted_matches)}** matching primary categories (all automatically taken):")
                clubbed_categories = st.multiselect(
                    f"Clubbed categories for '{keyword_input.strip()}':",
                    options=sorted_matches,
                    default=sorted_matches,
                    help="All primary categories matching your generic term are automatically included. You can inspect or refine them here."
                )
            else:
                st.info(f"ℹ️ Generic search: All records matching '{keyword_input.strip()}' will be clubbed during extraction.")

        # Unified Categories: Combine specific primary selections with all taken clubbed categories
        combined = list(dict.fromkeys(selected_primary + clubbed_categories))
        selected_categories = combined


# ---------------- MAIN DASHBOARD HERO ----------------
# Build formatted location label
if not selected_cities:
    location_summary = f"{selected_state}, {selected_country}"
    cat_city_slug = "all_cities"
elif len(selected_cities) == 1:
    location_summary = f"{selected_cities[0]}, {selected_state}, {selected_country}"
    cat_city_slug = slugify(selected_cities[0])
elif select_all_cities:
    location_summary = f"All {len(selected_cities)} Cities in {selected_state}, {selected_country}"
    cat_city_slug = f"all_cities_{slugify(selected_state)}"
else:
    location_summary = f"{len(selected_cities)} Cities ({', '.join(selected_cities[:2])}...) in {selected_state}"
    cat_city_slug = f"{len(selected_cities)}_cities_{slugify(selected_state)}"

# Determine Category Display Text
if select_all_cats:
    category_summary = "All Categories (Full Directory)"
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

# Hero Header: Independent & Proprietary Look
st.markdown(f"""
<div class="hero-header">
    <div class="hero-title-group">
        <div class="hero-badge-row">
            <span class="hero-tag"><span class="dot-yellow"></span> Live Directory</span>
            <span class="hero-tag-outline">250+ Countries</span>
            <span class="hero-tag-outline">Global Coverage</span>
        </div>
        <h1 class="hero-title">Business Directory <span class="highlight-yellow">Crawler</span></h1>
        <div class="hero-subtitle">High-speed global business directory extraction with phone numbers, websites, emails, and physical addresses.</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Target Parameter Chips & Run Action (Aligned perfectly on Laptop & Mobile)
st.markdown(f"""
<div class="chip-container" style="margin-top: 0.4rem; margin-bottom: 0.85rem;">
    <span class="param-chip">📍 <strong>{location_summary}</strong></span>
    <span class="param-chip">🏷️ <strong>{category_summary}</strong></span>
    <span class="param-chip">🎯 <strong>{'Metro (+20%)' if buffer_ratio > 0 else 'Strict Limits'}</strong></span>
</div>
""", unsafe_allow_html=True)

run_clicked = st.button("⚡ Extract Businesses →", type="primary", use_container_width=True)

# Session State Persistence
if "global_places_df" not in st.session_state:
    st.session_state.global_places_df = None
if "last_query_meta" not in st.session_state:
    st.session_state.last_query_meta = {}


# ---------------- STREAMLINED MULTI-CITY PIPELINE ----------------
if run_clicked:
    if not selected_cities:
        st.error("Please select at least one target city in the sidebar.")
        st.stop()

    start_time = time.time()
    
    # Clean progress container
    progress_placeholder = st.empty()
    status_box = progress_placeholder.status(f"Resolving boundaries for {len(selected_cities)} city/cities...", expanded=True)

    try:
        # Phase 1: Multi-City Coordinate Resolution (Offline First)
        city_bboxes = []
        center_lat = 0.0
        center_lon = 0.0

        if len(selected_cities) == 1:
            c = selected_cities[0]
            loc_query = loc_service.format_location_query(city=c, state=selected_state, country=selected_country)
            status_box.write(f"📍 **Phase 1: Resolving coordinates for '{c}'...**")
            loc_details = cached_geocode_location(loc_query, buffer_ratio=buffer_ratio)
            bbox = loc_details["bounding_box"]
            display_address = loc_details["display_name"]
            center_lat = loc_details["latitude"]
            center_lon = loc_details["longitude"]
        else:
            status_box.write(f"📍 **Phase 1: Computing enclosing boundary for {len(selected_cities)} cities...**")
            for c in selected_cities:
                c_query = loc_service.format_location_query(city=c, state=selected_state, country=selected_country)
                c_details = cached_geocode_location(c_query, buffer_ratio=buffer_ratio)
                city_bboxes.append(c_details["bounding_box"])

            min_lon = min(b[0] for b in city_bboxes)
            min_lat = min(b[1] for b in city_bboxes)
            max_lon = max(b[2] for b in city_bboxes)
            max_lat = max(b[3] for b in city_bboxes)
            bbox = (round(min_lon, 4), round(min_lat, 4), round(max_lon, 4), round(max_lat, 4))
            display_address = f"{len(selected_cities)} Cities in {selected_state}, {selected_country}"
            center_lat = round((min_lat + max_lat) / 2.0, 4)
            center_lon = round((min_lon + max_lon) / 2.0, 4)

        status_box.write(
            f"✅ **Location Resolved**: `{display_address}`\n\n"
            f"📐 **Bounding Box**: `[{bbox[0]:.4f}, {bbox[1]:.4f}, {bbox[2]:.4f}, {bbox[3]:.4f}]`"
        )

        # Phase 2: Places Streaming
        status_box.write(f"⚡ **Phase 2: Extracting verified business records ({category_summary})...**")
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
            progress_placeholder.empty()
            st.warning(
                f"No businesses found in **{display_address}** for **{category_summary}**. "
                "Try enabling 'Include Metro / Suburbs (+20%)' or selecting additional categories."
            )
            st.session_state.global_places_df = None
            st.stop()

        # High-contrast Black & Yellow Completion Banner (Zero broken icon ligatures)
        progress_placeholder.empty()
        st.markdown(f"""
        <div class="result-banner">
            <span class="banner-badge">COMPLETED</span>
            <span>Successfully extracted <strong>{total_extracted:,}</strong> businesses across <strong>{display_address}</strong> in <strong>{total_time}s</strong></span>
        </div>
        """, unsafe_allow_html=True)

        # Persist results to session
        st.session_state.global_places_df = places_df
        st.session_state.last_query_meta = {
            "country": selected_country,
            "state": selected_state,
            "city_slug": cat_city_slug,
            "location_label": display_address,
            "category_label": category_summary,
            "cat_slug": cat_slug_for_file,
            "total": total_extracted,
            "duration": total_time,
            "display_name": display_address,
            "center_lat": center_lat,
            "center_lon": center_lon,
        }

    except Exception as e:
        progress_placeholder.empty()
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

    # 6 Modern Metric Cards (Single-line numbers, zero wrapping)
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
                <span class="metric-subbadge">Fast</span>
            </div>
            <div class="metric-number">{meta.get("duration", 0)}s</div>
            <div class="metric-title">Pipeline Time</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Standard Export File Naming: {country}_{state}_{city_slug}_{category}.csv
    filename_country = slugify(meta.get("country", "country"))
    filename_state = slugify(meta.get("state", "state"))
    filename_city = slugify(meta.get("city_slug", "directory"))
    filename_cat = slugify(meta.get("cat_slug", "all"))
    export_filename = f"{filename_country}_{filename_state}_{filename_city}_{filename_cat}.csv"

    # Display Columns
    display_columns = [
        "name", "category", "phone", "website", "email",
        "street_address", "locality", "postcode", "region", "country"
    ]
    available_cols = [c for c in display_columns if c in df.columns]

    # Tabs for Data View and Map View
    tab_data, tab_map = st.tabs(["📋 Directory Dataset", "🗺️ Geographic Map"])

    with tab_data:
        # Real-Time Keystroke Search Box (filters on every letter typed)
        search_name = ""
        if st_keyup is not None:
            try:
                search_name = st_keyup(
                    label="Search business name",
                    placeholder="🔍 Search businesses in real-time (type to filter instantly without pressing Enter)...",
                    debounce=150,
                    key="realtime_keystroke_search",
                    label_visibility="collapsed"
                )
            except Exception:
                search_name = st.text_input(
                    "Filter dataset by name",
                    placeholder="🔍 Search businesses in real-time...",
                    label_visibility="collapsed"
                )
        else:
            search_name = st.text_input(
                "Filter dataset by name",
                placeholder="🔍 Search businesses in real-time...",
                label_visibility="collapsed"
            )

        # Filters Row
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            filt_phone = st.checkbox("Only with Phone", value=False)
        with f_col2:
            filt_website = st.checkbox("Only with Website", value=False)
        with f_col3:
            filt_email = st.checkbox("Only with Email", value=False)
        with f_col4:
            filt_addr = st.checkbox("Only with Address", value=False)

        # Apply Real-Time Table Filters
        view_df = df.copy()
        if filt_phone:
            view_df = view_df[view_df["phone"].str.strip().str.len() > 3]
        if filt_website:
            view_df = view_df[view_df["website"].str.strip().str.len() > 3]
        if filt_email:
            view_df = view_df[view_df["email"].str.strip().str.len() > 3]
        if filt_addr:
            view_df = view_df[view_df["street_address"].str.strip().str.len() > 0]
        if search_name and search_name.strip():
            view_df = view_df[view_df["name"].str.contains(search_name.strip(), case=False, na=False)]

        csv_bytes = view_df[available_cols].to_csv(index=False).encode("utf-8")

        st.caption(f"Displaying **{len(view_df):,}** of **{total_count:,}** extracted businesses")

        # Interactive Dataframe
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

        st.markdown("<br>", unsafe_allow_html=True)

        # Bottom Download Button with Ample Width (Never truncated)
        b_col_dl, b_col_spacer = st.columns([1.2, 1.0])
        with b_col_dl:
            st.download_button(
                label=f"📥 Download Dataset ({len(view_df):,} Records)",
                data=csv_bytes,
                file_name=export_filename,
                mime="text/csv",
                key="bottom_download_csv_btn",
                use_container_width=True
            )

    with tab_map:
        if "latitude" in df.columns and "longitude" in df.columns:
            map_data = df.dropna(subset=["latitude", "longitude"]).copy()
            map_data["latitude"] = pd.to_numeric(map_data["latitude"], errors="coerce")
            map_data["longitude"] = pd.to_numeric(map_data["longitude"], errors="coerce")
            map_data = map_data.dropna(subset=["latitude", "longitude"])

            if not map_data.empty:
                st.caption(f"Displaying **{len(map_data):,}** geographic points across {meta.get('location_label', 'selected area')}:")
                st.map(map_data, latitude="latitude", longitude="longitude", size=18)
            else:
                st.info("No valid coordinates available to map.")
        else:
            st.info("Coordinates not present in dataset.")
