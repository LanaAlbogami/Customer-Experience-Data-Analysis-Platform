# -*- coding: utf-8 -*-

# Application entry point.

import base64
from pathlib import Path
import sys

import streamlit as st

import app_mode
from style import COLORS


# ==================================================
# Import paths
# ==================================================

_INDIVIDUALS_DIR = str(Path(__file__).parent / "Individuals")

if _INDIVIDUALS_DIR not in sys.path:
    sys.path.insert(0, _INDIVIDUALS_DIR)


_DEPARTMENTS_DIR = str(Path(__file__).parent / "Departments")

if _DEPARTMENTS_DIR not in sys.path:
    sys.path.insert(0, _DEPARTMENTS_DIR)


_INITIATIVES_DIR = str(Path(__file__).parent / "Initiatives")

if _INITIATIVES_DIR not in sys.path:
    sys.path.insert(0, _INITIATIVES_DIR)


# ==================================================
# Landing colours
# ==================================================

BG = COLORS["navy"]
CARD_HOVER = COLORS["navy_light"]

CARD_BG = "#1F2C4C"
ICON_COLOR = "#3A4A72"
LABEL_COLOR = "#E7EAF3"


LOGO_FILE = Path(__file__).parent / "LogoWhite_cropped.png"


def _logo_data_uri():

    try:
        data = base64.b64encode(
            LOGO_FILE.read_bytes()
        ).decode()

        return f"data:image/png;base64,{data}"

    except Exception:
        return ""


# ==================================================
# Landing page
# ==================================================

def show_landing():

    st.set_page_config(
        page_title="منصة تحليل تجربة العملاء",
        layout="wide",
    )

    chosen = st.query_params.get("mode")

    if chosen in (
        "departments",
        "individuals",
        "initiatives",
    ):

        app_mode.set_mode(chosen)

        # تنظيف حالة التوقل القديمة
        st.session_state.pop(
            "mode_switch",
            None,
        )

        st.query_params.clear()

        st.rerun()


    logo = _logo_data_uri()

    logo_html = (
        f'<img src="{logo}" '
        f'style="height:clamp(72px,13vh,120px);">'
        if logo
        else ""
    )


    # ==================================================
    # Icons
    # ==================================================

    building_svg = (
        f'<svg viewBox="0 0 24 24" fill="{ICON_COLOR}" '
        'style="width:clamp(56px,11vh,92px);'
        'height:clamp(56px,11vh,92px);" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<path d="M3 21V9l5-2v14H3zm6 0V4l5 3v14H9zm6 0V11l5 3v7h-5z'
        'M5 12h1v1H5v-1zm0 3h1v1H5v-1zm6-5h1v1h-1v-1zm0 3h1v1h-1v-1z'
        'm0 3h1v1h-1v-1zm6 0h1v1h-1v-1z"/></svg>'
    )


    person_svg = (
        f'<svg viewBox="0 0 24 24" fill="{ICON_COLOR}" '
        'style="width:clamp(56px,11vh,92px);'
        'height:clamp(56px,11vh,92px);" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<circle cx="12" cy="8" r="4.5"/>'
        '<path d="M3.5 20c0-4.2 3.8-6.5 8.5-6.5'
        's8.5 2.3 8.5 6.5v.5h-17V20z"/></svg>'
    )


    initiative_svg = (
        f'<svg viewBox="0 0 24 24" fill="{ICON_COLOR}" '
        'style="width:clamp(56px,11vh,92px);'
        'height:clamp(56px,11vh,92px);" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<path d="M12 2a7 7 0 0 0-4 12.74V18'
        'h8v-3.26A7 7 0 0 0 12 2zm2.85 11.1'
        '-.85.6V16h-4v-2.3l-.85-.6'
        'A5 5 0 1 1 14.85 13.1z"/>'
        '<path d="M9 20h6v2H9z"/>'
        '</svg>'
    )


    # ==================================================
    # CSS
    # ==================================================

    st.markdown(
        f"""
        <style>

        @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;600;700;800&display=swap');

        .landing-title, .mode-card .label {{
            font-family: 'Tajawal', sans-serif !important;
        }}
        
        [data-testid="stAppViewContainer"] {{
            background:{BG};
            direction:rtl;
            overflow:hidden;
        }}

        [data-testid="stHeader"] {{
            background:transparent;
        }}

        [data-testid="stSidebar"] {{
            display:none;
        }}

        [data-testid="stHeaderActionElements"] {{
            display:none;
        }}

        [data-testid="stMain"] {{
            overflow:hidden;
        }}

        [data-testid="stMainBlockContainer"] {{
            max-width:1200px;
            padding-top:0 !important;
            padding-bottom:0 !important;
        }}


        .landing-wrap {{
            height:100vh;

            display:flex;
            flex-direction:column;

            align-items:center;
            justify-content:flex-start;

            padding-top:8vh;

            gap:4vh;
        }}


        .landing-head {{
            text-align:center;
        }}


        .landing-title {{
            color:#FFFFFF;

            font-size:clamp(
                30px,
                3vh,
                80px
            );

            font-weight:800;

            margin:8vh 0 0 0;
        }}


        .cards-row {{
            display:flex;

            gap:40px;

            justify-content:center;
            align-items:center;

            direction:rtl;

            flex-wrap:nowrap;
        }}


        /* الكروت مربعة */
        .mode-card {{
            width:min(38vh,400px);
            height:min(38vh,400px);

            background:{CARD_BG};

            border:
                1px solid
                rgba(255,255,255,0.06);

            border-radius:22px;

            display:flex;
            flex-direction:column;

            align-items:center;
            justify-content:center;

            gap:3vh;

            text-decoration:none;

            transition:
                background .15s,
                border-color .15s,
                transform .1s;
        }}


        .mode-card:hover {{
            background:{CARD_HOVER};

            border-color:
                rgba(255,255,255,0.18);

            transform:translateY(-3px);
        }}


        .mode-card .label {{
            color:{LABEL_COLOR};

            font-size:clamp(
                18px,
                2.6vh,
                28px
            );

            font-weight:700;
        }}


        .mode-card,
        .mode-card:hover,
        .mode-card * {{
            text-decoration:none !important;
        }}

        </style>
        """,
        unsafe_allow_html=True,
    )


    # ==================================================
    # Cards
    # ==================================================

    st.markdown(
        f'<div class="landing-wrap">'

        f'<div class="landing-head">'
        f'{logo_html}'
        f'<div class="landing-title">'
        f'منصة تحليل تجربة العملاء'
        f'</div>'
        f'</div>'

        f'<div class="cards-row">'

        f'<a class="mode-card" '
        f'href="?mode=individuals" target="_self">'
        f'<div>{person_svg}</div>'
        f'<div class="label">أفراد</div>'
        f'</a>'

        f'<a class="mode-card" '
        f'href="?mode=departments" target="_self">'
        f'<div>{building_svg}</div>'
        f'<div class="label">جهات حكومية</div>'
        f'</a>'

        f'<a class="mode-card" '
        f'href="?mode=initiatives" target="_self">'
        f'<div>{initiative_svg}</div>'
        f'<div class="label">المبادرات</div>'
        f'</a>'

        f'</div>'

        f'</div>',
        unsafe_allow_html=True,
    )


# ==================================================
# Start
# ==================================================

if app_mode.get_mode() is None:

    show_landing()

    st.stop()


import pages

pages.run_app()