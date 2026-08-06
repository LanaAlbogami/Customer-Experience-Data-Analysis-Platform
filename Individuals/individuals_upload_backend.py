# -*- coding: utf-8 -*-
"""
individuals_upload_backend.py
-----------------------------
تجهيز وحفظ ملف بيانات الأفراد داخل individuals_experience_db.

كل صف في ملف Excel يمثل استبيانًا واحدًا لفرد واحد.
إذا لم يُحدد عمود IndividualID، ينشئ النظام IndividualProfile جديدًا لكل صف.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from sqlalchemy import select

from database_individuals.connection import SessionLocal
from database_individuals.models import (
    IndividualFactorResponse,
    IndividualIndicatorResponse,
    IndividualMeasurementRecord,
    IndividualProfile,
    SharedCSATFactor,
    SharedIndicator,
)


VALID_PERIODS = (
    "الربع الأول",
    "الربع الثاني",
    "الربع الثالث",
    "الربع الرابع",
)


# ==================================================
# القيم المرجعية من قاعدة البيانات
# ==================================================

def get_factors() -> list[dict[str, Any]]:
    """إرجاع عوامل CSAT حسب ترتيب العرض."""
    with SessionLocal() as session:
        factors = session.scalars(
            select(SharedCSATFactor)
            .order_by(SharedCSATFactor.display_order)
        ).all()

        return [
            {
                "id": factor.factor_id,
                "name": factor.factor_name,
                "display_order": factor.display_order,
            }
            for factor in factors
        ]


def get_indicators() -> list[dict[str, Any]]:
    """إرجاع المؤشرات الخام الأخرى مثل CES وNPS."""
    with SessionLocal() as session:
        indicators = session.scalars(
            select(SharedIndicator)
            .order_by(SharedIndicator.indicator_id)
        ).all()

        return [
            {
                "id": indicator.indicator_id,
                "name": indicator.indicator_name,
                "unit": indicator.unit,
                "minimum": indicator.min_value,
                "maximum": indicator.max_value,
            }
            for indicator in indicators
        ]


# ==================================================
# أدوات التنظيف والتحويل
# ==================================================

def _clean_text(value: Any) -> str | None:
    if pd.isna(value):
        return None

    text = str(value).strip()
    return text or None


def _arabic_digits_to_english(value: Any) -> str:
    return str(value).translate(
        str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    )


def _optional_integer(
    value: Any,
    *,
    field_name: str,
    row_number: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int | None:
    """
    يحول القيمة إلى عدد صحيح.

    القيم الفارغة و99 تعامل كقيمة غير منطبقة ولا تُحفظ.
    """
    if pd.isna(value) or value == "":
        return None

    text = _arabic_digits_to_english(value).strip()

    if not text:
        return None

    try:
        number = float(text)
    except (TypeError, ValueError):
        raise ValueError(
            f"الصف {row_number}: قيمة {field_name} غير رقمية: {value}"
        )

    if number == 99:
        return None

    if not number.is_integer():
        raise ValueError(
            f"الصف {row_number}: قيمة {field_name} يجب أن تكون عددًا صحيحًا."
        )

    integer = int(number)

    if minimum is not None and integer < minimum:
        raise ValueError(
            f"الصف {row_number}: قيمة {field_name} أقل من {minimum}."
        )

    if maximum is not None and integer > maximum:
        raise ValueError(
            f"الصف {row_number}: قيمة {field_name} أكبر من {maximum}."
        )

    return integer


def normalize_period(value: Any) -> str:
    """تحويل صيغ الربع المختلفة إلى النص العربي المعتمد."""
    if pd.isna(value):
        raise ValueError("قيمة الفترة فارغة.")

    text = _arabic_digits_to_english(value).strip().lower()

    normalized = (
        text.replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("_", " ")
        .replace("-", " ")
    )

    normalized = " ".join(normalized.split())

    aliases = {
        "الربع الاول": "الربع الأول",
        "ربع اول": "الربع الأول",
        "q1": "الربع الأول",
        "quarter 1": "الربع الأول",
        "1": "الربع الأول",
        "الربع الثاني": "الربع الثاني",
        "ربع ثاني": "الربع الثاني",
        "q2": "الربع الثاني",
        "quarter 2": "الربع الثاني",
        "2": "الربع الثاني",
        "الربع الثالث": "الربع الثالث",
        "ربع ثالث": "الربع الثالث",
        "q3": "الربع الثالث",
        "quarter 3": "الربع الثالث",
        "3": "الربع الثالث",
        "الربع الرابع": "الربع الرابع",
        "ربع رابع": "الربع الرابع",
        "q4": "الربع الرابع",
        "quarter 4": "الربع الرابع",
        "4": "الربع الرابع",
    }

    period = aliases.get(normalized)

    if period is None:
        raise ValueError(
            f"الفترة غير معروفة: {value}. "
            "القيم المقبولة: الربع الأول، الربع الثاني، "
            "الربع الثالث، الربع الرابع، أو Q1 إلى Q4."
        )

    return period


def _period_from_date(value: Any) -> tuple[int, str]:
    if pd.isna(value):
        raise ValueError("قيمة التاريخ فارغة.")

    date_value = pd.to_datetime(value, errors="raise")
    month = int(date_value.month)

    if month <= 3:
        period = "الربع الأول"
    elif month <= 6:
        period = "الربع الثاني"
    elif month <= 9:
        period = "الربع الثالث"
    else:
        period = "الربع الرابع"

    return int(date_value.year), period


def _get_cell(row: pd.Series, column_name: str | None) -> Any:
    if not column_name:
        return None

    return row.get(column_name)


# ==================================================
# تجهيز صفوف Excel
# ==================================================

def prepare_individual_records(
    dataframe: pd.DataFrame,
    *,
    individual_id_column: str | None = None,
    date_column: str | None = None,
    year_column: str | None = None,
    period_column: str | None = None,
    fixed_year: int | None = None,
    fixed_period: str | None = None,
    gender_column: str | None = None,
    age_group_column: str | None = None,
    id_type_column: str | None = None,
    education_column: str | None = None,
    device_column: str | None = None,
    region_column: str | None = None,
    review_column: str | None = None,
    factor_columns: dict[str, str | None] | None = None,
    indicator_columns: dict[str, str | None] | None = None,
) -> list[dict[str, Any]]:
    """تحويل DataFrame إلى سجلات جاهزة للحفظ."""
    if dataframe.empty:
        raise ValueError("ملف Excel لا يحتوي على بيانات.")

    factor_columns = factor_columns or {}
    indicator_columns = indicator_columns or {}

    factor_names = {factor["name"] for factor in get_factors()}
    indicator_specs = {
        indicator["name"]: indicator
        for indicator in get_indicators()
    }

    unknown_factors = set(factor_columns) - factor_names
    if unknown_factors:
        raise ValueError(
            "العوامل التالية غير موجودة في قاعدة البيانات: "
            + "، ".join(sorted(unknown_factors))
        )

    unknown_indicators = set(indicator_columns) - set(indicator_specs)
    if unknown_indicators:
        raise ValueError(
            "المؤشرات التالية غير موجودة في قاعدة البيانات: "
            + "، ".join(sorted(unknown_indicators))
        )

    prepared_records: list[dict[str, Any]] = []
    errors: list[str] = []

    for dataframe_index, row in dataframe.iterrows():
        excel_row_number = int(dataframe_index) + 2

        try:
            existing_individual_id = _optional_integer(
                _get_cell(row, individual_id_column),
                field_name="IndividualID",
                row_number=excel_row_number,
                minimum=1,
            )

            if date_column:
                year, period = _period_from_date(
                    _get_cell(row, date_column)
                )
            else:
                if year_column:
                    year = _optional_integer(
                        _get_cell(row, year_column),
                        field_name="السنة",
                        row_number=excel_row_number,
                        minimum=1900,
                        maximum=2100,
                    )
                else:
                    year = int(fixed_year) if fixed_year is not None else None

                if period_column:
                    period = normalize_period(
                        _get_cell(row, period_column)
                    )
                else:
                    period = (
                        normalize_period(fixed_period)
                        if fixed_period
                        else None
                    )

                if year is None:
                    raise ValueError(
                        f"الصف {excel_row_number}: السنة مطلوبة."
                    )

                if period is None:
                    raise ValueError(
                        f"الصف {excel_row_number}: الفترة مطلوبة."
                    )

            factor_responses: dict[str, int] = {}

            for factor_name, column_name in factor_columns.items():
                if not column_name:
                    continue

                rating = _optional_integer(
                    _get_cell(row, column_name),
                    field_name=f"عامل {factor_name}",
                    row_number=excel_row_number,
                    minimum=1,
                    maximum=5,
                )

                if rating is not None:
                    factor_responses[factor_name] = rating

            indicator_responses: dict[str, int] = {}

            for indicator_name, column_name in indicator_columns.items():
                if not column_name:
                    continue

                spec = indicator_specs[indicator_name]

                rating = _optional_integer(
                    _get_cell(row, column_name),
                    field_name=f"مؤشر {indicator_name}",
                    row_number=excel_row_number,
                    minimum=int(spec["minimum"]),
                    maximum=int(spec["maximum"]),
                )

                if rating is not None:
                    indicator_responses[indicator_name] = rating

            prepared_records.append(
                {
                    "existing_individual_id": existing_individual_id,
                    "profile": {
                        "gender": _clean_text(_get_cell(row, gender_column)),
                        "age_group": _clean_text(_get_cell(row, age_group_column)),
                        "id_type": _clean_text(_get_cell(row, id_type_column)),
                        "education": _clean_text(_get_cell(row, education_column)),
                        "device": _clean_text(_get_cell(row, device_column)),
                        "region": _clean_text(_get_cell(row, region_column)),
                    },
                    "year": int(year),
                    "period": period,
                    "review": _clean_text(_get_cell(row, review_column)),
                    "factor_responses": factor_responses,
                    "indicator_responses": indicator_responses,
                    "source_row": excel_row_number,
                }
            )

        except ValueError as error:
            errors.append(str(error))

    if errors:
        shown_errors = errors[:20]
        remaining = len(errors) - len(shown_errors)
        message = "\n".join(shown_errors)

        if remaining > 0:
            message += f"\n... ويوجد {remaining} أخطاء إضافية."

        raise ValueError(message)

    return prepared_records


# ==================================================
# الحفظ في قاعدة البيانات
# ==================================================

def _append_review(
    old_review: str | None,
    new_review: str | None,
) -> str | None:
    if not new_review:
        return old_review

    if not old_review:
        return new_review

    if new_review.strip().lower() in old_review.strip().lower():
        return old_review

    return f"{old_review}\n{new_review}"


def _find_record(
    session,
    individual_id: int,
    year: int,
    period: str,
) -> IndividualMeasurementRecord | None:
    return session.scalar(
        select(IndividualMeasurementRecord)
        .where(
            IndividualMeasurementRecord.individual_id == individual_id,
            IndividualMeasurementRecord.year == year,
            IndividualMeasurementRecord.period == period,
        )
    )


def save_individual_records(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """حفظ سجلات الأفراد ونتائجهم داخل قاعدة بيانات الأفراد."""
    if not records:
        return {
            "ok": False,
            "errors": ["لا توجد سجلات جاهزة للحفظ."],
            "created_profiles": 0,
            "inserted_records": 0,
            "updated_records": 0,
            "saved_factor_responses": 0,
            "saved_indicator_responses": 0,
        }

    created_profiles = 0
    inserted_records = 0
    updated_records = 0
    saved_factor_responses = 0
    saved_indicator_responses = 0

    with SessionLocal() as session:
        try:
            factors = {
                factor.factor_name: factor
                for factor in session.scalars(
                    select(SharedCSATFactor)
                ).all()
            }

            indicators = {
                indicator.indicator_name: indicator
                for indicator in session.scalars(
                    select(SharedIndicator)
                ).all()
            }

            for item in records:
                existing_individual_id = item.get("existing_individual_id")
                profile_data = item.get("profile") or {}

                if existing_individual_id is not None:
                    profile = session.get(
                        IndividualProfile,
                        existing_individual_id,
                    )

                    if profile is None:
                        raise ValueError(
                            f"الصف {item.get('source_row')}: "
                            f"IndividualID {existing_individual_id} "
                            "غير موجود في قاعدة البيانات."
                        )

                    for field_name, field_value in profile_data.items():
                        if field_value is not None:
                            setattr(profile, field_name, field_value)

                else:
                    profile = IndividualProfile(
                        gender=profile_data.get("gender"),
                        age_group=profile_data.get("age_group"),
                        id_type=profile_data.get("id_type"),
                        education=profile_data.get("education"),
                        device=profile_data.get("device"),
                        region=profile_data.get("region"),
                    )

                    session.add(profile)
                    session.flush()
                    created_profiles += 1

                record = _find_record(
                    session,
                    profile.individual_id,
                    int(item["year"]),
                    item["period"],
                )

                if record is None:
                    record = IndividualMeasurementRecord(
                        individual_id=profile.individual_id,
                        year=int(item["year"]),
                        period=item["period"],
                        review=item.get("review"),
                    )

                    session.add(record)
                    session.flush()
                    inserted_records += 1
                else:
                    record.review = _append_review(
                        record.review,
                        item.get("review"),
                    )
                    updated_records += 1

                for factor_name, rating_value in (
                    item.get("factor_responses") or {}
                ).items():
                    factor = factors.get(factor_name)

                    if factor is None:
                        raise ValueError(
                            f"عامل CSAT غير موجود: {factor_name}"
                        )

                    response = session.scalar(
                        select(IndividualFactorResponse)
                        .where(
                            IndividualFactorResponse.record_id == record.record_id,
                            IndividualFactorResponse.factor_id == factor.factor_id,
                        )
                    )

                    if response is None:
                        response = IndividualFactorResponse(
                            record_id=record.record_id,
                            factor_id=factor.factor_id,
                            rating_value=int(rating_value),
                        )
                        session.add(response)
                    else:
                        response.rating_value = int(rating_value)

                    saved_factor_responses += 1

                for indicator_name, rating_value in (
                    item.get("indicator_responses") or {}
                ).items():
                    indicator = indicators.get(indicator_name)

                    if indicator is None:
                        raise ValueError(
                            f"المؤشر غير موجود: {indicator_name}"
                        )

                    response = session.scalar(
                        select(IndividualIndicatorResponse)
                        .where(
                            IndividualIndicatorResponse.record_id == record.record_id,
                            IndividualIndicatorResponse.indicator_id == indicator.indicator_id,
                        )
                    )

                    if response is None:
                        response = IndividualIndicatorResponse(
                            record_id=record.record_id,
                            indicator_id=indicator.indicator_id,
                            rating_value=int(rating_value),
                        )
                        session.add(response)
                    else:
                        response.rating_value = int(rating_value)

                    saved_indicator_responses += 1

            session.commit()

            return {
                "ok": True,
                "errors": [],
                "created_profiles": created_profiles,
                "inserted_records": inserted_records,
                "updated_records": updated_records,
                "saved_factor_responses": saved_factor_responses,
                "saved_indicator_responses": saved_indicator_responses,
            }

        except Exception as error:
            session.rollback()

            return {
                "ok": False,
                "errors": [f"تعذر حفظ بيانات الأفراد: {error}"],
                "created_profiles": 0,
                "inserted_records": 0,
                "updated_records": 0,
                "saved_factor_responses": 0,
                "saved_indicator_responses": 0,
            }
