# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import html
import json

import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import select

# Optional component for capturing clicks on pie slices directly from Plotly.
try:
    from streamlit_plotly_events import plotly_events

    HAVE_PLOTLY_EVENTS = True
except Exception:
    HAVE_PLOTLY_EVENTS = False

from database_Initiatives.connection import SessionLocal
from database_Initiatives.models import Action, Product, Section, Status
from style import apply_theme


apply_theme()

# Data loading and quarter calculation

# Canonical quarter order.
QUARTERS = [
    "الربع الأول",
    "الربع الثاني",
    "الربع الثالث",
    "الربع الرابع",
]


def quarter_from_date(value):
    """Return the quarter name from the date's month, or None if there is no date."""
    if value is None:
        return None

    month = getattr(value, "month", None)
    if not month:
        return None

    return QUARTERS[(int(month) - 1) // 3]


@st.cache_data(ttl=300, show_spinner="جاري تحميل بيانات المبادرات...")
def fetch_initiatives():
    """
    Return all initiatives from the database as a list of dicts ready for
    display and filtering.

    Each item holds: initiative number, sector, product, status, title, and
    the four date fields.
    """
    with SessionLocal() as session:
        rows = session.execute(
            select(
                Action.action_id,
                Action.action_name,
                Action.initiative_number,
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
        records.append(
            {
                "action_id": row.action_id,
                "initiative_number": row.initiative_number,
                "section": row.section_name,
                "product": row.product_name,
                "status": row.status_name,
                "action_name": row.action_name,
                "creation_date": row.creation_date,
                "start_date": row.start_date,
                "expected_execution_date": row.expected_execution_date,
                "actual_execution_date": row.actual_execution_date,
            }
        )

    return records


# Constant representing the "All" option in the filters.
ALL = "الكل"

# Status colors: match the mockup colors for known statuses,
# any unknown status gets a color from the fallback palette in a stable order.
STATUS_COLOR_MAP = {
    "منجز": "#2FA88E",
    "لاينطبق": "#50459C",
    "تحت المراجعة": "#1A2269",
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

# Opacity of non-selected slices when a status is selected (lower = more transparent).
FADED_ALPHA = 0.25


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert a hex color to rgba with the given alpha (for non-selected slices)."""
    value = hex_color.lstrip("#")
    if len(value) == 3:
        value = "".join(char * 2 for char in value)

    red = int(value[0:2], 16)
    green = int(value[2:4], 16)
    blue = int(value[4:6], 16)
    return f"rgba({red}, {green}, {blue}, {alpha})"


class _NoModebar:
    """Hide the Plotly mode bar in plotly_events by injecting config into the figure JSON."""

    def __init__(self, figure):
        self.figure = figure

    def to_json(self):
        payload = json.loads(self.figure.to_json())
        payload["config"] = {"displayModeBar": False}
        return json.dumps(payload)


# Page styling

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


# Load data

try:
    records = fetch_initiatives()
except Exception as error:
    st.error(f"تعذر تحميل بيانات المبادرات من قاعدة البيانات: {error}")
    st.stop()

if not records:
    st.warning("لا توجد مبادرات في قاعدة البيانات بعد. ارفع ملفًا من صفحة رفع بيانات المبادرات.")
    st.stop()


# Filters: "View by"

st.subheader("عرض حسب")

# Date field used for filtering (year and quarter are derived from it).
DATE_BASIS = {
    "تاريخ الإنشاء": "creation_date",
    "تاريخ البدء": "start_date",
}

basis_label = st.selectbox(
    "نوع التاريخ",
    options=list(DATE_BASIS.keys()),
    index=0,
    key="init_dash_date_basis",
)
basis_field = DATE_BASIS[basis_label]


def basis_year(record):
    """Year of the record's selected date field (or None if empty)."""
    value = record.get(basis_field)
    return value.year if value is not None else None


def basis_quarter(record):
    """Quarter of the record's selected date field."""
    return quarter_from_date(record.get(basis_field))


years = sorted(
    {basis_year(r) for r in records if basis_year(r) is not None},
    reverse=True,
)
sections = sorted({r["section"] for r in records if r["section"]})

filter_row1 = st.columns(2)
filter_row2 = st.columns(2)

# All filters are multi-select: leaving one empty means "All".
with filter_row1[0]:
    year_choice = st.multiselect(
        "السنة",
        options=years,
        default=[],
        key="init_dash_years",
        placeholder="الكل",
    )

with filter_row1[1]:
    period_choice = st.multiselect(
        "الفترة",
        options=QUARTERS,
        default=[],
        key="init_dash_periods",
        placeholder="الكل",
    )

with filter_row2[0]:
    section_choice = st.multiselect(
        "القطاع",
        options=sections,
        default=[],
        key="init_dash_sections",
        placeholder="الكل",
    )

# Service (product) options depend on the selected sectors.
if not section_choice:
    products = sorted({r["product"] for r in records if r["product"]})
else:
    section_set = set(section_choice)
    products = sorted(
        {
            r["product"]
            for r in records
            if r["product"] and r["section"] in section_set
        }
    )

with filter_row2[1]:
    product_choice = st.multiselect(
        "الخدمة",
        options=products,
        default=[],
        key="init_dash_products",
        placeholder="الكل",
    )


def passes_top_filters(record) -> bool:
    """Does the record pass the year/period/sector/service filters? (empty = all)

    Year and quarter are derived from the selected date field (creation or start).
    """
    if year_choice and basis_year(record) not in year_choice:
        return False
    if period_choice and basis_quarter(record) not in period_choice:
        return False
    if section_choice and record["section"] not in section_choice:
        return False
    if product_choice and record["product"] not in product_choice:
        return False
    return True


filtered = [r for r in records if passes_top_filters(r)]


# Pie chart (by status) + initiatives-count card

status_counts: dict[str, int] = {}
for record in filtered:
    status = record["status"] or "غير محدد"
    status_counts[status] = status_counts.get(status, 0) + 1

# Stable color per status (same color across all filters).
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

# Spacing between the filters and the chart/card row.
st.markdown("<div style='height: 40px'></div>", unsafe_allow_html=True)

chart_col, kpi_col = st.columns([1.7, 1])

total_filtered = len(filtered)
selected_status = None  # الحالة المختارة بالنقر على الرسمة (إن وجدت)

with chart_col:
    if status_counts:
        labels = list(status_counts.keys())
        values = list(status_counts.values())
        base_colors = [color_for_status.get(label, "#7A7F94") for label in labels]

        # Current selection (from a previous click, or from the fallback selector).
        if HAVE_PLOTLY_EVENTS:
            current_selection = st.session_state.get("init_pie_status")
        else:
            segment_value = st.session_state.get("init_status_segment")
            current_selection = (
                segment_value if segment_value and segment_value != ALL else None
            )

        # When a status is selected: keep its slice at full color and fade the rest.
        if current_selection in labels:
            colors = [
                color if label == current_selection
                else _hex_to_rgba(color, FADED_ALPHA)
                for label, color in zip(labels, base_colors)
            ]
        else:
            colors = base_colors

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
            # Real slice clicks via the streamlit-plotly-events component.
            clicked = plotly_events(
                _NoModebar(pie),
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
                    new_status = labels[index]
                    # Rerun immediately when the selection changes so the fade shows at once.
                    if new_status != st.session_state.get("init_pie_status"):
                        st.session_state["init_pie_status"] = new_status
                        st.rerun()

            selected_status = st.session_state.get("init_pie_status")

            # Small clear button shown only when something is selected.
            # The chart stays stable (same key) so there is no reload.
            if selected_status:
                if st.button("✕ إلغاء التحديد وعرض الكل", key="init_pie_clear"):
                    st.session_state["init_pie_status"] = None
                    # Rerun immediately to remove the fade.
                    st.rerun()
        else:
            # Fallback: if the component is not installed, show a plain chart with a status selector.
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
        # When a status is selected: its count and share of the filtered total.
        count_value = status_counts.get(selected_status, 0)
        count_label = f"عدد المبادرات ({selected_status})"
    else:
        # No selection: the total and 100%.
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


# Initiatives details

st.markdown('<div class="block-title">تفاصيل المبادرات</div>', unsafe_allow_html=True)

statuses_in_view = sorted({r["status"] or "غير محدد" for r in filtered})

table_controls = st.columns([2, 1])

# Multi-select filter: pick one or more statuses. Empty shows all statuses.
with table_controls[0]:
    table_status_choice = st.multiselect(
        "حالة المبادرة",
        options=statuses_in_view,
        default=[],
        key="init_dash_table_statuses",
        placeholder="كل الحالات",
    )

# Sort by the same date field selected above (creation or start).
with table_controls[1]:
    sort_order = st.selectbox(
        f"الترتيب حسب {basis_label}",
        options=["الأحدث أولًا", "الأقدم أولًا"],
        index=0,
        key="init_dash_table_sort",
    )

if not table_status_choice:
    table_records = filtered
else:
    selected_statuses = set(table_status_choice)
    table_records = [
        r for r in filtered if (r["status"] or "غير محدد") in selected_statuses
    ]

# Sort rows by the chosen date; rows without a date always go last.
newest_first = sort_order == "الأحدث أولًا"
dated = [r for r in table_records if r.get(basis_field) is not None]
undated = [r for r in table_records if r.get(basis_field) is None]
dated.sort(key=lambda r: r[basis_field], reverse=newest_first)
table_records = dated + undated

st.caption(f"عدد النتائج: {len(table_records):,}")


def _fmt_date(value) -> str:
    """Format a date as YYYY-MM-DD, or a dash when missing."""
    if value is None:
        return "—"
    try:
        return value.strftime("%Y-%m-%d")
    except Exception:
        return str(value)


# Table styling with the status column as a colored pill.
st.markdown(
    """
    <style>
    .init-table-wrap {
        background: #FFFFFF;
        border: 1px solid #E7E8F1;
        border-radius: 16px;
        overflow: auto;
        max-height: 560px;
        box-shadow: 0 5px 18px rgba(22, 33, 62, 0.05);
    }
    .init-table { border-collapse: separate; border-spacing: 0; width: 100%; }
    .init-table thead th {
        position: sticky;
        top: 0;
        background: #F7F8FC;
        color: #6B7398;
        font-size: 13px;
        font-weight: 700;
        padding: 14px 18px;
        text-align: right;
        white-space: nowrap;
        border-bottom: 1px solid #EEF0F5;
    }
    .init-table tbody tr { transition: background 0.15s ease; }
    .init-table tbody tr:nth-child(even) { background: #FAFBFD; }
    .init-table tbody tr:hover { background: #F1EEFA; }
    .init-table tbody td {
        padding: 13px 18px;
        color: #16213E;
        font-size: 14px;
        text-align: right;
        white-space: nowrap;
        border-bottom: 1px solid #F3F4F9;
    }
    .init-table td.title-cell { white-space: normal; min-width: 320px; }
    .status-pill {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 800;
        font-size: 13px;
        white-space: nowrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

TABLE_HEADERS = [
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


def _cell(value) -> str:
    """HTML-safe cell text."""
    return html.escape("—" if value is None else str(value))


def _status_pill(status: str) -> str:
    """Render the status as a colored pill using the status's own color."""
    color = color_for_status.get(status, "#6B7398")
    background = _hex_to_rgba(color, 0.14)
    return (
        f'<span class="status-pill" '
        f'style="background:{background}; color:{color};">'
        f"{html.escape(str(status))}</span>"
    )


def _row_html(r) -> str:
    return (
        "<tr>"
        f"<td>{_cell(r['initiative_number'])}</td>"
        f"<td>{_cell(r['section'])}</td>"
        f"<td>{_cell(r['product'])}</td>"
        f"<td>{_status_pill(r['status'] or 'غير محدد')}</td>"
        f"<td class='title-cell'>{_cell(r['action_name'])}</td>"
        f"<td>{_cell(_fmt_date(r['creation_date']))}</td>"
        f"<td>{_cell(_fmt_date(r['start_date']))}</td>"
        f"<td>{_cell(_fmt_date(r['expected_execution_date']))}</td>"
        f"<td>{_cell(_fmt_date(r['actual_execution_date']))}</td>"
        "</tr>"
    )


if table_records:
    header_html = "".join(f"<th>{h}</th>" for h in TABLE_HEADERS)
    rows_html = "".join(_row_html(r) for r in table_records)

    st.markdown(
        f'<div class="init-table-wrap" dir="rtl">'
        f'<table class="init-table">'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        f"</table></div>",
        unsafe_allow_html=True,
    )
else:
    st.info("لا توجد مبادرات مطابقة للفلاتر المختارة.")