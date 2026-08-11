"""
refresh_individual_cache.py
----------------------------
يحسب نتيجة CSAT العامة (لكل factor + المتوسط الكلي) ونتيجة NPS وCES
(بدون أي فلاتر)، ويخزنها بجدول IndividualDashboardCache.

شغّليه:
1) أول مرة بعد ما تبنين الجدول الجديد.
2) بعد كل مرة ترفعين بيانات أفراد جديدة (Excel).

الأمر (من جذر المشروع):
    python -m refresh_individual_cache
"""

from datetime import datetime

from database_individuals.connection import SessionLocal
from database_individuals.models import IndividualDashboardCache

try:
    from Individuals.data_service_individuals import (
        aggregate_records,
        fetch_factor_order,
        fetch_indicator_names,
        fetch_individual_dataset,
    )
except ModuleNotFoundError:
    from data_service_individuals import (
        aggregate_records,
        fetch_factor_order,
        fetch_indicator_names,
        fetch_individual_dataset,
    )


def _upsert(session, metric_name, value, participants_count):
    row = (
        session.query(IndividualDashboardCache)
        .filter_by(metric_name=metric_name)
        .first()
    )

    now = datetime.now().isoformat(timespec="seconds")

    if row is None:
        row = IndividualDashboardCache(
            metric_name=metric_name,
            current_value=value,
            participants_count=participants_count,
            updated_at=now,
        )
        session.add(row)
    else:
        row.current_value = value
        row.participants_count = participants_count
        row.updated_at = now


def refresh():
    dataset = fetch_individual_dataset()
    factor_order = fetch_factor_order()
    indicator_names = fetch_indicator_names()

    aggregated = aggregate_records(dataset, factor_order, indicator_names)

    session = SessionLocal()

    try:
        _upsert(
            session,
            "CSAT_OVERALL",
            aggregated.get("csat_current"),
            aggregated["participants_total"],
        )

        for factor_name, factor_data in aggregated["factors"].items():
            _upsert(
                session,
                factor_name,
                factor_data.get("current_value"),
                factor_data.get("participants_count", 0),
            )

        for indicator_name, indicator_data in aggregated["indicators"].items():
            _upsert(
                session,
                indicator_name,
                indicator_data.get("current_value"),
                indicator_data.get("participants_count", 0),
            )

        session.commit()

        print(
            "تم تحديث الجدول المخزّن مؤقتًا بنجاح "
            f"({aggregated['participants_total']} رد إجمالي)."
        )

    except Exception as error:
        session.rollback()
        print(f"خطأ أثناء تحديث الجدول المخزّن: {error}")
        raise

    finally:
        session.close()


if __name__ == "__main__":
    refresh()