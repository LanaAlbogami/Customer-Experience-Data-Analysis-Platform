'''import streamlit as st
import plotly.graph_objects as go 
from style import apply_theme, COLORS 

st.set_page_config(page_title= "لوحة المعلومات", layout='wide')
apply_theme()


st.markdown("""
<style>
st.stApp, .stApp p, .stApp span, .stMarkdown,  .stCaption, 
            .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
            div[data-testid="stMetricLable"], div[data-testid="stmetricValue"] {
            direction: rtl;
            text-align: right;
            }
            [data-testid="stHeaderActionElement"] {display: none;}
</style>
        
            
            """, unsafe_allow_html=True)
st.title("لوحة المعلومات")
st.caption("نظرة عامة على أداء مؤشرات تجربة العميل")
'''

import streamlit as st
import plotly.graph_objects as go
from style import apply_theme, COLORS

st.set_page_config(page_title="لوحة المعلومات", layout="wide")
apply_theme()

# ---- Force RTL + hide the auto header-link icon ----
st.markdown("""
<style>
.stApp, .stApp p, .stApp span, .stMarkdown, .stCaption,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"] {
    direction: rtl;
    text-align: right;
}
[data-testid="stHeaderActionElements"] { display: none; }
</style>
""", unsafe_allow_html=True)

st.title("لوحة المعلومات")
st.caption("نظرة عامة على أداء مؤشرات تجربة العميل")

# قبل: كتلة mock_records كاملة (احذفيها)
# بدلها بـ:
from data_service import fetch_records_from_db

mock_records = fetch_records_from_db()

if not mock_records:
    st.warning("لا توجد بيانات بعد بقاعدة البيانات")
    st.stop()

# ---- Filters: السنة، الفترة، الإدارة، الخدمة ----
st.subheader("عرض حسب")
f1, f2, f3, f4 = st.columns(4)

with f1:
    year = st.selectbox("السنة", sorted({r["year"] for r in mock_records}))
with f2:
    period = st.selectbox("الفترة", sorted({r["period"] for r in mock_records}))
with f3:
    dept = st.selectbox("الإدارة", ["كل الإدارات"] + list({r["department"] for r in mock_records}))
with f4:
    if dept == "كل الإدارات":
        services = {r["service"] for r in mock_records}
    else:
        services = {r["service"] for r in mock_records if r["department"] == dept}
    service = st.selectbox("الخدمة", ["كل الخدمات"] + list(services))

# ---- Pick the record matching ALL filters ----
rec = next(
    (r for r in mock_records
     if (dept == "كل الإدارات" or r["department"] == dept)
     and r["year"] == year
     and r["period"] == period
     and (service == "كل الخدمات" or r["service"] == service)),
    None
)

if rec is None:
    st.warning("لا توجد بيانات مطابقة لهذا الاختيار")
    st.stop()

# ---- KPI cards ----
LRM = "\u200e"  # علامة خفية تجبر الأرقام/الرموز تتعرض صح جوا نص عربي
st.subheader("المؤشرات الرئيسية")
col1, col2, col3 = st.columns(3)


def kpi_block(col, label, current, prev, target, normalized, is_percent=False):
    with col:
        display_val = f'{current}%' if is_percent else current
        st.metric(label, display_val, delta=current - prev)
        st.caption(
            f'السابق: {LRM}{prev}{"%" if is_percent else ""}{LRM}   ·   '
            f'المستهدف: {LRM}{target}{"%" if is_percent else ""}{LRM}'
        )
        pct = min(max(normalized, 0.0), 1.0)
        st.progress(pct)
        st.caption(f'{LRM}{int(pct * 100)}%{LRM}')


kpi_block(col1, "NPS - التوصية بالخدمة", rec["nps_current"], rec["nps_prev"], rec["nps_target"],
          (rec["nps_current"] + 100) / 200)
kpi_block(col2, "CES - جهد العميل", rec["ces_current"], rec["ces_prev"], rec["ces_target"],
          (rec["ces_current"] + 100) / 200)
kpi_block(col3, "CSAT - رضا العميل", rec["csat_current"], rec["csat_prev"], rec["csat_target"],
          rec["csat_current"] / 100, is_percent=True)

# ---- Comments (teammate) + Comparison chart, side by side ----
col_comments, col_chart = st.columns([1, 1])

with col_comments:
    st.markdown("#### تصنيف تعليقات العملاء")
    st.info("🔜 هذا المكان محجوز لصديقتك — بتلصق كودها من comments.py هنا")

with col_chart:
    st.markdown("#### مقارنة السابق والحالي والمستهدف")
    indicators = ["NPS", "CES", "CSAT"]
    prev = [rec["nps_prev"], rec["ces_prev"], rec["csat_prev"]]
    curr = [rec["nps_current"], rec["ces_current"], rec["csat_current"]]
    targ = [rec["nps_target"], rec["ces_target"], rec["csat_target"]]

    fig = go.Figure()
    fig.add_bar(name="السابق", x=indicators, y=prev, marker_color=COLORS["muted"])
    fig.add_bar(name="الحالي", x=indicators, y=curr, marker_color=COLORS["purple"])
    fig.add_bar(name="المستهدف", x=indicators, y=targ, marker_color=COLORS["green"])
    fig.update_layout(
        barmode="group",
        plot_bgcolor=COLORS["card"],
        paper_bgcolor=COLORS["card"],
        height=380,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

# ---- Recent records table: custom HTML, matches the mockup ----
# ---- Recent records table: custom HTML, matches the mockup ----
st.subheader("أحدث الإدخالات")


def make_row(r):
    return (f'<tr>'
            f'<td style="padding:12px 16px;">{r["department"]}</td>'
            f'<td style="padding:12px 16px;">{r["service"]}</td>'
            f'<td style="padding:12px 16px;">{r["period"]} - {r["year"]}</td>'
            f'<td style="padding:12px 16px; font-weight:600;">{r["nps_current"]}</td>'
            f'<td style="padding:12px 16px; font-weight:600;">{r["ces_current"]}</td>'
            f'<td style="padding:12px 16px; font-weight:600;">{r["csat_current"]}%</td>'
            f'</tr>')


rows_html = "".join(make_row(r) for r in mock_records)

table_html = (
    f'<div dir="rtl" style="text-align:right; background:{COLORS["card"]}; border-radius:12px; '
    f'border:1px solid {COLORS["border"]}; overflow:hidden;">'
    f'<table style="width:100%; border-collapse:collapse; font-family:inherit;">'
    f'<thead><tr style="border-bottom:2px solid {COLORS["border"]};">'
    f'<th style="padding:12px 16px; text-align:right;">الإدارة</th>'
    f'<th style="padding:12px 16px; text-align:right;">الخدمة</th>'
    f'<th style="padding:12px 16px; text-align:right;">الفترة</th>'
    f'<th style="padding:12px 16px; text-align:right;">NPS</th>'
    f'<th style="padding:12px 16px; text-align:right;">CES</th>'
    f'<th style="padding:12px 16px; text-align:right;">CSAT</th>'
    f'</tr></thead><tbody>{rows_html}</tbody></table></div>'
)
st.markdown(table_html, unsafe_allow_html=True)

