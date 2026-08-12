# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import os
import re
import time

import pandas as pd
import streamlit as st
from dotenv import find_dotenv, load_dotenv
from google import genai
from pydantic import BaseModel
from sqlalchemy import select
from pathlib import Path

from database_individuals.connection import SessionLocal
from database_individuals.models import (
    IndividualMeasurementRecord,
    IndividualProfile,
)

# ==================================================
# Environment setup
# ==================================================

def get_env_path():
    """Find the .env file within the project directories."""
    current_file = Path(__file__).resolve()

    candidates = [
        Path.cwd() / ".env",
        current_file.parent / ".env",
        current_file.parent.parent / ".env",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    found = find_dotenv(
        filename=".env",
        usecwd=True,
    )

    if found:
        return Path(found)

    raise RuntimeError(
        "لم يتم العثور على ملف .env. "
        "تأكدي أنه موجود في مجلد المشروع بجانب main.py."
    )


# Locate the environment file
ENV_PATH = get_env_path()

# Load values from the .env file
load_dotenv(
    dotenv_path=ENV_PATH,
    override=True,
)

# Gemini API key
GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    "",
).strip()

# Gemini model name
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
).strip()

# Number of comments per analysis batch
COMMENTS_BATCH_SIZE = int(
    os.getenv(
        "COMMENTS_BATCH_SIZE",
        "300",
    )
)

# Printed in the terminal only; the API key value is never displayed.
print(f"[Gemini] ENV file: {ENV_PATH}")
print(f"[Gemini] API key found: {bool(GEMINI_API_KEY)}")
print(f"[Gemini] Model: {GEMINI_MODEL}")


# Page styling
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

    .recommendation-card {
        margin-top: 25px;
        border-right: 5px solid #2FA88E;
    }

    .feedback-card {
        margin-top: 18px;
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

# Comments excluded from the analysis
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


# Clean comments and exclude empty values

def clean_comment(value):
    if value is None:
        return None

    comment = str(value).strip()
    comment = re.sub(r"^\s*[-•]\s*", "", comment).strip()

    if not comment:
        return None

    if comment.lower() in IGNORED_COMMENTS:
        return None

    return comment


# Read comments and individual data from the database
@st.cache_data(ttl=60)
def fetch_comments_from_db():
    with SessionLocal() as session:
        rows = session.execute(
            select(
                IndividualMeasurementRecord.review,
                IndividualMeasurementRecord.year,
                IndividualMeasurementRecord.period,
                IndividualProfile.gender,
                IndividualProfile.age_group,
                IndividualProfile.region,
            )
            .join(
                IndividualProfile,
                IndividualMeasurementRecord.individual_id
                == IndividualProfile.individual_id,
            )
            .where(
                IndividualMeasurementRecord.review.is_not(None),
                IndividualMeasurementRecord.review != "",
            )
            .order_by(
                IndividualMeasurementRecord.year.desc(),
                IndividualMeasurementRecord.period,
            )
        ).all()

    comments = []

    for review, year, period, gender, age_group, region in rows:
        for line in str(review).splitlines():
            comment = clean_comment(line)

            if comment is None:
                continue

            comments.append(
                {
                    "gender": gender or "غير محدد",
                    "age_group": age_group or "غير محدد",
                    "region": region or "غير محدد",
                    "year": int(year),
                    "period": period,
                    "comment": comment,
                }
            )

    return comments


# Reason data model
class Reason(BaseModel):
    name: str
    count: int


class BatchAnalysisResult(BaseModel):
    satisfaction_count: int
    dissatisfaction_count: int
    neutral_count: int
    satisfaction_reasons: list[Reason]
    dissatisfaction_reasons: list[Reason]


class AnalysisResult(BaseModel):
    satisfaction_count: int
    dissatisfaction_count: int
    neutral_count: int
    satisfaction_reasons: list[Reason]
    dissatisfaction_reasons: list[Reason]
    summary: str
    smart_recommendation: str


BatchAnalysisResult.model_rebuild(
    _types_namespace={"Reason": Reason}
)

AnalysisResult.model_rebuild(
    _types_namespace={"Reason": Reason}
)


BATCH_PROMPT = """
أنت متخصص في تحليل تعليقات تجربة العملاء للأفراد باللغة العربية.

صنف كل تعليق مرة واحدة فقط إلى:
- رضا: إشادة أو تجربة إيجابية واضحة.
- عدم رضا: مشكلة أو صعوبة أو تأخير أو شكوى واضحة.
- محايد: لا يحتوي رضا أو مشكلة واضحة.

القواعد:
1. حلل كل تعليق في الدفعة ولا تتجاهل أي تعليق.
2. satisfaction_count = عدد تعليقات الرضا.
3. dissatisfaction_count = عدد تعليقات عدم الرضا.
4. neutral_count = عدد التعليقات المحايدة.
5. استخرج سببًا رئيسيًا واحدًا فقط من كل تعليق رضا أو عدم رضا.
6. اجمع الأسباب المتشابهة تحت اسم عربي واضح ومختصر.
7. استخدم بحد أقصى 10 فئات داخل كل نوع.
8. يجب أن يساوي مجموع أعداد أسباب الرضا satisfaction_count.
9. يجب أن يساوي مجموع أعداد أسباب عدم الرضا dissatisfaction_count.
10. لا تخترع سببًا غير موجود.
11. لا تكرر السبب نفسه بصيغ مختلفة.
12. لا تكتب خلاصة أو توصية في هذه المرحلة.

أمثلة:
سهولة الاستخدام، وضوح الإجراءات، سرعة تنفيذ الخدمة،
مشكلات تسجيل الدخول، توفر الخدمة، جودة الدعم الفني،
وضوح الإشعارات، سهولة التسجيل، المشكلات التقنية.
"""


FINAL_PROMPT = """
أنت متخصص في تلخيص نتائج تحليل تجربة العملاء للأفراد.

ستستلم الأعداد النهائية وأسبابًا مجمعة من عدة دفعات.

المطلوب:
1. ادمج الأسباب المتشابهة لغويًا ودلاليًا.
2. اجمع أعداد الأسباب عند دمجها.
3. أرجع أعلى 5 أسباب رضا فقط مرتبة تنازليًا.
4. أرجع أعلى 5 أسباب عدم رضا فقط مرتبة تنازليًا.
5. لا تغيّر satisfaction_count أو dissatisfaction_count أو neutral_count.
6. لا تخترع سببًا غير موجود.

ملاحظة:
مجموع أعلى 5 أسباب لا يلزم أن يساوي إجمالي التعليقات،
لأنها أعلى الأسباب فقط.

اكتب summary كخلاصة قصيرة جدًا:
- أبرز نقطة قوة.
- أبرز مشكلة.
ولا تتجاوز 60 كلمة.

واكتب smart_recommendation كتوصية عملية مستقلة:
- الإجراء الأهم المطلوب.
- ما الذي يجب تحسينه أولًا.
- نتيجة متوقعة مختصرة.
ولا تتجاوز 70 كلمة.
"""


# Create the Gemini client

def _gemini_client():
    if not GEMINI_API_KEY:
        raise ValueError(
            "مفتاح GEMINI_API_KEY غير موجود. "
            f"ملف البيئة المستخدم: {ENV_PATH}"
        )

    return genai.Client(
        api_key=GEMINI_API_KEY
    )


# Send a structured request with retry handling

def _structured_request(
    client,
    prompt,
    response_model,
    max_attempts=3,
):
    last_error = None

    for attempt in range(1, max_attempts + 1):
        try:
            interaction = client.interactions.create(
                model=GEMINI_MODEL,
                input=prompt,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": response_model.model_json_schema(),
                },
                store=False,
            )

            if not interaction.output_text:
                raise ValueError(
                    "Gemini لم يرجع نتيجة صالحة."
                )

            return response_model.model_validate_json(
                interaction.output_text
            )

        except Exception as error:
            last_error = error
            error_text = str(error).lower()

            temporary_error = any(
                value in error_text
                for value in (
                    "429",
                    "rate",
                    "resource_exhausted",
                    "timeout",
                    "503",
                    "temporarily",
                )
            )

            if (
                not temporary_error
                or attempt == max_attempts
            ):
                raise

            time.sleep(10 * attempt)

    raise last_error


# Analyze one batch of comments

def _analyze_batch(
    client,
    comments,
):
    records = "\n".join(
        f"{index}. {comment}"
        for index, comment in enumerate(
            comments,
            start=1,
        )
    )

    prompt = (
        BATCH_PROMPT
        + "\n\nالتعليقات:\n"
        + records
    )

    for _ in range(2):
        result = _structured_request(
            client,
            prompt,
            BatchAnalysisResult,
        )

        classified_count = (
            result.satisfaction_count
            + result.dissatisfaction_count
            + result.neutral_count
        )

        if classified_count == len(comments):
            return result

        prompt += (
            "\n\nأعد التصنيف وتأكد أن مجموع "
            "satisfaction_count + dissatisfaction_count + "
            f"neutral_count يساوي بالضبط {len(comments)}."
        )

    raise ValueError(
        "تعذر تصنيف جميع تعليقات إحدى الدفعات."
    )


# Merge batch results and generate the final output

def _finalize_analysis(
    client,
    satisfaction_count,
    dissatisfaction_count,
    neutral_count,
    satisfaction_reasons,
    dissatisfaction_reasons,
):
    satisfaction_text = "\n".join(
        f"- {item.name}: {item.count}"
        for item in satisfaction_reasons
    )

    dissatisfaction_text = "\n".join(
        f"- {item.name}: {item.count}"
        for item in dissatisfaction_reasons
    )

    prompt = f"""
{FINAL_PROMPT}

الأعداد النهائية:
satisfaction_count = {satisfaction_count}
dissatisfaction_count = {dissatisfaction_count}
neutral_count = {neutral_count}

أسباب الرضا المجمعة:
{satisfaction_text}

أسباب عدم الرضا المجمعة:
{dissatisfaction_text}
"""

    result = _structured_request(
        client,
        prompt,
        AnalysisResult,
    )

    # Final counts are calculated programmatically from all batches.
    result.satisfaction_count = satisfaction_count
    result.dissatisfaction_count = dissatisfaction_count
    result.neutral_count = neutral_count

    return result


# Split comments into batches and analyze them

def analyze_comments(data):
    if not data:
        raise ValueError(
            "لا توجد تعليقات مطابقة للتحليل."
        )

    comments = [
        item["comment"]
        for item in data
        if item.get("comment")
    ]

    if not comments:
        raise ValueError(
            "لا توجد تعليقات صالحة للتحليل."
        )

    batches = [
        comments[index:index + COMMENTS_BATCH_SIZE]
        for index in range(
            0,
            len(comments),
            COMMENTS_BATCH_SIZE,
        )
    ]

    client = _gemini_client()

    satisfaction_count = 0
    dissatisfaction_count = 0
    neutral_count = 0

    satisfaction_reasons = []
    dissatisfaction_reasons = []

    progress_bar = st.progress(
        0,
        text=(
            f"جاري تحليل {len(comments)} تعليق "
            f"على {len(batches)} دفعة..."
        ),
    )

    for batch_number, batch in enumerate(
        batches,
        start=1,
    ):
        batch_result = _analyze_batch(
            client,
            batch,
        )

        satisfaction_count += (
            batch_result.satisfaction_count
        )
        dissatisfaction_count += (
            batch_result.dissatisfaction_count
        )
        neutral_count += (
            batch_result.neutral_count
        )

        satisfaction_reasons.extend(
            batch_result.satisfaction_reasons
        )
        dissatisfaction_reasons.extend(
            batch_result.dissatisfaction_reasons
        )

        progress_bar.progress(
            batch_number / len(batches),
            text=(
                f"جاري تحليل الدفعة "
                f"{batch_number} من {len(batches)}"
            ),
        )

    result = _finalize_analysis(
        client=client,
        satisfaction_count=satisfaction_count,
        dissatisfaction_count=dissatisfaction_count,
        neutral_count=neutral_count,
        satisfaction_reasons=satisfaction_reasons,
        dissatisfaction_reasons=dissatisfaction_reasons,
    )

    progress_bar.progress(
        1.0,
        text=(
            f"تم تحليل جميع التعليقات: "
            f"{len(comments)} تعليق."
        ),
    )

    return result

# Display the top five reasons

def show_reasons(title, reasons, badge_class):
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


# Page title
st.markdown(
    '<div class="comments-title">تحليل تعليقات الأفراد</div>',
    unsafe_allow_html=True,
)

st.markdown(
    (
        '<div class="comments-description">'
        'تحليل التعليقات الفعلية المحفوظة في قاعدة بيانات الأفراد '
        'واستخراج أسباب الرضا وعدم الرضا'
        '</div>'
    ),
    unsafe_allow_html=True,
)

# Load comments from the database
try:
    comments_data = fetch_comments_from_db()
except Exception as error:
    st.error(
        f"تعذر قراءة تعليقات الأفراد من قاعدة البيانات: {error}"
    )
    st.stop()

if not comments_data:
    st.warning(
        "لا توجد تعليقات محفوظة في قاعدة بيانات الأفراد."
    )
    st.stop()


# Prepare filter options
all_genders = sorted(
    {item["gender"] for item in comments_data}
)

all_age_groups = sorted(
    {item["age_group"] for item in comments_data}
)

all_regions = sorted(
    {item["region"] for item in comments_data}
)

all_years = sorted(
    {item["year"] for item in comments_data},
    reverse=True,
)

all_periods = [
    period
    for period in [
        "الربع الأول",
        "الربع الثاني",
        "الربع الثالث",
        "الربع الرابع",
    ]
    if any(
        item["period"] == period
        for item in comments_data
    )
]


# Display filters in one row
filter1, filter2, filter3, filter4, filter5 = st.columns(5)

with filter1:
    selected_gender = st.selectbox(
        "الجنس",
        options=["الكل", *all_genders],
    )

with filter2:
    selected_age_group = st.selectbox(
        "الفئة العمرية",
        options=["الكل", *all_age_groups],
    )

with filter3:
    selected_region = st.selectbox(
        "المنطقة",
        options=["الكل", *all_regions],
    )

with filter4:
    selected_year = st.selectbox(
        "السنة",
        options=["كل السنوات", *all_years],
    )

with filter5:
    selected_period = st.selectbox(
        "الفترة",
        options=["كل الفترات", *all_periods],
    )


# Apply filters to comments
filtered_data = [
    item
    for item in comments_data
    if (
        (
            selected_gender == "الكل"
            or item["gender"] == selected_gender
        )
        and (
            selected_age_group == "الكل"
            or item["age_group"] == selected_age_group
        )
        and (
            selected_region == "الكل"
            or item["region"] == selected_region
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


# Display comment count and preview
info_col1, info_col2 = st.columns([1, 2])

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
            pd.DataFrame(filtered_data),
            use_container_width=True,
            hide_index=True,
            column_config={
                "gender": "الجنس",
                "age_group": "الفئة العمرية",
                "region": "المنطقة",
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




# Center the analysis button
_, center, _ = st.columns([1, 1.5, 1])

with center:
    analyze_button = st.button(
        "بدء تحليل التعليقات",
        use_container_width=True,
    )


# Run the analysis when the button is clicked
if analyze_button:
    with st.spinner(
        "جاري تحليل التعليقات..."
    ):
        try:
            result = analyze_comments(
                filtered_data
            )

            st.success(
                "تم تحليل جميع التعليقات بنجاح."
            )

            # Display comment counts by classification
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
                "الأرقام تمثل عدد التعليقات، وليست بالضرورة عدد أفراد مختلفين."
            )

            # Display satisfaction and dissatisfaction reasons
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

            # Prepare the recommendation for HTML display
            safe_recommendation = html.escape(
                result.smart_recommendation
            ).replace(
                "\n",
                "<br>",
            )

            st.markdown(
                (
                    '<div class="analysis-card recommendation-card">'
                    '<div class="analysis-card-title">'
                    'التوصية الذكية'
                    '</div>'
                    f'<div class="feedback-text">'
                    f'{safe_recommendation}'
                    '</div>'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )

            # Prepare the summary for HTML display
            safe_summary = html.escape(
                result.summary
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
                    f'{safe_summary}'
                    '</div>'
                    '</div>'
                ),
                unsafe_allow_html=True,
            )

        except Exception as error:
            st.error(
                f"حدث خطأ أثناء التحليل: {error}"
            )

