from collections import defaultdict

import streamlit as st
from style import apply_theme, COLORS

apply_theme()

st.markdown("""
<style>
.stApp, .stApp p, .stApp span, .stMarkdown, .stCaption,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5 {
    direction: rtl;
    text-align: right;
}
[data-testid="stHeaderActionElements"] { display: none; }

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

.filter-label {
    color: #6B7398;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 6px;
    text-align: right;
}

.summary-label {
    color: #6B7398;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 6px;
}
.summary-value {
    color: #16213E;
    font-size: 26px;
    font-weight: 800;
}
.summary-value.gold { color: #2FA88E; }
.summary-value.bad { color: #C94B5B; }

.summary-card-inner {
    display: flex;
    flex-direction: column;
    justify-content: center;
    min-height: 78px;
}

.entity-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: #FFFFFF;
    border: 1px solid #F1F2F7;
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 10px;
    direction: rtl;
}
.entity-row:last-child { margin-bottom: 0; }
.entity-name {
    color: #16213E;
    font-weight: 700;
    font-size: 14px;
}
.entity-badge {
    min-width: 60px;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: 800;
    font-size: 13px;
    text-align: center;
}
.badge-good { background: #E4F6F1; color: #2FA88E; }
.badge-mid { background: #FDEEE0; color: #D6822B; }
.badge-bad { background: #FCEBED; color: #C94B5B; }

.modern-table { border-collapse: separate; border-spacing: 0; width: 100%; }
.modern-table thead th {
    background: #16213E; color: #FFFFFF; font-size: 13px; font-weight: 700;
    padding: 13px 16px; text-align: right;
}
.modern-table tbody tr:nth-child(even) { background: #FAFBFD; }
.modern-table tbody tr:hover { background: #F1EEFA; }
.modern-table tbody td {
    padding: 12px 16px; color: #16213E; font-size: 13.5px; border-bottom: 1px solid #F3F4F9;
}
</style>
""", unsafe_allow_html=True)

from data_service import fetch_records_with_entity


def _num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _csat_tier(value):
    # 85 فأعلى = أخضر، من 50 إلى 84 = برتقالي، تحت 50 = أحمر
    if value is None:
        return "badge-mid"
    if value >= 85:
        return "badge-good"
    if value >= 50:
        return "badge-mid"
    return "badge-bad"


all_records = fetch_records_with_entity()

if not all_records:
    st.warning("لا توجد بيانات بعد بقاعدة البيانات")
    st.stop()

st.markdown(
    """
    <div>
        <h1 style="color:#16213E; font-weight:900; margin-bottom:4px;">
            تحليل رضا الجهات الحكومية عن الخدمات المقدمة لهم
        </h1>
        <p style="color:#6B7398; font-size:14px; margin-bottom:20px;">
            متوسط رضا العملاء (CSAT) لكل جهة، محسوب من كل الخدمات المرتبطة بها
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==================================================
# Period filter (فلتر الفترة)
# ==================================================

all_periods = sorted({r["period"] for r in all_records})
period_options = ["الكل"] + all_periods

st.markdown('<div class="filter-label">الفترة</div>', unsafe_allow_html=True)
selected_period = st.selectbox(
    "الفترة",
    options=period_options,
    label_visibility="collapsed",
)

records = (
    all_records
    if selected_period == "الكل"
    else [r for r in all_records if r["period"] == selected_period]
)

if not records:
    st.warning("لا توجد بيانات مطابقة لهذا الاختيار.")
    st.stop()

# ==================================================
# Aggregate CSAT per entity (الجهة)
#
# نحسب CSAT للجهة بنفس منهجية حسابه للخدمة الواحدة تمامًا:
# 1) نجمع قيم كل عامل من العوامل السبعة عبر كل سجلات الجهة.
# 2) نحسب متوسط كل عامل لحاله.
# 3) نتوسط متوسطات العوامل السبعة عشان نطلع بـ CSAT النهائي للجهة.
# (بدل ما ناخذ متوسط أرقام CSAT الجاهزة من كل سجل مباشرة).
# ==================================================

entity_factor_values = defaultdict(lambda: defaultdict(list))

for r in records:
    entity_name = r["entity"]
    for factor_name, factor_data in r.get("factors", {}).items():
        # نتجاهل العامل لو عدد المشاركين فيه صفر أو فاضي —
        # هذا معناه "ما فيه بيانات فعلية"، مو تقييم حقيقي بصفر.
        participants = factor_data.get("participants_count")
        if not participants:
            continue

        value = _num(factor_data.get("current_value"))
        if value is not None:
            entity_factor_values[entity_name][factor_name].append(value)

entity_avg = {}
for entity_name, factor_map in entity_factor_values.items():
    factor_averages = [
        sum(values) / len(values)
        for values in factor_map.values()
        if values
    ]
    if factor_averages:
        entity_avg[entity_name] = round(
            sum(factor_averages) / len(factor_averages), 1
        )

sorted_entities = sorted(
    entity_avg.items(), key=lambda item: item[1], reverse=True
)

# ==================================================
# Summary cards
#
# ملاحظة مهمة: "متوسط CSAT العام" يُحسب من كل البيانات مباشرة بنفس
# منهجية العوامل السبعة، مو كمتوسط لأرقام الجهات بعد حسابها — لأن
# متوسط متوسطات الجهات يوزن كل جهة بنفس الوزن بغض النظر عن حجمها،
# وهذا يعطي رقم مختلف شوي عن الرقم الإجمالي الحقيقي.
# ==================================================

overall_factor_values = defaultdict(list)

for r in records:
    for factor_name, factor_data in r.get("factors", {}).items():
        participants = factor_data.get("participants_count")
        if not participants:
            continue

        value = _num(factor_data.get("current_value"))
        if value is not None:
            overall_factor_values[factor_name].append(value)

overall_factor_averages = [
    sum(values) / len(values)
    for values in overall_factor_values.values()
    if values
]

overall_csat = (
    round(sum(overall_factor_averages) / len(overall_factor_averages), 1)
    if overall_factor_averages
    else None
)

best_entity = sorted_entities[0] if sorted_entities else None
worst_entity = sorted_entities[-1] if sorted_entities else None

summary_col1, summary_col2, summary_col3, summary_col4 = st.columns(4)

with summary_col1:
    with st.container(border=True):
        overall_display = f"{overall_csat}%" if overall_csat is not None else "—"
        st.markdown(
            f'<div class="summary-card-inner">'
            f'<div class="summary-label">متوسط CSAT العام</div>'
            f'<div class="summary-value">{overall_display}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

with summary_col2:
    with st.container(border=True):
        st.markdown(
            f'<div class="summary-card-inner">'
            f'<div class="summary-label">عدد الجهات</div>'
            f'<div class="summary-value">{len(entity_avg)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

with summary_col3:
    with st.container(border=True):
        best_name = best_entity[0] if best_entity else "—"
        st.markdown(
            f'<div class="summary-card-inner">'
            f'<div class="summary-label">أعلى جهة</div>'
            f'<div class="summary-value gold">{best_name}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

with summary_col4:
    with st.container(border=True):
        worst_name = worst_entity[0] if worst_entity else "—"
        st.markdown(
            f'<div class="summary-card-inner">'
            f'<div class="summary-label">أقل جهة</div>'
            f'<div class="summary-value bad">{worst_name}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

# ==================================================
# Top 5 / Bottom 5 entities by CSAT
# ==================================================

st.subheader("أعلى وأقل الجهات حسب CSAT")

entity_count = len(sorted_entities)
n = 5 if entity_count >= 10 else max(1, entity_count // 2)

top_entities = sorted_entities[:n]
bottom_entities = sorted_entities[-n:][::-1] if n else []


def _render_entity_rows(entities):
    rows_html = "".join(
        f'<div class="entity-row">'
        f'<span class="entity-name">{name}</span>'
        f'<span class="entity-badge {_csat_tier(value)}">{value}%</span>'
        f'</div>'
        for name, value in entities
    )
    return rows_html or '<p style="color:#8A94B5;">لا توجد بيانات كافية</p>'


col_top, col_bottom = st.columns(2)

with col_top:
    with st.container(border=True):
        st.markdown(f'<div class="card-title">أعلى {n} جهات</div>', unsafe_allow_html=True)
        st.markdown(_render_entity_rows(top_entities), unsafe_allow_html=True)

with col_bottom:
    with st.container(border=True):
        st.markdown(f'<div class="card-title">أقل {n} جهات</div>', unsafe_allow_html=True)
        st.markdown(_render_entity_rows(bottom_entities), unsafe_allow_html=True)

# ==================================================
# Search + sort controls, then the full table
# ==================================================

st.subheader("تفاصيل الجهات والخدمات")

search_col, sort_col = st.columns([2, 1])

with search_col:
    search_query = st.text_input(
        "ابحث باسم الجهة", placeholder="ابحث باسم الجهة...",
        label_visibility="collapsed",
    )

with sort_col:
    sort_labels = {
        "csat-desc": "CSAT: من الأعلى إلى الأقل",
        "csat-asc": "CSAT: من الأقل إلى الأعلى",
        "name-asc": "اسم الجهة (أبجدي)",
    }
    sort_choice = st.selectbox(
        "الترتيب",
        options=list(sort_labels.keys()),
        format_func=lambda v: sort_labels[v],
        label_visibility="collapsed",
    )

table_rows = [
    {
        "entity": r["entity"],
        "sector": r.get("department", "—"),
        "service": r.get("service", "—"),
        "csat": _num(r.get("csat_current")),
        "nps": _num(r.get("nps_current")),
        "ces": _num(r.get("ces_current")),
    }
    for r in records
]

if search_query:
    table_rows = [
        row for row in table_rows if search_query.strip() in row["entity"]
    ]

if sort_choice == "csat-desc":
    table_rows.sort(key=lambda row: row["csat"] if row["csat"] is not None else -1, reverse=True)
elif sort_choice == "csat-asc":
    table_rows.sort(key=lambda row: row["csat"] if row["csat"] is not None else 1000)
else:
    table_rows.sort(key=lambda row: row["entity"])

st.caption(f"عدد النتائج: {len(table_rows):,}")


def _fmt_pct(value):
    return f"{value:g}%" if value is not None else "—"


def _fmt_signed(value):
    if value is None:
        return "—"
    return f"+{value:g}" if value > 0 else f"{value:g}"


def _fmt_plain(value):
    return f"{value:g}" if value is not None else "—"


def _make_table_row(row):
    return (
        "<tr>"
        f'<td>{row["entity"]}</td>'
        f'<td style="color:#8A94B5;">{row["sector"]}</td>'
        f'<td style="color:#6B7398;">{row["service"]}</td>'
        f'<td><span class="entity-badge {_csat_tier(row["csat"])}">{_fmt_pct(row["csat"])}</span></td>'
        f'<td>{_fmt_signed(row["nps"])}</td>'
        f'<td>{_fmt_plain(row["ces"])}</td>'
        "</tr>"
    )


if not table_rows:
    table_html = (
        f'<div dir="rtl" style="text-align:right; background:{COLORS["card"]}; border-radius:16px; '
        f'border:1px solid {COLORS["border"]}; padding: 36px; text-align:center; color:#8A94B5;">'
        f'لا توجد نتائج مطابقة لبحثك</div>'
    )
else:
    rows_html = "".join(_make_table_row(row) for row in table_rows)
    table_html = (
        f'<div dir="rtl" style="text-align:right; background:{COLORS["card"]}; border-radius:16px; '
        f'border:1px solid {COLORS["border"]}; overflow:hidden; box-shadow: 0 5px 18px rgba(22, 33, 62, 0.05);">'
        f'<table class="modern-table">'
        f'<thead><tr>'
        f'<th>اسم الجهة</th><th>قطاع</th><th>الخدمة</th><th>CSAT</th><th>NPS</th><th>CES</th>'
        f'</tr></thead><tbody>{rows_html}</tbody></table></div>'
    )

st.markdown(table_html, unsafe_allow_html=True)