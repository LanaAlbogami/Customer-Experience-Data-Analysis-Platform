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

/* حاويات الكروت الحقيقية (st.container(border=True)) */
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 16px !important;
    box-shadow: 0 5px 18px rgba(22, 33, 62, 0.05);
    padding: 22px !important;
}

.card-title {
    color: #16213E;
    font-size: 20px;
    font-weight: 800;
    margin-bottom: 14px;
    text-align: right;
    direction: rtl;
}

.row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #FFFFFF;
    border: 1px solid #F1F2F7;
    border-radius: 10px;
    padding: 14px 16px;
    margin: 6px 4px 12px 4px;
    color: #16213E;
    font-weight: 700;
    direction: rtl;
    box-shadow: 0 1px 4px rgba(22, 33, 62, 0.03);
}
.row:last-child { margin-bottom: 0; }

.count-square {
    min-width: 56px;
    height: 34px;
    padding: 0 12px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    font-weight: 800;
    font-size: 14px;
}
.positive { background: #E4F6F1; color: #2FA88E; }
.negative { background: #FCEBED; color: #C94B5B; }
</style>
""", unsafe_allow_html=True)

st.title("لوحة المعلومات")
st.caption("نظرة عامة على أداء مؤشرات تجربة العميل")

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

# ---- KPI cards: دائرة نسبة + (مستهدف يمين صغير - حالي بالنص كبير - سابق يسار صغير) ----
LRM = "\u200e"
st.subheader("المؤشرات الرئيسية")

# ترتيب من اليمين لليسار: CSAT ثم CES ثم NPS
col_csat, col_ces, col_nps = st.columns(3)


import math


def donut_svg(fill_percent, display_text, color, size=140, stroke=14, font_size=20, track_color="#DDE1EA"):
    fill_percent = min(max(fill_percent, 0), 100)
    r = (size - stroke) / 2
    c = size / 2
    circumference = 2 * math.pi * r
    offset = circumference * (1 - fill_percent / 100)
    return f'''
<div style="display:flex; justify-content:center; align-items:center;">
<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="{track_color}" stroke-width="{stroke}" />
  <circle cx="{c}" cy="{c}" r="{r}" fill="none" stroke="{color}" stroke-width="{stroke}"
    stroke-dasharray="{circumference:.2f}" stroke-dashoffset="{offset:.2f}"
    stroke-linecap="round" transform="rotate(-90 {c} {c})" />
  <text x="{c}" y="{c}" dominant-baseline="central" text-anchor="middle"
    font-size="{font_size}" font-weight="800" fill="#16213E">{display_text}</text>
</svg>
</div>
'''


def _normalize(value, kind):
    # يستخدم فقط لتحديد نسبة امتلاء الحلقة بصريًا (دايمًا من 0 إلى 100)
    # kind == "percent": القيمة أصلاً من 0 إلى 100 (CSAT)
    # kind == "range": القيمة من -100 إلى 100 (CES/NPS)
    if kind == "percent":
        return value
    return (value + 100) / 2


def _display_value(value, kind):
    # الرقم المكتوب جوا الدائرة = القيمة الحقيقية للمؤشر، مو النسبة المطبّعة.
    # نثبّته كرقم صحيح دايمًا (بدون .0) عشان ما يطول وينقطع من حافة الدائرة الصغيرة.
    rounded = int(round(value))
    return f"{rounded}%" if kind == "percent" else f"{rounded}"


def kpi_block(col, label, current, prev, target, color, kind):
    with col:
        with st.container(border=True):
            st.markdown(f'<div class="card-title">{label}</div>', unsafe_allow_html=True)

            target_pct = _normalize(target, kind)
            current_pct = _normalize(current, kind)
            prev_pct = _normalize(prev, kind)

            # ترتيب من اليمين لليسار: المستهدف (صغير) - الحالي (كبير) - السابق (صغير)
            c_target, c_current, c_prev = st.columns([1, 1.3, 1])

            with c_target:
                st.markdown(
                    donut_svg(target_pct, _display_value(target, kind), color, size=115, stroke=13, font_size=18),
                    unsafe_allow_html=True,
                )
                st.markdown('<div style="text-align:center; font-size:12px; color:#8A94B5;">المستهدف</div>', unsafe_allow_html=True)

            with c_current:
                st.markdown(
                    donut_svg(current_pct, _display_value(current, kind), color, size=170, stroke=17, font_size=30),
                    unsafe_allow_html=True,
                )
                st.markdown('<div style="text-align:center; font-size:13px; font-weight:700; color:#16213E;">الحالي</div>', unsafe_allow_html=True)

            with c_prev:
                st.markdown(
                    donut_svg(prev_pct, _display_value(prev, kind), color, size=115, stroke=13, font_size=18),
                    unsafe_allow_html=True,
                )
                st.markdown('<div style="text-align:center; font-size:12px; color:#8A94B5;">السابق</div>', unsafe_allow_html=True)


kpi_block(col_csat, "CSAT - رضا العميل", rec["csat_current"], rec["csat_prev"], rec["csat_target"],
          color="#6C4AB6", kind="percent")
kpi_block(col_ces, "CES - جهد العميل", rec["ces_current"], rec["ces_prev"], rec["ces_target"],
          color="#2FA88E", kind="range")
kpi_block(col_nps, "NPS - التوصية بالخدمة", rec["nps_current"], rec["nps_prev"], rec["nps_target"],
          color="#3B82C4", kind="range")

# ---- أفضل 5 خدمات حسب CSAT + مخطط المقارنة ----
col_top5, col_chart = st.columns([1, 1])

with col_top5:
    with st.container(border=True):
        scope_records = [
            r for r in mock_records
            if r["year"] == year and r["period"] == period
            and (dept == "كل الإدارات" or r["department"] == dept)
        ]

        top_services = sorted(scope_records, key=lambda r: r["csat_current"], reverse=True)[:5]

        if not top_services:
            st.markdown('<div class="card-title">أفضل 5 خدمات حسب CSAT</div>', unsafe_allow_html=True)
            st.info("لا توجد بيانات كافية لهذا الاختيار")
        else:
            rows = "".join(
                (
                    '<div class="row">'
                    f'<span>{i + 1}. {r["service"]}</span>'
                    f'<span class="count-square positive">{r["csat_current"]}%</span>'
                    '</div>'
                )
                for i, r in enumerate(top_services)
            )
            # عنوان الكارت + الصفوف بنداء واحد فقط، عشان الـ padding يضمن ينطبق فعليًا
            st.markdown(
                f'<div style="padding: 6px 6px 0 6px;">'
                f'<div class="card-title">أفضل 5 خدمات حسب CSAT</div>'
                f'{rows}'
                f'</div>',
                unsafe_allow_html=True,
            )

with col_chart:
    with st.container(border=True):
        st.markdown('<div class="card-title">مقارنة السابق والحالي والمستهدف</div>', unsafe_allow_html=True)

        # نفس الترتيب: CSAT ثم CES ثم NPS
        indicators = ["CSAT", "CES", "NPS"]
        prev = [rec["csat_prev"], rec["ces_prev"], rec["nps_prev"]]
        curr = [rec["csat_current"], rec["ces_current"], rec["nps_current"]]
        targ = [rec["csat_target"], rec["ces_target"], rec["nps_target"]]

        fig = go.Figure()
        fig.add_bar(name="السابق", x=indicators, y=prev, marker_color=COLORS["muted"], marker_cornerradius=8)
        fig.add_bar(name="الحالي", x=indicators, y=curr, marker_color=COLORS["purple"], marker_cornerradius=8)
        fig.add_bar(name="المستهدف", x=indicators, y=targ, marker_color=COLORS["green"], marker_cornerradius=8)
        fig.update_layout(
            barmode="group",
            bargap=0.35,
            bargroupgap=0.12,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=360,
            margin=dict(l=10, r=10, t=10, b=10),
            font=dict(color="#16213E", size=13),
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1, font=dict(size=13)),
        )
        fig.update_yaxes(showgrid=True, gridcolor="#F1F2F7", gridwidth=1, zeroline=False, showline=False)
        fig.update_xaxes(showgrid=False, showline=False, zeroline=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# ---- Recent records table ----
st.subheader("أحدث الإدخالات")

st.markdown("""
<style>
.modern-table { border-collapse: separate; border-spacing: 0; width: 100%; }
.modern-table thead th {
    background: #F7F8FC;
    color: #6B7398;
    font-size: 13px;
    font-weight: 700;
    padding: 14px 18px;
    text-align: right;
    border-bottom: 1px solid #EEF0F5;
}
.modern-table tbody tr { transition: background 0.15s ease; }
.modern-table tbody tr:nth-child(even) { background: #FAFBFD; }
.modern-table tbody tr:hover { background: #F1EEFA; }
.modern-table tbody td {
    padding: 14px 18px;
    color: #16213E;
    font-size: 14px;
    border-bottom: 1px solid #F3F4F9;
}
.metric-pill {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: 800;
    font-size: 13px;
}
.pill-purple { background: #F1ECFB; color: #6C4AB6; }
.pill-green { background: #E4F6F1; color: #2FA88E; }
.pill-blue { background: #E9F2FB; color: #3B82C4; }
</style>
""", unsafe_allow_html=True)


def make_row(r):
    return (f'<tr>'
            f'<td>{r["department"]}</td>'
            f'<td>{r["service"]}</td>'
            f'<td>{r["period"]} - {r["year"]}</td>'
            f'<td><span class="metric-pill pill-purple">{r["csat_current"]}%</span></td>'
            f'<td><span class="metric-pill pill-green">{r["ces_current"]}</span></td>'
            f'<td><span class="metric-pill pill-blue">{r["nps_current"]}</span></td>'
            f'</tr>')


rows_html = "".join(make_row(r) for r in mock_records)

table_html = (
    f'<div dir="rtl" style="text-align:right; background:{COLORS["card"]}; border-radius:16px; '
    f'border:1px solid {COLORS["border"]}; overflow:hidden; box-shadow: 0 5px 18px rgba(22, 33, 62, 0.05);">'
    f'<table class="modern-table">'
    f'<thead><tr>'
    f'<th>الإدارة</th>'
    f'<th>الخدمة</th>'
    f'<th>الفترة</th>'
    f'<th>CSAT</th>'
    f'<th>CES</th>'
    f'<th>NPS</th>'
    f'</tr></thead><tbody>{rows_html}</tbody></table></div>'
)
st.markdown(table_html, unsafe_allow_html=True)