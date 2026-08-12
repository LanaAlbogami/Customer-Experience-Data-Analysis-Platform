# -*- coding: utf-8 -*-

"""
Initializes the CSAT factors and survey indicators used by the individuals database.

Note:
This script removes existing individual CSAT factors and their responses,
then recreates the eight approved factors.
"""

from sqlalchemy import delete, select

from database_individuals.connection import SessionLocal
from database_individuals.models import (
    IndividualFactorResponse,
    SharedCSATFactor,
    SharedIndicator,
)

INDIVIDUAL_FACTORS = [
    "المظهر العام",
    "اجراءات التسجيل",
    "اجراءات الدخول",
    "تنفيذ الخدمات عبر التطبيق",
    "توفر الخدمه",
    "رسائل الاشعارات والتنبيهات",
    "قنوات التواصل للحصول على الدعم",
    "الدعم الفني",
]

RAW_INDICATORS = [
    {
        "name": "CES",
        "unit": "درجة",
        "minimum": 1,
        "maximum": 5,
    },
    {
        "name": "NPS",
        "unit": "درجة",
        "minimum": 0,
        "maximum": 10,
    },
]


def sync_reference_data():
    """Synchronizes the predefined CSAT factors and raw indicators with the database."""
    with SessionLocal() as session:
        try:
            # Removes existing factor responses first to satisfy foreign key constraints.
            session.execute(
                delete(IndividualFactorResponse)
            )

            # Removes previously stored CSAT factors before recreating the approved list.
            session.execute(
                delete(SharedCSATFactor)
            )

            session.flush()

            # Inserts the eight individual CSAT factors in their defined display order.
            for order, factor_name in enumerate(
                INDIVIDUAL_FACTORS,
                start=1,
            ):
                session.add(
                    SharedCSATFactor(
                        factor_name=factor_name,
                        display_order=order,
                    )
                )

            # Creates missing indicators or updates their existing configuration.
            for item in RAW_INDICATORS:
                indicator = session.scalar(
                    select(SharedIndicator)
                    .where(
                        SharedIndicator.indicator_name
                        == item["name"]
                    )
                )

                if indicator is None:
                    indicator = SharedIndicator(
                        indicator_name=item["name"],
                        unit=item["unit"],
                        min_value=item["minimum"],
                        max_value=item["maximum"],
                    )
                    session.add(indicator)

                else:
                    indicator.unit = item["unit"]
                    indicator.min_value = item["minimum"]
                    indicator.max_value = item["maximum"]

            session.commit()

            print(
                "تم تجهيز قاعدة بيانات الأفراد بنجاح: "
                f"{len(INDIVIDUAL_FACTORS)} عوامل CSAT، "
                f"{len(RAW_INDICATORS)} مؤشرات."
            )

        except Exception:
            # Rolls back all changes if any part of the synchronization fails.
            session.rollback()
            raise


if __name__ == "__main__":
    sync_reference_data()