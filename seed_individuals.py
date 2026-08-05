"""
seed_individuals.py
--------------------
يعبّي الجداول الثابتة بقاعدة بيانات الأفراد:
  - SharedCSATFactors: الـ 8 عوامل الثابتة
  - SharedIndicators: مؤشر NPS

يُشغَّل مرة وحدة بس (بعد إنشاء الجداول بـ create_tables_individuals.py).
تشغيله أكثر من مرة آمن: يتحقق قبل كل إضافة عشان ما يكرر نفس الصف.
"""

from database_individuals.connection import SessionLocal
from database_individuals.models import SharedCSATFactor, SharedIndicator


FACTORS = [
    (1, "ما مدى رضاك عن إجراءات التسجيل في التطبيق؟"),
    (2, "ما مدى رضاك عن إجراءات الدخول للتطبيق؟"),
    (3, "ما مدى رضاك عن المظهر العام للتطبيق؟"),
    (4, "ما مدى رضاك عن توفر التطبيق في جميع الأوقات؟"),
    (5, "ما مدى رضاك عن رسائل الإشعارات والتنبيهات التي تردكم من التطبيق؟"),
    (6, "ما مدى رضاك عن تنفيذ الخدمات الخاصة بالجهات الحكومية عبر التطبيق؟"),
    (7, "ما مدى رضاك عن الدعم الفني للتطبيق؟"),
    (8, "ما مدى رضاك عن تعدد قنوات الاتصال للحصول على الدعم؟"),
]

# NPS يُسأل بمقياس 0-10 (وليس 1-5 مثل الـ Factors)
INDICATORS = [
    ("NPS", "score", 0, 10),
]


def seed() -> None:
    session = SessionLocal()

    try:
        # --- العوامل الثابتة ---
        added_factors = 0
        for display_order, factor_name in FACTORS:
            exists = (
                session.query(SharedCSATFactor)
                .filter(SharedCSATFactor.factor_name == factor_name)
                .first()
            )
            if exists is None:
                session.add(
                    SharedCSATFactor(
                        factor_name=factor_name,
                        display_order=display_order,
                    )
                )
                added_factors += 1

        # --- المؤشرات الأخرى (NPS) ---
        added_indicators = 0
        for name, unit, minimum, maximum in INDICATORS:
            exists = (
                session.query(SharedIndicator)
                .filter(SharedIndicator.indicator_name == name)
                .first()
            )
            if exists is None:
                session.add(
                    SharedIndicator(
                        indicator_name=name,
                        unit=unit,
                        min_value=minimum,
                        max_value=maximum,
                    )
                )
                added_indicators += 1

        session.commit()

        print(
            f"تمت إضافة {added_factors} عامل جديد، "
            f"و{added_indicators} مؤشر جديد."
        )

    except Exception as error:
        session.rollback()
        print(f"خطأ أثناء زرع البيانات: {error}")

    finally:
        session.close()


if __name__ == "__main__":
    seed()