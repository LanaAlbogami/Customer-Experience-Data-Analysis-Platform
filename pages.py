from pathlib import Path
import streamlit as st
from PIL import Image

import app_mode


# ==================================================
# تجهيز الشعار وقص الفراغ الشفاف
# ==================================================

def prepare_logo():
    original_logo = Path("LogoWhite.png")
    cropped_logo = Path("LogoWhite_cropped.png")

    if not original_logo.exists():
        return original_logo

    try:
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


# ==================================================
# إعداد الصفحة والشعار والتصميم
# ==================================================

def setup():
    st.set_page_config(
        page_title="منصة تجربة العميل",
        page_icon=str(LOGO_PATH),
        layout="wide",
        initial_sidebar_state="expanded",
    )

    if LOGO_PATH.exists():
        st.logo(
            str(LOGO_PATH),
            size="large",
        )

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

            flex-shrink: 0 !important;
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

        /* ============================================
           زر التبديل بين الجهات والأفراد (أسفل السايدبار)
           بدون position:absolute — نستخدم Flexbox عشان
           الزر يبقى جوا حدود السايدبار دايمًا، بدل ما "يطير"
           برّا حدوده ويرتبط بحواف الصفحة كلها.
           ============================================ */

        [data-testid="stSidebarContent"] {
            display: flex !important;
            flex-direction: column !important;
            min-height: 100vh !important;
        }

        .st-key-mode_switch_box {
            margin-top: auto !important;
            padding: 16px 4px 4px 4px !important;
            border-top: 1px solid rgba(255, 255, 255, 0.10) !important;
            background-color: #16213E !important;
            width: 100% !important;
        }

        /* تحييد أي صندوق حدود داخلي مختفي جوا الحاوية (ناتج من CSS
           صفحات معينة تلوّن كل الصناديق أبيض) — يضمن الخلفية الغامقة
           تبقى ظاهرة بدل أي "بقعة بيضاء" حول الزر. */
        html body section[data-testid="stSidebar"] .st-key-mode_switch_box,
        html body section[data-testid="stSidebar"] .st-key-mode_switch_box *,
        html body section[data-testid="stSidebar"] .st-key-mode_switch_box div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: transparent !important;
            background: transparent !important;
        }

        html body section[data-testid="stSidebar"] .st-key-mode_switch_box {
            background-color: #16213E !important;
        }

        .st-key-mode_switch_box div[data-testid="stVerticalBlockBorderWrapper"] {
            border: none !important;
            box-shadow: none !important;
            border-radius: 0 !important;
            padding: 0 !important;
        }

        .st-key-mode_switch_box [data-testid="stToggle"],
        .st-key-mode_switch_box label[data-baseweb="checkbox"] {
            display: flex !important;
            flex-direction: row-reverse !important;
            align-items: center !important;
            justify-content: space-between !important;
            width: 100% !important;
            gap: 12px !important;
            margin: 0 !important;
            direction: rtl !important;
        }

        .st-key-mode_switch_box [data-testid="stWidgetLabel"] p,
        .st-key-mode_switch_box label p,
        .st-key-mode_switch_box label span {
            color: #FFFFFF !important;
            font-family: "Tajawal", sans-serif !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            margin: 0 !important;
            opacity: 1 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ==================================================
# زر التبديل بين الجهات والأفراد
# ==================================================

def _sidebar_mode_toggle():
    current_is_individuals = app_mode.is_individuals()
    label = "أفراد" if current_is_individuals else "جهات حكومية"

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

    if new_mode != app_mode.get_mode():
        app_mode.set_mode(new_mode)
        st.rerun()


# ==================================================
# نافذة كلمة المرور لحماية صفحة التعديل
# ==================================================
CORRECT_PASSWORD = "123"  # كلمة السر

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
        st.switch_page("Dashboard.py")


# ==================================================
# تعريف صفحات التطبيق
# ==================================================

def _departments_pages():
    return [
        st.Page(
            "Dashboard.py",
            title="لوحة المعلومات",
            icon=":material/dashboard:",
            default=True,
        ),
        st.Page(
            "data_entry.py",
            title="إدخال بيانات المؤشرات",
            icon=":material/add:",
        ),
        st.Page(
            "data_upload.py",
            title="رفع ملف Excel",
            icon=":material/upload_file:",
        ),
        st.Page(
            "comments_page.py",
            title="تحليل تعليقات العملاء",
            icon=":material/chat_bubble_outline:",
        ),
        st.Page(
            "reports_page.py",
            title="التقارير",
            icon=":material/description:",
        ),
        st.Page(
            "management_page.py",
            title="التعديل",
            icon=":material/edit:",
        ),
    ]


def _individuals_pages():
    return [
        st.Page(
            "Individuals/Dashboard_individuals.py",
            title="لوحة المعلومات",
            icon=":material/dashboard:",
            default=True,
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
    ]


def _pages_for(mode):
    if mode == "individuals":
        return _individuals_pages()
    return _departments_pages()


# ==================================================
# تشغيل التطبيق
# ==================================================

def run_app():
    setup()

    _sidebar_mode_toggle()

    mode = app_mode.get_mode() or "departments"

    page = st.navigation(
        _pages_for(mode),
        position="sidebar",
        expanded=True,
    )

    if page.title != "التعديل":
        st.session_state["authenticated_management"] = False

    if page.title == "التعديل":
        if not st.session_state.get("authenticated_management", False):
            password_dialog()
            st.stop()

    page.run()


run_app()