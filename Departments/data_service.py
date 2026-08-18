from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
import streamlit as st
from sqlalchemy import select

from calculations import (
    calculate_ces,
    calculate_csat,
    calculate_nps,
)
from database.connection import SessionLocal
from database.models import (
    Factor,
    FactorResult,
    GovernmentEntity,
    Indicator,
    IndicatorResult,
    MeasurementRecord,
    Section,
    Service,
)


RAW_DATA = "raw"
CALCULATED_DATA = "calculated"


def _decimal_to_float(value):
    """Convert Decimal to float while preserving None."""
    return None if value is None else float(value)


@st.cache_data(ttl=300, show_spinner="جاري تحميل البيانات...")
def fetch_records_from_db():
    """
    Return measurement records with indicator and factor results.

    The entity is returned as descriptive metadata, but indicator values
    are the values already stored for the service record.
    """

    with SessionLocal() as session:
        rows = session.execute(
            select(
                MeasurementRecord,
                Service,
                Section,
                GovernmentEntity,
            )
            .join(
                Service,
                MeasurementRecord.service_id
                == Service.service_id,
            )
            .join(
                Section,
                Service.section_id
                == Section.section_id,
            )
            .join(
                GovernmentEntity,
                Section.entity_id
                == GovernmentEntity.entity_id,
            )
            .order_by(
                MeasurementRecord.record_id.desc()
            )
        ).all()

        indicator_results_by_record = {}

        for result, indicator in session.execute(
            select(
                IndicatorResult,
                Indicator,
            )
            .join(
                Indicator,
                IndicatorResult.indicator_id
                == Indicator.indicator_id,
            )
        ).all():
            indicator_results_by_record.setdefault(
                result.record_id,
                [],
            ).append(
                (result, indicator)
            )

        factor_results_by_record = {}

        for result, factor in session.execute(
            select(
                FactorResult,
                Factor,
            )
            .join(
                Factor,
                FactorResult.factor_id
                == Factor.factor_id,
            )
            .order_by(
                Factor.display_order
            )
        ).all():
            factor_results_by_record.setdefault(
                result.record_id,
                [],
            ).append(
                (result, factor)
            )

        output = []

        for (
            record,
            service,
            section,
            entity,
        ) in rows:

            row = {
                "record_id": record.record_id,
                "entity": entity.entity_name,
                "section": section.section_name,

                # Kept for compatibility with existing pages.
                "department": section.section_name,

                "service": service.service_name,
                "year": record.year,
                "period": record.period,
                "participants": record.participants_count,
                "review": record.review,
                "status": "معتمد",
                "factors": {},
            }

            for (
                result,
                indicator,
            ) in indicator_results_by_record.get(
                record.record_id,
                [],
            ):
                code = (
                    indicator.indicator_name.lower()
                )

                row[
                    f"{code}_prev"
                ] = _decimal_to_float(
                    result.prev_value
                )

                row[
                    f"{code}_current"
                ] = _decimal_to_float(
                    result.current_value
                )

                row[
                    f"{code}_target"
                ] = _decimal_to_float(
                    result.target_value
                )

            for (
                result,
                factor,
            ) in factor_results_by_record.get(
                record.record_id,
                [],
            ):
                row["factors"][
                    factor.factor_name
                ] = {
                    "participants_count":
                        result.participants_count,

                    "previous_value":
                        _decimal_to_float(
                            result.prev_value
                        ),

                    "current_value":
                        _decimal_to_float(
                            result.current_value
                        ),

                    "target_value":
                        _decimal_to_float(
                            result.target_value
                        ),
                }

            output.append(row)

        return output


# ==================================================
# Basic helpers
# ==================================================

def _clean_text(value):
    """Convert a value to clean text."""
    if pd.isna(value):
        return ""

    return str(value).strip()


def _period_code(value):
    """Convert a period value to the approved Arabic half-year name."""
    if pd.isna(value):
        return None

    cleaned = (
        str(value)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )

    first_half = {
        "h1",
        "1",
        "1.0",
        "النصف الأول",
        "النصف الاول",
        "الفترة الأولى",
        "الفتره الاولى",
    }

    second_half = {
        "h2",
        "2",
        "2.0",
        "النصف الثاني",
        "الفترة الثانية",
        "الفتره الثانيه",
    }

    if cleaned in first_half:
        return "النصف الأول"

    if cleaned in second_half:
        return "النصف الثاني"

    return None


def _period_from_month(month):
    """Convert month number to first or second half."""
    return (
        "النصف الأول"
        if int(month) <= 6
        else "النصف الثاني"
    )


def _read_numeric_value(value):
    """Read a numeric value such as 35, -20, or 85%."""
    if pd.isna(value):
        return None

    cleaned = (
        str(value)
        .strip()
        .replace("%", "")
        .replace(",", "")
    )

    if not cleaned:
        return None

    try:
        return round(
            float(cleaned),
            2,
        )

    except ValueError as error:
        raise ValueError(
            f"القيمة ليست رقمية: {value}"
        ) from error


def _read_percentage_value(value):
    """Read a percentage between 0 and 100."""
    number = _read_numeric_value(
        value
    )

    if number is None:
        return None

    if 0 <= number <= 1:
        number *= 100

    if not 0 <= number <= 100:
        raise ValueError(
            "النسبة يجب أن تكون بين 0 و100: "
            f"{number}"
        )

    return round(
        number,
        2,
    )


def _read_net_score_value(
    value,
    field_name,
):
    """Read CES/NPS value between -100 and 100."""
    number = _read_numeric_value(
        value
    )

    if number is None:
        return None

    if not -100 <= number <= 100:
        raise ValueError(
            f"قيمة {field_name} يجب أن تكون "
            f"بين -100 و100: {number}"
        )

    return round(
        number,
        2,
    )


def _single_group_value(
    group,
    column_name,
    reader,
    field_name,
):
    """
    Read one unique calculated value from a service group.

    Repeated copies of the same value are allowed.
    Different values for the same service/year/period are rejected.
    """
    if not column_name:
        return None

    values = []

    for value in group[
        column_name
    ]:
        parsed_value = reader(
            value
        )

        if parsed_value is not None:
            values.append(
                parsed_value
            )

    unique_values = list(
        dict.fromkeys(values)
    )

    if not unique_values:
        return None

    if len(unique_values) > 1:
        raise ValueError(
            f"يوجد أكثر من قيمة لـ {field_name} "
            "لنفس الخدمة والسنة والفترة."
        )

    return unique_values[0]


def _average_question_scores(
    group,
    columns,
    calculation_function,
    minimum,
    maximum,
):
    """
    Calculate the indicator for each selected question,
    then average the question scores.
    """
    scores = []

    for column_name in columns:
        numeric_answers = pd.to_numeric(
            group[column_name],
            errors="coerce",
        )

        valid_answers = numeric_answers[
            numeric_answers.between(
                minimum,
                maximum,
            )
        ]

        score = calculation_function(
            valid_answers
        )

        if score is not None:
            scores.append(
                score
            )

    if not scores:
        return None

    return round(
        sum(scores) / len(scores),
        2,
    )


def _collect_comments(
    group,
    comment_columns,
):
    """Collect comments while removing blank and duplicate values."""
    ignored_comments = {
        "",
        "لا يوجد تعليق",
        "لا يوجد تعليق.",
        "لا توجد ملاحظات",
        "لا توجد ملاحظة",
        "nan",
        "none",
        "null",
    }

    comments = []
    existing_comments = set()

    for column_name in comment_columns:
        for value in group[
            column_name
        ]:
            if pd.isna(value):
                continue

            comment = str(
                value
            ).strip()

            normalized = (
                comment.lower()
            )

            if (
                normalized
                in ignored_comments
            ):
                continue

            if (
                normalized
                in existing_comments
            ):
                continue

            existing_comments.add(
                normalized
            )

            comments.append(
                comment
            )

    if not comments:
        return None

    return "\n".join(
        comments
    )


# ==================================================
# Factors
# ==================================================

def _load_fixed_factor_names():
    """Load the seven fixed CSAT factors in display order."""
    with SessionLocal() as session:
        factors = (
            session.query(Factor)
            .order_by(
                Factor.display_order
            )
            .all()
        )

        names = [
            factor.factor_name
            for factor in factors
        ]

    if not names:
        raise ValueError(
            "جدول Factors فارغ. "
            "شغلي seed_data.py أولًا."
        )

    if len(names) != 7:
        raise ValueError(
            "يجب أن يحتوي جدول Factors "
            "على سبعة عوامل بالضبط، "
            f"لكن الموجود حاليًا: {len(names)}."
        )

    return names


def _resolve_factor_mapping(
    selected,
    available_columns,
    field_name,
):
    """
    Convert factor selections to:
        {fixed factor name: Excel column name}
    """
    factor_names = (
        _load_fixed_factor_names()
    )

    if isinstance(
        selected,
        Mapping,
    ):
        mapping = {
            str(
                factor_name
            ).strip():
            str(
                column_name
            ).strip()

            for (
                factor_name,
                column_name,
            ) in selected.items()

            if column_name
        }

        missing_factors = [
            name
            for name in factor_names
            if name not in mapping
        ]

        extra_factors = [
            name
            for name in mapping
            if name not in factor_names
        ]

        if missing_factors:
            raise ValueError(
                f"{field_name}: "
                "لم يتم ربط العوامل التالية: "
                + "، ".join(
                    missing_factors
                )
            )

        if extra_factors:
            raise ValueError(
                f"{field_name}: "
                "توجد عوامل غير معتمدة: "
                + "، ".join(
                    extra_factors
                )
            )

        ordered_mapping = {
            name: mapping[name]
            for name in factor_names
        }

    else:
        columns = list(
            selected or []
        )

        if (
            len(columns)
            != len(factor_names)
        ):
            raise ValueError(
                f"{field_name}: "
                "يجب اختيار سبعة أعمدة بالضبط."
            )

        ordered_mapping = dict(
            zip(
                factor_names,
                columns,
                strict=True,
            )
        )

    selected_columns = list(
        ordered_mapping.values()
    )

    if (
        len(selected_columns)
        != len(
            set(selected_columns)
        )
    ):
        raise ValueError(
            f"{field_name}: "
            "لا يمكن ربط العمود نفسه "
            "بأكثر من عامل."
        )

    missing_columns = [
        column_name
        for column_name
        in selected_columns
        if column_name
        not in available_columns
    ]

    if missing_columns:
        raise ValueError(
            f"{field_name}: "
            "الأعمدة التالية غير موجودة "
            "في الملف: "
            + "، ".join(
                missing_columns
            )
        )

    return ordered_mapping


def _calculate_raw_factor_results(
    group,
    factor_mapping,
):
    """
    Calculate CSAT for each factor at SERVICE level.

    Valid responses are 1..5 only.
    99, NaN, blank, and any value outside 1..5 are excluded.
    """
    results = {}

    for (
        factor_name,
        column_name,
    ) in factor_mapping.items():

        numeric_answers = pd.to_numeric(
            group[column_name],
            errors="coerce",
        )

        valid_answers = numeric_answers[
            numeric_answers.between(
                1,
                5,
            )
        ]

        results[
            factor_name
        ] = {
            "current_value":
                calculate_csat(
                    valid_answers
                ),

            "participants_count":
                int(
                    valid_answers.count()
                ),
        }

    return results


def _read_calculated_factor_results(
    group,
    factor_mapping,
):
    """Read pre-calculated factor results for one service group."""
    results = {}

    for (
        factor_name,
        column_name,
    ) in factor_mapping.items():

        value = _single_group_value(
            group=group,
            column_name=column_name,
            reader=_read_percentage_value,
            field_name=(
                f"عامل {factor_name}"
            ),
        )

        results[
            factor_name
        ] = {
            "current_value": value,
            "participants_count": None,
        }

    return results


def _calculate_overall_csat(
    factor_results,
):
    """Overall CSAT = average of available factor CSAT scores."""
    values = [
        item["current_value"]
        for item
        in factor_results.values()
        if item["current_value"]
        is not None
    ]

    if not values:
        return None

    return round(
        sum(values)
        / len(values),
        2,
    )


# ==================================================
# Service-level calculations
# ==================================================

def _participants_for_group(
    group,
    *,
    data_mode,
    response_id_column,
    participants_column,
):
    """
    Get participant count for one service/year/period group.
    """
    if (
        data_mode
        == CALCULATED_DATA
        and participants_column
    ):
        participants = (
            _single_group_value(
                group=group,
                column_name=participants_column,
                reader=_read_numeric_value,
                field_name="عدد المشاركين",
            )
        )

        return (
            0
            if participants is None
            else int(participants)
        )

    if response_id_column:
        return int(
            group[
                response_id_column
            ]
            .dropna()
            .nunique()
        )

    return int(
        len(group)
    )


def _calculate_service_metrics(
    group,
    *,
    data_mode,
    factor_mapping,
    ces_columns,
    nps_column,
    calculated_ces_column,
    calculated_nps_column,
    calculated_bps_column,
):
    """
    Calculate all KPI values from ALL responses of one service
    for one year and one period.

    IMPORTANT:
    Entity and section DO NOT split the indicator calculation.
    They are only kept later as descriptive/storage dimensions.
    """

    if (
        data_mode
        == RAW_DATA
    ):
        factor_results = (
            _calculate_raw_factor_results(
                group=group,
                factor_mapping=factor_mapping,
            )
        )

        ces_value = (
            _average_question_scores(
                group=group,
                columns=ces_columns,
                calculation_function=calculate_ces,
                minimum=1,
                maximum=5,
            )
        )

        nps_value = None

        if nps_column:
            numeric_nps = pd.to_numeric(
                group[nps_column],
                errors="coerce",
            )

            valid_nps = numeric_nps[
                numeric_nps.between(
                    0,
                    10,
                )
            ]

            nps_value = calculate_nps(
                valid_nps
            )

        bps_value = None

    else:
        factor_results = (
            _read_calculated_factor_results(
                group=group,
                factor_mapping=factor_mapping,
            )
        )

        ces_value = (
            _single_group_value(
                group=group,
                column_name=calculated_ces_column,
                reader=lambda value:
                    _read_net_score_value(
                        value,
                        "CES",
                    ),
                field_name="CES",
            )
        )

        nps_value = (
            _single_group_value(
                group=group,
                column_name=calculated_nps_column,
                reader=lambda value:
                    _read_net_score_value(
                        value,
                        "NPS",
                    ),
                field_name="NPS",
            )
        )

        bps_value = (
            _single_group_value(
                group=group,
                column_name=calculated_bps_column,
                reader=_read_percentage_value,
                field_name="BPS",
            )
        )

    overall_csat = (
        _calculate_overall_csat(
            factor_results
        )
    )

    return {
        "factors":
            factor_results,

        "indicators": {
            "CSAT":
                overall_csat,

            "CES":
                ces_value,

            "NPS":
                nps_value,

            "BPS":
                bps_value,
        },
    }


# ==================================================
# Upload preparation
# ==================================================

def prepare_uploaded_records(
    dataframe,
    data_mode,
    entity_column,
    service_column,
    section_column=None,
    fixed_section=None,
    response_id_column=None,
    date_column=None,
    year_column=None,
    period_column=None,
    fixed_year=None,
    fixed_period=None,
    factor_columns=None,
    factor_column_mapping=None,
    ces_columns=None,
    nps_column=None,
    calculated_factor_columns=None,
    calculated_factor_column_mapping=None,
    calculated_ces_column=None,
    calculated_nps_column=None,
    calculated_bps_column=None,
    participants_column=None,
    comment_columns=None,
):
    """
    Prepare an uploaded Excel file for saving.

    CRITICAL CALCULATION RULE:
    --------------------------
    KPI values are calculated at SERVICE level.

    Calculation grouping:
        service + year + period

    NOT:
        entity + section + service + year + period

    Entity and section are still preserved so the existing database
    hierarchy and entity pages can keep working, but they do NOT split
    the raw responses before CSAT/CES/NPS are calculated.
    """

    ces_columns = (
        ces_columns or []
    )

    comment_columns = (
        comment_columns or []
    )

    data = dataframe.copy()

    available_columns = (
        data.columns.tolist()
    )

    # ==================================================
    # Entity
    # ==================================================

    if (
        not entity_column
        or entity_column
        not in available_columns
    ):
        raise ValueError(
            "عمود الجهة الحكومية غير موجود في الملف: "
            f"{entity_column}"
        )

    data["_entity"] = (
        data[entity_column]
        .apply(
            _clean_text
        )
    )

    if (
        data["_entity"]
        == ""
    ).any():
        raise ValueError(
            "يوجد صف بدون اسم جهة حكومية."
        )

    # ==================================================
    # Service
    # ==================================================

    if (
        not service_column
        or service_column
        not in available_columns
    ):
        raise ValueError(
            "عمود الخدمة غير موجود في الملف: "
            f"{service_column}"
        )

    data["_service"] = (
        data[service_column]
        .apply(
            _clean_text
        )
    )

    if (
        data["_service"]
        == ""
    ).any():
        raise ValueError(
            "يوجد صف بدون اسم خدمة."
        )

    # ==================================================
    # Section
    # ==================================================

    if section_column:
        if (
            section_column
            not in available_columns
        ):
            raise ValueError(
                "عمود القسم غير موجود في الملف: "
                f"{section_column}"
            )

        data["_section"] = (
            data[section_column]
            .apply(
                _clean_text
            )
        )

        if (
            data["_section"]
            == ""
        ).any():
            raise ValueError(
                "يوجد صف بدون اسم قسم."
            )

    elif fixed_section:
        clean_fixed_section = str(
            fixed_section
        ).strip()

        if not clean_fixed_section:
            raise ValueError(
                "اسم القسم الثابت فارغ."
            )

        data["_section"] = (
            clean_fixed_section
        )

    else:
        raise ValueError(
            "يجب اختيار عمود القسم "
            "أو تحديد اسم قسم ثابت."
        )

    # ==================================================
    # Year and period
    # ==================================================

    if date_column:
        if (
            date_column
            not in available_columns
        ):
            raise ValueError(
                "عمود التاريخ غير موجود في الملف: "
                f"{date_column}"
            )

        parsed_dates = pd.to_datetime(
            data[date_column],
            errors="coerce",
            dayfirst=True,
        )

        if (
            parsed_dates
            .isna()
            .any()
        ):
            raise ValueError(
                "يوجد تاريخ غير صحيح في الملف."
            )

        data["_year"] = (
            parsed_dates.dt.year
        )

        data["_period"] = (
            parsed_dates
            .dt
            .month
            .apply(
                _period_from_month
            )
        )

    elif (
        year_column
        and period_column
    ):
        if (
            year_column
            not in available_columns
        ):
            raise ValueError(
                "عمود السنة غير موجود في الملف: "
                f"{year_column}"
            )

        if (
            period_column
            not in available_columns
        ):
            raise ValueError(
                "عمود الفترة غير موجود في الملف: "
                f"{period_column}"
            )

        data["_year"] = pd.to_numeric(
            data[year_column],
            errors="coerce",
        )

        data["_period"] = (
            data[period_column]
            .apply(
                _period_code
            )
        )

        if (
            data["_year"]
            .isna()
            .any()
        ):
            raise ValueError(
                "يوجد عام غير صحيح في الملف."
            )

        if (
            data["_period"]
            .isna()
            .any()
        ):
            raise ValueError(
                "يوجد اسم فترة غير معروف في الملف."
            )

    elif (
        fixed_year is not None
        and fixed_period
    ):
        data["_year"] = int(
            fixed_year
        )

        period = _period_code(
            fixed_period
        )

        if period is None:
            raise ValueError(
                "الفترة الثابتة غير صحيحة."
            )

        data["_period"] = (
            period
        )

    else:
        raise ValueError(
            "يجب تحديد التاريخ، "
            "أو عمودي السنة والفترة، "
            "أو سنة وفترة ثابتة."
        )

    # ==================================================
    # Factor mapping
    # ==================================================

    if data_mode == RAW_DATA:
        selected_factors = (
            factor_column_mapping
            if factor_column_mapping
            is not None
            else factor_columns
        )

        factor_mapping = (
            _resolve_factor_mapping(
                selected=selected_factors,
                available_columns=available_columns,
                field_name="عوامل CSAT",
            )
        )

    elif (
        data_mode
        == CALCULATED_DATA
    ):
        selected_factors = (
            calculated_factor_column_mapping
            if calculated_factor_column_mapping
            is not None
            else calculated_factor_columns
        )

        factor_mapping = (
            _resolve_factor_mapping(
                selected=selected_factors,
                available_columns=available_columns,
                field_name="نتائج عوامل CSAT",
            )
        )

    else:
        raise ValueError(
            "نوع بيانات المؤشرات غير معروف."
        )

    # ==================================================
    # Validate optional columns
    # ==================================================

    optional_columns = [
        response_id_column,
        participants_column,
        nps_column,
        calculated_ces_column,
        calculated_nps_column,
        calculated_bps_column,
        *ces_columns,
        *comment_columns,
    ]

    missing_optional_columns = [
        column_name
        for column_name
        in optional_columns
        if (
            column_name
            and column_name
            not in available_columns
        )
    ]

    if missing_optional_columns:
        raise ValueError(
            "الأعمدة التالية غير موجودة في الملف: "
            + "، ".join(
                sorted(
                    set(
                        missing_optional_columns
                    )
                )
            )
        )

    # ==================================================
    # STEP 1:
    # Calculate KPI values at SERVICE level only.
    #
    # The entity and section are intentionally NOT included here.
    # ==================================================

    service_groups = data.groupby(
        [
            "_service",
            "_year",
            "_period",
        ],
        dropna=False,
        sort=True,
    )

    service_metrics = {}

    for (
        service,
        year,
        period,
    ), service_group in service_groups:

        metrics = _calculate_service_metrics(
            service_group,
            data_mode=data_mode,
            factor_mapping=factor_mapping,
            ces_columns=ces_columns,
            nps_column=nps_column,
            calculated_ces_column=calculated_ces_column,
            calculated_nps_column=calculated_nps_column,
            calculated_bps_column=calculated_bps_column,
        )

        service_metrics[
            (
                str(service).strip(),
                int(year),
                period,
            )
        ] = metrics

    # ==================================================
    # STEP 2:
    # Preserve entity/section/service combinations for the DB.
    #
    # Every entity-specific DB record receives the SAME service-level
    # KPI result calculated in STEP 1 for that service/year/period.
    # ==================================================

    storage_groups = data.groupby(
        [
            "_entity",
            "_section",
            "_service",
            "_year",
            "_period",
        ],
        dropna=False,
        sort=True,
    )

    prepared_records = []

    for (
        entity,
        section,
        service,
        year,
        period,
    ), entity_group in storage_groups:

        service_key = (
            str(service).strip(),
            int(year),
            period,
        )

        metrics = (
            service_metrics[
                service_key
            ]
        )

        # Keep the record-level participant count specific to this
        # entity/section/service group. This is descriptive only;
        # KPI calculation was already completed at service level above.
        participants = _participants_for_group(
            entity_group,
            data_mode=data_mode,
            response_id_column=response_id_column,
            participants_column=participants_column,
        )

        # Keep comments specific to the entity group.
        review = _collect_comments(
            group=entity_group,
            comment_columns=comment_columns,
        )

        # Copy nested structures so records do not share mutable dicts.
        factor_results = {
            factor_name: {
                "current_value":
                    factor_data.get(
                        "current_value"
                    ),

                "participants_count":
                    factor_data.get(
                        "participants_count"
                    ),
            }
            for (
                factor_name,
                factor_data,
            ) in metrics[
                "factors"
            ].items()
        }

        indicators = dict(
            metrics[
                "indicators"
            ]
        )

        prepared_records.append(
            {
                "entity":
                    str(
                        entity
                    ).strip(),

                "section":
                    str(
                        section
                    ).strip(),

                # Kept for compatibility with older pages.
                "department":
                    str(
                        section
                    ).strip(),

                "service":
                    str(
                        service
                    ).strip(),

                "year":
                    int(
                        year
                    ),

                "period":
                    period,

                "participants":
                    participants,

                "review":
                    review,

                "factors":
                    factor_results,

                "indicators":
                    indicators,
            }
        )

    return prepared_records
