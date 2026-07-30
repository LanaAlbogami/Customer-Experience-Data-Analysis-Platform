# -*- coding: utf-8 -*-
"""
entry_backend.py
----------------
BACKEND for the data entry page. Talks to the MySQL database through the
team's SQLAlchemy models.

RULE: this file must never import streamlit. Everything about how the
screen LOOKS belongs in data_entry.py; everything about the DATA is here.

The function NAMES are exactly the same as the old in-memory version, so
data_entry.py did not need to change when we switched to the database.

How the tables fit together for one saved entry:
    MeasurementRecord   -> one row  (service + year + period + participants)
      IndicatorResult   -> one row per indicator under that record
"""

from decimal import Decimal

from database.connection import SessionLocal
from database.models import (Department, Service, Indicator,
                             MeasurementRecord, IndicatorResult)


# ----------------------------------------------------------------------
# Periods live in the code, not the database (the schema has no period
# table). The code on the left is stored; the Arabic label is shown.
# ----------------------------------------------------------------------
PERIODS = {
    "H1": "النصف الأول",
    "H2": "النصف الثاني",
}

# Years also live in the code -- they are just numbers, not a table.
YEARS = [2024, 2025, 2026, 2027]


def get_period_codes():
    """Return the stored period codes: H1, H2."""
    return list(PERIODS.keys())


def previous_period(year, period):
    """
    Return the (year, period) that comes right before this one.

    With only two halves per year:
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
# Lookups: departments and services now come FROM the database.
# ----------------------------------------------------------------------

def get_departments():
    """Return the list of department names, read from the database."""
    session = SessionLocal()
    try:
        rows = session.query(Department).order_by(Department.department_id).all()
        return [row.department_name for row in rows]
    finally:
        session.close()


def get_services(department):
    """Return the services that belong to one department (by its name)."""
    session = SessionLocal()
    try:
        rows = (session.query(Service)
                .join(Department, Service.department_id == Department.department_id)
                .filter(Department.department_name == department)
                .order_by(Service.service_id)
                .all())
        return [row.service_name for row in rows]
    finally:
        session.close()


# ----------------------------------------------------------------------
# Indicators also come from the database. We cache them once per run,
# because the list is tiny and never changes while the app is open.
# ----------------------------------------------------------------------
_indicator_cache = None


def _load_indicators():
    """Read all indicators from the database once, then reuse them."""
    global _indicator_cache
    if _indicator_cache is None:
        session = SessionLocal()
        try:
            rows = session.query(Indicator).order_by(Indicator.indicator_id).all()
            _indicator_cache = [
                {"code": row.indicator_name,
                 "minimum": float(row.min_value),
                 "maximum": float(row.max_value),
                 "unit": row.unit}
                for row in rows
            ]
        finally:
            session.close()
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
    """
    The schema stores only the short name (CSAT), so there is no separate
    Arabic name. We return the code, which is what the page shows anyway.
    """
    return get_indicator(code).get("code", code)


def indicator_bounds(code):
    """Return (minimum, maximum) allowed for this indicator."""
    item = get_indicator(code)
    return item.get("minimum", 0.0), item.get("maximum", 100.0)


def is_higher_better(code):
    """
    The schema has no "direction" column, so we keep the rule here:
    all three indicators are "higher is better" (our CES is a net score).
    """
    return True


# ----------------------------------------------------------------------
# Default target values
# ----------------------------------------------------------------------
# The target box starts pre-filled with these, but the user can edit them
# before saving. Kept in code (not the database) so they are easy to see
# and change. An indicator not listed here just starts empty.
DEFAULT_TARGETS = {
    "CSAT": 85.0,
    "CES": 76.0,
    "NPS": 69.0,
}


def default_target(code):
    """Return the pre-filled target for one indicator, or None."""
    return DEFAULT_TARGETS.get(code)


# ----------------------------------------------------------------------
# Helper: find one service row from the department + service names
# ----------------------------------------------------------------------

def _find_service(session, department, service):
    """Return the Service row matching both names, or None."""
    return (session.query(Service)
            .join(Department, Service.department_id == Department.department_id)
            .filter(Department.department_name == department,
                    Service.service_name == service)
            .first())


# ----------------------------------------------------------------------
# Previous values: read last period's "current" value for each indicator
# ----------------------------------------------------------------------

def get_previous_values(department, service, year, period):
    """
    Look up what the CURRENT values were in the period right before this
    one, so they can be shown as this entry's "previous" values.

    Example: entering H2 2026 -> reads the CurrentValue that was saved
    for H1 2026.

    Returns a dictionary {indicator_code: value}. An indicator with no
    earlier record is simply left out of the dictionary.
    """
    previous_year, previous_code = previous_period(year, period)

    session = SessionLocal()
    try:
        service_row = _find_service(session, department, service)
        if service_row is None:
            return {}

        # Read each indicator's current value from the earlier record in
        # one query. Joining explicitly avoids relying on lazy-loaded
        # relationships after the row is fetched.
        rows = (session.query(Indicator.indicator_name,
                              IndicatorResult.current_value)
                .join(IndicatorResult,
                      IndicatorResult.indicator_id == Indicator.indicator_id)
                .join(MeasurementRecord,
                      MeasurementRecord.record_id == IndicatorResult.record_id)
                .filter(MeasurementRecord.service_id == service_row.service_id,
                        MeasurementRecord.year == previous_year,
                        MeasurementRecord.period == previous_code)
                .all())

        return {name: float(value) for name, value in rows}
    finally:
        session.close()


# ----------------------------------------------------------------------
# Duplicate check
# ----------------------------------------------------------------------

def entry_exists(department, service, year, period):
    """
    True when a MeasurementRecord already exists for this
    service + year + period. (Service already implies its department.)
    """
    session = SessionLocal()
    try:
        service_row = _find_service(session, department, service)
        if service_row is None:
            return False

        record = (session.query(MeasurementRecord)
                  .filter_by(service_id=service_row.service_id,
                             year=year, period=period)
                  .first())
        return record is not None
    finally:
        session.close()


# ----------------------------------------------------------------------
# Validating and saving what the user typed
# ----------------------------------------------------------------------

def _has_any_value(row):
    """
    True when the user actually started this row.

    The target box is pre-filled with a default, so its presence does not
    mean the user entered anything. Only a typed CURRENT value counts as
    "this row is being used".
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

    # A used row must still have a target (it is NOT NULL in the schema).
    # The box is pre-filled, but the user could clear it, so we check.
    for code, row in typed_values.items():
        if _has_any_value(row) and row.get("target") is None:
            errors.append(f"المؤشر {code}: القيمة المستهدفة مطلوبة.")

    return errors


def save_entry(department, service, year, period, typed_values,
               participants=0, review=None):
    """
    Save one MeasurementRecord plus one IndicatorResult per filled row.

    participants / review: the page does not collect these yet, so they
    default to 0 / None. ParticipantsCount is NOT NULL in the schema, so
    0 is a safe placeholder until the field is added to the form.

    Returns {ok, errors, saved_count}.
    """
    errors = validate_entry(department, service, year, period, typed_values)
    if errors:
        return {"ok": False, "errors": errors, "saved_count": 0}

    # The previous values are NOT typed by the user -- read them from the
    # period before, so each row is stored with its real prev_value.
    previous_values = get_previous_values(department, service, year, period)

    session = SessionLocal()
    try:
        service_row = _find_service(session, department, service)
        if service_row is None:
            return {"ok": False,
                    "errors": [f"الخدمة غير موجودة في قاعدة البيانات: {service}"],
                    "saved_count": 0}

        # 1) The parent record for this service + period.
        record = MeasurementRecord(
            service_id=service_row.service_id,
            year=year,
            period=period,
            participants_count=participants,
            review=review,
        )
        session.add(record)
        session.flush()          # gives the record its RecordID now

        # 2) One IndicatorResult per filled indicator row.
        # Read the indicators through the SAME session (not a helper that
        # opens its own), so everything stays in one transaction.
        indicator_rows = {ind.indicator_name: ind
                          for ind in session.query(Indicator).all()}

        saved_count = 0
        for code, indicator_row in indicator_rows.items():
            row = typed_values.get(code, {})
            if not _has_any_value(row):
                continue

            # previous comes from the earlier period, may be missing
            previous = previous_values.get(code)
            session.add(IndicatorResult(
                record_id=record.record_id,
                indicator_id=indicator_row.indicator_id,
                prev_value=None if previous is None else Decimal(str(previous)),
                current_value=Decimal(str(row["current"])),
                target_value=Decimal(str(row["target"])),
            ))
            saved_count += 1

        session.commit()
        return {"ok": True, "errors": [], "saved_count": saved_count}

    except Exception as error:
        session.rollback()       # undo the half-written entry
        return {"ok": False,
                "errors": [f"خطأ في الحفظ: {error}"],
                "saved_count": 0}
    finally:
        session.close()


# ----------------------------------------------------------------------
# Read / clear helpers (used for testing and by later pages)
# ----------------------------------------------------------------------

def get_all_records():
    """Return every saved indicator result as a list of plain dicts."""
    session = SessionLocal()
    try:
        results = (session.query(IndicatorResult)
                   .join(MeasurementRecord)
                   .join(Service)
                   .join(Department)
                   .join(Indicator)
                   .all())
        output = []
        for result in results:
            record = result.record
            output.append({
                "Department": record.service.department.department_name,
                "Service": record.service.service_name,
                "Year": record.year,
                "Period": record.period,
                "Indicator": result.indicator.indicator_name,
                "PreviousValue": (None if result.prev_value is None
                                  else float(result.prev_value)),
                "CurrentValue": float(result.current_value),
                "TargetValue": float(result.target_value),
            })
        return output
    finally:
        session.close()


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
