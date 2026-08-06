# -*- coding: utf-8 -*-
"""
comments_page.py
----------------
تحليل التعليقات الحقيقية المخزنة في قاعدة بيانات الجهات.

مصدر التعليقات:
    MeasurementRecords.Review
"""

from __future__ import annotations

import html
import os
import re

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel
from sqlalchemy import select

from database.connection import SessionLocal
from database.models import (
    MeasurementRecord,
    Section,
    Service,
)


# ==================================================
# الإعدادات
# ==================================================

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")

# لمنع إرسال عدد ضخم جدًا من التعليقات في طلب واحد.
MAX_COMMENTS_PER_ANALYSIS = 500


# ==================================================
# التصميم
# ==================================================

st.markdown(
    """
    <style>
    @import url(
        'https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap'
    );

    [data-testid="stMain"] {
        direction: rtl;
        text-align: right;
        background-color: #F5F6FA;
    }

    [data-testid="stMain"] .block-container {
        max-width: 1400px;
        padding-top: 45px;
        padding-right: 45px;
        padding-left: 45px;
    }

    [data-testid="stMain"] h1,
    [data-testid="stMain"] h2,
    [data-testid="stMain"] h3,
    [data-testid="stMain"] h4,
    [data-testid="stMain"] h5,
    [data-testid="stMain"] h6,
    [data-testid="stMain"] p,
    [data-testid="stMain"] label,
    [data-testid="stMain"] input,
    [data-testid="stMain"] textarea,
    [data-testid="stMain"] button {
        font-family: 'Tajawal', sans-serif !important;
    }

    span[data-testid="stIconMaterial"],
    .material-symbols-rounded {
        font-family: "Material Symbols Rounded" !important;
        direction: ltr !important;
        text-align: center !important;
    }

    .comments-title {
        color: #16213E;
        font-size: 44px;
        font-weight: 800;
        line-height: 1.4;
        margin-bottom: 5px;
        direction: rtl;
        text-align: right;
    }

    .comments-description {
        color: #8A94B5;
        font-size: 18px;
        line-height: 1.8;
        margin-bottom: 25px;
        direction: rtl;
        text-align: right;
    }

    .analysis-card {
        direction: rtl;
        text-align: right;
        background-color: #FFFFFF;
        padding: 28px;
        border-radius: 16px;
        border: 1px solid #EEF0F5;
        box-shadow: 0 5px 18px rgba(22, 33, 62, 0.05);
    }

    .analysis-card-title {
        color: #16213E;
        font-size: 23px;
        font-weight: 800;
        margin-bottom: 20px;
    }

    .reason-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 20px;
        padding: 15px 0;
        border-bottom: 1px solid #EEF0F5;
        color: #16213E;
        font-weight: 700;
    }

    .reason-row:last-child {
        border-bottom: none;
    }

    .reason-count {
        min-width: 40px;
        width: 40px;
        height: 40px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        font-weight: 800;
        flex-shrink: 0;
    }

    .positive-count {
        background-color: #E4F6F1;
        color: #2FA88E;
    }

    .negative-count {
        background-color: #FCEBED;
        color: #C94B5B;
    }

    .feedback-card {
        margin-top: 25px;
        border-right: 5px solid #6C4AB6;
    }

    .feedback-text {
        color: #58627E;
        font-size: 16px;
        line-height: 2;
    }

    [data-testid="stMain"] div.stButton > button {
        width: 100%;
        min-height: 58px;
        background-color: #6C4AB6 !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 10px !important;
        font-size: 17px !important;
        font-weight: 700 !important;
    }

    [data-testid="stMain"] div.stButton > button:hover {
        background-color: #5B3DA5 !important;
        color: #FFFFFF !important;
        border: none !important;
    }

    [data-testid="stMain"] div.stButton > button:focus {
        box-shadow: none !important;
        color: #FFFFFF !important;
    }

    [data-testid="stMain"] [data-testid="stAlert"],
    [data-testid="stMain"] [data-testid="stCaptionContainer"] {
        direction: rtl;
        text-align: right;
        font-family: 'Tajawal', sans-serif !important;
    }

    div[data-baseweb="select"] > div,
    div[data-baseweb="select"] span {
        direction: rtl;
        text-align: right;
    }

    @media (max-width: 900px) {
        [data-testid="stMain"] .block-container {
            padding-top: 30px;
            padding-right: 20px;
            padding-left: 20px;
        }

        .comments-title {
            font-size: 34px;
        }

        .comments-description {
            font-size: 16px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# تنظيف التعليقات
# ==================================================

IGNORED_COMMENTS = {
    "",
    "لا يوجد تعليق",
    "لا يوجد تعليق.",
    "لا توجد ملاحظات",
    "لا توجد ملاحظة",
    "لا يوجد",
    "لا شيء",
    "nan",
    "none",
    "null",
}


def clean_comment(value):
    """تنظيف سطر تعليق واحد واستبعاد النصوص غير المفيدة."""
    if value is None:
        return None

    comment = str(value).strip()

    comment = re.sub(
        r"^\s*[-•]\s*",
        "",
        comment,
    ).strip()

    if not comment:
        return None

    if comment.lower() in IGNORED_COMMENTS:
        return None

    return comment


# ==================================================
# قراءة التعليقات من قاعدة البيانات
# ==================================================

@st.cache_data(ttl=60)
def fetch_comments_from_db():
    """
    قراءة التعليقات المحفوظة في MeasurementRecords.Review.

    إذا كان Review يحتوي عدة تعليقات مفصولة بأسطر،
    يتحول كل سطر إلى تعليق مستقل.
    """
    with SessionLocal() as session:
        rows = session.execute(
            select(
                MeasurementRecord.review,
                MeasurementRecord.year,
                MeasurementRecord.period,
                Section.section_name,
                Service.service_name,
            )
            .join(
                Service,
                MeasurementRecord.service_id
                == Service.service_id,
            )
            .join(
                Section,
                Service.section_id
                == Section.section_id,
            )
            .where(
                MeasurementRecord.review.is_not(None),
                MeasurementRecord.review != "",
            )
            .order_by(
                MeasurementRecord.year.desc(),
                Section.section_name,
                Service.service_name,
            )
        ).all()

    comments = []

    for (
        review,
        year,
        period,
        section_name,
        service_name,
    ) in rows:
        for line in str(review).splitlines():
            comment = clean_comment(line)

            if comment is None:
                continue

            comments.append(
                {
                    "section": section_name,
                    "service": service_name,
                    "year": int(year),
                    "period": period,
                    "comment": comment,
                }
            )

    return comments


# ==================================================
# شكل استجابة OpenAI
# ==================================================

class Reason(BaseModel):
    name: str
    count: int


class AnalysisResult(BaseModel):
    satisfaction_count: int
    dissatisfaction_count: int
    neutral_count: int
    satisfaction_reasons: list[Reason]
    dissatisfaction_reasons: list[Reason]
    smart_feedback: str


# إصلاح مراجع Pydantic المؤجلة بسبب:
# from __future__ import annotations
AnalysisResult.model_rebuild(
    _types_namespace={
        "Reason": Reason,
    }
)


# ==================================================
# التحليل
# ==================================================

def analyze_comments(data):
    if not API_KEY:
        raise ValueError(
            "مفتاح OPENAI_API_KEY غير موجود داخل ملف .env"
        )

    if not data:
        raise ValueError(
            "لا توجد تعليقات مطابقة للتحليل."
        )

    records = "\n".join(
        (
            f"{index}. القسم: {item['section']} | "
            f"الخدمة: {item['service']} | "
            f"السنة: {item['year']} | "
            f"الفترة: {item['period']} | "
            f"التعليق: {item['comment']}"
        )
        for index, item in enumerate(
            data,
            start=1,
        )
    )

    client = OpenAI(
        api_key=API_KEY
    )

    response = client.chat.completions.parse(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": """
أنت متخصص في تحليل تعليقات تجربة العملاء باللغة العربية.

لا يوجد تقييم رقمي منفصل لكل تعليق، لذلك صنف التعليق من معناه فقط:
- رضا: إشادة أو تجربة إيجابية واضحة.
- عدم رضا: مشكلة أو صعوبة أو تأخير أو شكوى واضحة.
- محايد: لا يحتوي رضا أو مشكلة واضحة.

القواعد:
1. صنّف كل تعليق مرة واحدة فقط إلى رضا أو عدم رضا أو محايد.
2. احسب:
   - satisfaction_count: عدد التعليقات المصنفة رضا.
   - dissatisfaction_count: عدد التعليقات المصنفة عدم رضا.
   - neutral_count: عدد التعليقات المحايدة.
3. استخرج سببًا رئيسيًا واحدًا فقط من كل تعليق المصنف رضا أو عدم رضا.
4. اجمع الأسباب المتشابهة تحت اسم عربي واضح ومختصر.
5. رتب الأسباب تنازليًا حسب العدد، وأرجع أعلى 5 أسباب فقط لكل قسم.
6. يجب أن يساوي مجموع أعداد أسباب الرضا satisfaction_count.
7. يجب أن يساوي مجموع أعداد أسباب عدم الرضا dissatisfaction_count.
8. لا تخترع سببًا غير موجود.
9. لا تعتبر اسم القسم أو الخدمة سببًا.
10. لا تكرر السبب نفسه بصيغ مختلفة.

أمثلة مناسبة للأسباب:
المشكلات التقنية، سرعة إنجاز الخدمة، سهولة الاستخدام،
وضوح الإجراءات، تسجيل الدخول والوصول،
جودة الدعم وخدمة العملاء، استقرار الخدمة،
توفر المعلومات، تأخر تنفيذ الطلب.

اكتب smart_feedback كخلاصة قصيرة جدًا من ثلاث نقاط فقط:
- أبرز نقطة قوة.
- أبرز مشكلة.
- أهم توصية عملية.
لا تتجاوز الخلاصة 90 كلمة.
""",
            },
            {
                "role": "user",
                "content": records,
            },
        ],
        response_format=AnalysisResult,
    )

    result = (
        response.choices[0]
        .message.parsed
    )

    if result is None:
        raise ValueError(
            "لم يرجع النموذج نتيجة صالحة."
        )

    return result


# ==================================================
# عرض النتائج
# ==================================================

def show_reasons(
    title,
    reasons,
    badge_class,
):
    top_reasons = sorted(
        reasons,
        key=lambda item: item.count,
        reverse=True,
    )[:5]

    if top_reasons:
        rows = "".join(
            (
                '<div class="reason-row">'
                f'<span>{html.escape(item.name)}</span>'
                f'<span class="reason-count {badge_class}">'
                f'{item.count}'
                '</span>'
                '</div>'
            )
            for item in top_reasons
        )

    else:
        rows = (
            '<p class="feedback-text">'
            'لا توجد أسباب في هذا القسم.'
            '</p>'
        )

    st.markdown(
        (
            '<div class="analysis-card">'
            f'<div class="analysis-card-title">{title}</div>'
            f'{rows}'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


# ==================================================
# عنوان الصفحة
# ==================================================

st.markdown(
    '<div class="comments-title">تحليل تعليقات العملاء</div>',
    unsafe_allow_html=True,
)

st.markdown(
    (
        '<div class="comments-description">'
        'تحليل التعليقات المحفوظة في قاعدة البيانات '
        'واستخراج أسباب الرضا وعدم الرضا'
        '</div>'
    ),
    unsafe_allow_html=True,
)


# ==================================================
# جلب البيانات
# ==================================================

try:
    comments_data = fetch_comments_from_db()

except Exception as error:
    st.error(
        f"تعذر قراءة التعليقات من قاعدة البيانات: {error}"
    )
    st.stop()


if not comments_data:
    st.warning(
        "لا توجد تعليقات محفوظة في قاعدة بيانات الجهات."
    )
    st.stop()


# ==================================================
# الفلاتر
# ==================================================

all_sections = sorted(
    {
        item["section"]
        for item in comments_data
    }
)

all_years = sorted(
    {
        item["year"]
        for item in comments_data
    },
    reverse=True,
)

all_periods = [
    period
    for period in [
        "النصف الأول",
        "النصف الثاني",
    ]
    if any(
        item["period"] == period
        for item in comments_data
    )
]


filter1, filter2, filter3, filter4 = st.columns(4)

with filter1:
    selected_section = st.selectbox(
        "القسم",
        options=[
            "كل الأقسام",
            *all_sections,
        ],
    )


available_services = sorted(
    {
        item["service"]
        for item in comments_data
        if (
            selected_section == "كل الأقسام"
            or item["section"] == selected_section
        )
    }
)


with filter2:
    selected_service = st.selectbox(
        "الخدمة",
        options=[
            "كل الخدمات",
            *available_services,
        ],
    )

with filter3:
    selected_year = st.selectbox(
        "السنة",
        options=[
            "كل السنوات",
            *all_years,
        ],
    )

with filter4:
    selected_period = st.selectbox(
        "الفترة",
        options=[
            "كل الفترات",
            *all_periods,
        ],
    )


filtered_data = [
    item
    for item in comments_data
    if (
        (
            selected_section == "كل الأقسام"
            or item["section"] == selected_section
        )
        and (
            selected_service == "كل الخدمات"
            or item["service"] == selected_service
        )
        and (
            selected_year == "كل السنوات"
            or item["year"] == selected_year
        )
        and (
            selected_period == "كل الفترات"
            or item["period"] == selected_period
        )
    )
]


# ==================================================
# العدد والمعاينة
# ==================================================

info_col1, info_col2 = st.columns(
    [1, 2]
)

with info_col1:
    st.metric(
        "عدد التعليقات",
        len(filtered_data),
    )

with info_col2:
    with st.expander(
        "معاينة التعليقات",
        expanded=False,
    ):
        st.dataframe(
            pd.DataFrame(
                filtered_data
            ),
            use_container_width=True,
            hide_index=True,
            column_config={
                "section": "القسم",
                "service": "الخدمة",
                "year": "السنة",
                "period": "الفترة",
                "comment": "التعليق",
            },
        )


if not filtered_data:
    st.info(
        "لا توجد تعليقات مطابقة للفلاتر المحددة."
    )
    st.stop()


analysis_data = filtered_data[
    :MAX_COMMENTS_PER_ANALYSIS
]

if (
    len(filtered_data)
    > MAX_COMMENTS_PER_ANALYSIS
):
    st.warning(
        "عدد التعليقات كبير؛ سيتم تحليل أول "
        f"{MAX_COMMENTS_PER_ANALYSIS} تعليق فقط."
    )


# ==================================================
# زر التحليل
# ==================================================

_, center, _ = st.columns(
    [1, 1.5, 1]
)

with center:
    analyze_button = st.button(
        "بدء تحليل التعليقات",
        use_container_width=True,
    )


# ==================================================
# تنفيذ التحليل
# ==================================================

if analyze_button:
    with st.spinner(
        "جاري تحليل التعليقات..."
    ):
        try:
            result = analyze_comments(
                analysis_data
            )

            st.success(
                "تم تحليل التعليقات بنجاح."
            )

            count_col1, count_col2, count_col3, count_col4 = st.columns(4)

            with count_col1:
                st.metric(
                    "تعليقات الرضا",
                    result.satisfaction_count,
                )

            with count_col2:
                st.metric(
                    "تعليقات عدم الرضا",
                    result.dissatisfaction_count,
                )

            with count_col3:
                st.metric(
                    "التعليقات المحايدة",
                    result.neutral_count,
                )

            with count_col4:
                st.metric(
                    "إجمالي التعليقات المحللة",
                    (
                        result.satisfaction_count
                        + result.dissatisfaction_count
                        + result.neutral_count
                    ),
                )

            st.caption(
                "الأرقام تمثل عدد التعليقات، وليست بالضرورة عدد أشخاص مختلفين."
            )

            col_right, col_left = st.columns(
                2,
                gap="large",
            )

            with col_right:
                show_reasons(
                    "أسباب الرضا",
                    result.satisfaction_reasons,
                    "positive-count",
                )

            with col_left:
                show_reasons(
                    "أسباب عدم الرضا",
                    result.dissatisfaction_reasons,
                    "negative-count",
                )

            safe_feedback = html.escape(
                result.smart_feedback
            ).replace(
                "\n",
                "<br>",
            )

            st.markdown(
                (
                    '<div class="analysis-card feedback-card">'
                    '<div class="analysis-card-title">'
                    'الخلاصة'
                    '</div>'
                    f'<div class="feedback-text">'
                    f'{safe_feedback}'
                    '</div>'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )

        except Exception as error:
            st.error(
                f"حدث خطأ أثناء التحليل: {error}"
            )

