# -*- coding: utf-8 -*-

"""
app_mode.py
-----------

Stores the currently selected section of the platform:

    departments  -> جهات حكومية
    individuals  -> أفراد
    initiatives  -> المبادرات

Government departments and individuals use separate databases.

Initiatives are handled as an independent section.
"""

import streamlit as st


VALID_MODES = (
    "departments",
    "individuals",
    "initiatives",
)


MODE_DATABASES = {
    "departments": "customer_experience_db",
    "individuals": "customer_experience_individuals_db",

    # المبادرات مستقلة
    "initiatives": None,
}


MODE_LABELS = {
    "departments": "جهات حكومية",
    "individuals": "أفراد",
    "initiatives": "المبادرات",
}


def set_mode(mode):
    """Store the selected application mode."""

    if mode not in VALID_MODES:
        raise ValueError(
            f"Unknown mode: {mode}"
        )

    st.session_state["mode"] = mode


def get_mode():
    """Return the current mode."""

    return st.session_state.get(
        "mode"
    )


def clear_mode():
    """Clear the selected mode."""

    st.session_state.pop(
        "mode",
        None,
    )


def is_individuals():
    """True when the active mode is individuals."""

    return get_mode() == "individuals"


def is_departments():
    """True when the active mode is departments."""

    return get_mode() == "departments"


def is_initiatives():
    """True when the active mode is initiatives."""

    return get_mode() == "initiatives"


def mode_label(mode=None):
    """Return Arabic label for a mode."""

    return MODE_LABELS.get(
        mode or get_mode(),
        "",
    )


def current_database():
    """Return database for current mode."""

    return MODE_DATABASES.get(
        get_mode()
    )