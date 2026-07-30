import pandas as pd
import streamlit as st

from data_service import (
    RAW_DATA,
    CALCULATED_DATA,
    prepare_uploaded_records,
)
from entry_backend import save_uploaded_records
from style import apply_theme


# تطبيق الستايل المشترك بدون تعديله
apply_theme()


# تطبيق اتجاه عربي على هذه الصفحة فقط، بدون تعديل style.py
st.markdown(
    """
    <style>
    /* اتجاه الصفحة بالكامل */
    div[data-testid="stMainBlockContainer"] {
        direction: rtl;
        text-align: right;
    }

    /* العناوين والنصوص والوصف */
    div[data-testid="stMarkdownContainer"],
    div[data-testid="stCaptionContainer"],
    label[data-testid="stWidgetLabel"] {
        direction: rtl;
        text-align: right;
    }

    label[data-testid="stWidgetLabel"] p {
        width: 100%;
        text-align: right;
    }

    /* القوائم المنسدلة */
    div[data-baseweb="select"] > div {
        direction: rtl;
        text-align: right;
    }

    div[data-baseweb="select"] span {
        direction: rtl;
        text-align: right;
    }

    /* حقول الإدخال */
    div[data-baseweb="input"] > div,
    div[data-baseweb="input"] input {
        direction: rtl;
        text-align: right;
    }

    /* أزرار الاختيار Radio */
    div[role="radiogroup"] {
        direction: rtl;
        justify-content: flex-start;
    }

    div[role="radiogroup"] label {
        direction: rtl;
    }

    /* الاختيارات المتعددة */
    div[data-baseweb="tag"] {
        direction: rtl;
    }

    /* رسائل النجاح والخطأ والتنبيه */
    div[data-testid="stAlert"] {
        direction: rtl;
        text-align: right;
    }

    /* الأزرار */
    div[data-testid="stButton"] {
        direction: rtl;
        text-align: right;
    }

    /* محتوى الـ expander */
    details {
        direction: rtl;
        text-align: right;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------
# خيارات الواجهة
# ----------------------------------------------------------------------

NO_COLUMN = "غير موجود"

DEPARTMENT_FROM_COLUMN = "القسم موجود داخل الملف"
DEPARTMENT_FIXED = "كل الملف تابع لقسم واحد"

TIME_FROM_DATE = "يوجد عمود تاريخ"
TIME_FROM_COLUMNS = "يوجد عمود سنة وعمود فترة"
TIME_FIXED = "سنة وفترة واحدة لكل الملف"

RAW_DATA_LABEL = "إجابات استبيان خام"
CALCULATED_DATA_LABEL = "مؤشرات محسوبة مسبقًا"


# ----------------------------------------------------------------------
# دوال بسيطة للواجهة
# ----------------------------------------------------------------------

def find_default_index(options, preferred_names):
    """اختيار العمود المتوقع تلقائيًا إذا كان موجودًا."""

    for name in preferred_names:
        if name in options:
            return options.index(name)

    return 0


def find_default_columns(columns, preferred_names):
    """اختيار الأعمدة المتوقعة تلقائيًا للـ multiselect."""

    return [
        name
        for name in preferred_names
        if name in columns
    ]


# ----------------------------------------------------------------------
# عنوان الصفحة
# ----------------------------------------------------------------------

st.markdown(
    """
    <div dir="rtl" style="text-align: right;">
        <h1>رفع البيانات</h1>
        <p style="color: #7A7F94; font-size: 17px;">
            ارفع ملف Excel وحدد وظيفة الأعمدة، ثم احفظ البيانات في قاعدة البيانات
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------
# رفع الملف
# ----------------------------------------------------------------------

uploaded_file = st.file_uploader(
    "اسحب ملف Excel هنا أو اضغط للاختيار",
    type=["xlsx", "xls"],
)


if uploaded_file is not None:
    try:
        dataframe = pd.read_excel(uploaded_file)

        dataframe.columns = [
            str(column).strip()
            for column in dataframe.columns
        ]

    except Exception as error:
        st.error(
            f"تعذر قراءة ملف Excel: {error}"
        )
        st.stop()

    if dataframe.empty:
        st.warning(
            "ملف Excel لا يحتوي على بيانات."
        )
        st.stop()

    available_columns = (
        dataframe.columns.tolist()
    )

    optional_columns = (
        [NO_COLUMN]
        + available_columns
    )

    st.success(
        f"تمت قراءة الملف بنجاح — عدد الصفوف: {len(dataframe)}"
    )

    with st.expander(
        "معاينة الملف",
        expanded=False,
    ):
        st.dataframe(
            dataframe.head(20),
            use_container_width=True,
            hide_index=True,
        )

    # ==================================================================
    # 1. البيانات الأساسية
    # ==================================================================

    with st.container(border=True):
        st.markdown("## 1. البيانات الأساسية")

        st.caption(
            "حددي الخدمة والقسم والفترة الزمنية الخاصة بالبيانات."
        )

        service_column = st.selectbox(
            "عمود اسم الخدمة *",
            options=available_columns,
            index=find_default_index(
                available_columns,
                [
                    "اسم_الخدمة",
                    "اسم الخدمة",
                    "الخدمة",
                    "Service",
                    "Service Name",
                ],
            ),
        )

        # --------------------------------------------------------------
        # القسم
        # --------------------------------------------------------------

        st.markdown("#### القسم")

        department_mode = st.radio(
            "طريقة تحديد القسم",
            options=[
                DEPARTMENT_FROM_COLUMN,
                DEPARTMENT_FIXED,
            ],
            horizontal=True,
            label_visibility="collapsed",
        )

        department_column = None
        fixed_department = None

        if department_mode == DEPARTMENT_FROM_COLUMN:
            department_column = st.selectbox(
                "عمود اسم القسم *",
                options=available_columns,
                index=find_default_index(
                    available_columns,
                    [
                        "اسم_القسم",
                        "اسم القسم",
                        "القسم",
                        "Department",
                    ],
                ),
            )

        else:
            fixed_department = st.text_input(
                "اسم القسم الذي يخص جميع صفوف الملف *",
                placeholder="مثال: إدارة تجربة العميل",
            )

        # --------------------------------------------------------------
        # السنة والفترة
        # --------------------------------------------------------------

        st.markdown("#### السنة والفترة")

        time_mode = st.radio(
            "طريقة تحديد السنة والفترة",
            options=[
                TIME_FROM_DATE,
                TIME_FROM_COLUMNS,
                TIME_FIXED,
            ],
            horizontal=True,
            label_visibility="collapsed",
        )

        date_column = None
        year_column = None
        period_column = None
        fixed_year = None
        fixed_period = None

        if time_mode == TIME_FROM_DATE:
            date_column = st.selectbox(
                "عمود التاريخ *",
                options=available_columns,
                index=find_default_index(
                    available_columns,
                    [
                        "تاريخ_الاستجابة",
                        "تاريخ الاستجابة",
                        "التاريخ",
                        "Response Date",
                        "Date",
                    ],
                ),
                help=(
                    "سيستخرج النظام السنة تلقائيًا، "
                    "ويحدد النصف الأول أو الثاني من الشهر."
                ),
            )

        elif time_mode == TIME_FROM_COLUMNS:
            time_col1, time_col2 = st.columns(2)

            with time_col1:
                year_column = st.selectbox(
                    "عمود السنة *",
                    options=available_columns,
                    index=find_default_index(
                        available_columns,
                        [
                            "السنة",
                            "السنه",
                            "العام",
                            "Year",
                        ],
                    ),
                )

            with time_col2:
                period_column = st.selectbox(
                    "عمود الفترة *",
                    options=available_columns,
                    index=find_default_index(
                        available_columns,
                        [
                            "الفترة",
                            "الفتره",
                            "النصف",
                            "Period",
                        ],
                    ),
                    help=(
                        "القيم المقبولة تشمل: "
                        "النصف الأول، النصف الثاني، H1، H2."
                    ),
                )

        else:
            fixed_col1, fixed_col2 = st.columns(2)

            with fixed_col1:
                fixed_year = st.number_input(
                    "السنة *",
                    min_value=2000,
                    max_value=2100,
                    value=2026,
                    step=1,
                )

            with fixed_col2:
                fixed_period = st.selectbox(
                    "الفترة *",
                    options=[
                        "النصف الأول",
                        "النصف الثاني",
                    ],
                )

    # ==================================================================
    # 2. المؤشرات
    # ==================================================================

    with st.container(border=True):
        st.markdown("## 2. المؤشرات")

        data_mode_label = st.radio(
            "نوع البيانات الموجودة داخل الملف",
            options=[
                RAW_DATA_LABEL,
                CALCULATED_DATA_LABEL,
            ],
            horizontal=True,
        )

        # قيم افتراضية للمتغيرات
        response_id_column = None

        csat_columns = []
        ces_columns = []
        nps_column = None

        calculated_csat_column = None
        calculated_ces_column = None
        calculated_nps_column = None
        participants_column = None

        # --------------------------------------------------------------
        # بيانات استبيان خام
        # --------------------------------------------------------------

        if data_mode_label == RAW_DATA_LABEL:
            st.caption(
                "اختاري أعمدة إجابات الاستبيان، "
                "وسيحسب النظام المؤشرات تلقائيًا."
            )

            response_id_selection = st.selectbox(
                "عمود رقم الاستجابة",
                options=optional_columns,
                index=find_default_index(
                    optional_columns,
                    [
                        "رقم_الاستجابة",
                        "رقم الاستجابة",
                        "Response ID",
                        "ID",
                    ],
                ),
                help=(
                    "يُستخدم لحساب عدد المشاركين بدون تكرار. "
                    "عند عدم وجوده سيحسب النظام عدد الصفوف."
                ),
            )

            if response_id_selection != NO_COLUMN:
                response_id_column = (
                    response_id_selection
                )

            default_csat_columns = (
                find_default_columns(
                    available_columns,
                    [
                        "تقييم_1",
                        "CSAT",
                        "الرضا العام",
                    ],
                )
            )

            default_ces_columns = (
                find_default_columns(
                    available_columns,
                    [
                        "تقييم_2",
                        "CES",
                        "سهولة الاستخدام",
                    ],
                )
            )

            csat_columns = st.multiselect(
                "أسئلة CSAT",
                options=available_columns,
                default=default_csat_columns,
                help=(
                    "يمكن اختيار أكثر من سؤال. "
                    "سيحسب النظام CSAT لكل سؤال ثم يأخذ المتوسط."
                ),
            )

            ces_columns = st.multiselect(
                "أسئلة CES",
                options=available_columns,
                default=default_ces_columns,
                help=(
                    "يمكن اختيار أكثر من سؤال. "
                    "سيحسب النظام CES لكل سؤال ثم يأخذ المتوسط."
                ),
            )

            nps_selection = st.selectbox(
                "عمود إجابات NPS",
                options=optional_columns,
                index=find_default_index(
                    optional_columns,
                    [
                        "تقييم_الترشيح_NPS",
                        "NPS",
                        "التوصية",
                    ],
                ),
            )

            if nps_selection != NO_COLUMN:
                nps_column = nps_selection

            with st.expander(
                "طريقة حساب المؤشرات"
            ):
                st.markdown(
                    """
                    - **CSAT:** نسبة التقييمات 4 و5 من مقياس 1–5.
                    - **CES:** نسبة الإجابات السهلة 4–5 ناقص نسبة الإجابات الصعبة 1–2.
                    - **NPS:** نسبة المروجين 9–10 ناقص نسبة غير المروجين 0–6.
                    - القيم خارج نطاق السؤال، مثل 99، تُستبعد.
                    """
                )

        # --------------------------------------------------------------
        # مؤشرات محسوبة مسبقًا
        # --------------------------------------------------------------

        else:
            st.caption(
                "اختاري الأعمدة التي تحتوي على النتائج النهائية. "
                "لن يعيد النظام حسابها."
            )

            calculated_col1, calculated_col2, calculated_col3 = (
                st.columns(3)
            )

            with calculated_col1:
                csat_selection = st.selectbox(
                    "عمود قيمة CSAT",
                    options=optional_columns,
                    index=find_default_index(
                        optional_columns,
                        [
                            "CSAT",
                            "CSAT الحالي",
                            "Current CSAT",
                        ],
                    ),
                )

                if csat_selection != NO_COLUMN:
                    calculated_csat_column = (
                        csat_selection
                    )

            with calculated_col2:
                ces_selection = st.selectbox(
                    "عمود قيمة CES",
                    options=optional_columns,
                    index=find_default_index(
                        optional_columns,
                        [
                            "CES",
                            "CES الحالي",
                            "Current CES",
                        ],
                    ),
                )

                if ces_selection != NO_COLUMN:
                    calculated_ces_column = (
                        ces_selection
                    )

            with calculated_col3:
                nps_value_selection = st.selectbox(
                    "عمود قيمة NPS",
                    options=optional_columns,
                    index=find_default_index(
                        optional_columns,
                        [
                            "NPS",
                            "NPS الحالي",
                            "Current NPS",
                        ],
                    ),
                )

                if nps_value_selection != NO_COLUMN:
                    calculated_nps_column = (
                        nps_value_selection
                    )

            participants_selection = st.selectbox(
                "عمود عدد المشاركين",
                options=optional_columns,
                index=find_default_index(
                    optional_columns,
                    [
                        "عدد المشاركين",
                        "عدد_المشاركين",
                        "Participants",
                        "Participants Count",
                    ],
                ),
                help=(
                    "إذا لم يوجد عمود لعدد المشاركين، "
                    "سيتم حفظ العدد بقيمة صفر."
                ),
            )

            if participants_selection != NO_COLUMN:
                participants_column = (
                    participants_selection
                )

    # ==================================================================
    # 3. التعليقات
    # ==================================================================

    with st.container(border=True):
        st.markdown("## 3. التعليقات")

        st.caption(
            "اختيار أعمدة التعليقات اختياري. "
            "يمكن اختيار أكثر من عمود."
        )

        default_comment_columns = [
            column
            for column in available_columns
            if (
                "تعليق" in column
                or "comment" in column.lower()
                or "ملاحظة" in column
            )
        ]

        comment_columns = st.multiselect(
            "أعمدة التعليقات",
            options=available_columns,
            default=default_comment_columns,
        )

    # ==================================================================
    # التحقق والحفظ
    # ==================================================================

    save_button = st.button(
        "التحقق وحفظ البيانات",
        type="primary",
        use_container_width=True,
    )

    if save_button:
        errors = []

        # --------------------------------------------------------------
        # التحقق من القسم
        # --------------------------------------------------------------

        if (
            department_mode
            == DEPARTMENT_FIXED
            and not str(
                fixed_department or ""
            ).strip()
        ):
            errors.append(
                "يجب كتابة اسم القسم "
                "الذي يخص جميع صفوف الملف."
            )

        # --------------------------------------------------------------
        # التحقق من المؤشرات
        # --------------------------------------------------------------

        if data_mode_label == RAW_DATA_LABEL:
            repeated_questions = (
                set(csat_columns)
                .intersection(ces_columns)
            )

            if repeated_questions:
                errors.append(
                    "لا يمكن استخدام السؤال نفسه "
                    "ضمن CSAT وCES معًا: "
                    + "، ".join(
                        sorted(repeated_questions)
                    )
                )

            if (
                nps_column is not None
                and (
                    nps_column in csat_columns
                    or nps_column in ces_columns
                )
            ):
                errors.append(
                    "لا يمكن استخدام عمود NPS "
                    "ضمن أسئلة CSAT أو CES."
                )

            has_indicators = bool(
                csat_columns
                or ces_columns
                or nps_column
            )

        else:
            selected_calculated_columns = [
                column
                for column in [
                    calculated_csat_column,
                    calculated_ces_column,
                    calculated_nps_column,
                ]
                if column is not None
            ]

            if len(
                selected_calculated_columns
            ) != len(
                set(selected_calculated_columns)
            ):
                errors.append(
                    "لا يمكن استخدام العمود نفسه "
                    "لأكثر من مؤشر."
                )

            has_indicators = bool(
                selected_calculated_columns
            )

        if (
            not has_indicators
            and not comment_columns
        ):
            errors.append(
                "يجب اختيار مؤشر واحد على الأقل "
                "أو اختيار عمود للتعليقات."
            )

        # --------------------------------------------------------------
        # عرض الأخطاء
        # --------------------------------------------------------------

        if errors:
            for error_message in errors:
                st.error(error_message)

        else:
            try:
                data_mode = (
                    RAW_DATA
                    if data_mode_label
                    == RAW_DATA_LABEL
                    else CALCULATED_DATA
                )

                with st.spinner(
                    "جاري تجهيز الملف وحفظ البيانات..."
                ):
                    prepared_records = (
                        prepare_uploaded_records(
                            dataframe=dataframe,
                            data_mode=data_mode,
                            service_column=(
                                service_column
                            ),
                            department_column=(
                                department_column
                            ),
                            fixed_department=(
                                fixed_department
                            ),
                            response_id_column=(
                                response_id_column
                            ),
                            date_column=(
                                date_column
                            ),
                            year_column=(
                                year_column
                            ),
                            period_column=(
                                period_column
                            ),
                            fixed_year=(
                                fixed_year
                            ),
                            fixed_period=(
                                fixed_period
                            ),
                            csat_columns=(
                                csat_columns
                            ),
                            ces_columns=(
                                ces_columns
                            ),
                            nps_column=(
                                nps_column
                            ),
                            calculated_csat_column=(
                                calculated_csat_column
                            ),
                            calculated_ces_column=(
                                calculated_ces_column
                            ),
                            calculated_nps_column=(
                                calculated_nps_column
                            ),
                            participants_column=(
                                participants_column
                            ),
                            comment_columns=(
                                comment_columns
                            ),
                        )
                    )

                    result = save_uploaded_records(
                        prepared_records
                    )

                if result["ok"]:
                    st.success(
                        "تم حفظ البيانات في قاعدة البيانات بنجاح. "
                        f"السجلات الجديدة: "
                        f"{result['inserted_records']}، "
                        f"السجلات المحدثة: "
                        f"{result['updated_records']}، "
                        f"نتائج المؤشرات المحفوظة: "
                        f"{result['saved_indicators']}."
                    )

                else:
                    for error_message in result[
                        "errors"
                    ]:
                        st.error(error_message)

            except ValueError as error:
                st.error(str(error))

            except Exception as error:
                st.error(
                    "حدث خطأ أثناء معالجة الملف: "
                    f"{error}"
                )