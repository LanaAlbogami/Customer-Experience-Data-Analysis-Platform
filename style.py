"""
Shared theme for the Customer Experience Platform.
Import this in every page (app.py + every file inside pages/) so all four
members' screens look identical without copy-pasting CSS everywhere.

Usage, at the top of each page:
    from style import apply_theme, COLORS
    apply_theme()
"""

import streamlit as st

# ---- Color palette: Navy + Orange + Green (inspired by the SDAIA look) ----
COLORS = {
    "navy":         "#0F2C4C",   # sidebar background, headings
    "navy_light":   "#1F3F63",   # sidebar hover
    "orange":       "#E8871E",   # primary / active state / buttons / links
    "orange_light": "#FDEEDC",   # soft highlight / info boxes
    "green":        "#1F9D55",   # success / positive KPI
    "green_light":  "#E3F6EA",
    "bg":           "#F5F6FA",   # page background
    "card":         "#FFFFFF",   # card background
    "text":         "#1E2233",   # main text
    "muted":        "#7A7F94",   # secondary text
    "border":       "#E7E8F1",
    "danger":       "#D64545",   # negative KPI / errors
    "danger_light": "#FBE4E4",
}


def apply_theme():
    """Call once at the top of every page (after st.set_page_config)."""
    st.markdown(
        f"""
        <style>
        /* ---- Sidebar ---- */
        section[data-testid="stSidebar"] {{
            background-color: {COLORS['navy']};
            width: 21rem;               /* Streamlit's default sidebar width — keep it the same on every page */
        }}
        section[data-testid="stSidebar"] * {{
            color: #C4C9E0;
        }}
        /* Sidebar page links (auto-generated from the pages/ folder) */
        section[data-testid="stSidebarNav"] a {{
            border-radius: 10px;
            padding: 8px 10px;
            font-weight: 600;
            font-size: 14px;
        }}
        section[data-testid="stSidebarNav"] a:hover {{
            background-color: {COLORS['navy_light']};
        }}
        section[data-testid="stSidebarNav"] a[aria-current="page"] {{
            background-color: {COLORS['orange']};
            color: #FFFFFF !important;
        }}

        /* ---- Cards / KPI containers ---- */
        div[data-testid="stMetric"], .kpi-card {{
            background-color: {COLORS['card']};
            border: 1px solid {COLORS['border']};
            border-radius: 12px;
            padding: 16px 18px;
        }}

        /* ---- Buttons ---- */
        .stButton > button {{
            background-color: {COLORS['orange']};
            color: #FFFFFF;
            border-radius: 8px;
            border: none;
            font-weight: 600;
        }}
        .stButton > button:hover {{
            background-color: {COLORS['navy_light']};
        }}

        /* ---- App background ---- */
        .stApp {{
            background-color: {COLORS['bg']};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
