# -*- coding: utf-8 -*-
"""
data_entry.py
-------------
FRONTEND for the data entry page: Streamlit widgets and layout only.

RULE: no business rules in this file. It asks entry_backend.py what the
options are, shows them, and hands the typed values back.

Run it with:
    streamlit run data_entry.py

Built step by step. Done so far:
    STEP 1 - page setup + the basic data fields
    STEP 2 - the indicators card + Save / Cancel
"""

import streamlit as st

from style import apply_theme
import entry_backend as backend


# ----------------------------------------------------------------------
# Page setup
# ----------------------------------------------------------------------
apply_theme()

# Streamlit has no built-in right-to-left setting, so we add it as CSS.
st.markdown(
    """
    <style>
    .stApp, .main, section[data-testid="stSidebar"] { direction: rtl; }
    h1, h2, h3, p, label, .stMarkdown { text-align: right; }
    div[data-baseweb="select"], .stTextInput input { direction: rtl; }

    /* Table header labels above the boxes */
    .column-head { text-align: center; font-weight: 600; padding-bottom: 6px; }
    /* The indicator name at the start of each row */
    .row-name { text-align: right; font-weight: 700; padding-top: 10px; }
    /* Thin separator line under the header row */
    .thin-line { border: none; border-top: 1px solid #E7E8F1; margin: 0 0 8px 0; }
    /* Hide the little +/- buttons so the boxes look clean */
    div[data-testid="stNumberInput"] button { display: none; }
    div[data-testid="stNumberInput"] input { text-align: center; }
    /* Read-only "previous" cell: looks like a box but cannot be typed in */
    .previous-cell {
        text-align: center; font-weight: 600; color: #7A7F94;
        background: #F5F6FA; border: 1px solid #E7E8F1; border-radius: 8px;
        padding: 8px 0; margin-top: 2px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------
# Small helpers for clearing the boxes
# ----------------------------------------------------------------------
# Every box key ends with a version number. Raising the version makes
# Streamlit build brand-new (empty) boxes, which is how we clear the form.
if "form_version" not in st.session_state:
    st.session_state.form_version = 0

# A message that must survive the refresh caused by clearing the form.
if "flash_message" not in st.session_state:
    st.session_state.flash_message = None


def clear_boxes(message=None):
    """Empty every number box, optionally leaving a message on screen."""
    st.session_state.form_version += 1
    st.session_state.flash_message = message
    st.rerun()


def box_key(prefix, code):
    """Build the unique key of one box, e.g. "current_CSAT_3"."""
    return f"{prefix}_{code}_{st.session_state.form_version}"


# ----------------------------------------------------------------------
# Basic data: which service, and which period
# ----------------------------------------------------------------------
st.title("إدخال بيانات المؤشرات")

# In right-to-left, the FIRST column appears on the right of the screen.
right_column, left_column = st.columns(2)

with right_column:
    department = st.selectbox("الإدارة", backend.get_departments())

with left_column:
    # The service list is filtered by the department chosen above.
    service = st.selectbox("الخدمة", backend.get_services(department))

right_column, left_column = st.columns(2)

with right_column:
    years = backend.get_years()
    year = st.selectbox("السنة", years, index=years.index(2026))

with left_column:
    # The stored value stays "H1"; only the label shown is Arabic.
    period = st.selectbox("الفترة", backend.get_period_codes(),
                          format_func=backend.period_label)


# ----------------------------------------------------------------------
# The indicators card
# ----------------------------------------------------------------------
# Column widths: the name column is wider than the three value columns.
COLUMN_WIDTHS = [1.2, 1, 1, 1]

with st.container(border=True):
    st.subheader("جدول المؤشرات")

    # Header row. In right-to-left the first column is the right-most one.
    header_columns = st.columns(COLUMN_WIDTHS)
    for column, label in zip(header_columns,
                             ["المؤشر", "السابق", "الحالي", "المستهدف"]):
        with column:
            st.markdown(f'<div class="column-head">{label}</div>',
                        unsafe_allow_html=True)

    st.markdown('<hr class="thin-line">', unsafe_allow_html=True)

    # The "previous" values are read from the period before -- they are
    # shown to the user, not typed. Fetched once for the chosen service.
    previous_values = backend.get_previous_values(department, service,
                                                  year, period)

    # One row per indicator, built from the list in entry_backend.
    typed_values = {}
    for code in backend.get_indicator_codes():
        lowest, highest = backend.indicator_bounds(code)

        name_column, previous_column, current_column, target_column = \
            st.columns(COLUMN_WIDTHS)

        with name_column:
            st.markdown(f'<div class="row-name">{code}</div>',
                        unsafe_allow_html=True)

        # "السابق" is read-only: the saved current value of the previous
        # period. A dash means there is no earlier record yet.
        with previous_column:
            previous = previous_values.get(code)
            shown = "—" if previous is None else f"{previous:g}"
            st.markdown(f'<div class="previous-cell">{shown}</div>',
                        unsafe_allow_html=True)

        # value=None keeps the box empty until the user types something.
        with current_column:
            current = st.number_input(
                "الحالي", key=box_key("current", code),
                min_value=lowest, max_value=highest, value=None, step=1.0,
                label_visibility="collapsed")

        with target_column:
            # Starts at the default target but the user can change it.
            # After a save/cancel the version bump rebuilds the box, so it
            # resets back to this default -- which is what we want.
            target = st.number_input(
                "المستهدف", key=box_key("target", code),
                min_value=lowest, max_value=highest,
                value=backend.default_target(code), step=1.0,
                label_visibility="collapsed")

        # "previous" is no longer typed; the backend fills it when saving.
        typed_values[code] = {"current": current, "target": target}

    st.write("")

    # Buttons. The first column is the right-most one, so Save sits first.
    save_column, cancel_column, _spacer = st.columns([1, 1, 3])
    with save_column:
        save_clicked = st.button("حفظ", type="primary", width="stretch")
    with cancel_column:
        cancel_clicked = st.button("إلغاء", width="stretch")


# ----------------------------------------------------------------------
# What the buttons do
# ----------------------------------------------------------------------
if save_clicked:
    # All the rules live in the backend; this file only shows the answer.
    result = backend.save_entry(department, service, year, period,
                               typed_values)

    if result["ok"]:
        clear_boxes(f"تم حفظ {result['saved_count']} مؤشرات للخدمة "
                    f"{service} — {backend.period_label(period)} {year}.")
    else:
        # Keep what the user typed so nothing is lost, and show why.
        for message in result["errors"]:
            st.error(message)

if cancel_clicked:
    clear_boxes("تم إلغاء الإدخال ومسح الحقول.")


# Show the message left behind by a save or a cancel.
if st.session_state.flash_message:
    st.success(st.session_state.flash_message)
    st.session_state.flash_message = None