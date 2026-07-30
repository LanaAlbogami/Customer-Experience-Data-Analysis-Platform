import os
import html
import streamlit as st

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel


# =========================
# الإعدادات
# =========================

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")

st.set_page_config(
    page_title="تحليل التعليقات",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================
# التصميم
# =========================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');

    .stApp, .stApp * {
        font-family: 'Tajawal', sans-serif !important;
        direction: rtl;
        text-align: right;
    }

    [data-testid="stAppViewContainer"] {
        background: #F5F6FA;
    }

    [data-testid="collapsedControl"],
    [data-testid="stSidebar"] {
        display: none !important;
    }

    .block-container {
        max-width: 1400px;
        padding-top: 45px;
    }

    .title {
        color: #16213E;
        font-size: 44px;
        font-weight: 800;
        margin-bottom: 5px;
    }

    .description {
        color: #8A94B5;
        font-size: 18px;
        margin-bottom: 25px;
    }

    .card {
        background: white;
        padding: 28px;
        border-radius: 16px;
        border: 1px solid #EEF0F5;
        box-shadow: 0 5px 18px rgba(22, 33, 62, 0.05);
    }

    .card-title {
        color: #16213E;
        font-size: 23px;
        font-weight: 800;
        margin-bottom: 20px;
    }

    .row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 15px 0;
        border-bottom: 1px solid #EEF0F5;
        color: #16213E;
        font-weight: 700;
    }

    .row:last-child {
        border-bottom: none;
    }

    .count {
        min-width: 40px;
        height: 40px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        font-weight: 800;
    }

    .positive {
        background: #E4F6F1;
        color: #2FA88E;
    }

    .negative {
        background: #FCEBED;
        color: #C94B5B;
    }

    .feedback {
        margin-top: 25px;
        border-right: 5px solid #6C4AB6;
    }

    .feedback-text {
        color: #58627E;
        font-size: 16px;
        line-height: 2;
    }

    div.stButton > button {
        background: #6C4AB6 !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
        padding: 12px 30px !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# بيانات تجريبية
# لاحقًا نربطها بقاعدة البيانات
# =========================

feedback_data = [
    {
        "rating": 1,
        "comment": "التطبيق يعلق كثير ويقفل فجأة.",
    },
    {
        "rating": 1,
        "comment": "رمز تسجيل الدخول لا يصل.",
    },
    {
        "rating": 2,
        "comment": "الخدمة تأخرت وتجاوزت المدة المحددة.",
    },
    {
        "rating": 2,
        "comment": "واجهة الموقع معقدة وصعبة.",
    },
    {
        "rating": 1,
        "comment": "خدمة العملاء لا ترد.",
    },
    {
        "rating": 4,
        "comment": "الإجراءات واضحة والخدمة جيدة.",
    },
    {
        "rating": 5,
        "comment": "الخدمة سريعة والموظف متعاون.",
    },
]


# =========================
# شكل استجابة OpenAI
# =========================

class Reason(BaseModel):
    name: str
    count: int


class AnalysisResult(BaseModel):
    satisfaction_reasons: list[Reason]
    dissatisfaction_reasons: list[Reason]
    smart_feedback: str


# =========================
# التحليل
# =========================

def analyze_comments(data):
    if not API_KEY:
        raise ValueError(
            "مفتاح OPENAI_API_KEY غير موجود داخل ملف .env"
        )

    records = "\n".join(
        f"- التقييم: {item['rating']} | التعليق: {item['comment']}"
        for item in data
        if item.get("comment")
    )

    client = OpenAI(api_key=API_KEY)

    response = client.chat.completions.parse(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": """
أنت متخصص في تحليل تعليقات تجربة العملاء باللغة العربية.

صنف السجلات حسب التقييم فقط:
- التقييم 1 أو 2: سبب عدم رضا.
- التقييم 4 أو 5: سبب رضا.
- التقييم 3: تجاهله.

استخرج سبباً رئيسياً واحداً من كل تعليق، ثم اجمع الأسباب المتشابهة
واحسب عدد مرات تكرارها.

استخدم أسماء أسباب عربية واضحة ومختصرة مثل:
المشاكل التقنية، سرعة إنجاز الخدمة، سهولة الاستخدام،
وضوح الإجراءات، تسجيل الدخول والوصول،
جودة الدعم وخدمة العملاء، جودة الخدمة.

لا تخترع سبباً غير موجود في التعليق.

اكتب أيضاً فيدباك ذكياً يتضمن:
- أبرز نقاط القوة.
- أبرز المشكلات.
- توصيات عملية للتحسين.
"""
            },
            {
                "role": "user",
                "content": records,
            },
        ],
        response_format=AnalysisResult,
    )

    result = response.choices[0].message.parsed

    if result is None:
        raise ValueError("لم يرجع النموذج نتيجة صالحة.")

    return result


# =========================
# عرض بطاقة الأسباب
# =========================

def show_reasons(title, reasons, badge_class):
    if reasons:
        rows = "".join(
            (
                '<div class="row">'
                f'<span>{html.escape(item.name)}</span>'
                f'<span class="count {badge_class}">{item.count}</span>'
                '</div>'
            )
            for item in reasons
        )
    else:
        rows = '<p class="feedback-text">لا توجد أسباب في هذا القسم.</p>'

    card = (
        '<div class="card">'
        f'<div class="card-title">{title}</div>'
        f'{rows}'
        '</div>'
    )

    st.markdown(card, unsafe_allow_html=True)


# =========================
# واجهة الصفحة
# =========================

st.markdown(
    '<div class="title">تحليل تعليقات العملاء</div>',
    unsafe_allow_html=True,
)

st.markdown(
    (
        '<div class="description">'
        'تحليل أسباب رضا وعدم رضا العملاء وتقديم ملخلص تحليلي ذكي'
        '</div>'
    ),
    unsafe_allow_html=True,
)

_, center, _ = st.columns([1, 1.5, 1])

with center:
    analyze_button = st.button(
        "بدء تحليل البيانات بالذكاء الاصطناعي",
        use_container_width=True,
    )


# =========================
# تنفيذ وعرض النتائج
# =========================

if analyze_button:
    with st.spinner("جاري تحليل التعليقات..."):
        try:
            result = analyze_comments(feedback_data)

            st.success("تم تحليل التعليقات بنجاح.")

            col_right, col_left = st.columns(2, gap="large")

            with col_right:
                show_reasons(
                    "أسباب الرضا",
                    result.satisfaction_reasons,
                    "positive",
                )

            with col_left:
                show_reasons(
                    "أسباب عدم الرضا",
                    result.dissatisfaction_reasons,
                    "negative",
                )

            safe_feedback = html.escape(
                result.smart_feedback
            ).replace("\n", "<br>")

            feedback_card = (
                '<div class="card feedback">'
                '<div class="card-title">ملخص التحليل الذكي</div>'
                f'<div class="feedback-text">{safe_feedback}</div>'
                '</div>'
            )

            st.markdown(
                feedback_card,
                unsafe_allow_html=True,
            )

        except Exception as error:
            st.error(f"حدث خطأ أثناء التحليل: {error}")


st.caption(
    f"البيانات الحالية تجريبية: {len(feedback_data)} تعليقات"
)