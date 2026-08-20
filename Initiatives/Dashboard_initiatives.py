# -*- coding: utf-8 -*-
"""
Initiatives/Dashboard_initiatives.py
------------------------------------
لوحة معلومات المبادرات.

- كل البيانات تُقرأ من قاعدة بيانات المبادرات.
- الفترات تُحسب كأرباع (الربع الأول..الرابع) اعتمادًا على تاريخ الإنشاء.
- الرسم الدائري (Pie) يعرض نسب المبادرات حسب حالتها، ويتغيّر تفاعليًا
  مع الفلاتر (السنة، الفترة، القطاع، الخدمة).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import select

# مكوّن اختياري لالتقاط النقر على شرائح الرسمة مباشرةً من Plotly.
try:
    from streamlit_plotly_events import plotly_events

    HAVE_PLOTLY_EVENTS = True
except Exception:
    HAVE_PLOTLY_EVENTS = False

from database_Initiatives.connection import SessionLocal
from database_Initiatives.models import Action, Product, Section, Status
from style import apply_theme


apply_theme()


# ==================================================
# قراءة البيانات وحساب الأرباع (مدمجة في نفس ملف الداشبورد)
# ==================================================

# ترتيب الأرباع المعتمد.
QUARTERS = [
    "الربع الأول",
    "الربع الثاني",
    "الربع الثالث",
    "الربع الرابع",
]


def quarter_from_date(value):
    """إرجاع اسم الربع اعتمادًا على شهر تاريخ الإنشاء، أو None إذا لا يوجد تاريخ."""
    if value is None:
        return None

    month = getattr(value, "month", None)
    if not month:
        return None

    return QUARTERS[(int(month) - 1) // 3]


@st.cache_data(ttl=300, show_spinner="جاري تحميل بيانات المبادرات...")
def fetch_initiatives():
    """
    إرجاع كل المبادرات من قاعدة البيانات كقائمة قواميس جاهزة للعرض والفلترة.

    كل عنصر يحتوي: رقم المبادرة، القطاع، المنتج، الحالة، عنوان المبادرة،
    التواريخ الأربعة، بالإضافة إلى السنة والربع المحسوبين من تاريخ الإنشاء.
    """
    with SessionLocal() as session:
        rows = session.execute(
            select(
                Action.action_id,
                Action.action_name,
                Action.creation_date,
                Action.start_date,
                Action.expected_execution_date,
                Action.actual_execution_date,
                Section.section_name,
                Product.product_name,
                Status.status_name,
            )
            .join(Section, Action.section_id == Section.section_id)
            .join(Product, Action.product_id == Product.product_id)
            .join(Status, Action.status_id == Status.status_id)
            .order_by(Action.action_id)
        ).all()

    records = []

    for row in rows:
        creation_date = row.creation_date
        year = creation_date.year if creation_date is not None else None

        records.append(
            {
                "action_id": row.action_id,
                "section": row.section_name,
                "product": row.product_name,
                "status": row.status_name,
                "action_name": row.action_name,
                "creation_date": creation_date,
                "start_date": row.start_date,
                "expected_execution_date": row.expected_execution_date,
                "actual_execution_date": row.actual_execution_date,
                "year": year,
                "quarter": quarter_from_date(creation_date),
            }
        )

    return records


# ثابت يمثّل خيار "الكل" في الفلاتر.
ALL = "الكل"

# ألوان الحالات: نطابق ألوان المخطط في التصميم للحالات المعروفة،
# وأي حالة غير معروفة تأخذ لونًا من قائمة احتياطية بترتيب ثابت.
STATUS_COLOR_MAP = {
    "منجز": "#725BF8",
    "لا ينطبق": "#6A6D7E",
    "تم الحل": "#2FA88E",
    "تم الإسناد": "#FFD43B",
    "ألغيت": "#BA625D",
    "تحت الإجراء": "#63A1E8",
    "متأخر": "#F0A860",
}

FALLBACK_PALETTE = [
    "#4C6EF5", "#9775FA", "#F0A860", "#FFD43B", "#2FA88E",
    "#63D2E8", "#8B6F5C", "#E0654F", "#C94B5B", "#7A7F94",
    "#3BA55D", "#A67CDB",
]


# Page styling (مستوحى من لوحة المعلومات الحالية)

st.markdown(
    """
    <style>
    .stApp, .stApp p, .stApp span, .stMarkdown, .stCaption,
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
        direction: rtl;
        text-align: right;
    }
    [data-testid="stHeaderActionElements"] { display: none; }

    div[data-baseweb="select"] > div,
    div[data-baseweb="select"] span {
        direction: rtl;
        text-align: right;
    }

    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E7E8F1;
        border-radius: 16px;
        padding: 22px 26px;
        text-align: center;
        box-shadow: 0 5px 18px rgba(22, 33, 62, 0.04);
    }
    .kpi-card .kpi-label {
        color: #7A7F94;
        font-size: 15px;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .kpi-card .kpi-value {
        color: #16213E;
        font-size: 40px;
        font-weight: 850;
        line-height: 1.1;
    }
    .kpi-card .kpi-divider {
        height: 1px;
        background: #EEF0F6;
        margin: 14px 0;
    }

    .block-title {
        color: #16213E;
        font-size: 22px;
        font-weight: 850;
        margin: 6px 0 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.title("لوحة معلومات المبادرات")


# قراءة البيانات

try:
    records = fetch_initiatives()
except Exception as error:
    st.error(f"تعذر تحميل بيانات المبادرات من قاعدة البيانات: {error}")
    st.stop()

if not records:
    st.warning("لا توجد مبادرات في قاعدة البيانات بعد. ارفعي ملفًا من صفحة رفع بيانات المبادرات.")
    st.stop()


# الفلاتر: عرض حسب

st.subheader("عرض حسب")

years = sorted({r["year"] for r in records if r["year"] is not None}, reverse=True)
sections = sorted({r["section"] for r in records if r["section"]})

filter_row1 = st.columns(2)
filter_row2 = st.columns(2)

with filter_row1[0]:
    year_choice = st.selectbox(
        "السنة",
        options=[ALL, *years],
        index=0,
        key="init_dash_year",
    )

with filter_row1[1]:
    period_choice = st.selectbox(
        "الفترة",
        options=[ALL, *QUARTERS],
        index=0,
        key="init_dash_period",
    )

with filter_row2[0]:
    section_choice = st.selectbox(
        "القطاع",
        options=[ALL, *sections],
        index=0,
        key="init_dash_section",
    )

# خيارات الخدمة (المنتج) تعتمد على القطاع المختار.
if section_choice == ALL:
    products = sorted({r["product"] for r in records if r["product"]})
else:
    products = sorted(
        {
            r["product"]
            for r in records
            if r["product"] and r["section"] == section_choice
        }
    )

with filter_row2[1]:
    product_choice = st.selectbox(
        "الخدمة",
        options=[ALL, *products],
        index=0,
        key="init_dash_product",
    )


def passes_top_filters(record) -> bool:
    """هل يمرّ السجل من فلاتر: السنة والفترة والقطاع والخدمة؟"""
    if year_choice != ALL and record["year"] != year_choice:
        return False
    if period_choice != ALL and record["quarter"] != period_choice:
        return False
    if section_choice != ALL and record["section"] != section_choice:
        return False
    if product_choice != ALL and record["product"] != product_choice:
        return False
    return True


filtered = [r for r in records if passes_top_filters(r)]


# الرسم الدائري (حسب الحالة) + بطاقة عدد المبادرات

status_counts: dict[str, int] = {}
for record in filtered:
    status = record["status"] or "غير محدد"
    status_counts[status] = status_counts.get(status, 0) + 1

# ألوان ثابتة لكل حالة (نفس اللون في كل الفلاتر).
all_statuses = sorted({r["status"] or "غير محدد" for r in records})
color_for_status: dict[str, str] = {}
fallback_index = 0
for status in all_statuses:
    if status in STATUS_COLOR_MAP:
        color_for_status[status] = STATUS_COLOR_MAP[status]
    else:
        color_for_status[status] = FALLBACK_PALETTE[
            fallback_index % len(FALLBACK_PALETTE)
        ]
        fallback_index += 1

# مسافة بين الفلاتر وبين الرسمة والكارد.
st.markdown("<div style='height: 40px'></div>", unsafe_allow_html=True)

chart_col, kpi_col = st.columns([1.7, 1])

total_filtered = len(filtered)
selected_status = None  # الحالة المختارة بالنقر على الرسمة (إن وجدت)

with chart_col:
    if status_counts:
        labels = list(status_counts.keys())
        values = list(status_counts.values())
        colors = [color_for_status.get(label, "#7A7F94") for label in labels]

        pie = go.Figure(
            go.Pie(
                labels=labels,
                values=values,
                marker=dict(colors=colors),
                sort=False,
                direction="clockwise",
                textinfo="percent",
                texttemplate="%{percent:.0%}",
                textfont=dict(size=13, color="#FFFFFF"),
                hovertemplate="%{label}<br>عدد المبادرات: %{value}<br>النسبة: %{percent}<extra></extra>",
            )
        )
        pie.update_layout(
            height=430,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#16213E", size=13),
            legend=dict(
                orientation="v",
                x=1,
                y=0.5,
                font=dict(size=13),
            ),
        )

        if HAVE_PLOTLY_EVENTS:
            # النقر الحقيقي على شرائح الرسمة عبر مكوّن streamlit-plotly-events.
            #
            # نستخدم مفتاحًا ثابتًا حتى لا يُعاد تحميل الرسمة عند كل نقرة
            # (تغيير المفتاح يعيد بناء المكوّن ويسبّب وميضًا/إعادة تحميل).
            # المكوّن يرجّع آخر نقرة باستمرار، لذلك نتعامل مع النقرة الجديدة
            # فقط عندما تختلف عن آخر نقرة عولجت — وهذا يمنع أيضًا إلغاء
            # التحديد بالخطأ عند تغيير الفلاتر.
            clicked = plotly_events(
                pie,
                click_event=True,
                override_height=440,
                override_width="100%",
                key="init_pie_events",
            )

            raw_click = clicked or None
            if raw_click and raw_click != st.session_state.get(
                "init_pie_last_click"
            ):
                st.session_state["init_pie_last_click"] = raw_click

                index = raw_click[0].get("pointNumber")
                if index is None:
                    index = raw_click[0].get("pointIndex")

                if isinstance(index, int) and 0 <= index < len(labels):
                    st.session_state["init_pie_status"] = labels[index]

            selected_status = st.session_state.get("init_pie_status")

            # زر صغير لإلغاء التحديد يظهر فقط عند وجود تحديد.
            # الرسمة تبقى ثابتة (نفس المفتاح) فلا يحدث أي إعادة تحميل.
            if selected_status:
                if st.button("✕ إلغاء التحديد وعرض الكل", key="init_pie_clear"):
                    st.session_state["init_pie_status"] = None
                    selected_status = None
        else:
            # احتياطي: إن لم يكن المكوّن مثبتًا، نعرض الرسمة عاديًا مع محدّد حالات.
            st.plotly_chart(
                pie,
                use_container_width=True,
                config={"displayModeBar": False},
            )
            st.caption(
                "لتفعيل النقر على الرسمة نفسها، أضيفي الحزمة "
                "streamlit-plotly-events إلى requirements.txt."
            )
            status_choice = st.segmented_control(
                "اختر حالة لعرض عددها ونسبتها في البطاقة",
                options=[ALL, *labels],
                default=ALL,
                key="init_status_segment",
            )
            if status_choice and status_choice != ALL:
                selected_status = status_choice
    else:
        st.info("لا توجد مبادرات مطابقة للفلاتر المختارة.")

with kpi_col:
    if selected_status:
        # عند اختيار حالة: عدد مبادراتها ونسبتها من الإجمالي المفلتر.
        count_value = status_counts.get(selected_status, 0)
        count_label = f"عدد المبادرات ({selected_status})"
    else:
        # بدون اختيار: الإجمالي و100%.
        count_value = total_filtered
        count_label = "عدد المبادرات"

    percent_value = (
        (count_value / total_filtered * 100) if total_filtered else 0
    )

    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{count_label}</div>
            <div class="kpi-value">{count_value:,}</div>
            <div class="kpi-divider"></div>
            <div class="kpi-label">النسبة المئوية</div>
            <div class="kpi-value">{percent_value:.0f}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# تفاصيل المبادرات

st.markdown('<div class="block-title">تفاصيل المبادرات</div>', unsafe_allow_html=True)

statuses_in_view = sorted({r["status"] or "غير محدد" for r in filtered})

table_status_choice = st.selectbox(
    "حالة المبادرة",
    options=["كل الحالات", *statuses_in_view],
    index=0,
    key="init_dash_table_status",
)

if table_status_choice == "كل الحالات":
    table_records = filtered
else:
    table_records = [
        r for r in filtered if (r["status"] or "غير محدد") == table_status_choice
    ]

st.caption(f"عدد النتائج: {len(table_records):,}")


def _fmt_date(value) -> str:
    """عرض التاريخ بصيغة YYYY-MM-DD، أو شرطة عند غيابه."""
    if value is None:
        return "—"
    try:
        return value.strftime("%Y-%m-%d")
    except Exception:
        return str(value)


# بناء صفوف الجدول بالترتيب الظاهر في التصميم.
table_rows = [
    {
        "رقم المبادرة": r["action_id"],
        "القطاع": r["section"],
        "المنتج": r["product"],
        "حالة المبادرة": r["status"],
        "عنوان المبادرة": r["action_name"],
        "تاريخ الانشاء": _fmt_date(r["creation_date"]),
        "تاريخ بدء المبادرة": _fmt_date(r["start_date"]),
        "التاريخ المتوقع للتنفيذ": _fmt_date(r["expected_execution_date"]),
        "التاريخ الفعلي للتنفيذ": _fmt_date(r["actual_execution_date"]),
    }
    for r in table_records
]

column_order = [
    "رقم المبادرة",
    "القطاع",
    "المنتج",
    "حالة المبادرة",
    "عنوان المبادرة",
    "تاريخ الانشاء",
    "تاريخ بدء المبادرة",
    "التاريخ المتوقع للتنفيذ",
    "التاريخ الفعلي للتنفيذ",
]

if table_rows:
    table_dataframe = pd.DataFrame(table_rows, columns=column_order)
    st.dataframe(
        table_dataframe,
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("لا توجد مبادرات مطابقة للفلاتر المختارة.")