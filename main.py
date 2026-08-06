# -*- coding: utf-8 -*-

import streamlit as st

import app_mode


# ----------------------------------------------------------------------
# Landing page (only shown before a mode is chosen)
# ----------------------------------------------------------------------
def show_landing():
    # The landing page owns the page config here, because pages.py has not
    # run yet. This is the only set_page_config on the landing path.
    st.set_page_config(page_title="منصة تجربة العميل", layout="wide")

    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] { background:#F5F6FA; direction:rtl; }
        [data-testid="stSidebar"] { display:none; }
        [data-testid="stHeaderActionElements"] { display:none; }
        .landing-title { text-align:center; color:#16213E; font-size:40px;
                         font-weight:800; margin-top:6vh; }
        .landing-sub   { text-align:center; color:#7A7F94; font-size:18px;
                         margin-bottom:4vh; }
        [data-testid="stButton"] > button {
            height:200px; width:100%; background:#FFFFFF;
            border:1px solid #E7E8F1; border-radius:18px;
            color:#16213E; font-size:24px; font-weight:800;
            white-space:pre-line; line-height:1.6;
            transition:border-color .15s, box-shadow .15s;
        }
        [data-testid="stButton"] > button:hover {
            border-color:#7C5CFC; box-shadow:0 4px 14px rgba(124,92,252,0.15);
            color:#16213E;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="landing-title">منصة تجربة العميل</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="landing-sub">اختر نوع الاستخدام للمتابعة</div>',
                unsafe_allow_html=True)

    _, right, left, _ = st.columns([1, 2, 2, 1])
    with right:
        if st.button("🏢\nجهات\nمؤشرات تجربة العميل للإدارات والخدمات",
                     key="pick_departments", use_container_width=True):
            app_mode.set_mode("departments")
            st.rerun()
    with left:
        if st.button("👤\nأفراد\nمؤشرات تجربة العميل للأفراد",
                     key="pick_individuals", use_container_width=True):
            app_mode.set_mode("individuals")
            st.rerun()


# ----------------------------------------------------------------------
# Flow
# ----------------------------------------------------------------------
if app_mode.get_mode() is None:
    show_landing()
    st.stop()

# A mode is chosen: hand entirely to pages.py. It sets the page config,
# draws the sidebar + toggle, and runs the selected page -- the original
# flow, untouched.
import pages
pages.run_app()