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
    """Delete every MeasurementRecord and IndicatorResult. Testing only."""
    session = SessionLocal()
    try:
        session.query(IndicatorResult).delete()
        session.query(MeasurementRecord).delete()
        session.commit()
    finally:
        session.close()

def _get_or_create_department(
    session,
    department_name,
):
    """
    جلب القسم من قاعدة البيانات،
    أو إنشاؤه إذا لم يكن موجودًا.
    """

    department = (
        session.query(Department)
        .filter(
            Department.department_name
            == department_name
        )
        .first()
    )

    if department is None:
        department = Department(
            department_name=department_name
        )

        session.add(department)
        session.flush()

    return department


def _get_or_create_service(
    session,
    department,
    service_name,
):
    """
    جلب الخدمة التابعة للقسم،
    أو إنشاؤها إذا لم تكن موجودة.
    """

    service = (
        session.query(Service)
        .filter(
            Service.department_id
            == department.department_id,
            Service.service_name
            == service_name,
        )
        .first()
    )

    if service is None:
        service = Service(
            department_id=department.department_id,
            service_name=service_name,
        )

        session.add(service)
        session.flush()

    return service


def _append_uploaded_review(
    old_review,
    new_review,
):
    """
    دمج التعليقات القديمة والجديدة
    بدون تكرار.
    """

    if not new_review:
        return old_review

    if not old_review:
        return new_review

    existing_comments = {
        line.strip().lower()
        for line in old_review.splitlines()
        if line.strip()
    }

    comments_to_add = []

    for line in new_review.splitlines():
        comment = line.strip()

        if not comment:
            continue

        normalized_comment = comment.lower()

        if normalized_comment in existing_comments:
            continue

        existing_comments.add(
            normalized_comment
        )

        comments_to_add.append(comment)

    if not comments_to_add:
        return old_review

    return (
        old_review
        + "\n"
        + "\n".join(comments_to_add)
    )


def _get_previous_values_in_session(
    session,
    service_id,
    year,
    period,
):
    """
    جلب قيم المؤشرات من الفترة السابقة
    باستخدام نفس جلسة قاعدة البيانات.
    """

    previous_year, previous_code = (
        previous_period(year, period)
    )

    rows = (
        session.query(
            Indicator.indicator_name,
            IndicatorResult.current_value,
        )
        .join(
            IndicatorResult,
            IndicatorResult.indicator_id
            == Indicator.indicator_id,
        )
        .join(
            MeasurementRecord,
            MeasurementRecord.record_id
            == IndicatorResult.record_id,
        )
        .filter(
            MeasurementRecord.service_id
            == service_id,
            MeasurementRecord.year
            == previous_year,
            MeasurementRecord.period
            == previous_code,
        )
        .all()
    )

    return {
        indicator_name: current_value
        for indicator_name, current_value
        in rows
    }


def save_uploaded_records(
    records,
    targets=None,
):
    """
    حفظ مجموعة سجلات قادمة من ملف Excel.

    شكل كل سجل متوقع:

    {
        "department": "اسم القسم",
        "service": "اسم الخدمة",
        "year": 2025,
        "period": "H1",
        "participants": 100,
        "review": "التعليقات",
        "indicators": {
            "CSAT": 85.5,
            "CES": 42.0,
            "NPS": 30.0,
        }
    }

    يمكن تمرير المستهدفات:

    {
        "CSAT": 85,
        "CES": 76,
        "NPS": 69,
    }
    """

    if not records:
        return {
            "ok": False,
            "errors": [
                "لا توجد بيانات جاهزة للحفظ."
            ],
            "inserted_records": 0,
            "updated_records": 0,
            "saved_indicators": 0,
        }

    targets = targets or DEFAULT_TARGETS

    inserted_records = 0
    updated_records = 0
    saved_indicators = 0

    # نرتب السجلات زمنيًا حتى تكون
    # القيمة السابقة صحيحة.
    sorted_records = sorted(
        records,
        key=lambda record: (
            int(record["year"]),
            1 if record["period"] == "H1" else 2,
        ),
    )

    session = SessionLocal()

    try:
        indicator_rows = {
            indicator.indicator_name: indicator
            for indicator
            in session.query(Indicator).all()
        }

        for uploaded_record in sorted_records:
            department_name = str(
                uploaded_record["department"]
            ).strip()

            service_name = str(
                uploaded_record["service"]
            ).strip()

            year = int(
                uploaded_record["year"]
            )

            period = str(
                uploaded_record["period"]
            ).strip()

            participants = int(
                uploaded_record.get(
                    "participants",
                    0,
                )
            )

            review = uploaded_record.get(
                "review"
            )

            indicator_values = (
                uploaded_record.get(
                    "indicators",
                    {}
                )
            )

            if not department_name:
                raise ValueError(
                    "يوجد سجل بدون اسم قسم."
                )

            if not service_name:
                raise ValueError(
                    "يوجد سجل بدون اسم خدمة."
                )

            if period not in PERIODS:
                raise ValueError(
                    f"الفترة غير صحيحة: {period}. "
                    "يجب أن تكون H1 أو H2."
                )

            if participants < 0:
                raise ValueError(
                    "عدد المشاركين لا يمكن "
                    "أن يكون سالبًا."
                )

            department = (
                _get_or_create_department(
                    session=session,
                    department_name=(
                        department_name
                    ),
                )
            )

            service = (
                _get_or_create_service(
                    session=session,
                    department=department,
                    service_name=service_name,
                )
            )

            previous_values = (
                _get_previous_values_in_session(
                    session=session,
                    service_id=(
                        service.service_id
                    ),
                    year=year,
                    period=period,
                )
            )

            measurement_record = (
                session.query(
                    MeasurementRecord
                )
                .filter(
                    MeasurementRecord.service_id
                    == service.service_id,
                    MeasurementRecord.year
                    == year,
                    MeasurementRecord.period
                    == period,
                )
                .first()
            )

            if measurement_record is None:
                measurement_record = (
                    MeasurementRecord(
                        service_id=(
                            service.service_id
                        ),
                        year=year,
                        period=period,
                        participants_count=(
                            participants
                        ),
                        review=review,
                    )
                )

                session.add(
                    measurement_record
                )

                session.flush()

                inserted_records += 1

            else:
                measurement_record.participants_count = (
                    participants
                )

                measurement_record.review = (
                    _append_uploaded_review(
                        old_review=(
                            measurement_record.review
                        ),
                        new_review=review,
                    )
                )

                session.flush()

                updated_records += 1

            for (
                indicator_code,
                current_value,
            ) in indicator_values.items():

                if current_value is None:
                    continue

                indicator = indicator_rows.get(
                    indicator_code
                )

                if indicator is None:
                    raise ValueError(
                        "المؤشر غير موجود في "
                        f"قاعدة البيانات: "
                        f"{indicator_code}"
                    )

                target_value = targets.get(
                    indicator_code
                )

                if target_value is None:
                    raise ValueError(
                        "لا توجد قيمة مستهدفة "
                        f"للمؤشر {indicator_code}."
                    )

                current_decimal = Decimal(
                    str(current_value)
                )

                target_decimal = Decimal(
                    str(target_value)
                )

                if (
                    current_decimal
                    < indicator.min_value
                    or current_decimal
                    > indicator.max_value
                ):
                    raise ValueError(
                        f"قيمة {indicator_code} "
                        f"خارج النطاق المسموح: "
                        f"{current_decimal}"
                    )

                previous_value = (
                    previous_values.get(
                        indicator_code
                    )
                )

                indicator_result = (
                    session.query(
                        IndicatorResult
                    )
                    .filter(
                        IndicatorResult.record_id
                        == measurement_record.record_id,
                        IndicatorResult.indicator_id
                        == indicator.indicator_id,
                    )
                    .first()
                )

                if indicator_result is None:
                    indicator_result = (
                        IndicatorResult(
                            record_id=(
                                measurement_record
                                .record_id
                            ),
                            indicator_id=(
                                indicator.indicator_id
                            ),
                            prev_value=(
                                None
                                if previous_value
                                is None
                                else Decimal(
                                    str(
                                        previous_value
                                    )
                                )
                            ),
                            current_value=(
                                current_decimal
                            ),
                            target_value=(
                                target_decimal
                            ),
                        )
                    )

                    session.add(
                        indicator_result
                    )

                else:
                    indicator_result.prev_value = (
                        None
                        if previous_value is None
                        else Decimal(
                            str(previous_value)
                        )
                    )

                    indicator_result.current_value = (
                        current_decimal
                    )

                    indicator_result.target_value = (
                        target_decimal
                    )

                saved_indicators += 1

        session.commit()

        return {
            "ok": True,
            "errors": [],
            "inserted_records": (
                inserted_records
            ),
            "updated_records": (
                updated_records
            ),
            "saved_indicators": (
                saved_indicators
            ),
        }

    except Exception as error:
        session.rollback()

        return {
            "ok": False,
            "errors": [
                f"خطأ في حفظ ملف Excel: {error}"
            ],
            "inserted_records": 0,
            "updated_records": 0,
            "saved_indicators": 0,
        }

    finally:
        session.close()
