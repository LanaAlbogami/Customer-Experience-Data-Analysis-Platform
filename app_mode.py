# -*- coding: utf-8 -*-
"""
app_mode.py
-----------
The one small module that remembers which mode the app is in:
    "individuals" (أفراد)  or  "departments" (جهات)

The two modes use DIFFERENT databases, so this module is also the single
place that says which database name belongs to each mode. When a page (or
the connection layer) needs the right database, it asks here.
"""

import streamlit as st


MODE_DATABASES = {
    "departments": "customer_experience_db",
    "individuals": "customer_experience_individuals_db",
}

MODE_LABELS = {
    "departments": "جهات",
    "individuals": "أفراد",
}


def set_mode(mode):
    """Store the chosen mode. mode is "individuals" or "departments"."""
    if mode not in MODE_DATABASES:
        raise ValueError(f"Unknown mode: {mode}")
    st.session_state["mode"] = mode


def get_mode():
    """Return the current mode, or None if the user has not chosen yet."""
    return st.session_state.get("mode")


def clear_mode():
    """Forget the choice, so the landing page shows again."""
    st.session_state.pop("mode", None)


def is_individuals():
    """True when the user chose أفراد."""
    return get_mode() == "individuals"


def is_departments():
    """True when the user chose جهات."""
    return get_mode() == "departments"


def mode_label(mode=None):
    """Arabic label for a mode (defaults to the current one)."""
    return MODE_LABELS.get(mode or get_mode(), "")


def current_database():
    """The database name that belongs to the current mode."""
    return MODE_DATABASES.get(get_mode())