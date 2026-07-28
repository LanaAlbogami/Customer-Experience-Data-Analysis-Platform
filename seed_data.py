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

from database.connection import SessionLocal
from database.models import Department, Service, Indicator


# The same department -> services structure the page uses.
DEPARTMENTS = {
    "إدارة تجربة العميل": ["خدمة المستفيدين", "مركز الاتصال", "المحادثة المباشرة"],
    "الخدمات الرقمية": ["تطبيق الجوال", "البوابة الإلكترونية", "النماذج الإلكترونية"],
    "الموارد البشرية": ["تعيين الموظفين الجدد", "دعم الرواتب"],
    "العمليات": ["الزيارات الميدانية", "طلبات الصيانة"],
}

# The three indicators, with the min/max range the schema requires.
INDICATORS = [
    {"name": "CSAT", "unit": "%", "min_value": 0, "max_value": 100},
    {"name": "CES", "unit": "score", "min_value": -100, "max_value": 100},
    {"name": "NPS", "unit": "score", "min_value": -100, "max_value": 100},
]


def seed():
    # A session is one "conversation" with the database.
    session = SessionLocal()
    try:
        # ---- Departments and their services ----
        for department_name, service_names in DEPARTMENTS.items():

            # Only add the department if it is not already there.
            department = (session.query(Department)
                          .filter_by(department_name=department_name)
                          .first())
            if department is None:
                department = Department(department_name=department_name)
                session.add(department)
                session.flush()   # gives the new department its ID now
                print(f"+ إدارة: {department_name}")

            # Add each service under that department.
            for service_name in service_names:
                exists = (session.query(Service)
                          .filter_by(service_name=service_name,
                                     department_id=department.department_id)
                          .first())
                if exists is None:
                    session.add(Service(service_name=service_name,
                                        department_id=department.department_id))
                    print(f"    - خدمة: {service_name}")

        # ---- Indicators ----
        for item in INDICATORS:
            exists = (session.query(Indicator)
                      .filter_by(indicator_name=item["name"])
                      .first())
            if exists is None:
                session.add(Indicator(
                    indicator_name=item["name"],
                    unit=item["unit"],
                    min_value=item["min_value"],
                    max_value=item["max_value"],
                ))
                print(f"+ مؤشر: {item['name']}")

        # Save everything at once.
        session.commit()
        print("\nتمت تعبئة البيانات المرجعية بنجاح.")

    except Exception as error:
        session.rollback()          # undo everything if something failed
        print("فشلت التعبئة:", error)
    finally:
        session.close()


if __name__ == "__main__":
    seed()