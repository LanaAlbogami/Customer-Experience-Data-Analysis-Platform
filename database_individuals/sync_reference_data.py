# -*- coding: utf-8 -*-
"""
database_individuals/sync_reference_data.py
-------------------------------------------
تجهيز عوامل ومؤشرات قاعدة بيانات الأفراد.

تنبيه:
هذا الملف يحذف عوامل الأفراد القديمة وإجاباتها، ثم يعيد إنشاء
العوامل الثمانية الصحيحة.
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
    with SessionLocal() as session:
        try:
            # حذف إجابات العوامل القديمة أولًا بسبب المفتاح الخارجي.
            session.execute(
                delete(IndividualFactorResponse)
            )

            # حذف عوامل الجهات التي نُسخت سابقًا بالخطأ.
            session.execute(
                delete(SharedCSATFactor)
            )

            session.flush()

            # إدخال عوامل الأفراد الثمانية بالترتيب.
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

            # إضافة أو تحديث المؤشرات الخام للأفراد.
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
            session.rollback()
            raise


if __name__ == "__main__":
    sync_reference_data()
