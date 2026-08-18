from pathlib import Path
import streamlit as st
from PIL import Image

import app_mode


# Prepare the logo and crop away the transparent padding

def prepare_logo():
    original_logo = Path("LogoWhite.png")
    cropped_logo = Path("LogoWhite_cropped.png")

    # No source logo? Just return its path and let the caller handle it.
    if not original_logo.exists():
        return original_logo

    try:
        # Re-crop only if the cropped file is missing or the original is newer.
        should_crop = (
            not cropped_logo.exists()
            or original_logo.stat().st_mtime
            > cropped_logo.stat().st_mtime
        )

        if should_crop:
            with Image.open(original_logo) as original_image:
                image = original_image.convert("RGBA")

                alpha = image.getchannel("A")

                threshold = 20
                mask = alpha.point(
                    lambda alpha_value: 255
                    if alpha_value > threshold
                    else 0
                )

                bounding_box = mask.getbbox()

                if bounding_box:
                    cropped_image = image.crop(bounding_box)
                    cropped_image.save(cropped_logo)
                else:
                    image.save(cropped_logo)

        return cropped_logo

    except Exception:
        return original_logo


LOGO_PATH = prepare_logo()


# Page setup: config, logo, and styling

def setup():
    # Basic page configuration (title, favicon, wide layout, open sidebar).
    st.set_page_config(
        page_title="منصة تجربة العميل",
        page_icon=str(LOGO_PATH),
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Show the logo in the sidebar if the file exists.
    if LOGO_PATH.exists():
        st.logo(
            str(LOGO_PATH),
            size="large",
        )

    # Inject the app's global CSS: loads the Tajawal font, sets a
    # right-to-left layout, styles the dark sidebar and its navigation,
    # the login dialog, and the mode-switch toggle pinned to the bottom.
    st.markdown(
        """
        <style>
        @import url(
            'https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;600;700;800&display=swap'
        );

        html,
        body {
            direction: rtl;
        }

        [data-testid="stAppViewContainer"] {
            background-color: #F5F6FA;
            direction: rtl;
            flex-direction: row !important;
        }

        [data-testid="stMain"] {
            direction: rtl;
            text-align: right;
        }

        [data-testid="stMainBlockContainer"] {
            direction: rtl;
            text-align: right;
            padding-top: 3rem;
            padding-right: 3rem;
            padding-left: 3rem;
        }

        [data-testid="stMain"] p,
        [data-testid="stMain"] h1,
        [data-testid="stMain"] h2,
        [data-testid="stMain"] h3,
        [data-testid="stMain"] label,
        [data-testid="stMain"] button,
        [data-testid="stMain"] input,
        [data-testid="stMain"] textarea {
            font-family: "Tajawal", sans-serif !important;
        }

        section[data-testid="stSidebar"] {
            background-color: #16213E !important;
            width: 320px !important;
            min-width: 320px !important;
            border-left: 1px solid rgba(255, 255, 255, 0.08);
            border-right: none !important;
        }

        section[data-testid="stSidebar"] > div {
            background-color: #16213E !important;
            direction: rtl !important;
            text-align: right !important;
        }

        [data-testid="stSidebarContent"] {
            direction: rtl !important;
            padding: 18px 18px !important;
        }

        section[data-testid="stSidebar"] [data-testid="stLogo"] {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            width: 100% !important;
            margin: 10px auto 20px auto !important;
            padding: 0 !important;
        }

        section[data-testid="stSidebar"] [data-testid="stLogo"] img {
            width: 100% !important;
            max-width: 280px !important;
            height: auto !important;
            max-height: 200px !important;
            object-fit: contain !important;
        }

        [data-testid="stSidebarNav"] {
            direction: rtl !important;
            padding-top: 5px !important;
        }

        [data-testid="stSidebarNav"] ul {
            gap: 8px !important;
        }

        [data-testid="stSidebarNav"] li {
            direction: rtl !important;
        }

        [data-testid="stSidebarNav"] a {
            min-height: 62px !important;
            padding: 14px 18px !important;
            margin-bottom: 6px !important;

            border-radius: 13px !important;
            background-color: transparent !important;

            direction: rtl !important;
            text-align: right !important;

            color: #FFFFFF !important;
            text-decoration: none !important;

            transition: background-color 0.2s ease !important;
        }

        [data-testid="stSidebarNav"] a > div {
            display: flex !important;
            flex-direction: row !important;
            justify-content: flex-start !important;
            align-items: center !important;

            width: 100% !important;
            gap: 12px !important;
            direction: rtl !important;
        }

        [data-testid="stSidebarNav"] a p {
            margin: 0 !important;

            color: #FFFFFF !important;
            font-family: "Tajawal", sans-serif !important;
            font-size: 16px !important;
            font-weight: 700 !important;

            line-height: 1.5 !important;
            text-align: right !important;
        }

        [data-testid="stSidebarNav"] span[data-testid="stIconMaterial"] {
            font-family: "Material Symbols Rounded" !important;
            font-size: 22px !important;
            font-weight: normal !important;
            font-style: normal !important;

            color: #FFFFFF !important;
            direction: ltr !important;
            text-align: center !important;

            shrink: 0 !important;
        }

        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background-color: #6C4AB6 !important;
            color: #FFFFFF !important;
        }

        [data-testid="stSidebarNav"] a[aria-current="page"] p,
        [data-testid="stSidebarNav"] a[aria-current="page"] span {
            color: #FFFFFF !important;
        }

        [data-testid="stSidebarNav"] a:hover {
            background-color: #22335C !important;
            color: #FFFFFF !important;
        }

        [data-testid="stSidebarNavSeparator"] {
            display: none !important;
        }

        [data-testid="stSidebarCollapseButton"] {
            display: none !important;
        }

        span[data-testid="stIconMaterial"],
        .material-symbols-rounded {
            font-family: "Material Symbols Rounded" !important;
        }

        header[data-testid="stHeader"] {
            background-color: transparent;
        }

        footer {
            visibility: hidden;
        }

        div[data-testid="stDialog"] div[data-testid="stVerticalBlock"] {
            text-align: right !important;
            direction: rtl !important;
        }

        div[data-testid="stDialog"] [data-baseweb="input"] button,
        div[data-testid="stDialog"] input::-webkit-contacts-auto-fill-button,
        div[data-testid="stDialog"] input::-webkit-credentials-auto-fill-button {
            display: none !important;
            visibility: hidden !important;
        }

        div[data-testid="stDialog"] button:not([kind="header"]):not([data-testid="baseButton-header"]) {
            background-color: #FFFFFF !important;
            color: #333333 !important;
            border: 1px solid rgba(49, 51, 63, 0.2) !important;
        }
        
        div[data-testid="stDialog"] button:not([kind="header"]):not([data-testid="baseButton-header"]):hover {
            background-color: #F0F2F6 !important;
            color: #000000 !important;
            border-color: rgba(49, 51, 63, 0.4) !important;
        }

        section[data-testid="stSidebar"] > div {
            position: relative !important;
        }
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding-bottom: 92px !important;
        }

        section[data-testid="stSidebar"] .st-key-mode_switch_box {
            position: absolute !important;
            bottom: 0 !important;
            right: 0 !important;
            left: 0 !important;
            z-index: 5 !important;

            padding: 16px 18px !important;
            border-top: 1px solid rgba(255, 255, 255, 0.10) !important;
            background-color: #16213E !important;
        }

        section[data-testid="stSidebar"] .st-key-mode_switch_box
        [data-testid="stToggle"],
        section[data-testid="stSidebar"] .st-key-mode_switch_box
        label[data-baseweb="checkbox"] {
            display: flex !important;
            flex-direction: row-reverse !important;
            align-items: center !important;
            justify-content: space-between !important;
            width: 100% !important;
            gap: 12px !important;
            margin: 0 !important;
            direction: rtl !important;
        }

        section[data-testid="stSidebar"] .st-key-mode_switch_box
        [data-testid="stWidgetLabel"] p {
            color: #FFFFFF !important;
            font-family: "Tajawal", sans-serif !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            margin: 0 !important;
        }

        section[data-testid="stSidebar"] .st-key-mode_switch_box
        [data-baseweb="checkbox"] * {
            transition: none !important;
        }
        /* التوقل نفسه (track + thumb) — نرجّعه LTR عشان الكرة ما تطير */
        section[data-testid="stSidebar"] .st-key-mode_switch_box
        label[data-baseweb="checkbox"] > div:last-child,
        section[data-testid="stSidebar"] .st-key-mode_switch_box
        label[data-baseweb="checkbox"] > div:last-child * {
            direction: ltr !important;
        }
        /* إجبار الكرة تلتصق يسار البيل وتتحرك يمين عند التفعيل */
        section[data-testid="stSidebar"] .st-key-mode_switch_box
        .st-emotion-cache-1hoeffx {
            direction: ltr !important;
            right: auto !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# Toggle for switching between government and individuals modes

def _sidebar_mode_toggle():
    # Read the current mode; label the toggle with the *current* mode's name.
    current_is_individuals = app_mode.is_individuals()
    label = "أفراد" if current_is_individuals else "جهات حكومية"

    # Render the toggle inside a keyed container (styled by the CSS above).
    with st.sidebar:
        with st.container(key="mode_switch_box"):
            is_individuals = st.toggle(
                label,
                value=current_is_individuals,
                key="mode_switch",
            )

    new_mode = (
        "individuals"
        if is_individuals
        else "departments"
    )

    # If the toggle changed the mode, save it and rerun to reload the pages.
    if new_mode != app_mode.get_mode():
        app_mode.set_mode(new_mode)
        st.rerun()


# Password dialog that protects the management (edit) page
CORRECT_PASSWORD = "123"

@st.dialog("تسجيل الدخول لصفحة التعديل")
def password_dialog():
    st.markdown('<div style="text-align: right; direction: rtl; margin-bottom: 10px;">الرجاء إدخال كلمة السر للوصول إلى صفحة التعديل:</div>', unsafe_allow_html=True)
    
    password_input = st.text_input(
        "كلمة السر", 
        type="default", 
        label_visibility="collapsed", 
        placeholder="أدخل كلمة السر هنا..."
    )
    
    col1, col2 = st.columns(2)
    
    if col1.button("دخول", key="submit_pwd", use_container_width=True):
        if password_input == CORRECT_PASSWORD:
            st.session_state["authenticated_management"] = True
            st.success("تم تسجيل الدخول بنجاح!")
            st.rerun()
        else:
            st.error("كلمة السر غير صحيحة، حاول مرة أخرى.")
            
    if col2.button("إلغاء", key="cancel_pwd", use_container_width=True):
        st.session_state["authenticated_management"] = False
        st.switch_page("Departments/Dashboard.py")


# Application page definitions

def _departments_pages():
    # The pages shown in "government departments" mode, in sidebar order.
    return [
        st.Page(
            "Departments/Dashboard.py",
            title="لوحة المعلومات",
            icon=":material/dashboard:",
            default=True, # landing page for this mode
        ),
        st.Page(
            "Departments/data_entry.py",
            title="إدخال بيانات المؤشرات",
            icon=":material/add:",
        ),
        st.Page(
            "Departments/data_upload.py",
            title="رفع ملف Excel",
            icon=":material/upload_file:",
        ),
        st.Page(
            "Departments/comments_page.py",
            title="تحليل تعليقات العملاء",
            icon=":material/chat_bubble_outline:",
        ),
        st.Page(
            "Departments/reports_page.py",
            title="التقارير",
            icon=":material/description:",
        ),
        st.Page(
            "Departments/management_page.py",
            title="التعديل",
            icon=":material/edit:",
        ),
        st.Page(
            "Departments/entities_analysis_page.py",
            title="الجهات",
            icon=":material/apartment:",
        ),
    ]


def _individuals_pages():
    # The pages shown in "individuals" mode, in sidebar order.
    return [
        st.Page(
            "Individuals/Dashboard_individuals.py",
            title="لوحة المعلومات",
            icon=":material/dashboard:",
            default=True, # landing page for this mode
        ),
        st.Page(
            "Individuals/data_upload_individuals.py",
            title="رفع ملف Excel",
            icon=":material/upload_file:",
        ),
        st.Page(
            "Individuals/comments_page_individuals.py",
            title="تحليل تعليقات العملاء",
            icon=":material/chat_bubble_outline:",
        ),
        st.Page(
            "Individuals/reports_individuals_page.py",
            title="التقارير",
            icon=":material/description:",
        ),
    ]


def _pages_for(mode):
    # Pick the page list based on the active mode (defaults to departments)
    if mode == "individuals":
        return _individuals_pages()
    return _departments_pages()


# Run the application

def run_app():

    # Apply page config and styling.
    setup()

    # Draw the mode-switch toggle in the sidebar.
    _sidebar_mode_toggle()

    # Determine the active mode (default to departments).
    mode = app_mode.get_mode() or "departments"

    # Build the sidebar navigation from the mode's pages.
    page = st.navigation(
        _pages_for(mode),
        position="sidebar",
        expanded=True,
    )

    # Leaving the edit page clears authentication, so it's required again next time.
    if page.title != "التعديل":
        st.session_state["authenticated_management"] = False

    # Entering the edit page requires the password dialog first.
    if page.title == "التعديل":
        if not st.session_state.get("authenticated_management", False):
            password_dialog()
            st.stop()

    # Render the selected page.
    page.run()

