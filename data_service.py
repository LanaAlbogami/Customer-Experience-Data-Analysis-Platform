from sqlalchemy import select
from database.connection import SessionLocal
from database.models import Department, Service, MeasurementRecord, IndicatorResult, Indicator


def fetch_records_from_db():
    """يرجع قائمة بنفس شكل mock_records بالضبط، لكن من الداتابيز الحقيقية."""
    session = SessionLocal()
    try:
        rows = session.execute(
            select(MeasurementRecord, Service, Department)
            .join(Service, MeasurementRecord.service_id == Service.service_id)
            .join(Department, Service.department_id == Department.department_id)
        ).all()

        result = []
        for mrecord, service, dept in rows:
            row = {
                "department": dept.department_name,
                "service": service.service_name,
                "year": mrecord.year,
                "period": mrecord.period,
                "status": "معتمد",  # ملاحظة: ما فيه عمود status بجدولكم حاليًا، قيمة ثابتة مؤقتًا
            }

            indicator_rows = session.execute(
                select(IndicatorResult, Indicator)
                .join(Indicator, IndicatorResult.indicator_id == Indicator.indicator_id)
                .where(IndicatorResult.record_id == mrecord.record_id)
            ).all()

            for ind_result, indicator in indicator_rows:
                key = indicator.indicator_name.lower()  # "nps" / "ces" / "csat"
                row[f"{key}_prev"] = float(ind_result.prev_value or 0)
                row[f"{key}_current"] = float(ind_result.current_value)
                row[f"{key}_target"] = float(ind_result.target_value)

            result.append(row)
        return result
    finally:
        session.close()