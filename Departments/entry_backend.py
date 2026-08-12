# -*- coding: utf-8 -*-
"""
entry_backend.py
----------------
منطق الإدخال اليدوي ورفع ملفات Excel لقاعدة بيانات الأقسام والخدمات.
"""

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


# ==================================================
# الفترات
# لا يوجد جدول Period في التصميم، لذلك تبقى كقيم نظام ثابتة.
# ==================================================

PERIODS = {
    "النصف الأول": "النصف الأول",
    "النصف الثاني": "النصف الثاني",
}


# ==================================================
# أدوات عامة
# ==================================================

def _to_decimal(value: Any) -> Decimal | None:
    """تحويل قيمة رقمية إلى Decimal مع الحفاظ على None."""
    if value is None or value == "":
        return None

    return Decimal(str(value))


def _validate_range(
    value: Decimal,
    minimum: Decimal,
    maximum: Decimal,
    field_name: str,
) -> None:
    """التحقق أن القيمة داخل نطاق المؤشر."""
    if value < minimum or value > maximum:
        raise ValueError(
            f"قيمة {field_name} خارج النطاق المسموح "
            f"({minimum} إلى {maximum}): {value}"
        )


def get_period_codes() -> list[str]:
    """إرجاع أسماء الفترات العربية المحفوظة."""
    return list(PERIODS.keys())


def period_label(code: str) -> str:
    """إرجاع اسم الفترة العربية."""
    return PERIODS.get(code, code)


def previous_period(year: int, period: str) -> tuple[int, str]:
    """
    إرجاع الفترة السابقة:
    النصف الثاني -> النصف الأول من نفس السنة
    النصف الأول -> النصف الثاني من السنة السابقة
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
    يرجع السنوات الموجودة في قاعدة البيانات،
    ويضيف سنوات قريبة من السنة الحالية حتى يمكن إدخال بيانات جديدة.
    """

    current_year = datetime.now().year

    with SessionLocal() as session:
        database_years = session.scalars(
            select(MeasurementRecord.year)
            .distinct()
            .order_by(MeasurementRecord.year)
        ).all()

    available_years = set(database_years)

    # سنوات الإدخال المتاحة حتى لو لم توجد لها بيانات مسبقًا
    available_years.update(
        range(
            current_year - 2,
            current_year + 2,
        )
    )

    return sorted(available_years)


# ==================================================
# الأقسام والخدمات من قاعدة البيانات
# ==================================================

def get_sections() -> list[str]:
    """إرجاع أسماء الأقسام من قاعدة البيانات."""
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
    اسم قديم للتوافق مع صفحة الإدخال الحالية.
    داخليًا يعيد Sections وليس Departments.
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


def _get_or_create_section(
    session,
    section_name: str,
) -> Section:
    """جلب القسم أو إنشاؤه عند رفع ملف جديد."""
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


def get_services(section_name: str) -> list[str]:
    """إرجاع خدمات قسم محدد من قاعدة البيانات."""
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


def _get_or_create_service(
    session,
    section: Section,
    service_name: str,
) -> Service:
    """جلب الخدمة داخل القسم أو إنشاؤها عند الرفع."""
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


# ==================================================
# المؤشرات والعوامل من قاعدة البيانات
# ==================================================

def _get_indicators(session) -> list[Indicator]:
    return list(
        session.scalars(
            select(Indicator)
            .order_by(Indicator.indicator_id)
        ).all()
    )


def get_indicator_codes(
    include_factor_based: bool = True,
) -> list[str]:
    """
    إرجاع المؤشرات المعروضة في صفحة الإدخال اليدوي.

    تعرض الصفحة:
    CSAT ثم CES ثم NPS فقط.
    لا يظهر BPS في صفحة الإدخال اليدوي.
    """
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


def get_indicator(code: str) -> dict[str, Any]:
    """إرجاع بيانات مؤشر واحد من قاعدة البيانات."""
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


def indicator_name_ar(code: str) -> str:
    """إرجاع اسم المؤشر المخزن في قاعدة البيانات."""
    return get_indicator(code).get("code", code)


def indicator_bounds(code: str) -> tuple[float, float]:
    """إرجاع النطاق المسموح للمؤشر."""
    indicator = get_indicator(code)

    return (
        indicator.get("minimum", 0.0),
        indicator.get("maximum", 100.0),
    )


def is_higher_better(code: str) -> bool:
    """
    مؤشرات المنصة الحالية الأعلى فيها أفضل.
    لا يوجد عمود مخصص لهذا الخيار في التصميم الحالي.
    """
    return True


def get_factors() -> list[dict[str, Any]]:
    """إرجاع العوامل السبعة حسب ترتيب العرض."""
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


def default_target(code: str) -> float | None:
    """
    إرجاع المستهدف الافتراضي لصفحة الإدخال اليدوي.

    يمكن للمستخدم تعديل القيمة قبل الحفظ.
    """
    targets = {
        "CSAT": 85.0,
        "CES": 76.0,
        "NPS": 69.0,
    }

    return targets.get(code)



# ==================================================
# السجل السابق والقيم السابقة
# ==================================================

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


def _previous_indicator_values(
    session,
    service_id: int,
    year: int,
    period: str,
) -> dict[str, Decimal]:
    """إرجاع القيم الحالية للمؤشرات من الفترة السابقة."""
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


def _previous_factor_values(
    session,
    service_id: int,
    year: int,
    period: str,
) -> dict[str, Decimal]:
    """إرجاع نتائج العوامل من الفترة السابقة."""
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


def get_previous_values(
    section: str,
    service: str,
    year: int,
    period: str,
) -> dict[str, float]:
    """إرجاع قيم المؤشرات السابقة لصفحة الإدخال."""
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


# ==================================================
# الإدخال اليدوي
# ==================================================

def entry_exists(
    section: str,
    service: str,
    year: int,
    period: str,
) -> bool:
    """التحقق من وجود سجل للخدمة والفترة نفسها."""
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


def validate_entry(
    section: str,
    service: str,
    year: int,
    period: str,
    typed_values: dict[str, dict[str, Any]],
) -> list[str]:
    """التحقق من بيانات الإدخال اليدوي."""
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
    حفظ الإدخال اليدوي للمؤشرات المعروضة في الصفحة.

    يمكن إدخال CSAT هنا على أنه المتوسط المحسوب مسبقًا،
    بينما رفع Excel يستمر في حساب CSAT من نتائج العوامل.
    TargetValue اختياري.
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


# ==================================================
# رفع ملفات Excel
# ==================================================

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


def _factor_current_value(payload: Any) -> Any:
    """دعم الشكل الجديد والشكل الرقمي المبسط."""
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
    حفظ سجلات ملف Excel.

    targets:
        مستهدفات المؤشرات العامة، مثل:
        {"CSAT": 85, "CES": 70}

    factor_targets:
        مستهدفات العوامل، مثل:
        {"سهولة الاستخدام": 90}

    ويمكن لكل سجل تمرير:
        indicator_targets
        factor_targets

    لا توجد مستهدفات افتراضية ثابتة في الكود.
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

                # ------------------------------------------
                # CSAT يُحسب من نتائج العوامل ولا يؤخذ
                # من قيمة مرفوعة يدويًا.
                # ------------------------------------------

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

                # ------------------------------------------
                # المؤشرات غير المعتمدة على عوامل
                # ------------------------------------------

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


# ==================================================
# القراءة والحذف للاختبار
# ==================================================

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
    حذف نتائج القياس للاختبار فقط.
    الأقسام والخدمات والمؤشرات والعوامل لا تُحذف.
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
