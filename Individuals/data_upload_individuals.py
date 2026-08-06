# -*- coding: utf-8 -*-
"""
data_upload_individuals.py
--------------------------
صفحة رفع بيانات الأفراد من Excel إلى individuals_experience_db.
"""

from datetime import datetime

import pandas as pd
import streamlit as st

from individuals_upload_backend import (
    VALID_PERIODS,
    get_factors,
    get_indicators,
    prepare_individual_records,
    save_individual_records,
)
from style import apply_theme


st.set_page_config(
    page_title="رفع بيانات الأفراد",
    layout="wide",
)

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
    div[data-testid="stAlert"],
    details {
        direction: rtl;
        text-align: right;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


NO_COLUMN = "غير موجود"

TIME_FROM_DATE = "يوجد عمود تاريخ"
TIME_FROM_COLUMNS = "السنة والربع في عمودين"
TIME_FIXED = "سنة وربع ثابتان لكل الملف"


def find_default_index(options, preferred_names):
    for preferred_name in preferred_names:
        if preferred_name in options:
            return options.index(preferred_name)

    return 0


def optional_selectbox(
    label,
    columns,
    preferred_names,
    *,
    key=None,
    help=None,
):
    options = [NO_COLUMN] + columns

    selected = st.selectbox(
        label,
        options=options,
        index=find_default_index(
            options,
            preferred_names,
        ),
        key=key,
        help=help,
    )

    return None if selected == NO_COLUMN else selected


st.markdown(
    """
    <div dir="rtl" style="text-align:right;">
        <h1>رفع بيانات الأفراد</h1>
        <p style="color:#7A7F94; font-size:17px;">
            ارفع ملف Excel وحدد أعمدة بيانات الفرد وإجابات الاستبيان
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


factors = get_factors()
indicators = get_indicators()

if not factors and not indicators:
    st.error(
        "جداول العوامل والمؤشرات المرجعية فارغة. "
        "شغلي أولًا: "
        "python -m database_individuals.sync_reference_data"
    )
    st.stop()

if not factors:
    st.warning(
        "جدول SharedCSATFactors فارغ؛ لن تظهر حقول عوامل CSAT."
    )

if not indicators:
    st.warning(
        "جدول SharedIndicators فارغ؛ لن تظهر حقول CES وNPS."
    )


uploaded_file = st.file_uploader(
    "اسحب ملف Excel هنا أو اضغط للاختيار",
    type=["xlsx", "xls"],
)

if uploaded_file is None:
    st.info(
        "كل صف في الملف يجب أن يمثل استبيان فرد واحد."
    )
    st.stop()


try:
    dataframe = pd.read_excel(uploaded_file)
    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

except Exception as error:
    st.error(f"تعذر قراءة ملف Excel: {error}")
    st.stop()


if dataframe.empty:
    st.warning("ملف Excel لا يحتوي على بيانات.")
    st.stop()


columns = dataframe.columns.tolist()

st.success(
    f"تمت قراءة الملف بنجاح — عدد الصفوف: {len(dataframe)}"
)

with st.expander("معاينة الملف", expanded=False):
    st.dataframe(
        dataframe.head(20),
        use_container_width=True,
        hide_index=True,
    )


# ==================================================
# 1. تحديد الفرد والفترة
# ==================================================

with st.container(border=True):
    st.markdown("## 1. الفرد والفترة الزمنية")

    st.caption(
        "اتركي IndividualID غير موجود عند رفع أفراد جدد. "
        "اختاريه فقط عند تحديث أفراد محفوظين سابقًا."
    )

    individual_id_column = optional_selectbox(
        "عمود IndividualID",
        columns,
        [
            "IndividualID",
            "Individual ID",
            "معرف الفرد",
            "رقم الفرد",
        ],
        help=(
            "عند عدم اختياره، ينشئ النظام ملف فرد جديد لكل صف."
        ),
    )

    time_mode = st.radio(
        "طريقة تحديد السنة والربع",
        options=[
            TIME_FROM_DATE,
            TIME_FROM_COLUMNS,
            TIME_FIXED,
        ],
        horizontal=True,
    )

    date_column = None
    year_column = None
    period_column = None
    fixed_year = None
    fixed_period = None

    if time_mode == TIME_FROM_DATE:
        date_column = st.selectbox(
            "عمود التاريخ *",
            options=columns,
            index=find_default_index(
                columns,
                [
                    "التاريخ",
                    "تاريخ الاستجابة",
                    "Response Date",
                    "Date",
                ],
            ),
            help=(
                "سيستخرج النظام السنة والربع تلقائيًا من التاريخ."
            ),
        )

    elif time_mode == TIME_FROM_COLUMNS:
        col_year, col_period = st.columns(2)

        with col_year:
            year_column = st.selectbox(
                "عمود السنة *",
                options=columns,
                index=find_default_index(
                    columns,
                    [
                        "السنة",
                        "السنه",
                        "Year",
                    ],
                ),
            )

        with col_period:
            period_column = st.selectbox(
                "عمود الربع *",
                options=columns,
                index=find_default_index(
                    columns,
                    [
                        "الربع",
                        "الفترة",
                        "Period",
                        "Quarter",
                    ],
                ),
                help=(
                    "القيم المقبولة تشمل الربع الأول إلى الرابع "
                    "أو Q1 إلى Q4."
                ),
            )

    else:
        col_year, col_period = st.columns(2)

        with col_year:
            fixed_year = st.number_input(
                "السنة *",
                min_value=2000,
                max_value=2100,
                value=datetime.now().year,
                step=1,
            )

        with col_period:
            fixed_period = st.selectbox(
                "الربع *",
                options=list(VALID_PERIODS),
            )


# ==================================================
# 2. البيانات الديموغرافية
# ==================================================

with st.container(border=True):
    st.markdown("## 2. بيانات الفرد")

    st.caption(
        "جميع هذه الحقول اختيارية، لكن اختيارها يساعد في التحليل."
    )

    col1, col2 = st.columns(2)

    with col1:
        gender_column = optional_selectbox(
            "عمود الجنس",
            columns,
            ["الجنس", "Gender"],
        )

        id_type_column = optional_selectbox(
            "عمود نوع الهوية",
            columns,
            [
                "نوع الهوية",
                "نوع_الهوية",
                "ID Type",
                "IDType",
            ],
        )

        device_column = optional_selectbox(
            "عمود الجهاز",
            columns,
            [
                "الجهاز",
                "نوع الجهاز",
                "Device",
            ],
        )

    with col2:
        age_group_column = optional_selectbox(
            "عمود الفئة العمرية",
            columns,
            [
                "الفئة العمرية",
                "الفئه العمريه",
                "Age Group",
                "AgeGroup",
            ],
        )

        education_column = optional_selectbox(
            "عمود المستوى التعليمي",
            columns,
            [
                "المستوى التعليمي",
                "التعليم",
                "Education",
            ],
        )

        region_column = optional_selectbox(
            "عمود المنطقة",
            columns,
            ["المنطقة", "المنطقه", "Region"],
        )


# ==================================================
# 3. عوامل CSAT
# ==================================================

factor_columns = {}

with st.container(border=True):
    st.markdown("## 3. عوامل CSAT")

    if factors:
        st.caption(
            "اختاري عمود الإجابة الخام لكل عامل. "
            "القيم المقبولة من 1 إلى 5، والقيمة 99 تُعامل كغير منطبق."
        )

        factor_ui_columns = st.columns(2)

        for index, factor in enumerate(factors):
            with factor_ui_columns[index % 2]:
                factor_columns[factor["name"]] = optional_selectbox(
                    f'عمود: {factor["name"]}',
                    columns,
                    [factor["name"]],
                    key=f'factor_{factor["id"]}',
                )
    else:
        st.info("لا توجد عوامل محفوظة في قاعدة البيانات.")


# ==================================================
# 4. المؤشرات الأخرى
# ==================================================

indicator_columns = {}

with st.container(border=True):
    st.markdown("## 4. المؤشرات الأخرى")

    if indicators:
        st.caption(
            "اختاري عمود الإجابة الخام لكل مؤشر. "
            "النطاق يظهر حسب إعداد المؤشر في قاعدة البيانات."
        )

        indicator_ui_columns = st.columns(2)

        for index, indicator in enumerate(indicators):
            with indicator_ui_columns[index % 2]:
                indicator_columns[
                    indicator["name"]
                ] = optional_selectbox(
                    (
                        f'عمود {indicator["name"]} '
                        f'({indicator["minimum"]}–'
                        f'{indicator["maximum"]})'
                    ),
                    columns,
                    [indicator["name"]],
                    key=f'indicator_{indicator["id"]}',
                )
    else:
        st.info("لا توجد مؤشرات محفوظة في قاعدة البيانات.")


# ==================================================
# 5. التعليق
# ==================================================

with st.container(border=True):
    st.markdown("## 5. التعليق")

    review_column = optional_selectbox(
        "عمود التعليق",
        columns,
        [
            "التعليق",
            "تعليق",
            "الملاحظات",
            "Review",
            "Comment",
        ],
    )


# ==================================================
# التحقق والحفظ
# ==================================================

save_clicked = st.button(
    "التحقق وحفظ بيانات الأفراد",
    type="primary",
    use_container_width=True,
)

if save_clicked:
    selected_response_columns = [
        column
        for column in [
            *factor_columns.values(),
            *indicator_columns.values(),
        ]
        if column is not None
    ]

    duplicated_columns = {
        column
        for column in selected_response_columns
        if selected_response_columns.count(column) > 1
    }

    if duplicated_columns:
        st.error(
            "لا يمكن استخدام عمود الإجابة نفسه لأكثر من عامل أو مؤشر: "
            + "، ".join(sorted(duplicated_columns))
        )
        st.stop()

    if (
        not selected_response_columns
        and review_column is None
    ):
        st.error(
            "اختاري عاملًا أو مؤشرًا واحدًا على الأقل، "
            "أو اختاري عمود التعليق."
        )
        st.stop()

    try:
        with st.spinner(
            "جاري التحقق من الملف وحفظ بيانات الأفراد..."
        ):
            prepared_records = prepare_individual_records(
                dataframe=dataframe,
                individual_id_column=individual_id_column,
                date_column=date_column,
                year_column=year_column,
                period_column=period_column,
                fixed_year=fixed_year,
                fixed_period=fixed_period,
                gender_column=gender_column,
                age_group_column=age_group_column,
                id_type_column=id_type_column,
                education_column=education_column,
                device_column=device_column,
                region_column=region_column,
                review_column=review_column,
                factor_columns=factor_columns,
                indicator_columns=indicator_columns,
            )

            result = save_individual_records(
                prepared_records
            )

        if result["ok"]:
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
            for error_message in result.get("errors", []):
                st.error(error_message)

    except ValueError as error:
        for message in str(error).splitlines():
            st.error(message)

    except Exception as error:
        st.error(
            f"حدث خطأ أثناء معالجة ملف الأفراد: {error}"
        )
