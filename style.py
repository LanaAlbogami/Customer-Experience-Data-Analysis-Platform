"""
Shared theme for the Customer Experience Platform.
Import this in every page (app.py + every file inside pages/) so all four
members' screens look identical without copy-pasting CSS everywhere.

Usage, at the top of each page:
    from style import apply_theme, COLORS
    apply_theme()
"""

import streamlit as st

# ---- Color palette: Navy + Purple + Green (same as تصور_الموقع.html mockup) ----
COLORS = {
    "navy":         "#16213E",   # sidebar background, headings
    "navy_light":   "#22335C",   # sidebar hover
    "purple":       "#6C4AB6",   # primary / active state / buttons / links
    "purple_light": "#EFEAFA",   # soft highlight / info boxes
    "green":        "#2FA88E",   # success / positive KPI
    "green_light":  "#E4F6F1",
    "bg":           "#F5F6FA",   # page background
    "card":         "#FFFFFF",   # card background
    "text":         "#1E2233",   # main text
    "muted":        "#7A7F94",   # secondary text
    "border":       "#E7E8F1",
    "danger":       "#E0654F",   # negative KPI / errors
    "danger_light": "#FCEBE7",
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
            background-color: {COLORS['purple']};
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
            background-color: {COLORS['purple']};
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



def fix_sidebar_style():
    st.markdown(
        """
        <style>
        @import url(
            'https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;600;700;800&display=swap'
        );

        /* خلفية السايدبار */
        section[data-testid="stSidebar"] {
            background-color: #16213E !important;
            border: none !important;
        }

        section[data-testid="stSidebar"] > div {
            background-color: #16213E !important;
            direction: rtl !important;
        }

        /* مساحة محتوى السايدبار */
        section[data-testid="stSidebar"]
        [data-testid="stSidebarContent"] {
            padding: 20px 18px !important;
            direction: rtl !important;
        }

        /* قائمة الصفحات */
        section[data-testid="stSidebar"]
        [data-testid="stSidebarNav"] {
            direction: rtl !important;
        }

        section[data-testid="stSidebar"]
        [data-testid="stSidebarNav"] ul {
            gap: 8px !important;
        }

        /* رابط الصفحة */
        section[data-testid="stSidebar"]
        [data-testid="stSidebarNav"] a {
            min-height: 64px !important;
            width: 100% !important;

            padding: 14px 18px !important;
            margin: 0 0 7px 0 !important;

            border-radius: 13px !important;
            background-color: transparent !important;

            direction: rtl !important;
            text-align: right !important;

            color: #FFFFFF !important;
            text-decoration: none !important;
        }

        /* ترتيب الأيقونة والنص */
        section[data-testid="stSidebar"]
        [data-testid="stSidebarNav"] a > div {
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: flex-start !important;

            width: 100% !important;
            gap: 12px !important;

            direction: rtl !important;
        }

        /* نصوص القائمة */
        section[data-testid="stSidebar"]
        [data-testid="stSidebarNav"] a p {
            margin: 0 !important;

            color: #FFFFFF !important;
            font-family: "Tajawal", sans-serif !important;
            font-size: 16px !important;
            font-weight: 700 !important;

            line-height: 1.5 !important;
            text-align: right !important;
        }

        /* أيقونات Streamlit */
        section[data-testid="stSidebar"]
        span[data-testid="stIconMaterial"] {
            font-family: "Material Symbols Rounded" !important;
            font-size: 22px !important;
            font-weight: normal !important;
            font-style: normal !important;

            color: #FFFFFF !important;
            direction: ltr !important;
            text-align: center !important;

            flex-shrink: 0 !important;
        }

        /* الصفحة المختارة */
        section[data-testid="stSidebar"]
        [data-testid="stSidebarNav"]
        a[aria-current="page"] {
            background-color: #6C4AB6 !important;
            color: #FFFFFF !important;
        }

        section[data-testid="stSidebar"]
        [data-testid="stSidebarNav"]
        a[aria-current="page"] p,

        section[data-testid="stSidebar"]
        [data-testid="stSidebarNav"]
        a[aria-current="page"] span {
            color: #FFFFFF !important;
        }

        /* المرور بالماوس */
        section[data-testid="stSidebar"]
        [data-testid="stSidebarNav"] a:hover {
            background-color: #22335C !important;
            color: #FFFFFF !important;
        }

        /* الشعار */
        section[data-testid="stSidebar"]
        [data-testid="stLogo"] {
            margin-top: 10px !important;
            margin-bottom: 28px !important;
        }

        section[data-testid="stSidebar"]
        [data-testid="stLogo"] img {
            max-width: 185px !important;
            height: auto !important;
            object-fit: contain !important;
        }

        /* زر تصغير السايدبار */
        section[data-testid="stSidebar"]
        [data-testid="stSidebarCollapseButton"] button {
            color: #FFFFFF !important;
        }

        section[data-testid="stSidebar"]
        [data-testid="stSidebarCollapseButton"] svg {
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )