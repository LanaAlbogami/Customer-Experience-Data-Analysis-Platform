import streamlit as st
from style import fix_sidebar_style

# ==================================================
# إعدادات التطبيق
# ==================================================
st.set_page_config(
    page_title="منصة تجربة العميل",
    page_icon="logo.png",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==================================================
# الشعار أعلى السايدبار
# ==================================================
st.logo(
    "logo.png",
    size="large",
)


# ==================================================
# تنسيق التطبيق
# ==================================================
st.markdown(
    """
    <style>

    /* اتجاه الصفحة */
    html,
    body {
        direction: rtl;
    }

    /* خلفية التطبيق */
    [data-testid="stAppViewContainer"] {
        background-color: #F5F6FA;
        direction: rtl;

        /*
        مهم:
        لا تستخدمي row-reverse لأن اتجاه الصفحة RTL أصلًا
        */
        flex-direction: row !important;
    }

    /* اتجاه محتوى الصفحة */
    [data-testid="stMain"] {
        direction: rtl;
    }

    [data-testid="stMainBlockContainer"] {
        direction: rtl;
        text-align: right;
        padding-top: 3rem;
        padding-right: 3rem;
        padding-left: 3rem;
    }

    /* ==================================================
       السايدبار
    ================================================== */
    section[data-testid="stSidebar"] {
        background-color: #16213E !important;
        width: 315px !important;
        min-width: 315px !important;

        border-right: none !important;
        border-left: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    section[data-testid="stSidebar"] > div {
        direction: rtl;
        text-align: right;
    }

    [data-testid="stSidebarContent"] {
        direction: rtl;
        padding: 22px 16px;
    }

    /* ==================================================
       قائمة التنقل
    ================================================== */
    [data-testid="stSidebarNav"] {
        direction: rtl;
        padding-top: 20px;
    }

    [data-testid="stSidebarNav"] ul {
        gap: 9px;
    }

    [data-testid="stSidebarNav"] li {
        direction: rtl;
    }

    [data-testid="stSidebarNav"] a {
        direction: rtl;
        text-align: right;

        border-radius: 13px;
        padding: 15px 17px;

        color: #DCE3F5 !important;
        font-size: 16px;
        font-weight: 600;

        transition: all 0.2s ease;
    }

    [data-testid="stSidebarNav"] a:hover {
        background-color: #22335C !important;
        color: #FFFFFF !important;
    }

    /* الصفحة المحددة */
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background-color: #6C4AB6 !important;
        color: #FFFFFF !important;
    }

    /* ترتيب الأيقونة والنص */
    [data-testid="stSidebarNav"] a > div {
        flex-direction: row-reverse;
        justify-content: flex-start;
        gap: 12px;
    }

    [data-testid="stSidebarNav"] svg {
        color: inherit !important;
    }

    [data-testid="stSidebarNavSeparator"] {
        display: none;
    }

    /* ==================================================
       الشعار
    ================================================== */
    [data-testid="stLogo"] {
        margin: 12px auto 18px auto;
    }

    [data-testid="stLogo"] img {
        max-width: 210px;
        height: auto;
        object-fit: contain;
    }

    /* زر فتح وإغلاق السايدبار */
    [data-testid="stSidebarCollapseButton"] button {
        color: #FFFFFF !important;
    }

    /* إخفاء ترويسة Streamlit العلوية الزائدة */
    header[data-testid="stHeader"] {
        background-color: transparent;
    }

    /* إخفاء الفوتر */
    footer {
        visibility: hidden;
    }

    </style>
    """,
    unsafe_allow_html=True,
)

fix_sidebar_style()
# ==================================================
# تعريف الصفحات
# ==================================================
dashboard_page = st.Page(
    "Dashboard.py",
    title="لوحة المعلومات",
    icon=":material/dashboard:",
    default=True,
)

data_entry_page = st.Page(
    "data_entry.py",
    title="إدخال بيانات المؤشرات",
    icon=":material/add:",
)

upload_page = st.Page(
    "data_upload.py",
    title="رفع ملف Excel",
    icon=":material/upload_file:",
)

comments_page = st.Page(
    "comments_page.py",
    title="تحليل تعليقات العملاء",
    icon=":material/chat_bubble_outline:",
)

reports_page = st.Page(
    "reports_page.py",
    title="التقارير",
    icon=":material/description:",
)


# ==================================================
# التنقل بين الصفحات
# ==================================================
page = st.navigation(
    [
        dashboard_page,
        data_entry_page,
        upload_page,
        comments_page,
        reports_page,
    ],
    position="sidebar",
    expanded=True,
)

page.run()