# -*- coding: utf-8 -*-
"""
individuals/data_upload_individuals.py
--------------------------------------
Individual data upload page with AI-based Excel column mapping.

Each row in the file represents one individual survey response.
Gemini receives column names only.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


import hashlib
import json
import re
from datetime import datetime

import pandas as pd
import streamlit as st

try:
    from Individuals.individuals_column_mapper_ai import (
        map_individual_columns_with_ai,
    )
    from Individuals.individuals_upload_backend import (
        VALID_PERIODS,
        get_factors,
        get_indicators,
        prepare_individual_records,
        save_individual_records,
    )

except ModuleNotFoundError:
    from individuals_column_mapper_ai import (
        map_individual_columns_with_ai,
    )
    from individuals_upload_backend import (
        VALID_PERIODS,
        get_factors,
        get_indicators,
        prepare_individual_records,
        save_individual_records,
    )

# Automatically refresh cached result tables after a successful upload.
try:
    from refresh_individual_cache import refresh as refresh_individual_cache
except ModuleNotFoundError:
    refresh_individual_cache = None

from style import apply_theme


apply_theme()


# Page styling

st.markdown(
    """
    <style>
    div[data-testid="stMainBlockContainer"] {
        direction: rtl;
        text-align: right;
        max-width: 1350px;
        padding-top: 1.5rem;
    }

    div[data-testid="stMarkdownContainer"],
    div[data-testid="stCaptionContainer"],
    label[data-testid="stWidgetLabel"],
    div[data-testid="stAlert"] {
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

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px !important;
        border: 1px solid #E7E8F1 !important;
        box-shadow: 0 5px 18px rgba(22, 33, 62, 0.04);
        background: #FFFFFF;
    }

    .upload-header {
        background: #FFFFFF;
        border: 1px solid #E7E8F1;
        border-radius: 18px;
        padding: 24px 28px;
        margin-bottom: 18px;
    }

    .upload-header h1 {
        color: #16213E;
        font-size: 32px;
        font-weight: 850;
        margin: 0 0 7px;
    }

    .upload-header p {
        color: #7A7F94;
        font-size: 15px;
        margin: 0;
        line-height: 1.8;
    }

    .privacy-text {
        color: #2FA88E;
        font-size: 13px;
        font-weight: 750;
        margin-top: 10px;
    }

    .section-title {
        color: #16213E;
        font-size: 20px;
        font-weight: 850;
        margin-bottom: 4px;
    }

    .section-description {
        color: #7A7F94;
        font-size: 14px;
        margin-bottom: 12px;
    }

    .summary-value {
        color: #16213E;
        font-size: 20px;
        font-weight: 800;
        margin-top: -5px;
        overflow-wrap: anywhere;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Constants

NO_COLUMN = "غير موجود"

TIME_LABELS = {
    "date": "من عمود تاريخ",
    "combined": "السنة والربع في عمود واحد",
    "separate": "السنة والربع في عمودين",
    "fixed": "سنة وربع ثابتان لكل الملف",
}

DEMOGRAPHIC_FIELDS = {
    "gender_column": "الجنس",
    "age_group_column": "الفئة العمرية",
    "id_type_column": "نوع الهوية",
    "education_column": "المستوى التعليمي",
    "device_column": "الجهاز",
    "region_column": "المنطقة",
}


# Helper functions

def mapping_signature(
    column_names,
    factor_names,
    indicator_names,
):
    payload = json.dumps(
        {
            "columns": column_names,
            "factors": factor_names,
            "indicators": indicator_names,
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def option_index(
    options,
    selected,
):
    if selected in options:
        return options.index(selected)

    return 0


def optional_column(
    label,
    columns,
    selected=None,
    *,
    key,
    help=None,
):
    options = [
        NO_COLUMN,
        *columns,
    ]

    selected_value = st.selectbox(
        label,
        options=options,
        index=option_index(
            options,
            selected,
        ),
        key=key,
        help=help,
    )

    if selected_value == NO_COLUMN:
        return None

    return selected_value


def clear_review_state():
    keys_to_remove = [
        key
        for key in st.session_state
        if (
            str(key).startswith(
                "individual_review_"
            )
            or str(key).startswith(
                "individual_factor_"
            )
            or str(key).startswith(
                "individual_indicator_"
            )
        )
    ]

    for key in keys_to_remove:
        st.session_state.pop(
            key,
            None,
        )


def parse_year_quarter(value):
    """
    Extract the year and quarter from values such as:
    الربع الأول 2026
    2026 Q2
    """
    if pd.isna(value):
        raise ValueError(
            "قيمة السنة والربع فارغة."
        )

    original = str(value).strip()

    text = original.translate(
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
            f"تعذر استخراج السنة من القيمة: {original}"
        )

    patterns = {
        "الربع الأول": [
            "الربع الاول",
            "ربع اول",
            "q1",
            "quarter 1",
        ],
        "الربع الثاني": [
            "الربع الثاني",
            "ربع ثاني",
            "q2",
            "quarter 2",
        ],
        "الربع الثالث": [
            "الربع الثالث",
            "ربع ثالث",
            "q3",
            "quarter 3",
        ],
        "الربع الرابع": [
            "الربع الرابع",
            "ربع رابع",
            "q4",
            "quarter 4",
        ],
    }

    quarter = None

    for quarter_name, aliases in (
        patterns.items()
    ):
        if any(
            alias in normalized
            for alias in aliases
        ):
            quarter = quarter_name
            break

    if quarter is None:
        raise ValueError(
            f"تعذر تحديد الربع من القيمة: {original}"
        )

    return int(year_match.group()), quarter


def required_gaps(
    mapping,
    factor_names,
):
    gaps = []

    time_mode = mapping.get(
        "time_mode"
    )

    if time_mode == "date":
        if not mapping.get(
            "date_column"
        ):
            gaps.append(
                "التاريخ"
            )

    elif time_mode == "combined":
        if not mapping.get(
            "combined_time_column"
        ):
            gaps.append(
                "السنة والربع"
            )

    elif time_mode == "separate":
        if not mapping.get(
            "year_column"
        ):
            gaps.append(
                "السنة"
            )

        if not mapping.get(
            "period_column"
        ):
            gaps.append(
                "الربع"
            )

    else:
        gaps.append(
            "طريقة السنة والربع"
        )

    factor_mapping = mapping.get(
        "factor_mappings",
        {},
    )

    for factor_name in factor_names:
        if not factor_mapping.get(
            factor_name
        ):
            gaps.append(
                factor_name
            )

    return gaps


def combine_reviews(
    dataframe,
    selected_columns,
):
    """
    Combine the selected comment columns into one temporary column.
    """
    if not selected_columns:
        return dataframe, None

    output = dataframe.copy()

    def build_review(row):
        parts = []

        for column_name in selected_columns:
            value = row.get(
                column_name
            )

            if pd.isna(value):
                continue

            text = str(value).strip()

            if not text:
                continue

            parts.append(
                f"{column_name}: {text}"
            )

        if not parts:
            return None

        return "\n".join(parts)

    review_column = (
        "__selected_individual_reviews__"
    )

    output[
        review_column
    ] = output.apply(
        build_review,
        axis=1,
    )

    return output, review_column


def validate_mapping(
    *,
    time_mode,
    date_column,
    combined_time_column,
    year_column,
    period_column,
    factor_columns,
    indicator_columns,
):
    errors = []

    if (
        time_mode == "date"
        and not date_column
    ):
        errors.append(
            "عمود التاريخ مطلوب."
        )

    elif (
        time_mode == "combined"
        and not combined_time_column
    ):
        errors.append(
            "عمود السنة والربع مطلوب."
        )

    elif time_mode == "separate":
        if not year_column:
            errors.append(
                "عمود السنة مطلوب."
            )

        if not period_column:
            errors.append(
                "عمود الربع مطلوب."
            )

    missing_factors = [
        factor_name
        for factor_name, column_name
        in factor_columns.items()
        if not column_name
    ]

    if missing_factors:
        errors.append(
            "لم يتم ربط عوامل CSAT التالية: "
            + "، ".join(
                missing_factors
            )
        )

    used_columns = [
        column_name
        for column_name in [
            *factor_columns.values(),
            *indicator_columns.values(),
        ]
        if column_name
    ]

    if len(used_columns) != len(
        set(used_columns)
    ):
        errors.append(
            "لا يمكن استخدام عمود واحد لأكثر من عامل أو مؤشر."
        )

    return errors


# Page header

st.markdown(
    """
    <div class="upload-header" dir="rtl">
        <h1>رفع بيانات الأفراد</h1>
        <p>
            ارفع ملف Excel، وسيطابق Gemini أسماء الأعمدة تلقائيًا.
            افتح المراجعة فقط للتأكد أو تعديل المطابقة.
        </p>
        <div class="privacy-text">
            يتم إرسال أسماء الأعمدة فقط إلى Gemini
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# Read reference data

try:
    factors = get_factors()
    indicators = get_indicators()

except Exception as error:
    st.error(
        "تعذر قراءة عوامل ومؤشرات الأفراد "
        f"من قاعدة البيانات: {error}"
    )
    st.stop()


if not factors:
    st.error(
        "جدول SharedCSATFactors فارغ. "
        "شغلي database_individuals.sync_reference_data."
    )
    st.stop()


factor_names = [
    factor["name"]
    for factor in factors
]

indicator_names = [
    indicator["name"]
    for indicator in indicators
]


# Upload file

uploaded_file = st.file_uploader(
    "ملف Excel",
    type=[
        "xlsx",
        "xls",
    ],
)

if uploaded_file is None:
    st.stop()


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


columns = (
    dataframe.columns.tolist()
)

signature = mapping_signature(
    columns,
    factor_names,
    indicator_names,
)

if (
    st.session_state.get(
        "individual_mapping_signature"
    )
    != signature
):
    st.session_state.pop(
        "individual_ai_mapping",
        None,
    )

    clear_review_state()

    st.session_state[
        "individual_mapping_signature"
    ] = signature


# File setup

with st.container(
    border=True
):
    st.markdown(
        '<div class="section-title">إعداد الملف</div>',
        unsafe_allow_html=True,
    )

    file_col, rows_col, columns_col = (
        st.columns(
            [1.5, 1, 1]
        )
    )

    with file_col:
        st.caption(
            "اسم الملف"
        )
        st.markdown(
            f'<div class="summary-value">'
            f'{uploaded_file.name}'
            f'</div>',
            unsafe_allow_html=True,
        )

    with rows_col:
        st.caption(
            "عدد الصفوف"
        )
        st.markdown(
            f'<div class="summary-value">'
            f'{len(dataframe):,}'
            f'</div>',
            unsafe_allow_html=True,
        )

    with columns_col:
        st.caption(
            "عدد الأعمدة"
        )
        st.markdown(
            f'<div class="summary-value">'
            f'{len(columns):,}'
            f'</div>',
            unsafe_allow_html=True,
        )

    with st.expander(
        "معاينة أول 15 صفًا",
        expanded=False,
    ):
        st.dataframe(
            dataframe.head(15),
            use_container_width=True,
            hide_index=True,
        )

    analyze_clicked = st.button(
        "تحليل أسماء الأعمدة",
        type="primary",
        use_container_width=True,
    )


if analyze_clicked:
    try:
        with st.spinner(
            "جاري مطابقة أسماء الأعمدة..."
        ):
            st.session_state[
                "individual_ai_mapping"
            ] = map_individual_columns_with_ai(
                column_names=columns,
                factor_names=factor_names,
                indicator_names=indicator_names,
            )

        clear_review_state()
        st.rerun()

    except Exception as error:
        st.error(
            f"تعذر تحليل أسماء الأعمدة: {error}"
        )


mapping = st.session_state.get(
    "individual_ai_mapping"
)

if not mapping:
    st.stop()


# Mapping summary

gaps = required_gaps(
    mapping,
    factor_names,
)

factor_mapping_from_ai = mapping.get(
    "factor_mappings",
    {},
)

indicator_mapping_from_ai = mapping.get(
    "indicator_mappings",
    {},
)

matched_factors = sum(
    1
    for factor_name in factor_names
    if factor_mapping_from_ai.get(
        factor_name
    )
)

matched_demographics = sum(
    1
    for field_name in DEMOGRAPHIC_FIELDS
    if mapping.get(
        field_name
    )
)

matched_indicators = [
    indicator_name
    for indicator_name in indicator_names
    if indicator_mapping_from_ai.get(
        indicator_name
    )
]

time_mode_from_ai = mapping.get(
    "time_mode"
)

time_ready = (
    (
        time_mode_from_ai == "date"
        and mapping.get(
            "date_column"
        )
    )
    or (
        time_mode_from_ai == "combined"
        and mapping.get(
            "combined_time_column"
        )
    )
    or (
        time_mode_from_ai == "separate"
        and mapping.get(
            "year_column"
        )
        and mapping.get(
            "period_column"
        )
    )
)


with st.container(
    border=True
):
    st.markdown(
        '<div class="section-title">المطابقة جاهزة</div>',
        unsafe_allow_html=True,
    )

    summary1, summary2, summary3, summary4 = (
        st.columns(4)
    )

    with summary1:
        st.caption(
            "بيانات الفرد"
        )
        st.markdown(
            f"**{matched_demographics} / "
            f"{len(DEMOGRAPHIC_FIELDS)}**"
        )

    with summary2:
        st.caption(
            "عوامل CSAT"
        )
        st.markdown(
            f"**{matched_factors} / "
            f"{len(factor_names)}**"
        )

    with summary3:
        st.caption(
            "المؤشرات"
        )
        st.markdown(
            "**"
            + (
                " و ".join(
                    matched_indicators
                )
                if matched_indicators
                else "غير موجودة"
            )
            + "**"
        )

    with summary4:
        st.caption(
            "الفترة"
        )
        st.markdown(
            "**"
            + (
                TIME_LABELS.get(
                    time_mode_from_ai,
                    "تحتاج مراجعة",
                )
                if time_ready
                else "تحتاج مراجعة"
            )
            + "**"
        )

    if gaps:
        st.warning(
            "يلزم مراجعة: "
            + "، ".join(gaps)
        )
    else:
        st.success(
            "تم التعرف على الفترة وجميع عوامل CSAT."
        )


# Suggested values

individual_id_column = mapping.get(
    "individual_id_column"
)

time_mode = mapping.get(
    "time_mode"
)

if time_mode not in TIME_LABELS:
    time_mode = "fixed"

date_column = mapping.get(
    "date_column"
)

combined_time_column = mapping.get(
    "combined_time_column"
)

year_column = mapping.get(
    "year_column"
)

period_column = mapping.get(
    "period_column"
)

fixed_year = (
    datetime.now().year
    if time_mode == "fixed"
    else None
)

fixed_period = (
    VALID_PERIODS[0]
    if time_mode == "fixed"
    else None
)

gender_column = mapping.get(
    "gender_column"
)

age_group_column = mapping.get(
    "age_group_column"
)

id_type_column = mapping.get(
    "id_type_column"
)

education_column = mapping.get(
    "education_column"
)

device_column = mapping.get(
    "device_column"
)

region_column = mapping.get(
    "region_column"
)

factor_columns = {
    factor_name: factor_mapping_from_ai.get(
        factor_name
    )
    for factor_name in factor_names
}

indicator_columns = {
    indicator_name: indicator_mapping_from_ai.get(
        indicator_name
    )
    for indicator_name in indicator_names
}


# Review and edit mapping

with st.expander(
    "مراجعة وتعديل المطابقة",
    expanded=bool(gaps),
):
    st.caption(
        "جميع الاختيارات الحالية ظاهرة هنا. "
        "راجعيها وعدّلي غير الصحيح فقط."
    )

    individual_id_column = optional_column(
        "عمود IndividualID",
        columns,
        individual_id_column,
        key="individual_review_id",
        help=(
            "اختاريه فقط عند تحديث أفراد موجودين مسبقًا. "
            "اتركيه غير موجود عند رفع أفراد جدد."
        ),
    )

    time_mode_options = list(
        TIME_LABELS.keys()
    )

    time_mode = st.selectbox(
        "طريقة تحديد السنة والربع",
        options=time_mode_options,
        index=time_mode_options.index(
            time_mode
        ),
        format_func=lambda value: (
            TIME_LABELS[value]
        ),
        key="individual_review_time_mode",
    )

    date_column = (
        date_column
        if time_mode == "date"
        else None
    )

    combined_time_column = (
        combined_time_column
        if time_mode == "combined"
        else None
    )

    year_column = (
        year_column
        if time_mode == "separate"
        else None
    )

    period_column = (
        period_column
        if time_mode == "separate"
        else None
    )

    fixed_year = (
        fixed_year
        if time_mode == "fixed"
        else None
    )

    fixed_period = (
        fixed_period
        if time_mode == "fixed"
        else None
    )

    if time_mode == "date":
        date_column = optional_column(
            "عمود التاريخ *",
            columns,
            date_column,
            key="individual_review_date",
        )

    elif time_mode == "combined":
        combined_time_column = optional_column(
            "عمود السنة والربع *",
            columns,
            combined_time_column,
            key="individual_review_combined",
        )

    elif time_mode == "separate":
        year_col, period_col = (
            st.columns(2)
        )

        with year_col:
            year_column = optional_column(
                "عمود السنة *",
                columns,
                year_column,
                key="individual_review_year",
            )

        with period_col:
            period_column = optional_column(
                "عمود الربع *",
                columns,
                period_column,
                key="individual_review_period",
            )

    else:
        year_col, period_col = (
            st.columns(2)
        )

        with year_col:
            fixed_year = st.number_input(
                "السنة *",
                min_value=2000,
                max_value=2100,
                value=int(
                    fixed_year
                    or datetime.now().year
                ),
                step=1,
                key="individual_review_fixed_year",
            )

        with period_col:
            fixed_period = st.selectbox(
                "الربع *",
                options=list(
                    VALID_PERIODS
                ),
                index=(
                    list(VALID_PERIODS).index(
                        fixed_period
                    )
                    if fixed_period
                    in VALID_PERIODS
                    else 0
                ),
                key="individual_review_fixed_period",
            )

    st.markdown(
        "#### بيانات الفرد"
    )

    demographic_col1, demographic_col2 = (
        st.columns(2)
    )

    with demographic_col1:
        gender_column = optional_column(
            "عمود الجنس",
            columns,
            gender_column,
            key="individual_review_gender",
        )

        id_type_column = optional_column(
            "عمود نوع الهوية",
            columns,
            id_type_column,
            key="individual_review_id_type",
        )

        device_column = optional_column(
            "عمود الجهاز",
            columns,
            device_column,
            key="individual_review_device",
        )

    with demographic_col2:
        age_group_column = optional_column(
            "عمود الفئة العمرية",
            columns,
            age_group_column,
            key="individual_review_age_group",
        )

        education_column = optional_column(
            "عمود المستوى التعليمي",
            columns,
            education_column,
            key="individual_review_education",
        )

        region_column = optional_column(
            "عمود المنطقة",
            columns,
            region_column,
            key="individual_review_region",
        )

    st.markdown(
        "#### عوامل CSAT"
    )

    factor_ui_columns = st.columns(2)

    for index, factor_name in enumerate(
        factor_names
    ):
        with factor_ui_columns[
            index % 2
        ]:
            factor_columns[
                factor_name
            ] = optional_column(
                factor_name,
                columns,
                factor_columns.get(
                    factor_name
                ),
                key=(
                    f"individual_factor_"
                    f"{index}"
                ),
            )

    if indicator_names:
        st.markdown(
            "#### المؤشرات"
        )

        indicator_ui_columns = (
            st.columns(2)
        )

        for index, indicator_name in enumerate(
            indicator_names
        ):
            with indicator_ui_columns[
                index % 2
            ]:
                indicator_columns[
                    indicator_name
                ] = optional_column(
                    indicator_name,
                    columns,
                    indicator_columns.get(
                        indicator_name
                    ),
                    key=(
                        f"individual_indicator_"
                        f"{index}"
                    ),
                )


# Comments and saving

with st.container(
    border=True
):
    st.markdown(
        '<div class="section-title">التعليقات والحفظ</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-description">'
        'اختاري أعمدة التعليقات التي تريدين حفظها فقط.'
        '</div>',
        unsafe_allow_html=True,
    )

    review_columns = st.multiselect(
        "أعمدة التعليقات",
        options=columns,
        default=[],
        placeholder=(
            "اختاري الأعمدة النصية المطلوبة"
        ),
    )

    save_clicked = st.button(
        "حفظ بيانات الأفراد",
        type="primary",
        use_container_width=True,
    )


# Validation and saving

if save_clicked:
    errors = validate_mapping(
        time_mode=time_mode,
        date_column=date_column,
        combined_time_column=(
            combined_time_column
        ),
        year_column=year_column,
        period_column=period_column,
        factor_columns=factor_columns,
        indicator_columns=(
            indicator_columns
        ),
    )

    if errors:
        for error in errors:
            st.error(error)

        st.stop()

    try:
        with st.spinner(
            "جاري تجهيز ملف الأفراد وحفظه..."
        ):
            processing_dataframe = (
                dataframe.copy()
            )

            if time_mode == "combined":
                parsed_values = (
                    processing_dataframe[
                        combined_time_column
                    ]
                    .apply(
                        parse_year_quarter
                    )
                )

                processing_dataframe[
                    "__individual_upload_year__"
                ] = parsed_values.apply(
                    lambda item: item[0]
                )

                processing_dataframe[
                    "__individual_upload_period__"
                ] = parsed_values.apply(
                    lambda item: item[1]
                )

                year_column = (
                    "__individual_upload_year__"
                )

                period_column = (
                    "__individual_upload_period__"
                )

            (
                processing_dataframe,
                review_column,
            ) = combine_reviews(
                processing_dataframe,
                review_columns,
            )

            prepared_records = (
                prepare_individual_records(
                    dataframe=processing_dataframe,
                    individual_id_column=(
                        individual_id_column
                    ),
                    date_column=date_column,
                    year_column=year_column,
                    period_column=period_column,
                    fixed_year=fixed_year,
                    fixed_period=fixed_period,
                    gender_column=gender_column,
                    age_group_column=(
                        age_group_column
                    ),
                    id_type_column=id_type_column,
                    education_column=(
                        education_column
                    ),
                    device_column=device_column,
                    region_column=region_column,
                    review_column=review_column,
                    factor_columns=factor_columns,
                    indicator_columns=(
                        indicator_columns
                    ),
                )
            )

            result = save_individual_records(
                prepared_records
            )

        if result["ok"]:
            # Refresh the cached summary immediately after a successful save.
            if refresh_individual_cache is not None:
                try:
                    refresh_individual_cache()
                except Exception as cache_error:
                    st.warning(
                        "تم حفظ البيانات بنجاح، لكن تعذّر تحديث "
                        f"الملخّص المخزّن مؤقتًا: {cache_error}"
                    )

            st.success(
                "تم حفظ بيانات الأفراد بنجاح. "
                f"ملفات الأفراد الجديدة: "
                f"{result['created_profiles']}، "
                f"سجلات القياس الجديدة: "
                f"{result['inserted_records']}، "
                f"السجلات المحدثة: "
                f"{result['updated_records']}، "
                f"إجابات العوامل: "
                f"{result['saved_factor_responses']}، "
                f"إجابات المؤشرات: "
                f"{result['saved_indicator_responses']}."
            )

        else:
            for error_message in result.get(
                "errors",
                [],
            ):
                st.error(error_message)

    except ValueError as error:
        for message in str(error).splitlines():
            st.error(message)

    except Exception as error:
        st.error(
            "حدث خطأ أثناء معالجة ملف الأفراد: "
            f"{error}"
        )
