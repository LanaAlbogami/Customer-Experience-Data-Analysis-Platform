# -*- coding: utf-8 -*-

# Application entry point.


import base64
from pathlib import Path

import sys

import streamlit as st

import app_mode
from style import COLORS   # Reuse the shared palette so the app stays consistent.


# The individuals pages live inside the Individuals/ folder, and some of their
# files import their neighbours by plain name (e.g. data_service_individuals).
# Adding this folder to the search path makes those imports work no matter
# which directory the app is launched from.
_INDIVIDUALS_DIR = str(Path(__file__).parent / "Individuals")
if _INDIVIDUALS_DIR not in sys.path:
    sys.path.insert(0, _INDIVIDUALS_DIR)

# Same as above, but for the Departments/ folder.
_DEPARTMENTS_DIR = str(Path(__file__).parent / "Departments")
if _DEPARTMENTS_DIR not in sys.path:
    sys.path.insert(0, _DEPARTMENTS_DIR)

# Same as above, but for the Initiatives/ folder.
_INITIATIVES_DIR = str(Path(__file__).parent / "Initiatives")
if _INITIATIVES_DIR not in sys.path:
    sys.path.insert(0, _INITIATIVES_DIR)

# Landing-page colours.
BG = COLORS["navy"]                  # Page background — from style.py.
CARD_HOVER = COLORS["navy_light"]    # Card colour on hover — from style.py.
CARD_BG = "#1F2C4C"                # Card fill: between navy and navy_light.
ICON_COLOR = "#3A4A72"             # Icon colour inside each card (dark-mode indigo).
LABEL_COLOR = "#E7EAF3"            # Card label colour (light, for the dark background).


# Path to the white SDAIA logo shown on the dark background.
# Path(__file__).parent anchors it to this file's folder, so the image is
# found regardless of the working directory from which the app is launched.
LOGO_FILE = Path(__file__).parent / "LogoWhite_cropped.png"


def _logo_data_uri():
    """Read the logo and encode it as a base64 data URI for embedding in HTML."""
    try:
        data = base64.b64encode(LOGO_FILE.read_bytes()).decode()
        return f"data:image/png;base64,{data}"
    except Exception:
        return ""   # If the logo is missing, the page still works without it.


# Landing page (أفراد / جهات)
def show_landing():
    st.set_page_config(page_title="منصة تحليل تجربة العملاء", layout="wide")

    # When a card is clicked, the page reloads with ?mode=... in the URL.
    # Read that value, store the selection, clear the URL, and rerun.
    chosen = st.query_params.get("mode")
    if chosen in ("departments", "individuals"):
        app_mode.set_mode(chosen)
        st.query_params.clear()
        st.rerun()

    logo = _logo_data_uri()
    # Logo size uses clamp(minimum, viewport-relative, maximum).
    logo_html = (f'<img src="{logo}" style="height:clamp(72px,13vh,120px);">'
                 if logo else "")

    # The two card icons are drawn as inline SVG so their size and colour can
    # be controlled directly.
    # Building icon (for departments). The icon size is set in the
    # width/height style below — clamp(minimum, viewport-relative, maximum=92px).
    # The same value is repeated on the person icon so both match in size.
    building_svg = (
        f'<svg viewBox="0 0 24 24" fill="{ICON_COLOR}" style="width:clamp(56px,11vh,92px);height:clamp(56px,11vh,92px);" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<path d="M3 21V9l5-2v14H3zm6 0V4l5 3v14H9zm6 0V11l5 3v7h-5z'
        'M5 12h1v1H5v-1zm0 3h1v1H5v-1zm6-5h1v1h-1v-1zm0 3h1v1h-1v-1z'
        'm0 3h1v1h-1v-1zm6 0h1v1h-1v-1z"/></svg>'
    )
    # Person icon (for individuals).
    person_svg = (
        f'<svg viewBox="0 0 24 24" fill="{ICON_COLOR}" style="width:clamp(56px,11vh,92px);height:clamp(56px,11vh,92px);" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<circle cx="12" cy="8" r="4.5"/>'
        '<path d="M3.5 20c0-4.2 3.8-6.5 8.5-6.5s8.5 2.3 8.5 6.5v.5h-17V20z"/></svg>'
    )

    # Inject the landing page's CSS. This styles the dark full-screen layout
    # and the two clickable mode cards. Uses an f-string so the palette
    # colours (BG, CARD_BG, CARD_HOVER, LABEL_COLOR) are dropped in directly.
    st.markdown(
        f"""
<style>
[data-testid="stAppViewContainer"] {{ background:{BG}; direction:rtl; overflow:hidden; }}
[data-testid="stHeader"] {{ background:transparent; }}
[data-testid="stSidebar"] {{ display:none; }}
[data-testid="stHeaderActionElements"] {{ display:none; }}
[data-testid="stMain"] {{ overflow:hidden; }}
[data-testid="stMainBlockContainer"] {{ max-width:1100px; padding-top:0 !important; padding-bottom:0 !important; }}
.landing-wrap {{ height:100vh; display:flex; flex-direction:column; align-items:center; justify-content:flex-start; padding-top:8vh; gap:4vh; }}
.landing-head {{ text-align:center; }}
.landing-title {{ color:#FFFFFF; font-size:clamp(30px, 3vh, 80px); font-weight:800; margin:8vh 0 0 0; }}
.cards-row {{ display:flex; gap:80px; justify-content:center; direction:rtl; flex-wrap:nowrap; }}
.mode-card {{ width:min(42vh, 440px); height:min(42vh, 440px); background:{CARD_BG}; border:1px solid rgba(255,255,255,0.06); border-radius:22px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:3vh; text-decoration:none; transition:background .15s, border-color .15s, transform .1s; }}
.mode-card:hover {{ background:{CARD_HOVER}; border-color:rgba(255,255,255,0.18); transform:translateY(-3px); }}
.mode-card .label {{ color:{LABEL_COLOR}; font-size:clamp(18px,2.6vh,28px); font-weight:700; }}
.mode-card, .mode-card:hover, .mode-card * {{ text-decoration:none !important; }}
</style>
""",
        unsafe_allow_html=True,
    )

    # Build the landing markup and render it.
    # Structure: wrapper > (logo + title) + (row of two cards).
    # Each card is an <a> link that reloads the page with ?mode=... set,
    # which the code at the top of show_landing() reads to pick the mode.
    st.markdown(
        f'<div class="landing-wrap">'
        f'<div class="landing-head">{logo_html}'
        f'<div class="landing-title">منصة تحليل تجربة العملاء</div></div>'
        f'<div class="cards-row">'
        f'<a class="mode-card" href="?mode=individuals" target="_self">'
        f'<div>{person_svg}</div><div class="label">أفراد</div></a>'
        f'<a class="mode-card" href="?mode=departments" target="_self">'
        f'<div>{building_svg}</div><div class="label">جهات حكومية</div></a>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


# If no mode has been selected, show the landing page and stop here, so the
# rest of the script does not run.
if app_mode.get_mode() is None:
    show_landing()
    st.stop()

# A mode has been selected: hand control to pages.py.
import pages
pages.run_app()