# -*- coding: utf-8 -*-
"""
entry_backend.py
----------------
BACKEND for the data entry page.

It does NOT talk to the database directly anymore. Instead it calls the
team's shared repository functions in the database/ package (written by
the teammate who owns the data layer). This file's job is now just to
translate between what the PAGE speaks (department/service NAMES) and
what the repositories speak (numeric IDs), and to keep the page-specific
rules (periods, default targets, duplicate check).

RULE: this file must never import streamlit.

The function NAMES here are unchanged, so data_entry.py did not change.
"""

from decimal import Decimal

# The team's shared data-layer functions (in database/crud/).
from database.crud import departments as departments_repo
from database.crud import services as services_repo
from database.crud import indicators as indicators_repo
from database.crud import measurement_records as records_repo
from database.crud import indicator_results as results_repo


# ----------------------------------------------------------------------
# Periods and years live in code (there is no period table in the schema)
# ----------------------------------------------------------------------
PERIODS = {
    "H1": "النصف الأول",
    "H2": "النصف الثاني",
}

YEARS = [2024, 2025, 2026, 2027]


def get_period_codes():
    """Return the stored period codes: H1, H2."""
    return list(PERIODS.keys())


def previous_period(year, period):
    """
    Return the (year, period) right before this one.
        H2 -> H1 of the SAME year
        H1 -> H2 of the PREVIOUS year
    """
    if period == "H2":
        return year, "H1"
    return year - 1, "H2"


def period_label(code):
    """Turn a stored code like "H1" into its Arabic label."""
    return PERIODS.get(code, code)


def get_years():
    """Return the years available in the dropdown."""
    return list(YEARS)


# ----------------------------------------------------------------------
# Departments and services: read through the team's repositories.
# The page works with names, so we look up the matching rows.
# ----------------------------------------------------------------------

def get_departments():
    """Return the list of department names."""
    return [d.department_name for d in departments_repo.get_all_departments()]


def _department_id(department_name):
    """Find a department's ID from its name, or None."""
    for department in departments_repo.get_all_departments():
        if department.department_name == department_name:
            return department.department_id
    return None


def get_services(department):
    """Return the services that belong to one department (by name)."""
    department_id = _department_id(department)
    if department_id is None:
        return []
    services = services_repo.get_services_by_department(department_id)
    return [service.service_name for service in services]


def _service_id(department_name, service_name):
    """Find a service's ID from the department + service names, or None."""
    department_id = _department_id(department_name)
    if department_id is None:
        return None
    for service in services_repo.get_services_by_department(department_id):
        if service.service_name == service_name:
            return service.service_id
    return None


# ----------------------------------------------------------------------
# Indicators: read once and reuse. Each item keeps its DB id so we can
# save results without another lookup.
# ----------------------------------------------------------------------
_indicator_cache = None


def _load_indicators():
    """Read all indicators through the repository once, then reuse them."""
    global _indicator_cache
    if _indicator_cache is None:
        _indicator_cache = [
            {"id": indicator.indicator_id,
             "code": indicator.indicator_name,
             "minimum": float(indicator.min_value),
             "maximum": float(indicator.max_value),
             "unit": indicator.unit}
            for indicator in indicators_repo.get_all_indicators()
        ]
    return _indicator_cache


def get_indicator_codes():
    """Return the indicator names in order, e.g. CSAT, CES, NPS."""
    return [item["code"] for item in _load_indicators()]


def get_indicator(code):
    """Return the cached dictionary for one indicator code."""
    for item in _load_indicators():
        if item["code"] == code:
            return item
    return {}


def indicator_name_ar(code):
    """The schema stores only the short name, so we return the code."""
    return get_indicator(code).get("code", code)


def indicator_bounds(code):
    """Return (minimum, maximum) allowed for this indicator."""
    item = get_indicator(code)
    return item.get("minimum", 0.0), item.get("maximum", 100.0)


def is_higher_better(code):
    """All three indicators are 'higher is better' (CES is a net score)."""
    return True


# ----------------------------------------------------------------------
# Default target values (pre-filled in the form, editable by the user)
# ----------------------------------------------------------------------
DEFAULT_TARGETS = {
    "CSAT": 85.0,
    "CES": 76.0,
    "NPS": 69.0,
}


def default_target(code):
    """Return the pre-filled target for one indicator, or None."""
    return DEFAULT_TARGETS.get(code)


# ----------------------------------------------------------------------
# Previous values: last period's CURRENT value for each indicator
# ----------------------------------------------------------------------

def get_previous_values(department, service, year, period):
    """
    Read what the CURRENT values were in the period right before this one,
    so they can be shown as this entry's "previous" values.

    Returns {indicator_code: value}. Indicators with no earlier record are
    simply left out.
    """
    previous_year, previous_code = previous_period(year, period)

    service_id = _service_id(department, service)
    if service_id is None:
        return {}

    # Find the earlier record for this service + previous period.
    record = None
    for candidate in records_repo.get_records_by_service(service_id):
        if candidate.year == previous_year and candidate.period == previous_code:
            record = candidate
            break
    if record is None:
        return {}

    # Map indicator id -> code, then read that record's results.
    code_by_id = {item["id"]: item["code"] for item in _load_indicators()}
    values = {}
    for result in results_repo.get_results_by_record(record.record_id):
        code = code_by_id.get(result.indicator_id)
        if code is not None:
            values[code] = float(result.current_value)
    return values


# ----------------------------------------------------------------------
# Duplicate check (the repository's create does NOT check this)
# ----------------------------------------------------------------------

def entry_exists(department, service, year, period):
    """
    True when a record already exists for this service + year + period.
    """
    service_id = _service_id(department, service)
    if service_id is None:
        return False

    existing = records_repo.get_records_by_year_and_period(year, period)
    return any(record.service_id == service_id for record in existing)


# ----------------------------------------------------------------------
# Validating and saving what the user typed
# ----------------------------------------------------------------------

def _has_any_value(row):
    """
    True when the user started this row. The target box is pre-filled, so
    only a typed CURRENT value counts as "this row is being used".
    """
    return row.get("current") is not None


def validate_entry(department, service, year, period, typed_values):
    """
    Check the typed values before saving. Returns a list of Arabic error
    messages; an empty list means it is safe to save.
    """
    errors = []

    if entry_exists(department, service, year, period):
        errors.append(
            f"يوجد إدخال محفوظ مسبقاً لـ {department} / {service} — "
            f"{period_label(period)} {year}."
        )

    filled = [code for code, row in typed_values.items()
              if _has_any_value(row)]
    if not filled:
        errors.append("الرجاء إدخال القيمة الحالية لمؤشر واحد على الأقل قبل الحفظ.")

    for code, row in typed_values.items():
        if _has_any_value(row) and row.get("target") is None:
            errors.append(f"المؤشر {code}: القيمة المستهدفة مطلوبة.")

    return errors


def save_entry(department, service, year, period, typed_values,
               participants=0, review=None):
    """
    Save one measurement record plus one result per filled indicator,
    all through the team's repository functions.

    Returns {ok, errors, saved_count}.
    """
    errors = validate_entry(department, service, year, period, typed_values)
    if errors:
        return {"ok": False, "errors": errors, "saved_count": 0}

    service_id = _service_id(department, service)
    if service_id is None:
        return {"ok": False,
                "errors": [f"الخدمة غير موجودة في قاعدة البيانات: {service}"],
                "saved_count": 0}

    # Previous values are read (not typed) from the earlier period.
    previous_values = get_previous_values(department, service, year, period)
    indicator_id_by_code = {item["code"]: item["id"]
                            for item in _load_indicators()}

    try:
        # 1) The parent record. participants defaults to 0 because the
        #    form does not collect it yet (the column is NOT NULL).
        record = records_repo.create_measurement_record(
            service_id=service_id,
            year=year,
            period=period,
            participants_count=participants,
            review=review,
        )

        # 2) One result per filled indicator row.
        saved_count = 0
        for code in get_indicator_codes():
            row = typed_values.get(code, {})
            if not _has_any_value(row):
                continue

            indicator_id = indicator_id_by_code.get(code)
            if indicator_id is None:
                continue

            previous = previous_values.get(code)
            results_repo.create_indicator_result(
                record_id=record.record_id,
                indicator_id=indicator_id,
                prev_value=None if previous is None else Decimal(str(previous)),
                current_value=Decimal(str(row["current"])),
                target_value=Decimal(str(row["target"])),
            )
            saved_count += 1

        return {"ok": True, "errors": [], "saved_count": saved_count}

    except ValueError as error:
        # The repositories raise ValueError for bad data (out of range,
        # duplicate result, missing service). Show it, do not crash.
        return {"ok": False, "errors": [str(error)], "saved_count": 0}


# ----------------------------------------------------------------------
# Read / clear helpers (used for testing and by later pages)
# ----------------------------------------------------------------------

def get_all_records():
    """Return every saved indicator result as a list of plain dicts."""
    # Build id -> name maps once.
    departments = {d.department_id: d.department_name
                   for d in departments_repo.get_all_departments()}
    services = {s.service_id: (s.service_name, s.department_id)
                for s in services_repo.get_all_services()}
    indicators = {item["id"]: item["code"] for item in _load_indicators()}
    records = {r.record_id: r
               for r in records_repo.get_all_measurement_records()}

    output = []
    for result in results_repo.get_all_indicator_results():
        record = records.get(result.record_id)
        if record is None:
            continue
        service_name, department_id = services.get(record.service_id,
                                                   ("?", None))
        output.append({
            "Department": departments.get(department_id, "?"),
            "Service": service_name,
            "Year": record.year,
            "Period": record.period,
            "Indicator": indicators.get(result.indicator_id, "?"),
            "PreviousValue": (None if result.prev_value is None
                              else float(result.prev_value)),
            "CurrentValue": float(result.current_value),
            "TargetValue": float(result.target_value),
        })
    return output


def clear_all_records():
    """
    Delete every result then every record, through the repositories.
    Testing only.
    """
    for result in results_repo.get_all_indicator_results():
        results_repo.delete_indicator_result(result.result_id)
    for record in records_repo.get_all_measurement_records():
        records_repo.delete_measurement_record(record.record_id)