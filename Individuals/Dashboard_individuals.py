import math
import os
import sys

# Add the project root and Individuals directory to the import path so shared modules work when this file runs directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import plotly.graph_objects as go
from style import apply_theme, COLORS

apply_theme()

ROLE_COLORS = {
    "current": "#2FA88E",
    "target": "#F4B740",
    "previous": "#1F3A5F",
}

DEFAULT_TARGETS = {"csat": 85, "nps": 76, "ces": 69}

# Defines the chronological period order used to determine the previous reporting period.
PERIOD_ORDER = ["الربع الأول", "الربع الثاني", "الربع الثالث", "الربع الرابع"]


def _previous_year_period(year, period):
    """
    Returns the year and reporting period immediately preceding the provided period.
    Handles year transitions when the current period is the first quarter.
    """
    if period not in PERIOD_ORDER:
        return None, None
    idx = PERIOD_ORDER.index(period)
    if idx == 0:
        return year - 1, PERIOD_ORDER[-1]
    return year, PERIOD_ORDER[idx - 1]


# Applies RTL layout and shared dashboard styling.
st.markdown("""
<style>
.stApp, .stApp p, .stApp span, .stMarkdown, .stCaption,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"] {
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

div[data-testid="stExpander"] {
    border: 1.5px solid #E7E5F5 !important;
    border-radius: 12px !important;
    background: #FFFFFF !important;
    box-shadow: 0 2px 8px rgba(108, 74, 182, 0.06);
    overflow: hidden;
}
div[data-testid="stExpander"] summary {
    padding: 10px 16px !important;
    background: #FBFAFE !important;
}
div[data-testid="stExpander"] summary:hover {
    background: #F1ECFB !important;
}
div[data-testid="stExpander"] summary p {
    font-size: 14px;
    color: #16213E;
    font-weight: 700;
}
div[data-testid="stExpanderDetails"] {
    padding: 6px 14px 14px 14px !important;
}

div[data-testid="stExpanderDetails"] div[data-testid="stCheckbox"] {
    background: #F7F5FC;
    border-radius: 8px;
    padding: 6px 10px;
    margin-bottom: 4px;
    transition: background 0.15s ease;
}

div[data-testid="stExpanderDetails"] div[data-testid="stCheckbox"]:hover {
    background: #EFE9FA;
}

div[data-testid="stExpanderDetails"] div[data-testid="stCheckbox"] label p {
    font-size: 13px;
    color: #16213E;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

st.title("لوحة مؤشرات تجربة العميل (أفراد)")

try:
    from Individuals.data_service_individuals import (
        aggregate_records,
        fetch_factor_order,
        fetch_indicator_names,
        fetch_individual_dataset,
    )
except ModuleNotFoundError:
    from data_service_individuals import (
        aggregate_records,
        fetch_factor_order,
        fetch_indicator_names,
        fetch_individual_dataset,
    )

dataset = fetch_individual_dataset()

if not dataset:
    st.warning("لا توجد بيانات أفراد بعد بقاعدة البيانات")
    st.stop()

factor_order = fetch_factor_order()
indicator_names = fetch_indicator_names()


def _number_or_none(value):
    # Converts valid values to float while safely handling empty or invalid input.
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _target_or_default(code, value):
    # Returns the stored target value, or the configured default when no value is available.
    number = _number_or_none(value)
    return DEFAULT_TARGETS.get(code, 0) if number is None else number


# Builds the demographic multi-select filters used to narrow the individual dataset.
st.subheader("عرض حسب")

def _distinct(field):
    # Returns sorted unique non-empty values for a specific dataset field.
    return sorted({
        r[field] for r in dataset if r.get(field)
    })

all_years = sorted({r["year"] for r in dataset})
all_periods = sorted({r["period"] for r in dataset})
all_genders = _distinct("gender")
all_age_groups = _distinct("age_group")
all_regions = _distinct("region")
all_educations = _distinct("education")
all_id_types = _distinct("id_type")
all_devices = _distinct("device")


def _styled_multiselect(label, options, key, default=None):
    """Creates a custom expandable multi-select filter using checkboxes."""
    if not options:
        st.markdown(f'<div class="filter-label">{label}</div>', unsafe_allow_html=True)
        st.caption("لا توجد بيانات")
        return []

    if default is None:
        default = options

    def _is_checked(option):
        # Reads the current checkbox state while falling back to the default selection.
        state_k = f"{key}_opt_{option}"
        if state_k in st.session_state:
            return st.session_state[state_k]
        return option in default

    current = [opt for opt in options if _is_checked(opt)]

    if len(current) == len(options):
        summary_text = "الكل"
    elif not current:
        summary_text = "لا شيء محدد"
    elif len(current) <= 2:
        summary_text = "، ".join(str(v) for v in current)
    else:
        summary_text = f"{len(current)} خيارات محددة"

    st.markdown(f'<div class="filter-label">{label}</div>', unsafe_allow_html=True)

    with st.expander(summary_text, expanded=False, key=f"expander_{key}"):
        select_all = st.checkbox(
            "تحديد الكل",
            value=(len(current) == len(options)),
            key=f"{key}_select_all",
        )

        if select_all:
            for option in options:
                st.session_state[f"{key}_opt_{option}"] = True

        new_selection = []
        for option in options:
            checked = st.checkbox(
                str(option),
                value=option in default,
                key=f"{key}_opt_{option}",
            )
            if checked:
                new_selection.append(option)

    return new_selection


row1c1, row1c2, row1c3, row1c4 = st.columns(4)
with row1c1:
    selected_years = _styled_multiselect(
        "السنة", all_years, key="ind_year", default=[all_years[-1]]
    )
with row1c2:
    selected_periods = _styled_multiselect(
        "الفترة", all_periods, key="ind_period", default=[all_periods[-1]]
    )
with row1c3:
    selected_genders = _styled_multiselect(
        "الجنس", all_genders, key="ind_gender"
    )
with row1c4:
    selected_age_groups = _styled_multiselect(
        "الفئة العمرية", all_age_groups, key="ind_age"
    )

row2c1, row2c2, row2c3, row2c4 = st.columns(4)
with row2c1:
    selected_regions = _styled_multiselect(
        "المنطقة", all_regions, key="ind_region"
    )
with row2c2:
    selected_educations = _styled_multiselect(
        "المستوى التعليمي", all_educations, key="ind_education"
    )
with row2c3:
    selected_id_types = _styled_multiselect(
        "نوع الهوية", all_id_types, key="ind_id_type"
    )
with row2c4:
    selected_devices = _styled_multiselect(
        "الجهاز", all_devices, key="ind_device"
    )


def _match(value, selected, all_values):
    """Checks whether a value matches the active filter selection."""
    if not all_values:
        return True
    if not selected:
        return False
    return value in selected


matching_records = [
    r for r in dataset
    if r["year"] in (selected_years or all_years)
    and r["period"] in (selected_periods or all_periods)
    and _match(r.get("gender"), selected_genders, all_genders)
    and _match(r.get("age_group"), selected_age_groups, all_age_groups)
    and _match(r.get("region"), selected_regions, all_regions)
    and _match(r.get("education"), selected_educations, all_educations)
    and _match(r.get("id_type"), selected_id_types, all_id_types)
    and _match(r.get("device"), selected_devices, all_devices)
]

if not matching_records:
    st.warning("لا توجد بيانات مطابقة لهذا الاختيار.")
    st.stop()

agg = aggregate_records(matching_records, factor_order, indicator_names)

# Retrieves records from the previous reporting period using the same demographic filters.
prev_years = set()
prev_periods = set()
for y in (selected_years or all_years):
    for p in (selected_periods or all_periods):
        py, pp = _previous_year_period(y, p)
        if py is not None:
            prev_years.add(py)
            prev_periods.add(pp)

prev_matching_records = [
    r for r in dataset
    if r["year"] in prev_years
    and r["period"] in prev_periods
    and _match(r.get("gender"), selected_genders, all_genders)
    and _match(r.get("age_group"), selected_age_groups, all_age_groups)
    and _match(r.get("region"), selected_regions, all_regions)
    and _match(r.get("education"), selected_educations, all_educations)
    and _match(r.get("id_type"), selected_id_types, all_id_types)
    and _match(r.get("device"), selected_devices, all_devices)
]

prev_agg = aggregate_records(prev_matching_records, factor_order, indicator_names)

st.caption(f"عدد الردود المطابقة للاختيار الحالي: {agg['participants_total']:,}")

# Displays the main KPI cards for CSAT and any additional supported indicators.
st.subheader("المؤشرات الرئيسية")

# Adds NPS or CES dynamically when those indicators exist in the database.
extra_indicators = [name for name in indicator_names if name.upper() in ("NPS", "CES")]
kpi_cols = st.columns(1 + len(extra_indicators))


def donut_svg(fill_percent, display_text, color, size=170, stroke=17, font_size=30, track_color="#DDE1EA"):
    # Generates the SVG used to visualize a KPI value as a circular progress indicator.
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
    # Converts indicator values into a 0-100 range for donut chart rendering.
    number = _number_or_none(value)
    if number is None:
        return 0.0
    if kind == "percent":
        return min(max(number, 0.0), 100.0)
    return min(max((number + 100.0) / 2.0, 0.0), 100.0)


def _display_value(value, kind):
    # Formats indicator values for display inside KPI cards.
    number = _number_or_none(value)
    if number is None:
        return "—"
    rounded = int(round(number))
    return f"{rounded}%" if kind == "percent" else f"{rounded}"


def kpi_block(col, label, previous, current, target, kind):
    """
    Renders a KPI card containing previous, current, and target values.
    The current value is emphasized using the larger center donut.
    """
    with col:
        with st.container(border=True):
            st.markdown(f'<div class="card-title" style="text-align:center;">{label}</div>', unsafe_allow_html=True)
            c_prev, c_current, c_target = st.columns([1, 1.3, 1])

            with c_prev:
                st.markdown(
                    donut_svg(_normalize(previous, kind), _display_value(previous, kind), ROLE_COLORS["previous"], size=115, stroke=13, font_size=18),
                    unsafe_allow_html=True,
                )
                st.markdown('<div style="text-align:center; font-size:12px; color:#8A94B5;">السابق</div>', unsafe_allow_html=True)

            with c_current:
                st.markdown(
                    donut_svg(_normalize(current, kind), _display_value(current, kind), ROLE_COLORS["current"]),
                    unsafe_allow_html=True,
                )
                st.markdown('<div style="text-align:center; font-size:13px; font-weight:700; color:#16213E;">الحالي</div>', unsafe_allow_html=True)

            with c_target:
                st.markdown(
                    donut_svg(_normalize(target, kind), _display_value(target, kind), ROLE_COLORS["target"], size=115, stroke=13, font_size=18),
                    unsafe_allow_html=True,
                )
                st.markdown('<div style="text-align:center; font-size:12px; color:#8A94B5;">المستهدف</div>', unsafe_allow_html=True)


kpi_block(
    kpi_cols[0],
    "CSAT - رضا الأفراد",
    prev_agg.get("csat_current"),
    agg.get("csat_current"),
    _target_or_default("csat", None),
    kind="percent",
)

INDICATOR_LABELS = {
    "NPS": "NPS - التوصية بالتطبيق",
    "CES": "CES - جهد الفرد",
}

for i, indicator_name in enumerate(extra_indicators, start=1):
    kpi_block(
        kpi_cols[i],
        INDICATOR_LABELS.get(indicator_name, indicator_name),
        prev_agg["indicators"].get(indicator_name, {}).get("current_value"),
        agg["indicators"].get(indicator_name, {}).get("current_value"),
        _target_or_default(indicator_name.lower(), None),
        kind="range",
    )

# Displays CSAT values across the configured demographic or experience factors.
with st.container(border=True):
    st.markdown(
        '<div class="card-title" style="text-align:center;">CSAT حسب العوامل</div>',
        unsafe_allow_html=True,
    )

    factor_values = [
        _number_or_none(agg["factors"][name]["current_value"])
        for name in factor_order
    ]

    display_names = factor_order[::-1]
    display_values = factor_values[::-1]

    bar_colors = [
        COLORS["purple"] if v is not None else COLORS["muted"]
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
        textposition="inside",
        insidetextanchor="end",
        textfont=dict(color="white", size=13),
        hovertemplate="%{y}<br>%{x:.2f}%<extra></extra>",
    )
    factor_fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=max(340, 80 * len(display_names)),
        bargap=0.45,
        margin=dict(l=10, r=200, t=10, b=10),
        font=dict(color="#16213E", size=13),
        xaxis=dict(range=[100, 0], showgrid=True, gridcolor="#F1F2F7", zeroline=False, automargin=True),
        yaxis=dict(side="right", showgrid=False, zeroline=False, automargin=False, tickfont=dict(size=13)),
        showlegend=False,
    )
    st.plotly_chart(factor_fig, use_container_width=True, config={"displayModeBar": False})

# Displays the five most recent records that match the current filter selection.
st.subheader("أحدث المدخلات")

st.markdown("""
<style>
.modern-table { border-collapse: separate; border-spacing: 0; width: 100%; }
.modern-table thead th {
    background: #F7F8FC; color: #6B7398; font-size: 13px; font-weight: 700;
    padding: 14px 18px; text-align: right; border-bottom: 1px solid #EEF0F5;
}
.modern-table tbody tr:nth-child(even) { background: #FAFBFD; }
.modern-table tbody tr:hover { background: #F1EEFA; }
.modern-table tbody td {
    padding: 14px 18px; color: #16213E; font-size: 14px; border-bottom: 1px solid #F3F4F9;
}
</style>
""", unsafe_allow_html=True)


def make_row(r):
    # Builds one HTML table row for an individual survey record.
    return (
        f'<tr>'
        f'<td>{r.get("gender") or "—"}</td>'
        f'<td>{r.get("region") or "—"}</td>'
        f'<td>{r.get("age_group") or "—"}</td>'
        f'<td>{r.get("period", "—")} - {r.get("year", "—")}</td>'
        f'</tr>'
    )


rows_html = "".join(make_row(r) for r in matching_records[:5])

table_html = (
    f'<div dir="rtl" style="text-align:right; background:{COLORS["card"]}; border-radius:16px; '
    f'border:1px solid {COLORS["border"]}; overflow:hidden; box-shadow: 0 5px 18px rgba(22, 33, 62, 0.05);">'
    f'<table class="modern-table">'
    f'<thead><tr><th>الجنس</th><th>المنطقة</th><th>الفئة العمرية</th><th>الفترة</th></tr></thead>'
    f'<tbody>{rows_html}</tbody></table></div>'
)
st.markdown(table_html, unsafe_allow_html=True)