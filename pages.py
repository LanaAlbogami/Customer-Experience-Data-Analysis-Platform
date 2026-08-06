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
        # إعادة قص الشعار فقط إذا تغيرت الصورة الأصلية
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
    # إعدادات التطبيق
    st.set_page_config(
        page_title="منصة تجربة العميل",
        page_icon=str(LOGO_PATH),
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # الشعار أعلى القائمة الجانبية
    if LOGO_PATH.exists():
        st.logo(
            str(LOGO_PATH),
            size="large",
        )

    # تصميم التطبيق والقائمة الجانبية
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

        /* محتوى الصفحات */
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

        /* =========================
           القائمة الجانبية
        ========================= */

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

        /* =========================
           الشعار
        ========================= */

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

        /* =========================
           قائمة الصفحات
        ========================= */

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

        /* ترتيب الأيقونة والنص */
        [data-testid="stSidebarNav"] a > div {
            display: flex !important;
            flex-direction: row !important;
            justify-content: flex-start !important;
            align-items: center !important;

            width: 100% !important;
            gap: 12px !important;
            direction: rtl !important;
        }

        /* نصوص القائمة */
        [data-testid="stSidebarNav"] a p {
            margin: 0 !important;

            color: #FFFFFF !important;
            font-family: "Tajawal", sans-serif !important;
            font-size: 16px !important;
            font-weight: 700 !important;

            line-height: 1.5 !important;
            text-align: right !important;
        }

        /* أيقونات القائمة */
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

        /* الصفحة المحددة */
        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background-color: #6C4AB6 !important;
            color: #FFFFFF !important;
        }

        [data-testid="stSidebarNav"] a[aria-current="page"] p,
        [data-testid="stSidebarNav"] a[aria-current="page"] span {
            color: #FFFFFF !important;
        }

        /* عند تمرير الماوس */
        [data-testid="stSidebarNav"] a:hover {
            background-color: #22335C !important;
            color: #FFFFFF !important;
        }

        [data-testid="stSidebarNavSeparator"] {
            display: none !important;
        }

        /* زر تصغير القائمة الجانبية */
        [data-testid="stSidebarCollapseButton"] button {
            color: #FFFFFF !important;
        }

        [data-testid="stSidebarCollapseButton"] svg {
            color: #FFFFFF !important;
            fill: #FFFFFF !important;
        }

        /* المحافظة على خط الأيقونات */
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
        </style>
        """,
        unsafe_allow_html=True,
    )


# ==================================================
# زر التبديل بين الجهات والأفراد
# ==================================================

def _sidebar_mode_toggle():
    """
    OFF = الجهات
    ON = الأفراد
    """

    with st.sidebar:
        is_individuals = st.toggle(
            "وضع الأفراد",
            value=app_mode.is_individuals(),
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
# تعريف صفحات التطبيق
# ==================================================

def _pages_for(mode):
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

    page.run()


run_app()