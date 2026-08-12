from sqlalchemy import select

from database.connection import SessionLocal
from database.models import MeasurementRecord, Service


# create a new measurement record in the database and return the created MeasurementRecord object.
def create_measurement_record(
    service_id: int,
    year: int,
    period: str,
    participants_count: int,
    review: str | None = None,
) -> MeasurementRecord:
    period = period.strip()

    if not period:
        raise ValueError("Period cannot be empty.")

    if year < 2000:
        raise ValueError("Year is not valid.")

    if participants_count < 0:
        raise ValueError(
            "Participants count cannot be negative."
        )

    if review is not None:
        review = review.strip()

        if not review:
            review = None

    with SessionLocal() as session:
        service = session.get(
            Service,
            service_id,
        )

        if service is None:
            raise ValueError("Service was not found.")

        record = MeasurementRecord(
            service_id=service_id,
            year=year,
            period=period,
            participants_count=participants_count,
            review=review,
        )

        session.add(record)
        session.commit()
        session.refresh(record)

        return record

# get a measurement record by its ID. Returns None if not found.
def get_measurement_record(
        record_id: int,
) -> MeasurementRecord | None:

    with SessionLocal() as session:
        record = session.get(
            MeasurementRecord,
            record_id,
        )

        return record    

# get all measurement records ordered by year and period. Returns a list of MeasurementRecord objects.
def get_all_measurement_records() -> list[MeasurementRecord]:
    with SessionLocal() as session:
        statement = select(MeasurementRecord).order_by(
            MeasurementRecord.year,
            MeasurementRecord.period,
        )

        records = session.scalars(statement).all()

        return list(records)

# get measurement records by service ID. Returns a list of MeasurementRecord objects.
def get_records_by_service(
    service_id: int,
) -> list[MeasurementRecord]:
    with SessionLocal() as session:
        statement = (
            select(MeasurementRecord)
            .where(
                MeasurementRecord.service_id == service_id
            )
            .order_by(
                MeasurementRecord.year,
                MeasurementRecord.period,
            )
        )

        records = session.scalars(statement).all()

        return list(records)


# get measurement records by year. Returns a list of MeasurementRecord objects.
def get_records_by_year(
    year: int,
) -> list[MeasurementRecord]:
    if year < 2000:
        raise ValueError("Year is not valid.")

    with SessionLocal() as session:
        statement = (
            select(MeasurementRecord)
            .where(MeasurementRecord.year == year)
            .order_by(
                MeasurementRecord.service_id,
                MeasurementRecord.period,
            )
        )

        records = session.scalars(statement).all()

        return list(records)        


# get measurement records by period. Returns a list of MeasurementRecord objects.
def get_records_by_period(
    period: str,
) -> list[MeasurementRecord]:
    period = period.strip()

    if not period:
        raise ValueError("Period cannot be empty.")

    with SessionLocal() as session:
        statement = (
            select(MeasurementRecord)
            .where(
                MeasurementRecord.period == period
            )
            .order_by(
                MeasurementRecord.year,
                MeasurementRecord.service_id,
            )
        )

        records = session.scalars(statement).all()

        return list(records)

# get measurement records by year and period. Returns a list of MeasurementRecord objects.
def get_records_by_year_and_period(
    year: int,
    period: str,
) -> list[MeasurementRecord]:
    period = period.strip()

    if year < 2000:
        raise ValueError("Year is not valid.")

    if not period:
        raise ValueError("Period cannot be empty.")

    with SessionLocal() as session:
        statement = (
            select(MeasurementRecord)
            .where(
                MeasurementRecord.year == year,
                MeasurementRecord.period == period,
            )
            .order_by(
                MeasurementRecord.service_id
            )
        )

        records = session.scalars(statement).all()

        return list(records)    


# update an existing measurement record in the database and return the updated MeasurementRecord object. Returns None if the record was not found.
def update_measurement_record(
    record_id: int,
    service_id: int,
    year: int,
    period: str,
    participants_count: int,
    review: str | None = None,
) -> MeasurementRecord | None:
    period = period.strip()

    if not period:
        raise ValueError("Period cannot be empty.")

    if year < 2000:
        raise ValueError("Year is not valid.")

    if participants_count < 0:
        raise ValueError(
            "Participants count cannot be negative."
        )

    if review is not None:
        review = review.strip()

        if not review:
            review = None

    with SessionLocal() as session:
        record = session.get(
            MeasurementRecord,
            record_id,
        )

        if record is None:
            return None

        service = session.get(
            Service,
            service_id,
        )

        if service is None:
            raise ValueError("Service was not found.")

        record.service_id = service_id
        record.year = year
        record.period = period
        record.participants_count = participants_count
        record.review = review

        session.commit()
        session.refresh(record)

        return record

# delete a measurement record by its ID. Returns True if deleted, False if not found. Raises ValueError if the record has indicator results.
def delete_measurement_record(record_id: int) -> bool:
    with SessionLocal() as session:
        record = session.get(
            MeasurementRecord,
            record_id,
        )

        if record is None:
            return False

        if record.indicator_results:
            raise ValueError(
                "Cannot delete a measurement record "
                "that has indicator results."
            )

        session.delete(record)
        session.commit()

        return True