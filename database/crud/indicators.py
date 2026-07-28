from decimal import Decimal

from sqlalchemy import select

from database.connection import SessionLocal
from database.models import Indicator


DEFAULT_INDICATORS = [
    {
        "indicator_name": "CSAT",
        "unit": "%",
        "min_value": Decimal("0"),
        "max_value": Decimal("100"),
    },
    {
        "indicator_name": "CES",
        "unit": "Point",
        "min_value": Decimal("-100"),
        "max_value": Decimal("100"),
    },
    {
        "indicator_name": "NPS",
        "unit": "Point",
        "min_value": Decimal("-100"),
        "max_value": Decimal("100"),
    },
]

def create_default_indicators() -> None:
    with SessionLocal() as session:
        for indicator_data in DEFAULT_INDICATORS:
            statement = select(Indicator).where(
                Indicator.indicator_name
                == indicator_data["indicator_name"]
            )

            existing_indicator = session.scalar(statement)

            if existing_indicator is None:
                indicator = Indicator(**indicator_data)
                session.add(indicator)

        session.commit()


from decimal import Decimal

from sqlalchemy import select

from database.connection import SessionLocal
from database.models import Indicator


def create_indicator(
    indicator_name: str,
    unit: str,
    min_value: Decimal,
    max_value: Decimal,
) -> Indicator:
    indicator_name = indicator_name.strip()
    unit = unit.strip()

    if not indicator_name:
        raise ValueError("Indicator name cannot be empty.")

    if not unit:
        raise ValueError("Indicator unit cannot be empty.")

    if min_value > max_value:
        raise ValueError(
            "Minimum value cannot be greater than maximum value."
        )

    with SessionLocal() as session:
        statement = select(Indicator).where(
            Indicator.indicator_name == indicator_name
        )

        existing_indicator = session.scalar(statement)

        if existing_indicator is not None:
            raise ValueError(
                "An indicator with this name already exists."
            )

        indicator = Indicator(
            indicator_name=indicator_name,
            unit=unit,
            min_value=min_value,
            max_value=max_value,
        )

        session.add(indicator)
        session.commit()
        session.refresh(indicator)

        return indicator


def get_indicator(
    indicator_id: int,
) -> Indicator | None:
    with SessionLocal() as session:
        indicator = session.get(
            Indicator,
            indicator_id,
        )

        return indicator    


def get_all_indicators() -> list[Indicator]:
    with SessionLocal() as session:
        statement = select(Indicator).order_by(
            Indicator.indicator_name
        )

        indicators = session.scalars(statement).all()

        return list(indicators)



def update_indicator(
    indicator_id: int,
    new_name: str,
    new_unit: str,
    new_min_value: Decimal,
    new_max_value: Decimal,
) -> Indicator | None:
    new_name = new_name.strip()
    new_unit = new_unit.strip()

    if not new_name:
        raise ValueError("Indicator name cannot be empty.")

    if not new_unit:
        raise ValueError("Indicator unit cannot be empty.")

    if new_min_value > new_max_value:
        raise ValueError(
            "Minimum value cannot be greater than maximum value."
        )

    with SessionLocal() as session:
        indicator = session.get(
            Indicator,
            indicator_id,
        )

        if indicator is None:
            return None

        statement = select(Indicator).where(
            Indicator.indicator_name == new_name,
            Indicator.indicator_id != indicator_id,
        )

        existing_indicator = session.scalar(statement)

        if existing_indicator is not None:
            raise ValueError(
                "An indicator with this name already exists."
            )

        indicator.indicator_name = new_name
        indicator.unit = new_unit
        indicator.min_value = new_min_value
        indicator.max_value = new_max_value

        session.commit()
        session.refresh(indicator)

        return indicator


def delete_indicator(indicator_id: int) -> bool:
    with SessionLocal() as session:
        indicator = session.get(
            Indicator,
            indicator_id,
        )

        if indicator is None:
            return False

        if indicator.results:
            raise ValueError(
                "Cannot delete an indicator that has results."
            )

        session.delete(indicator)
        session.commit()

        return True    