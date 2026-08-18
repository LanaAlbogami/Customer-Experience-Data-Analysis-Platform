import math
import textwrap

import streamlit as st
import plotly.graph_objects as go
from style import apply_theme, COLORS

apply_theme()

ROLE_COLORS = {
    "current": "#2FA88E",
    "target": "#F4B740",
    "previous": "#1F3A5F",
}

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

div[data-baseweb="select"] > div {
    direction: rtl;
}
span[data-baseweb="tag"] {
    background-color: #6C4AB6 !important;
    border-radius: 8px !important;
    font-size: 12px !important;
    padding: 2px 6px !important;
}

div[data-testid="stPopoverBody"] {
    max-width: 280px;
    padding: 12px 16px !important;
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

st.title("لوحة مؤشرات تجربة العميل")

from data_service import fetch_records_from_db

mock_records = fetch_records_from_db()

if not mock_records:
    st.warning("لا توجد بيانات بعد بقاعدة البيانات")
    st.stop()


def _average_ignoring_none(values):
    """Return the arithmetic mean; formatting to 2 decimals is applied only when displayed."""
    numeric_values = [
        number
        for value in values
        if (number := _number_or_none(value)) is not None
    ]
    if not numeric_values:
        return None
    return sum(numeric_values) / len(numeric_values)


def _number_or_none(value):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_number(value):
    """Display values to two decimal places without changing stored/calculated values."""
    number = _number_or_none(value)
    if number is None:
        return "—"
    return f"{number:.2f}"


def _display_table_value(value, kind=None):
    text = _format_number(value)
    if text == "—":
        return text
    if kind == "percent":
        return f"{text}%"
    return text


# Default targets used only when a target is missing from the database.
DEFAULT_TARGETS = {"csat": 85, "ces": 76, "nps": 69}

# Indicator ranges according to the approved indicator definitions:
# CSAT: satisfied responses (4 + 5) / total sample => 0 to 100%
# CES: % easy (4 + 5) - % difficult (1 + 2) => -100 to 100
# NPS: % promoters (9 + 10) - % detractors (0 to 6) => -100 to 100
INDICATOR_RANGES = {
    "csat": (0, 100),
    "ces": (-100, 100),
    "nps": (-100, 100),
}


def _target_or_default(code, value):
    number = _number_or_none(value)
    return DEFAULT_TARGETS[code] if number is None else number


st.subheader("عرض حسب")

all_years = sorted({r["year"] for r in mock_records})
all_periods = sorted({r["period"] for r in mock_records})
all_depts = sorted({r["department"] for r in mock_records})


def _styled_multiselect(label, options, key, default=None):
    if default is None:
        default = options

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

    select_all_key = f"{key}_select_all"

    def _on_select_all_change():
        new_value = st.session_state[select_all_key]
        for option in options:
            st.session_state[f"{key}_opt_{option}"] = new_value

    def _on_option_change():
        all_now = all(
            st.session_state.get(f"{key}_opt_{opt}", opt in default)
            for opt in options
        )
        st.session_state[select_all_key] = all_now

    with st.expander(summary_text, expanded=False, key=f"expander_{key}"):
        if select_all_key not in st.session_state:
            st.session_state[select_all_key] = (len(current) == len(options))

        st.checkbox(
            "تحديد الكل",
            key=select_all_key,
            on_change=_on_select_all_change,
        )

        new_selection = []
        for option in options:
            opt_key = f"{key}_opt_{option}"

            if opt_key not in st.session_state:
                st.session_state[opt_key] = option in default

            checked = st.checkbox(
                str(option),
                key=opt_key,
                on_change=_on_option_change,
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

# If no department is explicitly selected, treat it as "all departments".
effective_depts = selected_depts if selected_depts else list(all_depts)

# Show only services that belong to the selected department(s).
available_services = sorted({
    r["service"]
    for r in mock_records
    if r["department"] in effective_depts
})

with row2_col2:
    selected_services = _styled_multiselect(
        "الخدمة",
        available_services,
        key="service",
        default=available_services,
    )

if not selected_years:
    selected_years = list(all_years)
if not selected_periods:
    selected_periods = list(all_periods)
if not selected_depts:
    selected_depts = list(all_depts)
if not selected_services:
    selected_services = list(available_services)

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


def _weighted_indicator(records, code):
    """
    Reproduce the Power BI filter-context calculation from stored groups.

    For CES/NPS, data_service stores each group's valid response count.
    Weighted averaging by that denominator is mathematically equivalent to
    calculating the measure over all raw rows in the current filter context.
    """
    weighted_pairs = []

    for record in records:
        value = _number_or_none(
            record.get(f"{code}_current")
        )
        count = _number_or_none(
            record.get(f"{code}_valid_count")
        )

        if (
            value is not None
            and count is not None
            and count > 0
        ):
            weighted_pairs.append(
                (value, count)
            )

    if weighted_pairs:
        total_count = sum(
            count
            for _, count in weighted_pairs
        )

        return sum(
            value * count
            for value, count in weighted_pairs
        ) / total_count

    # Calculated/manual records may not have a raw denominator.
    return _average_ignoring_none(
        record.get(f"{code}_current")
        for record in records
    )


def _weighted_factor(records, factor_name):
    """Aggregate one CSAT factor using its valid participant counts."""
    weighted_pairs = []
    fallback_values = []

    for record in records:
        factor = (
            record.get("factors", {})
            .get(factor_name)
        )

        if not factor:
            continue

        value = _number_or_none(
            factor.get("current_value")
        )
        count = _number_or_none(
            factor.get("participants_count")
        )

        if value is None:
            continue

        fallback_values.append(value)

        if count is not None and count > 0:
            weighted_pairs.append(
                (value, count)
            )

    if weighted_pairs:
        total_count = sum(
            count
            for _, count in weighted_pairs
        )

        return sum(
            value * count
            for value, count in weighted_pairs
        ) / total_count

    return _average_ignoring_none(
        fallback_values
    )


def _aggregate_period(records):
    """
    Aggregate all matching DB partitions for ONE half-year.

    CES/NPS use their exact valid-response denominators, matching the
    Power BI measures after 99/blanks are excluded.
    """
    if not records:
        return {}

    result = {
        "factors": {},
    }

    # CES / NPS match the raw Power BI measures through denominator weights.
    result["ces_current"] = _weighted_indicator(
        records,
        "ces",
    )
    result["nps_current"] = _weighted_indicator(
        records,
        "nps",
    )

    # CSAT remains based on the project's seven-factor method.
    all_factor_names = {
        name
        for record in records
        for name in record.get("factors", {})
    }

    factor_values = []

    for factor_name in all_factor_names:
        factor_value = _weighted_factor(
            records,
            factor_name,
        )

        result["factors"][factor_name] = {
            "current_value": factor_value,
        }

        if factor_value is not None:
            factor_values.append(
                factor_value
            )

    result["csat_current"] = (
        sum(factor_values) / len(factor_values)
        if factor_values
        else _average_ignoring_none(
            record.get("csat_current")
            for record in records
        )
    )

    for code in ("csat", "ces", "nps"):
        result[f"{code}_target"] = _average_ignoring_none(
            record.get(f"{code}_target")
            for record in records
        )

    result["department"] = (
        next(iter({
            r.get("department")
            for r in records
            if r.get("department")
        }))
        if len({
            r.get("department")
            for r in records
            if r.get("department")
        }) == 1
        else "عدة قطاعات"
    )

    services = {
        r.get("service")
        for r in records
        if r.get("service")
    }

    result["service"] = (
        next(iter(services))
        if len(services) == 1
        else f"متوسط {len(services)} خدمة"
    )

    result["period"] = (
        records[0].get("period")
    )

    return result


def _average_aggregates(aggregates):
    """
    Average already-calculated period/year results equally.

    This is where H1 and H2 are averaged 50/50 for the full-year view,
    matching the reporting rule the project uses.
    """
    aggregates = [
        item
        for item in aggregates
        if item
    ]

    if not aggregates:
        return {}

    if len(aggregates) == 1:
        return aggregates[0]

    result = {
        "factors": {},
    }

    for code in ("csat", "ces", "nps"):
        result[f"{code}_current"] = _average_ignoring_none(
            item.get(f"{code}_current")
            for item in aggregates
        )

        result[f"{code}_target"] = _average_ignoring_none(
            item.get(f"{code}_target")
            for item in aggregates
        )

    all_factor_names = {
        name
        for item in aggregates
        for name in item.get("factors", {})
    }

    for factor_name in all_factor_names:
        result["factors"][factor_name] = {
            "current_value": _average_ignoring_none(
                item.get("factors", {})
                .get(factor_name, {})
                .get("current_value")
                for item in aggregates
            ),
        }

    departments = {
        item.get("department")
        for item in aggregates
        if item.get("department")
    }

    services = {
        item.get("service")
        for item in aggregates
        if item.get("service")
    }

    result["department"] = (
        next(iter(departments))
        if len(departments) == 1
        else "عدة قطاعات"
    )

    result["service"] = (
        next(iter(services))
        if len(services) == 1
        else "عدة خدمات"
    )

    return result


def _combine_records(records):
    """
    Dashboard calculation flow:

    1) For each year and half-year, reproduce the Power BI measure over
       all raw-response partitions matching the filters.
    2) If H1 + H2 are selected, average the two half-year results equally.
    3) If several years are selected, average their yearly results equally.
    """
    if not records:
        return {}

    years = sorted({
        r.get("year")
        for r in records
        if r.get("year") is not None
    })

    yearly_results = []

    for year in years:
        year_records = [
            r for r in records
            if r.get("year") == year
        ]

        periods = [
            period
            for period in (
                "النصف الأول",
                "النصف الثاني",
            )
            if any(
                r.get("period") == period
                for r in year_records
            )
        ]

        period_results = []

        for period in periods:
            period_records = [
                r for r in year_records
                if r.get("period") == period
            ]

            period_results.append(
                _aggregate_period(
                    period_records
                )
            )

        year_result = _average_aggregates(
            period_results
        )
        year_result["year"] = year
        year_result["period"] = (
            periods[0]
            if len(periods) == 1
            else "السنة كاملة"
        )

        yearly_results.append(
            year_result
        )

    combined = _average_aggregates(
        yearly_results
    )

    combined["year"] = (
        years[0]
        if len(years) == 1
        else "عدة سنوات"
    )

    combined["period"] = (
        yearly_results[0].get("period")
        if len(yearly_results) == 1
        else "عدة فترات"
    )

    return combined


def _previous_period(year, period):
    if period == "النصف الثاني":
        return year, "النصف الأول"

    if period == "النصف الأول":
        return year - 1, "النصف الثاني"

    return None, None


rec = _combine_records(
    matching_records
)

# --------------------------------------------------
# Previous value
# --------------------------------------------------
# Previous is always derived from the actual previous period/year current
# result. Stored PrevValue is not used for the dashboard display.
previous_rec = {}

if len(selected_years) == 1:
    current_year = selected_years[0]

    if len(selected_periods) == 1:
        previous_year, previous_period = _previous_period(
            current_year,
            selected_periods[0],
        )

        if previous_year is not None and previous_period is not None:
            previous_records = [
                r for r in mock_records
                if r["year"] == previous_year
                and r["period"] == previous_period
                and r["department"] in selected_depts
                and r["service"] in selected_services
            ]

            if previous_records:
                previous_rec = _combine_records(
                    previous_records
                )

    else:
        previous_year = current_year - 1

        previous_records = [
            r for r in mock_records
            if r["year"] == previous_year
            and r["period"] in selected_periods
            and r["department"] in selected_depts
            and r["service"] in selected_services
        ]

        if previous_records:
            previous_rec = _combine_records(
                previous_records
            )

LRM = "\u200e"
st.subheader("المؤشرات الرئيسية")

col_csat, col_ces, col_nps = st.columns(3)


def donut_svg(fill_percent, value, color, kind, size=140, stroke=14, font_size=20, track_color="#DDE1EA"):
    # IMPORTANT: the value shown inside the donut is always formatted here
    # to exactly two decimal places, e.g. 90.518125 -> 90.52.
    display_text = _display_value(value, kind)

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
    number = _number_or_none(value)
    if number is None:
        return 0.0
    if kind == "percent":
        return min(max(number, 0.0), 100.0)
    return min(max((number + 100.0) / 2.0, 0.0), 100.0)


def _display_value(value, kind):
    text = _format_number(value)
    if text == "—":
        return text
    return f"{text}%" if kind == "percent" else text


def kpi_block(col, label, current, prev, target, kind):
    with col:
        with st.container(border=True):
            st.markdown(f'<div class="card-title">{label}</div>', unsafe_allow_html=True)

            target_pct = _normalize(target, kind)
            current_pct = _normalize(current, kind)
            prev_pct = _normalize(prev, kind)

            c_target, c_current, c_prev = st.columns([1, 1.3, 1])

            with c_target:
                st.markdown(
                    donut_svg(target_pct, target, ROLE_COLORS["target"], kind, size=115, stroke=13, font_size=18),
                    unsafe_allow_html=True,
                )
                st.markdown('<div style="text-align:center; font-size:12px; color:#8A94B5;">المستهدف</div>', unsafe_allow_html=True)

            with c_current:
                st.markdown(
                    donut_svg(current_pct, current, ROLE_COLORS["current"], kind, size=170, stroke=17, font_size=30),
                    unsafe_allow_html=True,
                )
                st.markdown('<div style="text-align:center; font-size:13px; font-weight:700; color:#16213E;">الحالي</div>', unsafe_allow_html=True)

            with c_prev:
                st.markdown(
                    donut_svg(prev_pct, prev, ROLE_COLORS["previous"], kind, size=115, stroke=13, font_size=18),
                    unsafe_allow_html=True,
                )
                st.markdown('<div style="text-align:center; font-size:12px; color:#8A94B5;">السابق</div>', unsafe_allow_html=True)


kpi_block(
    col_csat,
    "CSAT - رضا العملاء",
    rec.get("csat_current"),
    previous_rec.get("csat_current"),
    _target_or_default("csat", rec.get("csat_target")),
    kind="percent",
)

kpi_block(
    col_ces,
    "CES - جهد العميل",
    rec.get("ces_current"),
    previous_rec.get("ces_current"),
    _target_or_default("ces", rec.get("ces_target")),
    kind="range",
)

kpi_block(
    col_nps,
    "NPS - توصية العملاء",
    rec.get("nps_current"),
    previous_rec.get("nps_current"),
    _target_or_default("nps", rec.get("nps_target")),
    kind="range",
)

col_top5, col_chart = st.columns([0.8, 1.4])

def _top_services_by_csat(records, limit=5):
    """Rank services using the same period/year aggregation rules."""
    services = []

    for service_name in sorted({
        r.get("service")
        for r in records
        if r.get("service")
    }):
        service_records = [
            r for r in records
            if r.get("service") == service_name
        ]

        service_result = _combine_records(
            service_records
        )

        csat_value = _number_or_none(
            service_result.get("csat_current")
        )

        if csat_value is None:
            continue

        departments = {
            r.get("department")
            for r in service_records
            if r.get("department")
        }

        services.append(
            {
                "department": (
                    next(iter(departments))
                    if len(departments) == 1
                    else "عدة قطاعات"
                ),
                "service": service_name,
                "csat_current": csat_value,
            }
        )

    services.sort(
        key=lambda item: item["csat_current"],
        reverse=True,
    )

    return services[:limit]


with col_top5:
    with st.container(border=True):
        top_services = _top_services_by_csat(matching_records)

        if not top_services:
            st.markdown('<div class="card-title">أفضل 5 خدمات حسب CSAT</div>', unsafe_allow_html=True)
            st.info("لا توجد بيانات كافية لهذا الاختيار")
        else:
            # If the same service name exists under more than one department,
            # show the department too so the two services are distinguishable.
            service_name_counts = {}
            for item in top_services:
                service_name_counts[item["service"]] = (
                    service_name_counts.get(item["service"], 0) + 1
                )

            rows = ""
            for i, item in enumerate(top_services):
                service_label = item["service"]

                if service_name_counts[item["service"]] > 1:
                    service_label = (
                        f'{item["service"]}'
                        f'<div style="font-size:11px; color:#8A94B5; font-weight:600;">'
                        f'{item["department"]}</div>'
                    )

                rows += (
                    '<div class="row">'
                    f'<span>{i + 1}. {service_label}</span>'
                    f'<span class="count-square positive">'
                    f'{_display_table_value(item.get("csat_current"), "percent")}'
                    f'</span>'
                    '</div>'
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

        indicator_specs = [
            (
                "CSAT",
                previous_rec.get("csat_current"),
                rec.get("csat_current"),
                _target_or_default("csat", rec.get("csat_target")),
                list(INDICATOR_RANGES["csat"]),
            ),
            (
                "CES",
                previous_rec.get("ces_current"),
                rec.get("ces_current"),
                _target_or_default("ces", rec.get("ces_target")),
                list(INDICATOR_RANGES["ces"]),
            ),
            (
                "NPS",
                previous_rec.get("nps_current"),
                rec.get("nps_current"),
                _target_or_default("nps", rec.get("nps_target")),
                list(INDICATOR_RANGES["nps"]),
            ),
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
                    hovertemplate="%{x}<br>%{y}<extra></extra>",
                )
                mini_fig.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=320,
                    margin=dict(l=50, r=10, t=10, b=55),
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
                    automargin=False,
                    tickfont=dict(size=11),
                    dtick=25 if y_range[0] == 0 else 50,
                )
                mini_fig.update_xaxes(
                    showgrid=False,
                    tickangle=-15,
                    tickfont=dict(size=10),
                )

                st.plotly_chart(
                    mini_fig,
                    use_container_width=True,
                    config={"displayModeBar": False},
                )

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

        display_names = [
            "<br>".join(textwrap.wrap(name, width=45)) or name
            for name in display_names_raw
        ]

        bar_colors = [
            COLORS["purple"] if v is not None else COLORS["muted"]
            for v in display_values
        ]

        text_labels = [
            (
                f"{_format_number(v)}%"
                if v is not None
                else "—"
            )
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
            hovertemplate="%{y}<br>%{x}%<extra></extra>",
        )
        factor_fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=max(340, 80 * len(display_names)),
            bargap=0.45,
            margin=dict(l=10, r=260, t=10, b=10),
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