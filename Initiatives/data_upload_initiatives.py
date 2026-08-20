# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import hashlib
import json

import pandas as pd
import streamlit as st

try:
    from Initiatives.initiatives_column_mapper_ai import (
        map_initiative_columns_with_ai,
    )
    from Initiatives.initiatives_upload_backend import (
        prepare_initiative_records,
        save_initiative_records,
    )

except ModuleNotFoundError:
    from initiatives_column_mapper_ai import (
        map_initiative_columns_with_ai,
    )
    from initiatives_upload_backend import (
        prepare_initiative_records,
        save_initiative_records,
    )

from style import apply_theme


apply_theme()


# Page styling (نفس تنسيق صفحات الرفع القديمة)

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

# الحقول المطلوبة والاختيارية مع تسمياتها العربية.
REQUIRED_FIELDS = {
    "number_column": "رقم المبادرة",
    "section_column": "القسم",
    "product_column": "المنتج",
    "initiative_column": "اسم المبادرة",
    "status_column": "الحالة",
}

DATE_FIELDS = {
    "creation_date_column": "تاريخ الإنشاء",
    "start_date_column": "تاريخ البدء",
    "expected_execution_date_column": "تاريخ التنفيذ المتوقع",
    "actual_execution_date_column": "التاريخ الفعلي للتنفيذ",
}


# Helper functions

def mapping_signature(column_names):
    payload = json.dumps(
        {"columns": column_names},
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def option_index(options, selected):
    if selected in options:
        return options.index(selected)
    return 0


def column_selector(label, columns, selected=None, *, key, help=None):
    """قائمة اختيار عمود؛ ترجع اسم العمود أو None عند اختيار (غير موجود)."""
    options = [NO_COLUMN, *columns]

    chosen = st.selectbox(
        label,
        options=options,
        index=option_index(options, selected),
        key=key,
        help=help,
    )

    return None if chosen == NO_COLUMN else chosen


def clear_review_state():
    keys_to_remove = [
        key
        for key in st.session_state
        if str(key).startswith("initiative_review_")
    ]
    for key in keys_to_remove:
        st.session_state.pop(key, None)


# Page header

st.markdown(
    """
    <div class="upload-header" dir="rtl">
        <h1>رفع بيانات المبادرات</h1>
        <p>
            ارفع ملف Excel، وستُطابق أسماء الأعمدة تلقائيًا.
            راجع المطابقة وعدّلها إذا لزم قبل الحفظ.
        </p>
        <div class="privacy-text">
            يتم إرسال أسماء الأعمدة فقط عند استخدام الذكاء الاصطناعي
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# Upload file

uploaded_file = st.file_uploader(
    "ملف Excel",
    type=["xlsx", "xls"],
)

if uploaded_file is None:
    st.stop()


try:
    dataframe = pd.read_excel(uploaded_file)
    dataframe.columns = [str(column).strip() for column in dataframe.columns]

except Exception as error:
    st.error(f"تعذر قراءة ملف Excel: {error}")
    st.stop()


if dataframe.empty:
    st.warning("ملف Excel لا يحتوي على بيانات.")
    st.stop()


columns = dataframe.columns.tolist()
signature = mapping_signature(columns)

# عند تغيّر الملف (تغيّر الأعمدة): جهّز مطابقة مبدئية محلية وامسح المراجعة.
if st.session_state.get("initiative_mapping_signature") != signature:
    st.session_state["initiative_mapping_signature"] = signature
    clear_review_state()
    st.session_state["initiative_ai_mapping"] = (
        map_initiative_columns_with_ai(columns)
    )


# File setup

with st.container(border=True):
    st.markdown(
        '<div class="section-title">إعداد الملف</div>',
        unsafe_allow_html=True,
    )

    file_col, rows_col, columns_col = st.columns([1.5, 1, 1])

    with file_col:
        st.caption("اسم الملف")
        st.markdown(
            f'<div class="summary-value">{uploaded_file.name}</div>',
            unsafe_allow_html=True,
        )

    with rows_col:
        st.caption("عدد الصفوف")
        st.markdown(
            f'<div class="summary-value">{len(dataframe):,}</div>',
            unsafe_allow_html=True,
        )

    with columns_col:
        st.caption("عدد الأعمدة")
        st.markdown(
            f'<div class="summary-value">{len(columns):,}</div>',
            unsafe_allow_html=True,
        )

    with st.expander("معاينة أول 15 صفًا", expanded=False):
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
        with st.spinner("جاري مطابقة أسماء الأعمدة..."):
            st.session_state["initiative_ai_mapping"] = (
                map_initiative_columns_with_ai(columns)
            )
        clear_review_state()
        st.rerun()

    except Exception as error:
        st.error(f"تعذر تحليل أسماء الأعمدة: {error}")


mapping = st.session_state.get("initiative_ai_mapping") or {}


# Mapping summary

matched_required = sum(
    1 for field in REQUIRED_FIELDS if mapping.get(field)
)
matched_dates = sum(
    1 for field in DATE_FIELDS if mapping.get(field)
)
gaps = [
    label
    for field, label in REQUIRED_FIELDS.items()
    if not mapping.get(field)
]

with st.container(border=True):
    st.markdown(
        '<div class="section-title">المطابقة</div>',
        unsafe_allow_html=True,
    )

    summary1, summary2, summary3 = st.columns(3)

    with summary1:
        st.caption("الحقول المطلوبة")
        st.markdown(f"**{matched_required} / {len(REQUIRED_FIELDS)}**")

    with summary2:
        st.caption("حقول التواريخ")
        st.markdown(f"**{matched_dates} / {len(DATE_FIELDS)}**")

    with summary3:
        st.caption("طريقة المطابقة")
        st.markdown(
            "**"
            + (
                "ذكاء اصطناعي"
                if mapping.get("source") == "ai"
                else "مطابقة تلقائية"
            )
            + "**"
        )

    for warning in mapping.get("warnings", []):
        st.info(warning)

    if gaps:
        st.warning("يلزم مراجعة: " + "، ".join(gaps))
    else:
        st.success("تم التعرف على جميع الحقول المطلوبة.")


# Review and edit mapping

with st.expander("مراجعة وتعديل المطابقة", expanded=bool(gaps)):
    st.caption("راجع الأعمدة وعدّل غير الصحيح فقط. الحقول المعلّمة بـ * مطلوبة.")

    st.markdown("#### الحقول المطلوبة")

    required_ui = st.columns(2)
    selected = {}

    for index, (field, label) in enumerate(REQUIRED_FIELDS.items()):
        with required_ui[index % 2]:
            selected[field] = column_selector(
                f"عمود {label} *",
                columns,
                mapping.get(field),
                key=f"initiative_review_{field}",
            )

    st.markdown("#### التواريخ (اختيارية)")

    date_ui = st.columns(3)

    for index, (field, label) in enumerate(DATE_FIELDS.items()):
        with date_ui[index % 3]:
            selected[field] = column_selector(
                f"عمود {label}",
                columns,
                mapping.get(field),
                key=f"initiative_review_{field}",
            )


# Saving

with st.container(border=True):
    st.markdown(
        '<div class="section-title">الحفظ</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="section-description">'
        'سيتم إنشاء الأقسام والمنتجات والحالات الجديدة تلقائيًا، '
        'وتحديث المبادرات الموجودة مسبقًا بدل تكرارها.'
        '</div>',
        unsafe_allow_html=True,
    )

    save_clicked = st.button(
        "حفظ بيانات المبادرات",
        type="primary",
        use_container_width=True,
    )


# Validation and saving

if save_clicked:
    errors = []

    for field, label in REQUIRED_FIELDS.items():
        if not selected.get(field):
            errors.append(f"عمود {label} مطلوب.")

    used_columns = [value for value in selected.values() if value]
    if len(used_columns) != len(set(used_columns)):
        errors.append("لا يمكن استخدام عمود واحد لأكثر من حقل.")

    if errors:
        for error in errors:
            st.error(error)
        st.stop()

    try:
        with st.spinner("جاري تجهيز بيانات المبادرات وحفظها..."):
            prepared_records = prepare_initiative_records(
                dataframe=dataframe,
                section_column=selected["section_column"],
                product_column=selected["product_column"],
                initiative_column=selected["initiative_column"],
                status_column=selected["status_column"],
                number_column=selected.get("number_column"),
                creation_date_column=selected.get("creation_date_column"),
                start_date_column=selected.get("start_date_column"),
                expected_execution_date_column=selected.get(
                    "expected_execution_date_column"
                ),
                actual_execution_date_column=selected.get(
                    "actual_execution_date_column"
                ),
            )

            result = save_initiative_records(prepared_records)

        if result["ok"]:
            st.success(
                "تم حفظ بيانات المبادرات بنجاح. "
                f"مبادرات جديدة: {result['created_actions']}، "
                f"مبادرات محدّثة: {result['updated_actions']}، "
                f"أقسام جديدة: {result['created_sections']}، "
                f"منتجات جديدة: {result['created_products']}، "
                f"حالات جديدة: {result['created_statuses']}."
            )
        else:
            for error_message in result.get("errors", []):
                st.error(error_message)

    except ValueError as error:
        for message in str(error).splitlines():
            st.error(message)

    except Exception as error:
        st.error(f"حدث خطأ أثناء معالجة ملف المبادرات: {error}")