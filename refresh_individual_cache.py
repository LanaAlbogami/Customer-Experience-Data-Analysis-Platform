"""
Calculates the overall CSAT results, factor-level CSAT values, NPS, and CES
without applying filters, then stores the results in IndividualDashboardCache.

Run this script:
1. After creating the cache table for the first time.
2. After importing new individual survey data from Excel.

Command from the project root:
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
    """Creates a cache record or updates the existing record for the given metric."""
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
    """Recalculates all individual dashboard metrics and refreshes the cache table."""
    dataset = fetch_individual_dataset()
    factor_order = fetch_factor_order()
    indicator_names = fetch_indicator_names()

    aggregated = aggregate_records(dataset, factor_order, indicator_names)

    session = SessionLocal()

    try:
        # Stores the overall CSAT result for all individual responses.
        _upsert(
            session,
            "CSAT_OVERALL",
            aggregated.get("csat_current"),
            aggregated["participants_total"],
        )

        # Stores the calculated CSAT result for each individual factor.
        for factor_name, factor_data in aggregated["factors"].items():
            _upsert(
                session,
                factor_name,
                factor_data.get("current_value"),
                factor_data.get("participants_count", 0),
            )

        # Stores the calculated results for additional indicators such as NPS and CES.
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
        # Rolls back pending cache updates if any operation fails.
        session.rollback()
        print(f"خطأ أثناء تحديث الجدول المخزّن: {error}")
        raise

    finally:
        # Always closes the database session after the refresh process finishes.
        session.close()


if __name__ == "__main__":
    refresh()
