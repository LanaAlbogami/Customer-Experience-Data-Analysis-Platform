import math
import textwrap

import streamlit as st
import plotly.graph_objects as go
from style import apply_theme, COLORS

st.set_page_config(page_title="لوحة المعلومات", layout="wide")
apply_theme()

# ---- ألوان الأدوار: تُستخدم بثبات لكل مؤشر (CSAT/CES/NPS) وبار تشارت العوامل ----
ROLE_COLORS = {
    "current": "#2FA88E",   # الحالي: أخضر
    "target": "#F4B740",    # المستهدف: أصفر
    "previous": "#1F3A5F",  # السابق: كحلي
}

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

# ---- Filters: السنة، الفترة، القطاع، الخدمة ----
st.subheader("عرض حسب")
f1, f2, f3, f4 = st.columns(4)

with f1:
    year = st.selectbox("السنة", sorted({r["year"] for r in mock_records}))
with f2:
    period = st.selectbox("الفترة", sorted({r["period"] for r in mock_records}))
with f3:
    dept = st.selectbox("القطاع", ["كل القطاعات"] + list({r["department"] for r in mock_records}))
with f4:
    if dept == "كل القطاعات":
        services = {r["service"] for r in mock_records}
    else:
        services = {r["service"] for r in mock_records if r["department"] == dept}
    service = st.selectbox("الخدمة", ["كل الخدمات"] + list(services))


def _average_ignoring_none(values):
    """متوسط القيم المتوفرة فقط، أو None لو كلها فاضية."""
    numeric_values = [v for v in values if v is not None]
    if not numeric_values:
        return None
    return round(sum(numeric_values) / len(numeric_values), 2)


def _build_general_record(records, year, period, dept):
    """
    يبني سجل "عام" بمتوسط كل السجلات المطابقة لسنة/فترة/قطاع،
    يُستخدم لما ما فيه سجل يطابق الفلاتر بالضبط (مثلاً خدمة معينة
    ما عندها بيانات لهذي الفترة).
    """
    matching = [
        r for r in records
        if r["year"] == year
        and r["period"] == period
        and (dept == "كل القطاعات" or r["department"] == dept)
    ]

    if not matching:
        return None

    general = {
        "section": dept if dept != "كل القطاعات" else "عام",
        "department": dept if dept != "كل القطاعات" else "عام",
        "service": "عام (متوسط كل الخدمات المتاحة)",
        "year": year,
        "period": period,
        "factors": {},
    }

    for code in ("csat", "ces", "nps"):
        for suffix in ("prev", "current", "target"):
            key = f"{code}_{suffix}"
            general[key] = _average_ignoring_none(
                r.get(key) for r in matching
            )

    all_factor_names = {
        name
        for r in matching
        for name in r.get("factors", {})
    }
    for factor_name in all_factor_names:
        values = [
            r["factors"][factor_name]["current_value"]
            for r in matching
            if factor_name in r.get("factors", {})
        ]
        general["factors"][factor_name] = {
            "current_value": _average_ignoring_none(values),
        }

    return general


# ---- Pick the record matching ALL filters ----
rec = next(
    (r for r in mock_records
     if (dept == "كل القطاعات" or r["department"] == dept)
     and r["year"] == year
     and r["period"] == period
     and (service == "كل الخدمات" or r["service"] == service)),
    None
)

is_general_view = False

if rec is None:
    rec = _build_general_record(mock_records, year, period, dept)
    is_general_view = True

if rec is None:
    st.warning("لا توجد أي بيانات لهذه السنة والفترة على الإطلاق")
    st.stop()

if is_general_view:
    st.info(
        "لا توجد بيانات مطابقة تمامًا لهذا الاختيار، "
        "المعروض الآن متوسط عام لكل الخدمات المتاحة بنفس السنة والفترة."
    )

# ---- KPI cards: دائرة نسبة + (مستهدف يمين صغير - حالي بالنص كبير - سابق يسار صغير) ----
LRM = "\u200e"
st.subheader("المؤشرات الرئيسية")

# ترتيب من اليمين لليسار: CSAT ثم CES ثم NPS
col_csat, col_ces, col_nps = st.columns(3)


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


def _number_or_none(value):
    """تحويل القيمة إلى رقم، مع قبول None والقيم الفارغة."""
    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize(value, kind):
    """
    تحديد نسبة امتلاء الحلقة بصريًا.

    عند عدم وجود قيمة نستخدم صفرًا للحلقة،
    بينما النص داخلها يظهر كشرطة.
    """
    number = _number_or_none(value)

    if number is None:
        return 0.0

    if kind == "percent":
        return min(max(number, 0.0), 100.0)

    return min(max((number + 100.0) / 2.0, 0.0), 100.0)


def _display_value(value, kind):
    """عرض القيمة الحقيقية أو شرطة عند عدم توفرها."""
    number = _number_or_none(value)

    if number is None:
        return "—"

    rounded = int(round(number))

    return f"{rounded}%" if kind == "percent" else f"{rounded}"


def _display_table_value(value, kind=None):
    """تنسيق القيم داخل القوائم والجداول."""
    number = _number_or_none(value)

    if number is None:
        return "—"

    if kind == "percent":
        return f"{number:g}%"

    return f"{number:g}"


def kpi_block(col, label, current, prev, target, kind):
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
                    donut_svg(target_pct, _display_value(target, kind), ROLE_COLORS["target"], size=115, stroke=13, font_size=18),
                    unsafe_allow_html=True,
                )
                st.markdown('<div style="text-align:center; font-size:12px; color:#8A94B5;">المستهدف</div>', unsafe_allow_html=True)

            with c_current:
                st.markdown(
                    donut_svg(current_pct, _display_value(current, kind), ROLE_COLORS["current"], size=170, stroke=17, font_size=30),
                    unsafe_allow_html=True,
                )
                st.markdown('<div style="text-align:center; font-size:13px; font-weight:700; color:#16213E;">الحالي</div>', unsafe_allow_html=True)

            with c_prev:
                st.markdown(
                    donut_svg(prev_pct, _display_value(prev, kind), ROLE_COLORS["previous"], size=115, stroke=13, font_size=18),
                    unsafe_allow_html=True,
                )
                st.markdown('<div style="text-align:center; font-size:12px; color:#8A94B5;">السابق</div>', unsafe_allow_html=True)


kpi_block(
    col_csat,
    "CSAT - رضا العميل",
    rec.get("csat_current"),
    rec.get("csat_prev"),
    rec.get("csat_target"),
    kind="percent",
)

kpi_block(
    col_ces,
    "CES - جهد العميل",
    rec.get("ces_current"),
    rec.get("ces_prev"),
    rec.get("ces_target"),
    kind="range",
)

kpi_block(
    col_nps,
    "NPS - التوصية بالخدمة",
    rec.get("nps_current"),
    rec.get("nps_prev"),
    rec.get("nps_target"),
    kind="range",
)

# ---- أفضل 5 خدمات حسب CSAT + مخطط المقارنة ----
col_top5, col_chart = st.columns([1, 1])

with col_top5:
    with st.container(border=True):
        scope_records = [
            r for r in mock_records
            if r["year"] == year and r["period"] == period
            and (dept == "كل القطاعات" or r["department"] == dept)
        ]

        top_services = sorted(
            scope_records,
            key=lambda r: (
                _number_or_none(r.get("csat_current"))
                if _number_or_none(r.get("csat_current")) is not None
                else float("-inf")
            ),
            reverse=True,
        )[:5]

        if not top_services:
            st.markdown('<div class="card-title">أفضل 5 خدمات حسب CSAT</div>', unsafe_allow_html=True)
            st.info("لا توجد بيانات كافية لهذا الاختيار")
        else:
            rows = "".join(
                (
                    '<div class="row">'
                    f'<span>{i + 1}. {r["service"]}</span>'
                    f'<span class="count-square positive">{_display_table_value(r.get("csat_current"), "percent")}</span>'
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
        prev = [
            _number_or_none(rec.get("csat_prev")),
            _number_or_none(rec.get("ces_prev")),
            _number_or_none(rec.get("nps_prev")),
        ]

        curr = [
            _number_or_none(rec.get("csat_current")),
            _number_or_none(rec.get("ces_current")),
            _number_or_none(rec.get("nps_current")),
        ]

        targ = [
            _number_or_none(rec.get("csat_target")),
            _number_or_none(rec.get("ces_target")),
            _number_or_none(rec.get("nps_target")),
        ]

        fig = go.Figure()
        fig.add_bar(name="السابق", x=indicators, y=prev, marker_color=ROLE_COLORS["previous"], marker_cornerradius=8)
        fig.add_bar(name="الحالي", x=indicators, y=curr, marker_color=ROLE_COLORS["current"], marker_cornerradius=8)
        fig.add_bar(name="المستهدف", x=indicators, y=targ, marker_color=ROLE_COLORS["target"], marker_cornerradius=8)
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

# ---- توزيع CSAT حسب العوامل (Factors) للخدمة أو العرض العام المختار ----
with st.container(border=True):
    st.markdown(
        '<div class="card-title" style="text-align:center;">CSAT حسب العوامل</div>',
        unsafe_allow_html=True,
    )

    factors_dict = rec.get("factors") or {}

    if not factors_dict:
        st.info("لا توجد بيانات عوامل مسجلة لهذا الاختيار")
    else:
        factor_names = list(factors_dict.keys())
        factor_values = [
            _number_or_none(factors_dict[name].get("current_value"))
            for name in factor_names
        ]

        display_names_raw = factor_names[::-1]
        display_values = factor_values[::-1]

        # نلف الأسماء الطويلة على سطرين بدل ما تتقطع أو تتراكب
        display_names = [
            "<br>".join(textwrap.wrap(name, width=28)) or name
            for name in display_names_raw
        ]

        bar_colors = [
            ROLE_COLORS["current"] if v is not None else COLORS["muted"]
            for v in display_values
        ]

        text_labels = [
            f"{v:g}%" if v is not None else "—"
            for v in display_values
        ]

        factor_fig = go.Figure()
        factor_fig.add_bar(
            x=[v if v is not None else 0 for v in display_values],
            y=display_names,
            orientation="h",
            marker_color=bar_colors,
            marker_cornerradius=8,
            text=text_labels,
            textposition="outside",
            textfont=dict(color="#16213E", size=13),
        )
        factor_fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=max(340, 80 * len(display_names)),
            bargap=0.45,                  # يخلي الأشرطة أرفع بدل ما تملأ الصف كامل
            margin=dict(l=10, r=200, t=10, b=10),
            font=dict(color="#16213E", size=13),
            xaxis=dict(
                range=[100, 0],           # معكوس: يبدأ من اليمين
                showgrid=True,
                gridcolor="#F1F2F7",
                zeroline=False,
            ),
            yaxis=dict(
                side="right",              # أسماء العوامل يمين الرسم
                showgrid=False,
                zeroline=False,
                automargin=True,
                tickfont=dict(size=13),
            ),
            showlegend=False,
        )
        st.plotly_chart(
            factor_fig,
            use_container_width=True,
            config={"displayModeBar": False},
        )

# ---- Recent records table (آخر 5 إدخالات فقط) ----
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
    section_name = (
        r.get("section")
        or r.get("department")
        or "—"
    )

    return (
        f'<tr>'
        f'<td>{section_name}</td>'
        f'<td>{r.get("service", "—")}</td>'
        f'<td>{r.get("period", "—")} - {r.get("year", "—")}</td>'
        f'<td><span class="metric-pill pill-purple">'
        f'{_display_table_value(r.get("csat_current"), "percent")}'
        f'</span></td>'
        f'<td><span class="metric-pill pill-green">'
        f'{_display_table_value(r.get("ces_current"))}'
        f'</span></td>'
        f'<td><span class="metric-pill pill-blue">'
        f'{_display_table_value(r.get("nps_current"))}'
        f'</span></td>'
        f'</tr>'
    )


# آخر 5 سجلات فقط (mock_records مرتبة من الأحدث للأقدم من data_service.py)
rows_html = "".join(make_row(r) for r in mock_records[:5])

table_html = (
    f'<div dir="rtl" style="text-align:right; background:{COLORS["card"]}; border-radius:16px; '
    f'border:1px solid {COLORS["border"]}; overflow:hidden; box-shadow: 0 5px 18px rgba(22, 33, 62, 0.05);">'
    f'<table class="modern-table">'
    f'<thead><tr>'
    f'<th>القطاع</th>'
    f'<th>الخدمة</th>'
    f'<th>الفترة</th>'
    f'<th>CSAT</th>'
    f'<th>CES</th>'
    f'<th>NPS</th>'
    f'</tr></thead><tbody>{rows_html}</tbody></table></div>'
)
st.markdown(table_html, unsafe_allow_html=True)