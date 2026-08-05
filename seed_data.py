# -*- coding: utf-8 -*-
"""
seed_data.py
------------
Fills the lookup tables (Department, Service, Indicator) with the Arabic
values the page needs. Safe to run more than once: it checks whether a
row already exists before adding it, so nothing gets duplicated.

Run it ONCE after the tables are created:
    python seed_data.py

This uses the team's own models, so it stays consistent with their schema.
"""

from decimal import Decimal

from database.connection import SessionLocal
from database.models import (
    Section,
    Service,
    Indicator,
    Factor,
)


# الأقسام والخدمات

SECTIONS = {}



# المؤشرات

# CSAT يعتمد على متوسط نتائج العوامل السبعة.
# أما CES وNPS وBPS فتُحسب أو تُرفع بشكل مستقل.


INDICATORS = [
    {
        "name": "CSAT",
        "unit": "%",
        "min_value": Decimal("0"),
        "max_value": Decimal("100"),
        "is_factor_based": True,
    },
    {
        "name": "CES",
        "unit": "score",
        "min_value": Decimal("-100"),
        "max_value": Decimal("100"),
        "is_factor_based": False,
    },
    {
        "name": "NPS",
        "unit": "score",
        "min_value": Decimal("-100"),
        "max_value": Decimal("100"),
        "is_factor_based": False,
    },
    {
        "name": "BPS",
        "unit": "%",
        "min_value": Decimal("0"),
        "max_value": Decimal("100"),
        "is_factor_based": False,
    },
]



# عوامل CSAT السبعة الثابتة


FACTORS = [
    "سهولة الحصول على معلومات ",
    "إمكانيات وخصائص الخدمة",
    "استقرار وثبات الخدمة",
    "الإبلاغ بالتحديثات على الخدمة",
    "الرضا بشكل عام عن دعم العملاء ",
    "الرضا بشكل عام عن مدير الحساب",
    "الرضا بشكل عام عن الدعم الفني الميداني",
]


# تعبئة الأقسام والخدمات

def seed_sections_and_services(session):
    for section_name, service_names in SECTIONS.items():

        section = (
            session.query(Section)
            .filter_by(section_name=section_name)
            .first()
        )

        if section is None:
            section = Section(
                section_name=section_name
            )

            session.add(section)
            session.flush()

            print(f"+ قسم: {section_name}")

        for service_name in service_names:

            service = (
                session.query(Service)
                .filter_by(
                    section_id=section.section_id,
                    service_name=service_name,
                )
                .first()
            )

            if service is None:
                session.add(
                    Service(
                        section_id=section.section_id,
                        service_name=service_name,
                    )
                )

                print(f"    - خدمة: {service_name}")


# تعبئة المؤشرات


def seed_indicators(session):
    for item in INDICATORS:

        indicator = (
            session.query(Indicator)
            .filter_by(
                indicator_name=item["name"]
            )
            .first()
        )

        if indicator is None:
            indicator = Indicator(
                indicator_name=item["name"],
                unit=item["unit"],
                min_value=item["min_value"],
                max_value=item["max_value"],
                is_factor_based=item["is_factor_based"],
            )

            session.add(indicator)

            print(f"+ مؤشر: {item['name']}")

        else:
            # تحديث بيانات المؤشر إذا تغيرت
            indicator.unit = item["unit"]
            indicator.min_value = item["min_value"]
            indicator.max_value = item["max_value"]
            indicator.is_factor_based = item["is_factor_based"]


# تعبئة العوامل السبعة

def seed_factors(session):
    if len(FACTORS) != 7:
        raise ValueError(
            "يجب أن تحتوي قائمة FACTORS على سبعة عوامل بالضبط."
        )

    if len(set(FACTORS)) != 7:
        raise ValueError(
            "يوجد اسم عامل مكرر داخل قائمة FACTORS."
        )

    for display_order, factor_name in enumerate(
        FACTORS,
        start=1,
    ):
        clean_name = factor_name.strip()

        if not clean_name:
            raise ValueError(
                f"اسم العامل رقم {display_order} فارغ."
            )

        factor = (
            session.query(Factor)
            .filter_by(
                factor_name=clean_name
            )
            .first()
        )

        if factor is None:
            factor = Factor(
                factor_name=clean_name,
                display_order=display_order,
            )

            session.add(factor)

            print(
                f"+ عامل {display_order}: {clean_name}"
            )

        else:
            factor.display_order = display_order


# التشغيل الرئيسي

def seed():
    session = SessionLocal()

    try:
        seed_sections_and_services(session)
        seed_indicators(session)
        seed_factors(session)

        session.commit()

        print(
            "\nتمت تعبئة البيانات المرجعية بنجاح."
        )

    except Exception as error:
        session.rollback()

        print(
            "\nفشلت تعبئة البيانات المرجعية:"
        )
        print(error)

        raise

    finally:
        session.close()


if __name__ == "__main__":
    seed()