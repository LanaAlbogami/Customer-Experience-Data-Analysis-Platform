# -*- coding: utf-8 -*-
# Logic for manual entry and Excel upload to the Departments/Services database.

from __future__ import annotations

from decimal import Decimal
from typing import Any
from datetime import datetime

from sqlalchemy import select

from database.connection import SessionLocal
from database.models import (
    Factor,
    FactorResult,
    Indicator,
    IndicatorResult,
    MeasurementRecord,
    Section,
    Service,
)


# Periods
# There is no Period table in the schema, so these are kept as
# fixed system constants.

PERIODS = {
    "النصف الأول": "النصف الأول",
    "النصف الثاني": "النصف الثاني",
}



# General helpers

# Convert a numeric value to Decimal, preserving None
def _to_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None

    return Decimal(str(value))

# Check that the value falls within the indicator's allowed range.
def _validate_range(
    value: Decimal,
    minimum: Decimal,
    maximum: Decimal,
    field_name: str,
) -> None:
    if value < minimum or value > maximum:
        raise ValueError(
            f"قيمة {field_name} خارج النطاق المسموح "
            f"({minimum} إلى {maximum}): {value}"
        )

# Return the stored period names
def get_period_codes() -> list[str]:
    return list(PERIODS.keys())

# Return the period's display name.
def period_label(code: str) -> str:
    return PERIODS.get(code, code)


def previous_period(year: int, period: str) -> tuple[int, str]:
    """
    Return the previous period:
    second half -> first half of the same year
    first half  -> second half of the previous year
    """
    if period == "النصف الثاني":
        return year, "النصف الأول"

    if period == "النصف الأول":
        return year - 1, "النصف الثاني"

    raise ValueError(
        f"الفترة غير صحيحة: {period}. "
        "يجب أن تكون النصف الأول أو النصف الثاني."
    )


def get_years():
    """
    Return the years present in the database, plus a few years around the
    current year so new data can still be entered.
    """

    current_year = datetime.now().year

    with SessionLocal() as session:
        database_years = session.scalars(
            select(MeasurementRecord.year)
            .distinct()
            .order_by(MeasurementRecord.year)
        ).all()

    available_years = set(database_years)

    # Years available for data entry even if no data exists for them yet
    available_years.update(
        range(
            current_year - 2,
            current_year + 2,
        )
    )

    return sorted(available_years)


# Sections and services from the database

# Return the section names from the database.
def get_sections() -> list[str]:
    with SessionLocal() as session:
        sections = session.scalars(
            select(Section)
            .order_by(Section.section_name)
        ).all()

        return [
            section.section_name
            for section in sections
        ]


def get_departments() -> list[str]:
    """
    Legacy name kept for compatibility with the current entry page.
    Internally returns sections, not departments.
    """
    return get_sections()


def _get_section_by_name(
    session,
    section_name: str,
) -> Section | None:
    return session.scalar(
        select(Section)
        .where(Section.section_name == section_name)
    )

# Fetch the section, or create it when a new file is uploaded.
def _get_or_create_section(
    session,
    section_name: str,
) -> Section:
    section_name = str(section_name).strip()

    if not section_name:
        raise ValueError("اسم القسم مطلوب.")

    section = _get_section_by_name(
        session,
        section_name,
    )

    if section is None:
        section = Section(
            section_name=section_name,
        )
        session.add(section)
        session.flush()

    return section


# Return the services of a specific section from the database.
def get_services(section_name: str) -> list[str]:
    with SessionLocal() as session:
        section = _get_section_by_name(
            session,
            section_name,
        )

        if section is None:
            return []

        services = session.scalars(
            select(Service)
            .where(Service.section_id == section.section_id)
            .order_by(Service.service_name)
        ).all()

        return [
            service.service_name
            for service in services
        ]


def _get_service(
    session,
    section_name: str,
    service_name: str,
) -> Service | None:
    return session.scalar(
        select(Service)
        .join(
            Section,
            Service.section_id == Section.section_id,
        )
        .where(
            Section.section_name == section_name,
            Service.service_name == service_name,
        )
    )

# Fetch the service within the section, or create it on upload.
def _get_or_create_service(
    session,
    section: Section,
    service_name: str,
) -> Service:
    service_name = str(service_name).strip()

    if not service_name:
        raise ValueError("اسم الخدمة مطلوب.")

    service = session.scalar(
        select(Service)
        .where(
            Service.section_id == section.section_id,
            Service.service_name == service_name,
        )
    )

    if service is None:
        service = Service(
            section_id=section.section_id,
            service_name=service_name,
        )
        session.add(service)
        session.flush()

    return service


# Indicators and factors from the database

def _get_indicators(session) -> list[Indicator]:
    return list(
        session.scalars(
            select(Indicator)
            .order_by(Indicator.indicator_id)
        ).all()
    )

# Return the indicators shown on the manual entry page.

def get_indicator_codes(
    include_factor_based: bool = True,
) -> list[str]:
    preferred_order = ["CSAT", "CES", "NPS"]

    with SessionLocal() as session:
        existing_codes = set(
            session.scalars(
                select(Indicator.indicator_name)
            ).all()
        )

    return [
        code
        for code in preferred_order
        if code in existing_codes
    ]

# Return a single indicator's data from the database.
def get_indicator(code: str) -> dict[str, Any]:
    with SessionLocal() as session:
        indicator = session.scalar(
            select(Indicator)
            .where(Indicator.indicator_name == code)
        )

        if indicator is None:
            return {}

        return {
            "id": indicator.indicator_id,
            "code": indicator.indicator_name,
            "minimum": float(indicator.min_value),
            "maximum": float(indicator.max_value),
            "unit": indicator.unit,
            "is_factor_based": indicator.is_factor_based,
        }

# Return the indicator name stored in the database.
def indicator_name_ar(code: str) -> str:
    return get_indicator(code).get("code", code)

# Return the allowed range for the indicator.
def indicator_bounds(code: str) -> tuple[float, float]:
    indicator = get_indicator(code)

    return (
        indicator.get("minimum", 0.0),
        indicator.get("maximum", 100.0),
    )


def is_higher_better(code: str) -> bool:
    """
    For all current platform indicators, higher is better.
    There is no dedicated column for this option in the current schema.    """
    return True

# Return the seven factors in display order.
def get_factors() -> list[dict[str, Any]]:
    with SessionLocal() as session:
        factors = session.scalars(
            select(Factor)
            .order_by(Factor.display_order)
        ).all()

        return [
            {
                "id": factor.factor_id,
                "name": factor.factor_name,
                "display_order": factor.display_order,
            }
            for factor in factors
        ]


# Return the default target for the manual entry page.
# The user can adjust the value before saving.
def default_target(code: str) -> float | None:
    targets = {
        "CSAT": 85.0,
        "CES": 76.0,
        "NPS": 69.0,
    }

    return targets.get(code)



# Previous record and previous values

def _find_measurement_record(
    session,
    service_id: int,
    year: int,
    period: str,
) -> MeasurementRecord | None:
    return session.scalar(
        select(MeasurementRecord)
        .where(
            MeasurementRecord.service_id == service_id,
            MeasurementRecord.year == year,
            MeasurementRecord.period == period,
        )
    )


def _find_previous_record(
    session,
    service_id: int,
    year: int,
    period: str,
) -> MeasurementRecord | None:
    previous_year, previous_code = previous_period(
        year,
        period,
    )

    return _find_measurement_record(
        session,
        service_id,
        previous_year,
        previous_code,
    )


# Return the current indicator values from the previous period.
def _previous_indicator_values(
    session,
    service_id: int,
    year: int,
    period: str,
) -> dict[str, Decimal]:
    previous_record = _find_previous_record(
        session,
        service_id,
        year,
        period,
    )

    if previous_record is None:
        return {}

    rows = session.execute(
        select(
            Indicator.indicator_name,
            IndicatorResult.current_value,
        )
        .join(
            IndicatorResult,
            IndicatorResult.indicator_id
            == Indicator.indicator_id,
        )
        .where(
            IndicatorResult.record_id
            == previous_record.record_id
        )
    ).all()

    return {
        indicator_name: current_value
        for indicator_name, current_value in rows
    }


# Return the factor results from the previous period.
def _previous_factor_values(
    session,
    service_id: int,
    year: int,
    period: str,
) -> dict[str, Decimal]:
    previous_record = _find_previous_record(
        session,
        service_id,
        year,
        period,
    )

    if previous_record is None:
        return {}

    rows = session.execute(
        select(
            Factor.factor_name,
            FactorResult.current_value,
        )
        .join(
            FactorResult,
            FactorResult.factor_id
            == Factor.factor_id,
        )
        .where(
            FactorResult.record_id
            == previous_record.record_id
        )
    ).all()

    return {
        factor_name: current_value
        for factor_name, current_value in rows
    }


# Return the previous indicator values for the entry page.
def get_previous_values(
    section: str,
    service: str,
    year: int,
    period: str,
) -> dict[str, float]:
    with SessionLocal() as session:
        service_row = _get_service(
            session,
            section,
            service,
        )

        if service_row is None:
            return {}

        values = _previous_indicator_values(
            session,
            service_row.service_id,
            year,
            period,
        )

        return {
            code: float(value)
            for code, value in values.items()
        }


# Manual entry

# Check whether a record already exists for the same service and period.
def entry_exists(
    section: str,
    service: str,
    year: int,
    period: str,
) -> bool:
    with SessionLocal() as session:
        service_row = _get_service(
            session,
            section,
            service,
        )

        if service_row is None:
            return False

        record = _find_measurement_record(
            session,
            service_row.service_id,
            year,
            period,
        )

        return record is not None


def _has_current_value(row: dict[str, Any]) -> bool:
    return row.get("current") is not None

# Validate the manual entry data.
def validate_entry(
    section: str,
    service: str,
    year: int,
    period: str,
    typed_values: dict[str, dict[str, Any]],
) -> list[str]:
    errors = []

    if period not in PERIODS:
        errors.append(
            "الفترة يجب أن تكون النصف الأول أو النصف الثاني."
        )

    if entry_exists(
        section,
        service,
        year,
        period,
    ):
        errors.append(
            f"يوجد إدخال محفوظ مسبقًا لـ "
            f"{section} / {service} — "
            f"{period_label(period)} {year}."
        )

    filled = [
        code
        for code, row in typed_values.items()
        if _has_current_value(row)
    ]

    if not filled:
        errors.append(
            "الرجاء إدخال القيمة الحالية "
            "لمؤشر واحد على الأقل."
        )

    return errors


def save_entry(
    section: str,
    service: str,
    year: int,
    period: str,
    typed_values: dict[str, dict[str, Any]],
    participants: int = 0,
    review: str | None = None,
) -> dict[str, Any]:
    """
    Save the manual entry for the indicators shown on the page.

    CSAT can be entered here as a pre-computed average, whereas the Excel
    upload keeps calculating CSAT from the factor results.
    TargetValue is optional.
    """
    errors = validate_entry(
        section,
        service,
        year,
        period,
        typed_values,
    )

    if errors:
        return {
            "ok": False,
            "errors": errors,
            "saved_count": 0,
        }

    with SessionLocal() as session:
        try:
            service_row = _get_service(
                session,
                section,
                service,
            )

            if service_row is None:
                raise ValueError(
                    f"الخدمة غير موجودة في قاعدة البيانات: "
                    f"{service}"
                )

            indicators = {
                indicator.indicator_name: indicator
                for indicator in _get_indicators(session)
            }

            previous_values = _previous_indicator_values(
                session,
                service_row.service_id,
                year,
                period,
            )

            record = MeasurementRecord(
                service_id=service_row.service_id,
                year=int(year),
                period=period,
                participants_count=int(participants or 0),
                review=review,
            )

            session.add(record)
            session.flush()

            saved_count = 0

            for code, row in typed_values.items():
                if not _has_current_value(row):
                    continue

                indicator = indicators.get(code)

                if indicator is None:
                    raise ValueError(
                        f"المؤشر غير موجود في قاعدة البيانات: "
                        f"{code}"
                    )

                current_value = _to_decimal(
                    row.get("current")
                )

                if current_value is None:
                    continue

                _validate_range(
                    current_value,
                    indicator.min_value,
                    indicator.max_value,
                    code,
                )

                target_value = _to_decimal(
                    row.get("target")
                )

                previous_value = previous_values.get(code)

                session.add(
                    IndicatorResult(
                        record_id=record.record_id,
                        indicator_id=indicator.indicator_id,
                        prev_value=previous_value,
                        current_value=current_value,
                        target_value=target_value,
                    )
                )

                saved_count += 1

            session.commit()

            return {
                "ok": True,
                "errors": [],
                "saved_count": saved_count,
            }

        except Exception as error:
            session.rollback()

            return {
                "ok": False,
                "errors": [str(error)],
                "saved_count": 0,
            }



# Excel file uploads

# Merge review comments without duplicating them.
def _append_review(
    old_review: str | None,
    new_review: str | None,
) -> str | None:
    """دمج التعليقات بدون تكرار."""
    if not new_review:
        return old_review

    if not old_review:
        return new_review

    existing = {
        line.strip().lower()
        for line in old_review.splitlines()
        if line.strip()
    }

    additions = []

    for line in new_review.splitlines():
        comment = line.strip()

        if not comment:
            continue

        normalized = comment.lower()

        if normalized in existing:
            continue

        existing.add(normalized)
        additions.append(comment)

    if not additions:
        return old_review

    return old_review + "\n" + "\n".join(additions)


def _upsert_factor_result(
    session,
    record: MeasurementRecord,
    factor: Factor,
    current_value: Decimal,
    previous_value: Decimal | None,
    target_value: Decimal | None,
    participants_count: int | None,
) -> None:
    result = session.scalar(
        select(FactorResult)
        .where(
            FactorResult.record_id == record.record_id,
            FactorResult.factor_id == factor.factor_id,
        )
    )

    if result is None:
        result = FactorResult(
            record_id=record.record_id,
            factor_id=factor.factor_id,
            participants_count=participants_count,
            prev_value=previous_value,
            current_value=current_value,
            target_value=target_value,
        )
        session.add(result)

    else:
        result.participants_count = participants_count
        result.prev_value = previous_value
        result.current_value = current_value
        result.target_value = target_value


def _upsert_indicator_result(
    session,
    record: MeasurementRecord,
    indicator: Indicator,
    current_value: Decimal,
    previous_value: Decimal | None,
    target_value: Decimal | None,
) -> None:
    result = session.scalar(
        select(IndicatorResult)
        .where(
            IndicatorResult.record_id == record.record_id,
            IndicatorResult.indicator_id
            == indicator.indicator_id,
        )
    )

    if result is None:
        result = IndicatorResult(
            record_id=record.record_id,
            indicator_id=indicator.indicator_id,
            prev_value=previous_value,
            current_value=current_value,
            target_value=target_value,
        )
        session.add(result)

    else:
        result.prev_value = previous_value
        result.current_value = current_value
        result.target_value = target_value


# Support both the new dict shape and the simplified numeric shape.
def _factor_current_value(payload: Any) -> Any:
    if isinstance(payload, dict):
        return payload.get("current_value")

    return payload


def _factor_participants(payload: Any) -> int | None:
    if not isinstance(payload, dict):
        return None

    value = payload.get("participants_count")

    if value is None:
        return None

    return int(value)


def _factor_target(
    payload: Any,
    record_targets: dict[str, Any],
    global_targets: dict[str, Any],
    factor_name: str,
) -> Decimal | None:
    if isinstance(payload, dict):
        payload_target = payload.get("target_value")

        if payload_target is not None:
            return _to_decimal(payload_target)

    if factor_name in record_targets:
        return _to_decimal(
            record_targets[factor_name]
        )

    return _to_decimal(
        global_targets.get(factor_name)
    )


def save_uploaded_records(
    records: list[dict[str, Any]],
    targets: dict[str, Any] | None = None,
    factor_targets: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Save records from an Excel file.

    targets:
        Global indicator targets, e.g. {"CSAT": 85, "CES": 70}

    factor_targets:
        Factor targets, e.g. {"سهولة الاستخدام": 90}

    Each record may also pass its own:
        indicator_targets
        factor_targets

    There are no fixed default targets hard-coded here.
    """
    if not records:
        return {
            "ok": False,
            "errors": ["لا توجد بيانات جاهزة للحفظ."],
            "inserted_records": 0,
            "updated_records": 0,
            "saved_factors": 0,
            "saved_indicators": 0,
        }

    global_indicator_targets = targets or {}
    global_factor_targets = factor_targets or {}

    inserted_records = 0
    updated_records = 0
    saved_factors = 0
    saved_indicators = 0

    sorted_records = sorted(
        records,
        key=lambda item: (
            int(item["year"]),
            1 if item["period"] == "النصف الأول" else 2,
            str(
                item.get("section")
                or item.get("department")
                or ""
            ),
            str(item.get("service") or ""),
        ),
    )

    with SessionLocal() as session:
        try:
            indicators = {
                indicator.indicator_name: indicator
                for indicator in _get_indicators(session)
            }

            factors = {
                factor.factor_name: factor
                for factor in session.scalars(
                    select(Factor)
                    .order_by(Factor.display_order)
                ).all()
            }

            if len(factors) != 7:
                raise ValueError(
                    "جدول Factors يجب أن يحتوي على "
                    f"سبعة عوامل، والموجود حاليًا: {len(factors)}."
                )

            csat_indicator = indicators.get("CSAT")

            if csat_indicator is None:
                raise ValueError(
                    "مؤشر CSAT غير موجود في جدول Indicators. "
                    "شغلي seed_data.py."
                )

            for uploaded_record in sorted_records:
                section_name = str(
                    uploaded_record.get("section")
                    or uploaded_record.get("department")
                    or ""
                ).strip()

                service_name = str(
                    uploaded_record.get("service")
                    or ""
                ).strip()

                year = int(uploaded_record["year"])
                period = str(
                    uploaded_record["period"]
                ).strip()

                participants = int(
                    uploaded_record.get(
                        "participants",
                        0,
                    )
                    or 0
                )

                review = uploaded_record.get("review")

                if not section_name:
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
                        "يجب أن تكون النصف الأول أو النصف الثاني."
                    )

                if participants < 0:
                    raise ValueError(
                        "عدد المشاركين لا يمكن أن يكون سالبًا."
                    )

                section = _get_or_create_section(
                    session,
                    section_name,
                )

                service = _get_or_create_service(
                    session,
                    section,
                    service_name,
                )

                previous_indicators = _previous_indicator_values(
                    session,
                    service.service_id,
                    year,
                    period,
                )

                previous_factors = _previous_factor_values(
                    session,
                    service.service_id,
                    year,
                    period,
                )

                record = _find_measurement_record(
                    session,
                    service.service_id,
                    year,
                    period,
                )

                if record is None:
                    record = MeasurementRecord(
                        service_id=service.service_id,
                        year=year,
                        period=period,
                        participants_count=participants,
                        review=review,
                    )
                    session.add(record)
                    session.flush()
                    inserted_records += 1

                else:
                    record.participants_count = participants
                    record.review = _append_review(
                        record.review,
                        review,
                    )
                    updated_records += 1

                uploaded_factors = (
                    uploaded_record.get("factors")
                    or {}
                )

                unknown_factors = [
                    factor_name
                    for factor_name in uploaded_factors
                    if factor_name not in factors
                ]

                if unknown_factors:
                    raise ValueError(
                        "العوامل التالية غير موجودة في "
                        "جدول Factors: "
                        + "، ".join(unknown_factors)
                    )

                record_factor_targets = (
                    uploaded_record.get("factor_targets")
                    or {}
                )

                current_factor_values = []

                for factor_name, payload in uploaded_factors.items():
                    raw_current = _factor_current_value(payload)

                    if raw_current is None:
                        continue

                    current_value = _to_decimal(raw_current)

                    if current_value is None:
                        continue

                    _validate_range(
                        current_value,
                        Decimal("0"),
                        Decimal("100"),
                        f"عامل {factor_name}",
                    )

                    target_value = _factor_target(
                        payload,
                        record_factor_targets,
                        global_factor_targets,
                        factor_name,
                    )

                    if target_value is not None:
                        _validate_range(
                            target_value,
                            Decimal("0"),
                            Decimal("100"),
                            f"مستهدف عامل {factor_name}",
                        )

                    _upsert_factor_result(
                        session=session,
                        record=record,
                        factor=factors[factor_name],
                        current_value=current_value,
                        previous_value=previous_factors.get(
                            factor_name
                        ),
                        target_value=target_value,
                        participants_count=_factor_participants(
                            payload
                        ),
                    )

                    current_factor_values.append(
                        current_value
                    )
                    saved_factors += 1

                record_indicator_targets = (
                    uploaded_record.get("indicator_targets")
                    or {}
                )

                uploaded_indicators = (
                    uploaded_record.get("indicators")
                    or {}
                )

                # CSAT is calculated from the factor results,
                # not taken from a manually uploaded value.

                if current_factor_values:
                    csat_value = (
                        sum(current_factor_values)
                        / Decimal(
                            len(current_factor_values)
                        )
                    ).quantize(Decimal("0.01"))

                    csat_target = _to_decimal(
                        record_indicator_targets.get(
                            "CSAT",
                            global_indicator_targets.get(
                                "CSAT"
                            ),
                        )
                    )

                    if csat_target is not None:
                        _validate_range(
                            csat_target,
                            csat_indicator.min_value,
                            csat_indicator.max_value,
                            "مستهدف CSAT",
                        )

                    _upsert_indicator_result(
                        session=session,
                        record=record,
                        indicator=csat_indicator,
                        current_value=csat_value,
                        previous_value=previous_indicators.get(
                            "CSAT"
                        ),
                        target_value=csat_target,
                    )

                    saved_indicators += 1

                # Non-factor-based indicators

                for code, raw_value in uploaded_indicators.items():
                    if code == "CSAT" or raw_value is None:
                        continue

                    indicator = indicators.get(code)

                    if indicator is None:
                        raise ValueError(
                            f"المؤشر غير موجود في قاعدة البيانات: "
                            f"{code}"
                        )

                    if indicator.is_factor_based:
                        raise ValueError(
                            f"المؤشر {code} يعتمد على العوامل "
                            "ولا يقبل قيمة مباشرة."
                        )

                    current_value = _to_decimal(raw_value)

                    if current_value is None:
                        continue

                    _validate_range(
                        current_value,
                        indicator.min_value,
                        indicator.max_value,
                        code,
                    )

                    target_value = _to_decimal(
                        record_indicator_targets.get(
                            code,
                            global_indicator_targets.get(code),
                        )
                    )

                    if target_value is not None:
                        _validate_range(
                            target_value,
                            indicator.min_value,
                            indicator.max_value,
                            f"مستهدف {code}",
                        )

                    _upsert_indicator_result(
                        session=session,
                        record=record,
                        indicator=indicator,
                        current_value=current_value,
                        previous_value=previous_indicators.get(
                            code
                        ),
                        target_value=target_value,
                    )

                    saved_indicators += 1

            session.commit()

            return {
                "ok": True,
                "errors": [],
                "inserted_records": inserted_records,
                "updated_records": updated_records,
                "saved_factors": saved_factors,
                "saved_indicators": saved_indicators,
            }

        except Exception as error:
            session.rollback()

            return {
                "ok": False,
                "errors": [
                    f"خطأ في حفظ البيانات: {error}"
                ],
                "inserted_records": 0,
                "updated_records": 0,
                "saved_factors": 0,
                "saved_indicators": 0,
            }


# Read and delete (for testing)

def get_all_records() -> list[dict[str, Any]]:
    """إرجاع نتائج المؤشرات المحفوظة."""
    with SessionLocal() as session:
        rows = session.execute(
            select(
                Section,
                Service,
                MeasurementRecord,
                Indicator,
                IndicatorResult,
            )
            .join(
                Service,
                Service.section_id == Section.section_id,
            )
            .join(
                MeasurementRecord,
                MeasurementRecord.service_id
                == Service.service_id,
            )
            .join(
                IndicatorResult,
                IndicatorResult.record_id
                == MeasurementRecord.record_id,
            )
            .join(
                Indicator,
                Indicator.indicator_id
                == IndicatorResult.indicator_id,
            )
            .order_by(
                MeasurementRecord.year,
                MeasurementRecord.period,
                Section.section_name,
                Service.service_name,
                Indicator.indicator_id,
            )
        ).all()

        return [
            {
                "Section": section.section_name,
                "Department": section.section_name,
                "Service": service.service_name,
                "Year": record.year,
                "Period": record.period,
                "Indicator": indicator.indicator_name,
                "PreviousValue": (
                    None
                    if result.prev_value is None
                    else float(result.prev_value)
                ),
                "CurrentValue": float(
                    result.current_value
                ),
                "TargetValue": (
                    None
                    if result.target_value is None
                    else float(result.target_value)
                ),
            }
            for (
                section,
                service,
                record,
                indicator,
                result,
            ) in rows
        ]


def clear_all_records() -> None:
    """
    Delete measurement results (for testing only).
    Sections, services, indicators, and factors are not deleted.
    """
    with SessionLocal() as session:
        try:
            session.query(FactorResult).delete(
                synchronize_session=False
            )
            session.query(IndicatorResult).delete(
                synchronize_session=False
            )
            session.query(MeasurementRecord).delete(
                synchronize_session=False
            )

            session.commit()

        except Exception:
            session.rollback()
            raise
