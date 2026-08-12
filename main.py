# -*- coding: utf-8 -*-
"""
main.py
r

Application entry point. Launch the platform with:  streamlit run main.py

Behaviour:
    - When no mode has been selected, the landing page is displayed. It
      presents the SDAIA logo and two clickable cards (جهات حكومية / أفراد).
    - Once a mode is selected, control is handed to pages.py, which renders
      the sidebar and the remaining application pages.

st.set_page_config is called on the landing path only. After a mode has
been selected, pages.py is responsible for the page configuration and
styling.
"""

import base64
from pathlib import Path

import sys

import streamlit as st

import app_mode
from style import COLORS   # Reuse the shared palette so the app stays consistent.


# صفحات الأفراد موجودة داخل مجلد Individuals/، وبعض ملفاتها تستورد
# ملفاتها المجاورة باسم مباشر (مثل data_service_individuals). إضافة المجلد
# إلى مسار البحث تخلي هذي الاستيرادات تشتغل مهما كان مجلد التشغيل.
_INDIVIDUALS_DIR = str(Path(__file__).parent / "Individuals")
if _INDIVIDUALS_DIR not in sys.path:
    sys.path.insert(0, _INDIVIDUALS_DIR)


# Landing-page colours.
BG = COLORS["navy"]                # Page background — from style.py.
CARD_HOVER = COLORS["navy_light"]  # Card colour on hover — from style.py.
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
    st.set_page_config(page_title="منصة تحليل تجارب العملاء", layout="wide")

    # When a card is clicked, the page reloads with ?mode=... in the URL.
    # Read that value, store the selection, clear the URL, and rerun.
    chosen = st.query_params.get("mode")
    if chosen in ("departments", "individuals"):
        app_mode.set_mode(chosen)
        st.query_params.clear()
        st.rerun()

    logo = _logo_data_uri()
    # Logo size uses clamp(minimum, viewport-relative, maximum).
    # Increase the last value (120px) to enlarge the logo, decrease to shrink.
    logo_html = (f'<img src="{logo}" style="height:clamp(72px,13vh,120px);">'
                 if logo else "")

    # The two card icons are drawn as inline SVG so their size and colour can
    # be controlled directly.
    # Building icon (for government departments). The icon size is set in the
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

    # Each card is a full <a> link, with the icon placed above the label
    # using custom HTML. This avoids relying on Streamlit's internal button
    # structure, which proved difficult to style reliably.
    #
    # Adjustable values in the CSS below:
    #   .landing-wrap padding-top:6vh  -> raises/lowers all content (larger = lower)
    #   .landing-wrap gap:2vh          -> space between the logo/title and the cards
    #   .landing-title font-size clamp -> page title size (last value = 34px)
    #   .cards-row gap:36px            -> space between the two cards
    #   .mode-card width/height 42vh   -> card size (larger = bigger; the card is square)
    #   .mode-card gap:3vh             -> space between the icon and the label
    #   .mode-card .label font-size    -> card label size (أفراد / جهات حكومية)
    #   Colours: BG and CARD_HOVER come from style.py; the darker shades
    #            (CARD_BG, ICON_COLOR, LABEL_COLOR) are defined at the top of the file.
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

    st.markdown(
        f'<div class="landing-wrap">'
        f'<div class="landing-head">{logo_html}'
        f'<div class="landing-title">منصة تحليل تجارب العملاء</div></div>'
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