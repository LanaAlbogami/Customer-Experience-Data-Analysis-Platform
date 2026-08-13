import math
import textwrap

import streamlit as st
import plotly.graph_objects as go
from style import apply_theme, COLORS

apply_theme()

# Defines consistent colors for current, target, and previous KPI values.
ROLE_COLORS = {
    "current": "#2FA88E",   # Current value
    "target": "#F4B740",    # Target value
    "previous": "#1F3A5F",  # Previous value
}

# Applies right-to-left layout and custom dashboard styling.
st.markdown("""
<style>
.stApp, .stApp p, .stApp span, .stMarkdown, .stCaption,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
div[data-testid="stMetricLabel"], div[data-testid="stMetricValue"] {
    direction: rtl;
    text-align: right;
}
[data-testid="stHeaderActionElements"] { display: none; }

/* Styles bordered Streamlit containers as dashboard cards. */
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

/* Styles multi-select controls for compact RTL display. */
div[data-baseweb="select"] > div {
    direction: rtl;
}
span[data-baseweb="tag"] {
    background-color: #6C4AB6 !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    padding: 2px 6px !important;
}

/* Keeps filter popovers compact. */
div[data-testid="stPopoverBody"] {
    max-width: 280px;
    padding: 12px 16px !important;
}

/* Custom styling for dashboard filter controls. */
.filter-label {
    color: #6B7398;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 6px;
    text-align: right;
}

/* Styles filter expanders as clean cards. */
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

<<<<<<< Updated upstream:Departments/Dashboard.py
/* Styles filter checkboxes as pill-like options. */
=======
/* Checkbox كأنها Toggle Pill ملونة */
>>>>>>> Stashed changes:Dashboard.py
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

st.title("لوحة مؤشرات تجربة العميل")

from data_service import fetch_records_from_db

mock_records = fetch_records_from_db()

if not mock_records:
    st.warning("لا توجد بيانات بعد بقاعدة البيانات")
    st.stop()


def _average_ignoring_none(values):
    """Returns the average of available numeric values, ignoring missing entries."""
    numeric_values = [v for v in values if v is not None]
    if not numeric_values:
        return None
    return round(sum(numeric_values) / len(numeric_values), 2)


def _number_or_none(value):
    """Converts a value to a float while safely handling empty or invalid input."""
    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _display_table_value(value, kind=None):
    """Formats numeric values for display in dashboard tables and lists."""
    number = _number_or_none(value)

    if number is None:
        return "—"

    if kind == "percent":
        return f"{number:g}%"

    return f"{number:g}"


# Default KPI targets used when no target value is stored in the database.
DEFAULT_TARGETS = {"csat": 85, "ces": 69, "nps": 76}


def _target_or_default(code, value):
    """Returns the stored target value or falls back to the default target."""
    number = _number_or_none(value)
    return DEFAULT_TARGETS[code] if number is None else number


# Builds dashboard filters that support multiple selections.
st.subheader("عرض حسب")

all_years = sorted({r["year"] for r in mock_records})
all_periods = sorted({r["period"] for r in mock_records})
all_depts = sorted({r["department"] for r in mock_records})
all_services = sorted({r["service"] for r in mock_records})


def _sync_dept_with_services():
    """Synchronizes department selections with the currently selected services."""
    selected = st.session_state.get("filter_service", [])
    if not selected:
        return

    related_depts = sorted({
        r["department"] for r in mock_records if r["service"] in selected
    })
    if related_depts:
        st.session_state["filter_dept"] = related_depts


def _styled_multiselect(label, options, key, default=None):
    """Creates a custom multi-select filter using an expander and checkboxes."""
    if default is None:
        default = options

    # Reads the current checkbox state or falls back to its default selection.
    def _is_checked(option):
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

    st.markdown(
        f'<div class="filter-label">{label}</div>',
        unsafe_allow_html=True,
    )

    with st.expander(summary_text, expanded=False, key=f"expander_{key}"):
        select_all = st.checkbox(
            "تحديد الكل",
            value=(len(current) == len(options)),
            key=f"{key}_select_all",
        )

        # Updates all option states immediately when "Select All" is enabled.
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


row1_col1, row1_col2 = st.columns(2)
with row1_col1:
    selected_years = _styled_multiselect(
        "السنة", all_years, key="year", default=[all_years[-1]]
    )
with row1_col2:
    selected_periods = _styled_multiselect(
        "الفترة", all_periods, key="period", default=[all_periods[-1]]
    )

row2_col1, row2_col2 = st.columns(2)
with row2_col1:
    selected_depts = _styled_multiselect(
        "القطاع", all_depts, key="dept", default=all_depts
    )
with row2_col2:
    selected_services = _styled_multiselect(
        "الخدمة", all_services, key="service", default=all_services
    )

# Restores empty filters to "all" to keep the dashboard populated.
if not selected_years:
    selected_years = list(all_years)
if not selected_periods:
    selected_periods = list(all_periods)
if not selected_depts:
    selected_depts = list(all_depts)
if not selected_services:
    selected_services = list(all_services)

matching_records = [
    r for r in mock_records
    if r["year"] in selected_years
    and r["period"] in selected_periods
    and r["department"] in selected_depts
    and r["service"] in selected_services
]

if not matching_records:
    st.warning("لا توجد بيانات مطابقة لهذا الاختيار.")
    st.stop()


def _combine_records(records):
    """Combines matching records by averaging KPI and factor values when needed."""
    if len(records) == 1:
        return records[0]

    unique_depts = {r["department"] for r in records}
    unique_services = {r["service"] for r in records}

    combined = {
        "section": next(iter(unique_depts)) if len(unique_depts) == 1 else "عدة قطاعات",
        "department": next(iter(unique_depts)) if len(unique_depts) == 1 else "عدة قطاعات",
        "service": next(iter(unique_services)) if len(unique_services) == 1 else f"متوسط {len(records)} خدمة/سجل",
        "year": records[0]["year"],
        "period": records[0]["period"],
        "factors": {},
    }

    for code in ("csat", "ces", "nps"):
        for suffix in ("prev", "current", "target"):
            key = f"{code}_{suffix}"
            combined[key] = _average_ignoring_none(r.get(key) for r in records)

    all_factor_names = {
        name
        for r in records
        for name in r.get("factors", {})
    }
    for factor_name in all_factor_names:
        values = [
            r["factors"][factor_name]["current_value"]
            for r in records
            if factor_name in r.get("factors", {})
        ]
        combined["factors"][factor_name] = {
            "current_value": _average_ignoring_none(values),
        }

    return combined


rec = _combine_records(matching_records)

# Displays the main KPI cards with previous, current, and target values.
LRM = "\u200e"
st.subheader("المؤشرات الرئيسية")

# Keeps KPI cards ordered from right to left: CSAT, CES, then NPS.
col_csat, col_ces, col_nps = st.columns(3)


# Generates the SVG markup used to render a circular KPI indicator.
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
    """Normalizes KPI values into a 0–100 range for donut chart rendering."""
    number = _number_or_none(value)

    if number is None:
        return 0.0

    if kind == "percent":
        return min(max(number, 0.0), 100.0)

    return min(max((number + 100.0) / 2.0, 0.0), 100.0)


def _display_value(value, kind):
    """Formats a KPI value for display and shows a dash when it is unavailable."""
    number = _number_or_none(value)

    if number is None:
        return "—"

    rounded = int(round(number))

    return f"{rounded}%" if kind == "percent" else f"{rounded}"


# Renders a complete KPI card with target, current, and previous indicators.
def kpi_block(col, label, current, prev, target, kind):
    with col:
        with st.container(border=True):
            st.markdown(f'<div class="card-title">{label}</div>', unsafe_allow_html=True)

            target_pct = _normalize(target, kind)
            current_pct = _normalize(current, kind)
            prev_pct = _normalize(prev, kind)

            # Arranges target, current, and previous values within each KPI card.
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
    _target_or_default("csat", rec.get("csat_target")),
    kind="percent",
)

kpi_block(
    col_ces,
    "CES - جهد العميل",
    rec.get("ces_current"),
    rec.get("ces_prev"),
    _target_or_default("ces", rec.get("ces_target")),
    kind="range",
)

kpi_block(
    col_nps,
    "NPS - التوصية بالخدمة",
    rec.get("nps_current"),
    rec.get("nps_prev"),
    _target_or_default("nps", rec.get("nps_target")),
    kind="range",
)

# Displays the top CSAT services and the KPI comparison charts.
col_top5, col_chart = st.columns([0.8, 1.4])

with col_top5:
    with st.container(border=True):
        top_services = sorted(
            matching_records,
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
            st.markdown(
                f'<div style="padding: 6px 6px 0 6px;">'
                f'<div class="card-title">أفضل 5 خدمات حسب CSAT</div>'
                f'{rows}'
                f'</div>',
                unsafe_allow_html=True,
            )

with col_chart:
    with st.container(border=True):
        st.markdown(
            '<div class="card-title" style="text-align:center;">مقارنة السابق والحالي والمستهدف</div>',
            unsafe_allow_html=True,
        )

        # Uses each KPI's valid scale while keeping chart dimensions aligned.
        indicator_specs = [
            ("CSAT", rec.get("csat_prev"), rec.get("csat_current"), _target_or_default("csat", rec.get("csat_target")), [0, 100]),
            ("CES", rec.get("ces_prev"), rec.get("ces_current"), _target_or_default("ces", rec.get("ces_target")), [-100, 100]),
            ("NPS", rec.get("nps_prev"), rec.get("nps_current"), _target_or_default("nps", rec.get("nps_target")), [-100, 100]),
        ]

        categories = ["السابق", "الحالي", "المستهدف"]
        role_order = [ROLE_COLORS["previous"], ROLE_COLORS["current"], ROLE_COLORS["target"]]

        mini_col1, mini_col2, mini_col3 = st.columns(3)

        for mini_col, (name, prev_v, curr_v, targ_v, y_range) in zip(
            [mini_col1, mini_col2, mini_col3], indicator_specs
        ):
            with mini_col:
                st.markdown(
                    f'<div style="text-align:center; font-weight:800; '
                    f'color:#16213E; margin-bottom:6px;">{name}</div>',
                    unsafe_allow_html=True,
                )

                values = [
                    _number_or_none(prev_v) or 0,
                    _number_or_none(curr_v) or 0,
                    _number_or_none(targ_v) or 0,
                ]

                mini_fig = go.Figure()
                mini_fig.add_bar(
                    x=categories,
                    y=values,
                    marker_color=role_order,
                    marker_cornerradius=6,
                )
                mini_fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=320,
                    margin=dict(l=50, r=10, t=10, b=45),  # Keeps room for x-axis labels
                    font=dict(color="#16213E", size=12),
                    showlegend=False,
                )
                mini_fig.update_yaxes(
                    range=y_range,
                    showgrid=True,
                    gridcolor="#F1F2F7",
                    zeroline=True,
                    zerolinecolor="#8A94B5",
                    zerolinewidth=2,
                    automargin=False,  # Keeps chart margins consistent across KPIs
                    tickfont=dict(size=11),
                    dtick=25 if y_range[0] == 0 else 50,
                )
                mini_fig.update_xaxes(
                    showgrid=False,
                    tickangle=0,          # Keeps x-axis labels horizontal
                    tickfont=dict(size=11),
                )

                st.plotly_chart(
                    mini_fig,
                    use_container_width=True,
                    config={"displayModeBar": False},
                )

# Displays CSAT results grouped by the available factors.
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

        # Wraps long factor names to prevent overlap in the chart.
        display_names = [
            "<br>".join(textwrap.wrap(name, width=28)) or name
            for name in display_names_raw
        ]

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
            textposition="outside",
            textfont=dict(color="#16213E", size=13),
            hovertemplate="%{y}<br>%{x:.2f}%<extra></extra>",
        )
        factor_fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=max(340, 80 * len(display_names)),
            bargap=0.45,
            margin=dict(l=10, r=200, t=10, b=10),
            font=dict(color="#16213E", size=13),
            xaxis=dict(
                range=[100, 0],
                showgrid=True,
                gridcolor="#F1F2F7",
                zeroline=False,
            ),
            yaxis=dict(
                side="right",
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

# Displays the five most recent records for the active filters.
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


# Builds one HTML table row from a dashboard record.
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


# Uses the first five matching records, already ordered from newest to oldest.
rows_html = "".join(make_row(r) for r in matching_records[:5])

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