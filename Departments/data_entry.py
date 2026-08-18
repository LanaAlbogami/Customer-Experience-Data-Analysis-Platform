# -*- coding: utf-8 -*-
# Frontend for the data entry page.

import streamlit as st

from style import apply_theme
import entry_backend as backend


# ==================================================
# Page setup
# ==================================================

apply_theme()

# Streamlit has no built-in right-to-left setting,
# so RTL styling is applied with CSS.
st.markdown(
    """
    <style>
    .stApp, .main, section[data-testid="stSidebar"] {
        direction: rtl;
    }

    h1, h2, h3, p, label, .stMarkdown {
        text-align: right;
    }

    div[data-baseweb="select"],
    .stTextInput input {
        direction: rtl;
    }

    /* Table header labels above the boxes */
    .column-head {
        text-align: center;
        font-weight: 600;
        padding-bottom: 6px;
    }

    /* Indicator name */
    .row-name {
        text-align: right;
        font-weight: 700;
        padding-top: 10px;
    }

    /* Separator under the header row */
    .thin-line {
        border: none;
        border-top: 1px solid #E7E8F1;
        margin: 0 0 8px 0;
    }

    /* Hide +/- buttons */
    div[data-testid="stNumberInput"] button {
        display: none;
    }

    div[data-testid="stNumberInput"] input {
        text-align: center;
    }

    /* Previous value cell */
    .previous-cell {
        text-align: center;
        font-weight: 600;
        color: #7A7F94;
        background: #F5F6FA;
        border: 1px solid #E7E8F1;
        border-radius: 8px;
        padding: 8px 0;
        margin-top: 2px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ==================================================
# Session state helpers
# ==================================================

if "form_version" not in st.session_state:
    st.session_state.form_version = 0

if "flash_message" not in st.session_state:
    st.session_state.flash_message = None


def clear_boxes(message=None):
    """
    Clear the indicator input boxes by changing
    their Streamlit widget keys.
    """
    st.session_state.form_version += 1
    st.session_state.flash_message = message
    st.rerun()


def box_key(prefix, code):
    """
    Build a unique Streamlit key for each box.
    """
    return (
        f"{prefix}_{code}_"
        f"{st.session_state.form_version}"
    )


# ==================================================
# Page title
# ==================================================

st.title("إدخال بيانات المؤشرات")


# ==================================================
# Government entity
# ==================================================

entities = backend.get_entities()

if not entities:
    st.warning(
        "لا توجد جهات حكومية مسجلة في قاعدة البيانات."
    )
    st.stop()


entity = st.selectbox(
    "الجهة الحكومية",
    entities,
    key="manual_entry_entity",
)


# ==================================================
# Section and service
# ==================================================

sections = backend.get_departments(entity)

if not sections:
    st.warning(
        "لا توجد أقسام مسجلة لهذه الجهة الحكومية."
    )
    st.stop()


right_column, left_column = st.columns(2)

with right_column:
    department = st.selectbox(
        "القسم",
        sections,
        key="manual_entry_section",
    )


services = backend.get_services(
    department,
    entity_name=entity,
)

if not services:
    st.warning(
        "لا توجد خدمات مسجلة لهذا القسم."
    )
    st.stop()


with left_column:
    service = st.selectbox(
        "الخدمة",
        services,
        key="manual_entry_service",
    )


# ==================================================
# Year and period
# ==================================================

right_column, left_column = st.columns(2)

with right_column:
    years = backend.get_years()

    default_year = (
        2026
        if 2026 in years
        else years[-1]
    )

    year = st.selectbox(
        "السنة",
        years,
        index=years.index(default_year),
        key="manual_entry_year",
    )


with left_column:
    period = st.selectbox(
        "الفترة",
        backend.get_period_codes(),
        format_func=backend.period_label,
        key="manual_entry_period",
    )


# ==================================================
# Previous indicator values
# ==================================================

previous_values = backend.get_previous_values(
    department,
    service,
    year,
    period,
    entity=entity,
)


# ==================================================
# Indicators card
# ==================================================

COLUMN_WIDTHS = [1.2, 1, 1, 1]

with st.container(border=True):

    st.subheader("جدول المؤشرات")

    # Header row
    header_columns = st.columns(
        COLUMN_WIDTHS
    )

    header_labels = [
        "المؤشر",
        "السابق",
        "الحالي",
        "المستهدف",
    ]

    for column, label in zip(
        header_columns,
        header_labels,
    ):
        with column:
            st.markdown(
                f'<div class="column-head">'
                f'{label}'
                f'</div>',
                unsafe_allow_html=True,
            )

    st.markdown(
        '<hr class="thin-line">',
        unsafe_allow_html=True,
    )


    # ==================================================
    # Indicator rows
    # ==================================================

    typed_values = {}

    for code in backend.get_indicator_codes():

        lowest, highest = (
            backend.indicator_bounds(code)
        )

        (
            name_column,
            previous_column,
            current_column,
            target_column,
        ) = st.columns(COLUMN_WIDTHS)


        # Indicator name
        with name_column:
            st.markdown(
                f'<div class="row-name">'
                f'{code}'
                f'</div>',
                unsafe_allow_html=True,
            )


        # Previous value
        with previous_column:

            previous = previous_values.get(
                code
            )

            shown = (
                "—"
                if previous is None
                else f"{previous:.2f}"
            )

            st.markdown(
                f'<div class="previous-cell">'
                f'{shown}'
                f'</div>',
                unsafe_allow_html=True,
            )


        # Current value
        with current_column:

            current = st.number_input(
                "الحالي",
                key=box_key(
                    "current",
                    code,
                ),
                min_value=lowest,
                max_value=highest,
                value=None,
                step=0.01,
                format="%.2f",
                label_visibility="collapsed",
            )


        # Target value
        with target_column:

            default_target = (
                backend.default_target(code)
            )

            target = st.number_input(
                "المستهدف",
                key=box_key(
                    "target",
                    code,
                ),
                min_value=lowest,
                max_value=highest,
                value=default_target,
                step=0.01,
                format="%.2f",
                label_visibility="collapsed",
            )


        typed_values[code] = {
            "current": current,
            "target": target,
        }


    # ==================================================
    # Buttons
    # ==================================================

    st.write("")

    save_column, cancel_column, _spacer = (
        st.columns([1, 1, 3])
    )

    with save_column:
        save_clicked = st.button(
            "حفظ",
            type="primary",
            width="stretch",
        )

    with cancel_column:
        cancel_clicked = st.button(
            "إلغاء",
            width="stretch",
        )


# ==================================================
# Save
# ==================================================

if save_clicked:

    result = backend.save_entry(
        department,
        service,
        year,
        period,
        typed_values,
        entity=entity,
    )

    if result["ok"]:

        clear_boxes(
            f"تم حفظ "
            f"{result['saved_count']} مؤشرات "
            f"للخدمة {service} — "
            f"{backend.period_label(period)} "
            f"{year}."
        )

    else:

        for message in result["errors"]:
            st.error(message)


# ==================================================
# Cancel
# ==================================================

if cancel_clicked:
    clear_boxes(
        "تم إلغاء الإدخال ومسح الحقول."
    )


# ==================================================
# Flash message
# ==================================================

if st.session_state.flash_message:

    st.success(
        st.session_state.flash_message
    )

    st.session_state.flash_message = None