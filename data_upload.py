import re

import pandas as pd
import streamlit as st

from data_service import (
    CALCULATED_DATA,
    RAW_DATA,
    prepare_uploaded_records,
)
from entry_backend import (
    get_factors,
    save_uploaded_records,
)
from style import apply_theme


apply_theme()


st.markdown(
    """
    <style>
    div[data-testid="stMainBlockContainer"] {
        direction: rtl;
        text-align: right;
    }

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

    div[data-baseweb="select"] > div,
    div[data-baseweb="select"] span,
    div[data-baseweb="input"] > div,
    div[data-baseweb="input"] input {
        direction: rtl;
        text-align: right;
    }

    div[role="radiogroup"] {
        direction: rtl;
        justify-content: flex-start;
    }

    div[role="radiogroup"] label,
    div[data-baseweb="tag"],
    div[data-testid="stAlert"],
    div[data-testid="stButton"],
    details {
        direction: rtl;
        text-align: right;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# خيارات الواجهة
# ==================================================

NO_COLUMN = "غير موجود"

SECTION_NONE = "لا يوجد قسم داخل الملف"
SECTION_FROM_COLUMN = "يوجد عمود قسم داخل الملف"

TIME_FROM_DATE = "يوجد عمود تاريخ"
TIME_FROM_COMBINED = "السنة والفترة في عمود واحد"
TIME_FROM_COLUMNS = "السنة والفترة في عمودين منفصلين"
TIME_FIXED = "سنة وفترة واحدة لكل الملف"

RAW_DATA_LABEL = "إجابات استبيان خام"
CALCULATED_DATA_LABEL = "نتائج محسوبة مسبقًا"

FIRST_HALF = "النصف الأول"
SECOND_HALF = "النصف الثاني"


# ==================================================
# دوال مساعدة
# ==================================================

def find_default_index(options, preferred_names):
    """اختيار العمود المتوقع تلقائيًا إذا كان موجودًا."""
    for name in preferred_names:
        if name in options:
            return options.index(name)

    return 0


def find_default_columns(columns, preferred_names):
    """اختيار الأعمدة المتوقعة تلقائيًا."""
    return [
        name
        for name in preferred_names
        if name in columns
    ]


def parse_year_period(value):
    """
    استخراج السنة والفترة من قيمة واحدة.

    يقبل مثلًا:
    - النصف الأول 2025
    - النصف الثاني 2025
    - 2025 H1
    - H2 2025

    لكنه يعيد الفترة بالعربية دائمًا.
    """
    if pd.isna(value):
        raise ValueError(
            "قيمة السنة والفترة فارغة."
        )

    text = str(value).strip()
    text = text.translate(
        str.maketrans(
            "٠١٢٣٤٥٦٧٨٩",
            "0123456789",
        )
    )

    normalized = (
        text.lower()
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("_", " ")
        .replace("-", " ")
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    ).strip()

    year_match = re.search(
        r"\b(?:19|20)\d{2}\b",
        normalized,
    )

    if not year_match:
        raise ValueError(
            f"تعذر استخراج السنة من القيمة: {text}"
        )

    year = int(year_match.group())

    first_half_patterns = [
        "النصف الاول",
        "النصف 1",
        "h1",
        "half 1",
        "first half",
    ]

    second_half_patterns = [
        "النصف الثاني",
        "النصف 2",
        "h2",
        "half 2",
        "second half",
    ]

    if any(
        pattern in normalized
        for pattern in first_half_patterns
    ):
        period = FIRST_HALF

    elif any(
        pattern in normalized
        for pattern in second_half_patterns
    ):
        period = SECOND_HALF

    else:
        raise ValueError(
            "تعذر تحديد النصف الأول أو الثاني "
            f"من القيمة: {text}"
        )

    return year, period


def build_factor_mapping(
    factor_rows,
    available_columns,
    key_prefix,
    calculated=False,
):
    """
    عرض اختيار مستقل لكل عامل ثابت موجود في الداتابيس.

    الناتج:
        {اسم العامل: اسم عمود Excel}
    """
    mapping = {}
    options = [NO_COLUMN] + available_columns

    for index, factor in enumerate(factor_rows):
        factor_name = factor["name"]

        preferred_names = [
            factor_name,
            factor_name.replace(" ", "_"),
        ]

        default_index = find_default_index(
            options,
            preferred_names,
        )

        label = (
            f"عمود نتيجة: {factor_name} *"
            if calculated
            else f"عمود إجابات: {factor_name} *"
        )

        selected_column = st.selectbox(
            label,
            options=options,
            index=default_index,
            key=f"{key_prefix}_{index}",
        )

        if selected_column != NO_COLUMN:
            mapping[factor_name] = selected_column

    return mapping


def validate_factor_mapping(
    mapping,
    factor_names,
    field_name,
):
    """التحقق من ربط العوامل السبعة كاملة بدون تكرار."""
    errors = []

    missing = [
        factor_name
        for factor_name in factor_names
        if factor_name not in mapping
    ]

    if missing:
        errors.append(
            f"{field_name}: يجب تحديد عمود لكل عامل. "
            "العوامل غير المرتبطة: "
            + "، ".join(missing)
        )

    selected_columns = list(mapping.values())

    if len(selected_columns) != len(
        set(selected_columns)
    ):
        errors.append(
            f"{field_name}: لا يمكن استخدام العمود "
            "نفسه لأكثر من عامل."
        )

    return errors


# ==================================================
# عنوان الصفحة
# ==================================================

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


# ==================================================
# رفع الملف
# ==================================================

uploaded_file = st.file_uploader(
    "اسحب ملف Excel هنا أو اضغط للاختيار",
    type=["xlsx", "xls"],
)


if uploaded_file is not None:
    try:
        dataframe = pd.read_excel(
            uploaded_file
        )

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

    try:
        factor_rows = get_factors()

    except Exception as error:
        st.error(
            "تعذر قراءة عوامل CSAT من قاعدة البيانات: "
            f"{error}"
        )
        st.stop()

    if len(factor_rows) != 7:
        st.error(
            "يجب أن يحتوي جدول Factors على سبعة عوامل "
            f"بالضبط. الموجود حاليًا: {len(factor_rows)}. "
            "شغلي seed_data.py بعد إضافة الأسماء الرسمية."
        )
        st.stop()

    factor_names = [
        factor["name"]
        for factor in factor_rows
    ]

    available_columns = (
        dataframe.columns.tolist()
    )

    optional_columns = [
        NO_COLUMN,
        *available_columns,
    ]

    st.success(
        "تمت قراءة الملف بنجاح — "
        f"عدد الصفوف: {len(dataframe)}"
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

    # ==================================================
    # 1. البيانات الأساسية
    # ==================================================

    with st.container(border=True):
        st.markdown(
            "## 1. البيانات الأساسية"
        )

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

        st.markdown("#### القسم")

        section_mode = st.radio(
            "طريقة تحديد القسم",
            options=[
                SECTION_NONE,
                SECTION_FROM_COLUMN,
            ],
            index=0,
            horizontal=True,
            label_visibility="collapsed",
        )

        section_column = None
        fixed_section = "غير محدد"

        if section_mode == SECTION_FROM_COLUMN:
            section_column = st.selectbox(
                "عمود اسم القسم",
                options=available_columns,
                index=find_default_index(
                    available_columns,
                    [
                        "اسم_القسم",
                        "اسم القسم",
                        "القسم",
                        "Section",
                        "Section Name",
                        "Department",
                    ],
                ),
            )

            fixed_section = None

        else:
            st.caption(
                'سيُحفظ القسم تلقائيًا باسم "غير محدد".'
            )

        st.markdown("#### السنة والفترة")

        time_mode = st.radio(
            "طريقة تحديد السنة والفترة",
            options=[
                TIME_FROM_DATE,
                TIME_FROM_COMBINED,
                TIME_FROM_COLUMNS,
                TIME_FIXED,
            ],
            index=1,
            horizontal=True,
            label_visibility="collapsed",
        )

        combined_time_column = None
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
                    "ويحفظ الفترة باسم النصف الأول "
                    "أو النصف الثاني حسب الشهر."
                ),
            )

        elif time_mode == TIME_FROM_COMBINED:
            combined_time_column = st.selectbox(
                "عمود السنة والفترة *",
                options=available_columns,
                index=find_default_index(
                    available_columns,
                    [
                        "فترة القياس",
                        "السنة والفترة",
                        "السنة و الفترة",
                        "الفترة الزمنية",
                        "Measurement Period",
                        "Period",
                    ],
                ),
                help=(
                    "أمثلة مقبولة: النصف الأول 2025، "
                    "النصف الثاني 2025. ويمكن قراءة H1 وH2 "
                    "من الملف لكنهما سيُحفظان بالعربية."
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
                        "القيم الأساسية: النصف الأول "
                        "والنصف الثاني. ويمكن قراءة H1 وH2 "
                        "لكن التخزين سيكون بالعربية."
                    ),
                )

        else:
            fixed_col1, fixed_col2 = (
                st.columns(2)
            )

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
                        FIRST_HALF,
                        SECOND_HALF,
                    ],
                )

    # ==================================================
    # 2. العوامل والمؤشرات
    # ==================================================

    with st.container(border=True):
        st.markdown(
            "## 2. عوامل CSAT والمؤشرات"
        )

        data_mode_label = st.radio(
            "نوع البيانات الموجودة داخل الملف",
            options=[
                RAW_DATA_LABEL,
                CALCULATED_DATA_LABEL,
            ],
            horizontal=True,
        )

        response_id_column = None
        factor_column_mapping = {}
        calculated_factor_column_mapping = {}
        ces_columns = []
        nps_column = None
        calculated_ces_column = None
        calculated_nps_column = None
        calculated_bps_column = None
        participants_column = None

        if data_mode_label == RAW_DATA_LABEL:
            st.caption(
                "حددي عمود الإجابات المقابل لكل عامل من "
                "العوامل السبعة، وسيحسب النظام نتيجة كل عامل."
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

            st.markdown(
                "#### ربط العوامل السبعة بأعمدة الإجابات"
            )

            factor_column_mapping = build_factor_mapping(
                factor_rows=factor_rows,
                available_columns=available_columns,
                key_prefix="raw_factor",
                calculated=False,
            )

            default_ces_columns = find_default_columns(
                available_columns,
                [
                    "CES",
                    "سهولة الاستخدام",
                    "الجهد المبذول",
                ],
            )

            ces_columns = st.multiselect(
                "أسئلة CES",
                options=available_columns,
                default=default_ces_columns,
                help=(
                    "يمكن اختيار أكثر من سؤال. سيحسب النظام "
                    "CES لكل سؤال ثم يأخذ المتوسط."
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
                "طريقة حساب النتائج"
            ):
                st.markdown(
                    """
                    - **كل عامل CSAT:** نسبة التقييمات 4 و5 من مقياس 1–5.
                    - **CSAT العام:** متوسط نتائج العوامل السبعة، ويُحفظ تلقائيًا ضمن نتائج المؤشرات.
                    - **CES:** نسبة الإجابات السهلة 4–5 ناقص نسبة الإجابات الصعبة 1–2.
                    - **NPS:** نسبة الموصين 9–10 ناقص نسبة غير الموصين 0–6.
                    - القيم خارج نطاق السؤال، مثل 99، تُستبعد.
                    """
                )

        else:
            st.caption(
                "حددي عمود النتيجة النهائية المقابل لكل عامل. "
                "لن يعيد النظام حساب هذه النتائج."
            )

            st.markdown(
                "#### ربط العوامل السبعة بأعمدة النتائج"
            )

            calculated_factor_column_mapping = (
                build_factor_mapping(
                    factor_rows=factor_rows,
                    available_columns=available_columns,
                    key_prefix="calculated_factor",
                    calculated=True,
                )
            )

            calculated_col1, calculated_col2, calculated_col3 = (
                st.columns(3)
            )

            with calculated_col1:
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

            with calculated_col2:
                nps_selection = st.selectbox(
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

                if nps_selection != NO_COLUMN:
                    calculated_nps_column = (
                        nps_selection
                    )

            with calculated_col3:
                bps_selection = st.selectbox(
                    "عمود قيمة BPS",
                    options=optional_columns,
                    index=find_default_index(
                        optional_columns,
                        [
                            "BPS",
                            "BPS الحالي",
                            "Current BPS",
                        ],
                    ),
                )

                if bps_selection != NO_COLUMN:
                    calculated_bps_column = (
                        bps_selection
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
                    "إذا لم يوجد العمود، سيعتمد النظام على عدد الصفوف."
                ),
            )

            if participants_selection != NO_COLUMN:
                participants_column = (
                    participants_selection
                )

    # ==================================================
    # 3. التعليقات
    # ==================================================

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

    # ==================================================
    # التحقق والحفظ
    # ==================================================

    save_button = st.button(
        "التحقق وحفظ البيانات",
        type="primary",
        use_container_width=True,
    )

    if save_button:
        errors = []

        if data_mode_label == RAW_DATA_LABEL:
            errors.extend(
                validate_factor_mapping(
                    mapping=factor_column_mapping,
                    factor_names=factor_names,
                    field_name="عوامل CSAT",
                )
            )

            factor_columns = set(
                factor_column_mapping.values()
            )

            repeated_factor_ces = (
                factor_columns.intersection(
                    ces_columns
                )
            )

            if repeated_factor_ces:
                errors.append(
                    "لا يمكن استخدام العمود نفسه كعامل CSAT "
                    "وسؤال CES: "
                    + "، ".join(
                        sorted(repeated_factor_ces)
                    )
                )

            if (
                nps_column is not None
                and (
                    nps_column in factor_columns
                    or nps_column in ces_columns
                )
            ):
                errors.append(
                    "لا يمكن استخدام عمود NPS ضمن عوامل "
                    "CSAT أو أسئلة CES."
                )

        else:
            errors.extend(
                validate_factor_mapping(
                    mapping=(
                        calculated_factor_column_mapping
                    ),
                    factor_names=factor_names,
                    field_name="نتائج عوامل CSAT",
                )
            )

            selected_columns = [
                *calculated_factor_column_mapping.values(),
                *[
                    column
                    for column in [
                        calculated_ces_column,
                        calculated_nps_column,
                        calculated_bps_column,
                    ]
                    if column is not None
                ],
            ]

            if len(selected_columns) != len(
                set(selected_columns)
            ):
                errors.append(
                    "لا يمكن استخدام العمود نفسه لأكثر من "
                    "عامل أو مؤشر."
                )

        if errors:
            for error_message in errors:
                st.error(error_message)

        else:
            try:
                data_mode = (
                    RAW_DATA
                    if data_mode_label == RAW_DATA_LABEL
                    else CALCULATED_DATA
                )

                with st.spinner(
                    "جاري تجهيز الملف وحفظ البيانات..."
                ):
                    processing_dataframe = (
                        dataframe.copy()
                    )

                    if time_mode == TIME_FROM_COMBINED:
                        parsed_values = (
                            processing_dataframe[
                                combined_time_column
                            ]
                            .apply(parse_year_period)
                        )

                        processing_dataframe[
                            "__upload_year__"
                        ] = parsed_values.apply(
                            lambda item: item[0]
                        )

                        processing_dataframe[
                            "__upload_period__"
                        ] = parsed_values.apply(
                            lambda item: item[1]
                        )

                        year_column = "__upload_year__"
                        period_column = (
                            "__upload_period__"
                        )

                    prepared_records = (
                        prepare_uploaded_records(
                            dataframe=processing_dataframe,
                            data_mode=data_mode,
                            service_column=service_column,
                            section_column=section_column,
                            fixed_section=fixed_section,
                            response_id_column=(
                                response_id_column
                            ),
                            date_column=date_column,
                            year_column=year_column,
                            period_column=period_column,
                            fixed_year=fixed_year,
                            fixed_period=fixed_period,
                            factor_column_mapping=(
                                factor_column_mapping
                            ),
                            ces_columns=ces_columns,
                            nps_column=nps_column,
                            calculated_factor_column_mapping=(
                                calculated_factor_column_mapping
                            ),
                            calculated_ces_column=(
                                calculated_ces_column
                            ),
                            calculated_nps_column=(
                                calculated_nps_column
                            ),
                            calculated_bps_column=(
                                calculated_bps_column
                            ),
                            participants_column=(
                                participants_column
                            ),
                            comment_columns=comment_columns,
                        )
                    )

                    result = save_uploaded_records(
                        prepared_records
                    )

                if result["ok"]:
                    st.success(
                        "تم حفظ البيانات في قاعدة البيانات بنجاح. "
                        f"السجلات الجديدة: "
                        f"{result.get('inserted_records', 0)}، "
                        f"السجلات المحدثة: "
                        f"{result.get('updated_records', 0)}، "
                        f"نتائج العوامل المحفوظة: "
                        f"{result.get('saved_factors', 0)}، "
                        f"نتائج المؤشرات المحفوظة: "
                        f"{result.get('saved_indicators', 0)}."
                    )

                else:
                    for error_message in result.get(
                        "errors",
                        [],
                    ):
                        st.error(error_message)

            except ValueError as error:
                st.error(str(error))

            except TypeError as error:
                st.error(
                    "ملفات data_upload.py وdata_service.py "
                    "وentry_backend.py غير متوافقة. "
                    f"التفاصيل: {error}"
                )

            except Exception as error:
                st.error(
                    "حدث خطأ أثناء معالجة الملف: "
                    f"{error}"
                )
