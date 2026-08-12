from decimal import Decimal

from sqlalchemy import select

from database.connection import SessionLocal
from database.models import (
    Indicator,
    IndicatorResult,
    MeasurementRecord,
)


# validate that the result values are within the indicator's min and max range.
def validate_result_values(
    indicator: Indicator,
    prev_value: Decimal | None,
    current_value: Decimal,
    target_value: Decimal,
) -> None:
    values = {
        "Previous value": prev_value,
        "Current value": current_value,
        "Target value": target_value,
    }

    for value_name, value in values.items():
        if value is None:
            continue

        if value < indicator.min_value:
            raise ValueError(
                f"{value_name} cannot be less than "
                f"{indicator.min_value}."
            )

        if value > indicator.max_value:
            raise ValueError(
                f"{value_name} cannot be greater than "
                f"{indicator.max_value}."
            )

# create a new indicator result in the database and return the created IndicatorResult object.
def create_indicator_result(
    record_id: int,
    indicator_id: int,
    prev_value: Decimal | None,
    current_value: Decimal,
    target_value: Decimal,
) -> IndicatorResult:
    with SessionLocal() as session:
        record = session.get(
            MeasurementRecord,
            record_id,
        )

        if record is None:
            raise ValueError(
                "Measurement record was not found."
            )

        indicator = session.get(
            Indicator,
            indicator_id,
        )

        if indicator is None:
            raise ValueError(
                "Indicator was not found."
            )

        statement = select(IndicatorResult).where(
            IndicatorResult.record_id == record_id,
            IndicatorResult.indicator_id == indicator_id,
        )

        existing_result = session.scalar(statement)

        if existing_result is not None:
            raise ValueError(
                "A result for this record and indicator "
                "already exists."
            )

        validate_result_values(
            indicator=indicator,
            prev_value=prev_value,
            current_value=current_value,
            target_value=target_value,
        )

        result = IndicatorResult(
            record_id=record_id,
            indicator_id=indicator_id,
            prev_value=prev_value,
            current_value=current_value,
            target_value=target_value,
        )

        session.add(result)
        session.commit()
        session.refresh(result)

        return result

# get an indicator result by its ID. Returns None if not found.
def get_indicator_result(
    result_id: int,
) -> IndicatorResult | None:
    with SessionLocal() as session:
        result = session.get(
            IndicatorResult,
            result_id,
        )

        return result

# get all indicator results. Returns a list of IndicatorResult objects.
def get_all_indicator_results() -> list[IndicatorResult]:
    with SessionLocal() as session:
        statement = select(IndicatorResult).order_by(
            IndicatorResult.record_id,
            IndicatorResult.indicator_id,
        )

        results = session.scalars(statement).all()

        return list(results)

# get all indicator results for a specific measurement record. Returns a list of IndicatorResult objects.
def get_results_by_record(
    record_id: int,
) -> list[IndicatorResult]:
    with SessionLocal() as session:
        statement = (
            select(IndicatorResult)
            .where(
                IndicatorResult.record_id == record_id
            )
            .order_by(
                IndicatorResult.indicator_id
            )
        )

        results = session.scalars(statement).all()

        return list(results)

# get all indicator results for a specific indicator. Returns a list of IndicatorResult objects.
def get_results_by_indicator(
    indicator_id: int,
) -> list[IndicatorResult]:
    with SessionLocal() as session:
        statement = (
            select(IndicatorResult)
            .where(
                IndicatorResult.indicator_id == indicator_id
            )
            .order_by(
                IndicatorResult.record_id
            )
        )

        results = session.scalars(statement).all()

        return list(results)

# get an indicator result by its measurement record ID and indicator ID. Returns None if not found.
def get_result_by_record_and_indicator(
    record_id: int,
    indicator_id: int,
) -> IndicatorResult | None:
    with SessionLocal() as session:
        statement = select(IndicatorResult).where(
            IndicatorResult.record_id == record_id,
            IndicatorResult.indicator_id == indicator_id,
        )

        result = session.scalar(statement)

        return result

# update an existing indicator result in the database and return the updated IndicatorResult object. Returns None if the result was not found.
def update_indicator_result(
    result_id: int,
    record_id: int,
    indicator_id: int,
    prev_value: Decimal | None,
    current_value: Decimal,
    target_value: Decimal,
) -> IndicatorResult | None:
    with SessionLocal() as session:
        result = session.get(
            IndicatorResult,
            result_id,
        )

        if result is None:
            return None

        record = session.get(
            MeasurementRecord,
            record_id,
        )

        if record is None:
            raise ValueError(
                "Measurement record was not found."
            )

        indicator = session.get(
            Indicator,
            indicator_id,
        )

        if indicator is None:
            raise ValueError(
                "Indicator was not found."
            )

        statement = select(IndicatorResult).where(
            IndicatorResult.record_id == record_id,
            IndicatorResult.indicator_id == indicator_id,
            IndicatorResult.result_id != result_id,
        )

        existing_result = session.scalar(statement)

        if existing_result is not None:
            raise ValueError(
                "A result for this record and indicator "
                "already exists."
            )

        validate_result_values(
            indicator=indicator,
            prev_value=prev_value,
            current_value=current_value,
            target_value=target_value,
        )

        result.record_id = record_id
        result.indicator_id = indicator_id
        result.prev_value = prev_value
        result.current_value = current_value
        result.target_value = target_value

        session.commit()
        session.refresh(result)

        return result

# delete an indicator result by its ID. Returns True if deleted, False if not found.
def delete_indicator_result(
    result_id: int,
) -> bool:
    with SessionLocal() as session:
        result = session.get(
            IndicatorResult,
            result_id,
        )

        if result is None:
            return False

        session.delete(result)
        session.commit()

        return True