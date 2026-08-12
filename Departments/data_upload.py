# -*- coding: utf-8 -*-
"""
data_upload.py
--------------
صفحة رفع بيانات الأقسام والخدمات مع مطابقة ذكية لأسماء الأعمدة.

يرسل النظام إلى Gemini أسماء الأعمدة فقط، ولا يرسل محتوى الصفوف
أو إجابات العملاء أو التعليقات.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime

import pandas as pd
import streamlit as st

from column_mapper_ai import map_section_columns_with_ai
from data_service import (
    CALCULATED_DATA,
    RAW_DATA,
    prepare_uploaded_records,
)
from entry_backend import get_factors, save_uploaded_records
from style import apply_theme


apply_theme()


# ==================================================
# تنسيق الصفحة
# ==================================================

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

    div[data-testid="stDataFrame"] {
        direction: rtl;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# الثوابت
# ==================================================

NO_COLUMN = "غير موجود"

RAW_DATA_LABEL = "إجابات استبيان خام"
CALCULATED_DATA_LABEL = "نتائج محسوبة مسبقًا"

FIRST_HALF = "النصف الأول"
SECOND_HALF = "النصف الثاني"

TIME_LABELS = {
    "date": "من عمود تاريخ",
    "combined": "السنة والفترة في عمود واحد",
    "separate": "السنة والفترة في عمودين",
    "fixed": "سنة وفترة ثابتتان لكل الملف",
}

REVIEW_WIDGET_KEYS = [
    "review_service",
    "review_section",
    "review_time_mode",
    "review_date",
    "review_combined",
    "review_year",
    "review_period",
    "review_ces_raw",
    "review_ces_calculated",
    "review_nps",
    "review_response_id",
    "review_bps",
    "review_participants",
    "review_fixed_year",
    "review_fixed_period",
    "show_all_mapping_fields",
]


# ==================================================
# أدوات مساعدة
# ==================================================

def mapping_signature(column_names, factor_names, data_mode):
    payload = json.dumps(
        {
            "columns": column_names,
            "factors": factor_names,
            "mode": data_mode,
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    return hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


def clear_review_state():
    keys = list(REVIEW_WIDGET_KEYS)

    keys.extend(
        key
        for key in st.session_state
        if str(key).startswith("review_factor_")
    )

    for key in keys:
        st.session_state.pop(key, None)


def option_index(options, selected):
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
    options = [NO_COLUMN, *columns]

    selected_value = st.selectbox(
        label,
        options=options,
        index=option_index(options, selected),
        key=key,
        help=help,
    )

    if selected_value == NO_COLUMN:
        return None

    return selected_value


def parse_year_period(value):
    """استخراج السنة والنصف من قيمة مثل النصف الأول 2026 أو H2 2026."""
    if pd.isna(value):
        raise ValueError("قيمة السنة والفترة فارغة.")

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

    first_patterns = [
        "النصف الاول",
        "النصف 1",
        "h1",
        "half 1",
        "first half",
    ]

    second_patterns = [
        "النصف الثاني",
        "النصف 2",
        "h2",
        "half 2",
        "second half",
    ]

    if any(
        pattern in normalized
        for pattern in first_patterns
    ):
        period = FIRST_HALF

    elif any(
        pattern in normalized
        for pattern in second_patterns
    ):
        period = SECOND_HALF

    else:
        raise ValueError(
            f"تعذر تحديد النصف من القيمة: {original}"
        )

    return int(year_match.group()), period


def required_mapping_gaps(mapping, factor_names):
    gaps = []

    if not mapping.get("service_column"):
        gaps.append("اسم الخدمة")

    time_mode = mapping.get("time_mode")

    if time_mode == "date":
        if not mapping.get("date_column"):
            gaps.append("التاريخ")

    elif time_mode == "combined":
        if not mapping.get("combined_time_column"):
            gaps.append("السنة والفترة")

    elif time_mode == "separate":
        if not mapping.get("year_column"):
            gaps.append("السنة")

        if not mapping.get("period_column"):
            gaps.append("الفترة")

    else:
        gaps.append("طريقة السنة والفترة")

    factor_mapping = mapping.get(
        "factor_mappings",
        {},
    )

    for factor_name in factor_names:
        if not factor_mapping.get(factor_name):
            gaps.append(factor_name)

    return gaps


def validate_mapping(
    *,
    service_column,
    time_mode,
    date_column,
    combined_time_column,
    year_column,
    period_column,
    factor_mapping,
    ces_columns,
    nps_column,
    bps_column,
    data_mode,
):
    errors = []

    if not service_column:
        errors.append("عمود اسم الخدمة مطلوب.")

    if time_mode == "date" and not date_column:
        errors.append("عمود التاريخ مطلوب.")

    elif (
        time_mode == "combined"
        and not combined_time_column
    ):
        errors.append(
            "عمود السنة والفترة مطلوب."
        )

    elif time_mode == "separate":
        if not year_column:
            errors.append("عمود السنة مطلوب.")

        if not period_column:
            errors.append("عمود الفترة مطلوب.")

    missing_factors = [
        factor_name
        for factor_name, column_name
        in factor_mapping.items()
        if not column_name
    ]

    if missing_factors:
        errors.append(
            "لم يتم ربط العوامل التالية: "
            + "، ".join(missing_factors)
        )

    used_columns = [
        column_name
        for column_name in factor_mapping.values()
        if column_name
    ]

    used_columns.extend(ces_columns)

    if nps_column:
        used_columns.append(nps_column)

    if (
        data_mode == "calculated"
        and bps_column
    ):
        used_columns.append(bps_column)

    if len(used_columns) != len(
        set(used_columns)
    ):
        errors.append(
            "لا يمكن استخدام عمود واحد لأكثر من عامل أو مؤشر."
        )

    return errors


# ==================================================
# رأس الصفحة
# ==================================================

st.markdown(
    """
    <div class="upload-header" dir="rtl">
        <h1>رفع البيانات</h1>
        <p>
            ارفع ملف Excel، ثم دع Gemini يطابق أسماء الأعمدة تلقائيًا.
            راجع النتيجة وعدّل الحقول غير الصحيحة.
        </p>
        <div class="privacy-text">
            يتم إرسال أسماء الأعمدة فقط إلى Gemini
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# رفع الملف
# ==================================================

uploaded_file = st.file_uploader(
    "ملف Excel",
    type=["xlsx", "xls"],
)

if uploaded_file is None:
    st.info("ارفع ملف Excel للبدء.")
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
        "جدول Factors يجب أن يحتوي على سبعة عوامل. "
        f"الموجود حاليًا: {len(factor_rows)}."
    )
    st.stop()


factor_names = [
    factor["name"]
    for factor in factor_rows
]

available_columns = (
    dataframe.columns.tolist()
)


# ==================================================
# إعداد الملف والتحليل
# ==================================================

with st.container(border=True):
    st.markdown(
        '<div class="section-title">إعداد الملف</div>',
        unsafe_allow_html=True,
    )

    st.caption("اسم الملف")
    st.markdown(f"**{uploaded_file.name}**")

    info_col1, info_col2 = st.columns(2)

    with info_col1:
        st.caption("عدد الصفوف")
        st.markdown(f"**{len(dataframe):,}**")

    with info_col2:
        st.caption("عدد الأعمدة")
        st.markdown(f"**{len(available_columns):,}**")

    data_mode_label = st.radio(
        "نوع البيانات الموجودة في الملف",
        options=[
            RAW_DATA_LABEL,
            CALCULATED_DATA_LABEL,
        ],
        horizontal=True,
    )

    data_mode = (
        "raw"
        if data_mode_label == RAW_DATA_LABEL
        else "calculated"
    )

    current_signature = mapping_signature(
        available_columns,
        factor_names,
        data_mode,
    )

    previous_signature = st.session_state.get(
        "section_mapping_signature"
    )

    if previous_signature != current_signature:
        st.session_state.pop(
            "section_ai_mapping",
            None,
        )

        clear_review_state()

        st.session_state[
            "section_mapping_signature"
        ] = current_signature

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
                "section_ai_mapping"
            ] = map_section_columns_with_ai(
                column_names=available_columns,
                factor_names=factor_names,
                data_mode=data_mode,
            )

        clear_review_state()
        st.rerun()

    except Exception as error:
        st.error(
            f"تعذر تحليل أسماء الأعمدة: {error}"
        )


mapping = st.session_state.get(
    "section_ai_mapping"
)

if not mapping:
    st.stop()


# ==================================================
# ملخص المطابقة
# ==================================================

gaps = required_mapping_gaps(
    mapping,
    factor_names,
)

factor_mapping_from_ai = mapping.get(
    "factor_mappings",
    {},
)

matched_factor_count = sum(
    1
    for factor_name in factor_names
    if factor_mapping_from_ai.get(factor_name)
)

matched_indicators = []

if mapping.get("ces_columns"):
    matched_indicators.append("CES")

if mapping.get("nps_column"):
    matched_indicators.append("NPS")

if (
    data_mode == "calculated"
    and mapping.get("bps_column")
):
    matched_indicators.append("BPS")

basic_ready = bool(
    mapping.get("service_column")
)

time_mode_from_ai = mapping.get("time_mode")

if time_mode_from_ai == "date":
    time_ready = bool(
        mapping.get("date_column")
    )

elif time_mode_from_ai == "combined":
    time_ready = bool(
        mapping.get("combined_time_column")
    )

elif time_mode_from_ai == "separate":
    time_ready = bool(
        mapping.get("year_column")
        and mapping.get("period_column")
    )

else:
    time_ready = False


with st.container(border=True):
    st.markdown(
        '<div class="section-title">المطابقة جاهزة</div>',
        unsafe_allow_html=True,
    )

    if gaps:
        st.warning(
            "يلزم مراجعة الحقول التالية قبل الحفظ: "
            + "، ".join(gaps)
        )
    else:
        st.success(
            "تم التعرف على جميع الحقول الأساسية والعوامل."
        )

    indicators_text = (
        " و ".join(matched_indicators)
        if matched_indicators
        else "لا توجد مؤشرات مطابقة"
    )

    period_text = (
        TIME_LABELS.get(time_mode_from_ai)
        if time_ready
        else "تحتاج مراجعة"
    )

    st.caption(
        "البيانات الأساسية: "
        + ("مكتملة" if basic_ready else "تحتاج مراجعة")
        + " | عوامل CSAT: "
        + f"{matched_factor_count}/{len(factor_names)}"
        + " | المؤشرات: "
        + indicators_text
        + " | الفترة: "
        + period_text
    )


# ==================================================
# القيم المقترحة التي ستُستخدم في الحفظ
# ==================================================

service_column = mapping.get(
    "service_column"
)

section_column = mapping.get(
    "section_column"
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
    FIRST_HALF
    if time_mode == "fixed"
    else None
)

factor_mapping = {
    factor_name: factor_mapping_from_ai.get(
        factor_name
    )
    for factor_name in factor_names
}

ces_columns = [
    column
    for column in mapping.get(
        "ces_columns",
        [],
    )
    if column in available_columns
]

nps_column = mapping.get(
    "nps_column"
)

response_id_column = mapping.get(
    "response_id_column"
)

participants_column = mapping.get(
    "participants_column"
)

bps_column = mapping.get(
    "bps_column"
)


# ==================================================
# مراجعة وتعديل المطابقة
# ==================================================

with st.expander(
    "مراجعة وتعديل المطابقة",
    expanded=bool(gaps),
):
    st.caption(
        "راجعي الاختيارات التالية. عدّلي فقط الحقل غير الصحيح."
    )

    service_column = optional_column(
        "عمود اسم الخدمة *",
        available_columns,
        service_column,
        key="review_service",
    )

    section_column = optional_column(
        "عمود اسم القسم",
        available_columns,
        section_column,
        key="review_section",
    )

    time_mode_options = list(TIME_LABELS.keys())

    time_mode = st.selectbox(
        "طريقة تحديد السنة والفترة",
        options=time_mode_options,
        index=time_mode_options.index(time_mode),
        format_func=lambda value: TIME_LABELS[value],
        key="review_time_mode",
    )

    date_column = None
    combined_time_column = None
    year_column = None
    period_column = None
    fixed_year = None
    fixed_period = None

    if time_mode == "date":
        date_column = optional_column(
            "عمود التاريخ *",
            available_columns,
            mapping.get("date_column"),
            key="review_date",
        )

    elif time_mode == "combined":
        combined_time_column = optional_column(
            "عمود السنة والفترة *",
            available_columns,
            mapping.get("combined_time_column"),
            key="review_combined",
        )

    elif time_mode == "separate":
        year_col, period_col = st.columns(2)

        with year_col:
            year_column = optional_column(
                "عمود السنة *",
                available_columns,
                mapping.get("year_column"),
                key="review_year",
            )

        with period_col:
            period_column = optional_column(
                "عمود الفترة *",
                available_columns,
                mapping.get("period_column"),
                key="review_period",
            )

    else:
        year_col, period_col = st.columns(2)

        with year_col:
            fixed_year = st.number_input(
                "السنة *",
                min_value=2000,
                max_value=2100,
                value=datetime.now().year,
                step=1,
                key="review_fixed_year",
            )

        with period_col:
            fixed_period = st.selectbox(
                "الفترة *",
                options=[FIRST_HALF, SECOND_HALF],
                key="review_fixed_period",
            )

    st.markdown("#### عوامل CSAT")

    factor_ui_columns = st.columns(2)

    for index, factor_name in enumerate(factor_names):
        with factor_ui_columns[index % 2]:
            factor_mapping[factor_name] = optional_column(
                factor_name,
                available_columns,
                factor_mapping.get(factor_name),
                key=f"review_factor_{index}",
            )

    st.markdown("#### المؤشرات الأخرى")

    ces_col, nps_col = st.columns(2)

    with ces_col:
        if data_mode == "raw":
            ces_columns = st.multiselect(
                "أعمدة CES",
                options=available_columns,
                default=ces_columns,
                key="review_ces_raw",
            )
        else:
            selected_ces = optional_column(
                "عمود نتيجة CES",
                available_columns,
                ces_columns[0] if ces_columns else None,
                key="review_ces_calculated",
            )
            ces_columns = [selected_ces] if selected_ces else []

    with nps_col:
        nps_column = optional_column(
            "عمود إجابات NPS"
            if data_mode == "raw"
            else "عمود نتيجة NPS",
            available_columns,
            nps_column,
            key="review_nps",
        )

    if data_mode == "raw":
        response_id_column = optional_column(
            "عمود رقم الاستجابة",
            available_columns,
            response_id_column,
            key="review_response_id",
        )
    else:
        bps_col, participants_col = st.columns(2)

        with bps_col:
            bps_column = optional_column(
                "عمود نتيجة BPS",
                available_columns,
                bps_column,
                key="review_bps",
            )

        with participants_col:
            participants_column = optional_column(
                "عمود عدد المشاركين",
                available_columns,
                participants_column,
                key="review_participants",
            )

    warnings = mapping.get("warnings", [])

    if warnings:
        st.caption("ملاحظات النظام")
        for warning in warnings:
            st.write(f"• {warning}")


# ==================================================
# التعليقات والحفظ
# ==================================================

with st.container(border=True):
    st.markdown(
        '<div class="section-title">التعليقات والحفظ</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-description">'
        'اختاري أعمدة التعليقات التي تريدين الاحتفاظ بها فقط.'
        '</div>',
        unsafe_allow_html=True,
    )

    comment_columns = st.multiselect(
        "أعمدة التعليقات",
        options=available_columns,
        default=[],
        placeholder="اختاري الأعمدة النصية المطلوبة",
    )

    save_clicked = st.button(
        "حفظ البيانات في قاعدة البيانات",
        type="primary",
        use_container_width=True,
    )


# ==================================================
# التحقق والحفظ
# ==================================================

if save_clicked:
    errors = validate_mapping(
        service_column=service_column,
        time_mode=time_mode,
        date_column=date_column,
        combined_time_column=combined_time_column,
        year_column=year_column,
        period_column=period_column,
        factor_mapping=factor_mapping,
        ces_columns=ces_columns,
        nps_column=nps_column,
        bps_column=bps_column,
        data_mode=data_mode,
    )

    if errors:
        for error in errors:
            st.error(error)

        st.stop()

    try:
        with st.spinner(
            "جاري تجهيز الملف وحفظ البيانات..."
        ):
            processing_dataframe = (
                dataframe.copy()
            )

            if time_mode == "combined":
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
                period_column = "__upload_period__"

            fixed_section = (
                None
                if section_column
                else "غير محدد"
            )

            factor_column_mapping = {}
            calculated_factor_column_mapping = {}
            raw_ces_columns = []
            raw_nps_column = None
            calculated_ces_column = None
            calculated_nps_column = None
            calculated_bps_column = None

            if data_mode == "raw":
                factor_column_mapping = (
                    factor_mapping
                )

                raw_ces_columns = ces_columns
                raw_nps_column = nps_column

            else:
                calculated_factor_column_mapping = (
                    factor_mapping
                )

                calculated_ces_column = (
                    ces_columns[0]
                    if ces_columns
                    else None
                )

                calculated_nps_column = (
                    nps_column
                )

                calculated_bps_column = (
                    bps_column
                )

            prepared_records = (
                prepare_uploaded_records(
                    dataframe=processing_dataframe,
                    data_mode=(
                        RAW_DATA
                        if data_mode == "raw"
                        else CALCULATED_DATA
                    ),
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
                    ces_columns=raw_ces_columns,
                    nps_column=raw_nps_column,
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
                "تم حفظ البيانات بنجاح. "
                f"السجلات الجديدة: "
                f"{result.get('inserted_records', 0)}، "
                f"السجلات المحدثة: "
                f"{result.get('updated_records', 0)}، "
                f"نتائج العوامل: "
                f"{result.get('saved_factors', 0)}، "
                f"نتائج المؤشرات: "
                f"{result.get('saved_indicators', 0)}."
            )

        else:
            for error in result.get(
                "errors",
                [],
            ):
                st.error(error)

    except Exception as error:
        st.error(
            f"حدث خطأ أثناء معالجة الملف: {error}"
        )
