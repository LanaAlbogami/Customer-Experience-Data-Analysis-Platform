# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from typing import Any

import pandas as pd
from sqlalchemy import select

from database_Initiatives.connection import SessionLocal
from database_Initiatives.models import Action, Product, Section, Status


# ==================================================
# أدوات التنظيف والتحويل
# ==================================================

def _clean_text(value: Any) -> str | None:
    """تحويل الخلية إلى نص نظيف، أو None إذا كانت فارغة."""
    if pd.isna(value):
        return None

    text = str(value).strip()
    return text or None


def _get_cell(row: pd.Series, column_name: str | None) -> Any:
    if not column_name:
        return None

    return row.get(column_name)


def _parse_date(
    value: Any,
    *,
    field_name: str,
    row_number: int,
):
    """
    تحويل الخلية إلى تاريخ (date) أو None.

    - القيم الفارغة تعاد كـ None.
    - القيم غير الصالحة تُسبّب خطأً يوضّح رقم الصف واسم الحقل.
    """
    if pd.isna(value) or value == "":
        return None

    # القيم التي يقرأها pandas أصلًا كتاريخ (مثل خلايا التاريخ في Excel).
    if isinstance(value, (pd.Timestamp,)) or hasattr(value, "date"):
        try:
            return pd.to_datetime(value).date()
        except Exception:
            pass

    text = str(value).strip()
    if not text:
        return None

    # دعم الأرقام العربية داخل التواريخ النصية.
    text = text.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))

    # تحديد ترتيب اليوم/الشهر:
    # الصيغ التي تبدأ بالسنة (YYYY-MM-DD أو YYYY/MM/DD) تُقرأ بترتيب السنة أولًا،
    # وبقية الصيغ (مثل DD/MM/YYYY) تُقرأ باليوم أولًا.
    year_first = bool(re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}", text))

    try:
        parsed = pd.to_datetime(
            text,
            errors="raise",
            dayfirst=not year_first,
        )
    except Exception:
        raise ValueError(
            f"الصف {row_number}: قيمة {field_name} ليست تاريخًا صالحًا: {value}"
        )

    if pd.isna(parsed):
        raise ValueError(
            f"الصف {row_number}: قيمة {field_name} ليست تاريخًا صالحًا: {value}"
        )

    return parsed.date()


# ==================================================
# تجهيز صفوف Excel
# ==================================================

def prepare_initiative_records(
    dataframe: pd.DataFrame,
    *,
    section_column: str,
    product_column: str,
    initiative_column: str,
    status_column: str,
    number_column: str | None = None,
    creation_date_column: str | None = None,
    start_date_column: str | None = None,
    expected_execution_date_column: str | None = None,
    actual_execution_date_column: str | None = None,
) -> list[dict[str, Any]]:
    """تحويل DataFrame إلى سجلات مبادرات جاهزة للحفظ."""
    if dataframe.empty:
        raise ValueError("ملف Excel لا يحتوي على بيانات.")

    missing_required = [
        label
        for label, column in (
            ("عمود القسم", section_column),
            ("عمود المنتج", product_column),
            ("عمود اسم المبادرة", initiative_column),
            ("عمود الحالة", status_column),
        )
        if not column
    ]

    if missing_required:
        raise ValueError(
            "الحقول التالية مطلوبة ولم يتم ربطها: "
            + "، ".join(missing_required)
        )

    prepared_records: list[dict[str, Any]] = []
    errors: list[str] = []

    for dataframe_index, row in dataframe.iterrows():
        excel_row_number = int(dataframe_index) + 2

        try:
            section_name = _clean_text(_get_cell(row, section_column))
            product_name = _clean_text(_get_cell(row, product_column))
            action_name = _clean_text(_get_cell(row, initiative_column))
            status_name = _clean_text(_get_cell(row, status_column))
            initiative_number = _clean_text(_get_cell(row, number_column))

            required_values = [
                ("القسم", section_name),
                ("المنتج", product_name),
                ("اسم المبادرة", action_name),
                ("الحالة", status_name),
            ]

            # رقم المبادرة مطلوب فقط إذا تم ربط عموده.
            if number_column:
                required_values.append(("رقم المبادرة", initiative_number))

            row_missing = [
                label for label, value in required_values if not value
            ]

            if row_missing:
                raise ValueError(
                    f"الصف {excel_row_number}: القيم التالية فارغة: "
                    + "، ".join(row_missing)
                )

            creation_date = _parse_date(
                _get_cell(row, creation_date_column),
                field_name="تاريخ الإنشاء",
                row_number=excel_row_number,
            )

            start_date = _parse_date(
                _get_cell(row, start_date_column),
                field_name="تاريخ البدء",
                row_number=excel_row_number,
            )

            expected_execution_date = _parse_date(
                _get_cell(row, expected_execution_date_column),
                field_name="تاريخ التنفيذ المتوقع",
                row_number=excel_row_number,
            )

            actual_execution_date = _parse_date(
                _get_cell(row, actual_execution_date_column),
                field_name="التاريخ الفعلي للتنفيذ",
                row_number=excel_row_number,
            )

            prepared_records.append(
                {
                    "section_name": section_name,
                    "product_name": product_name,
                    "action_name": action_name,
                    "status_name": status_name,
                    "initiative_number": initiative_number,
                    "creation_date": creation_date,
                    "start_date": start_date,
                    "expected_execution_date": expected_execution_date,
                    "actual_execution_date": actual_execution_date,
                    "source_row": excel_row_number,
                }
            )

        except ValueError as error:
            errors.append(str(error))

    if errors:
        shown_errors = errors[:20]
        remaining = len(errors) - len(shown_errors)
        message = "\n".join(shown_errors)

        if remaining > 0:
            message += f"\n... ويوجد {remaining} أخطاء إضافية."

        raise ValueError(message)

    return prepared_records


# ==================================================
# الحفظ في قاعدة البيانات
# ==================================================

def save_initiative_records(
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    حفظ سجلات المبادرات داخل قاعدة بيانات المبادرات.

    الأقسام والمنتجات والحالات تُنشأ عند الحاجة فقط (get-or-create).
    المبادرة تُعرّف بالثلاثية (اسم المبادرة، القسم، المنتج):
        - إذا كانت موجودة تُحدّث حالتها وتواريخها.
        - وإلا تُضاف مبادرة جديدة.
    """
    empty_result = {
        "ok": False,
        "errors": ["لا توجد سجلات جاهزة للحفظ."],
        "created_sections": 0,
        "created_products": 0,
        "created_statuses": 0,
        "created_actions": 0,
        "updated_actions": 0,
    }

    if not records:
        return empty_result

    created_sections = 0
    created_products = 0
    created_statuses = 0
    created_actions = 0
    updated_actions = 0

    with SessionLocal() as session:
        try:
            # تحميل القيم المرجعية الموجودة مسبقًا إلى ذاكرة مؤقتة.
            sections_by_name: dict[str, Section] = {
                section.section_name: section
                for section in session.scalars(select(Section)).all()
            }

            statuses_by_name: dict[str, Status] = {
                status.status_name: status
                for status in session.scalars(select(Status)).all()
            }

            # المنتجات مفهرسة بالثنائية (اسم المنتج، معرّف القسم).
            products_by_key: dict[tuple[str, int], Product] = {
                (product.product_name, product.section_id): product
                for product in session.scalars(select(Product)).all()
            }

            def get_or_create_section(name: str) -> Section:
                nonlocal created_sections

                section = sections_by_name.get(name)
                if section is None:
                    section = Section(section_name=name)
                    session.add(section)
                    session.flush()
                    sections_by_name[name] = section
                    created_sections += 1

                return section

            def get_or_create_status(name: str) -> Status:
                nonlocal created_statuses

                status = statuses_by_name.get(name)
                if status is None:
                    status = Status(status_name=name)
                    session.add(status)
                    session.flush()
                    statuses_by_name[name] = status
                    created_statuses += 1

                return status

            def get_or_create_product(name: str, section: Section) -> Product:
                nonlocal created_products

                key = (name, section.section_id)
                product = products_by_key.get(key)
                if product is None:
                    product = Product(
                        product_name=name,
                        section_id=section.section_id,
                    )
                    session.add(product)
                    session.flush()
                    products_by_key[key] = product
                    created_products += 1

                return product

            for item in records:
                section = get_or_create_section(item["section_name"])
                product = get_or_create_product(item["product_name"], section)
                status = get_or_create_status(item["status_name"])
                number = item.get("initiative_number")

                # التعرّف على المبادرة الموجودة:
                # - إن توفّر رقم المبادرة فهو المعرّف (أدق وأضمن).
                # - وإلا نرجع للتطابق بالاسم داخل نفس القسم والمنتج.
                if number:
                    existing_action = session.scalar(
                        select(Action).where(
                            Action.initiative_number == number
                        )
                    )
                else:
                    existing_action = session.scalar(
                        select(Action).where(
                            Action.action_name == item["action_name"],
                            Action.section_id == section.section_id,
                            Action.product_id == product.product_id,
                        )
                    )

                if existing_action is None:
                    action = Action(
                        action_name=item["action_name"],
                        initiative_number=number,
                        section_id=section.section_id,
                        product_id=product.product_id,
                        status_id=status.status_id,
                        creation_date=item.get("creation_date"),
                        start_date=item.get("start_date"),
                        expected_execution_date=item.get(
                            "expected_execution_date"
                        ),
                        actual_execution_date=item.get(
                            "actual_execution_date"
                        ),
                    )
                    session.add(action)
                    created_actions += 1
                else:
                    # عند التطابق بالرقم، نحدّث بقية الحقول أيضًا (الرقم هو الهوية).
                    existing_action.status_id = status.status_id

                    if number:
                        existing_action.action_name = item["action_name"]
                        existing_action.section_id = section.section_id
                        existing_action.product_id = product.product_id

                    if item.get("creation_date") is not None:
                        existing_action.creation_date = item["creation_date"]

                    if item.get("start_date") is not None:
                        existing_action.start_date = item["start_date"]

                    if item.get("expected_execution_date") is not None:
                        existing_action.expected_execution_date = item[
                            "expected_execution_date"
                        ]

                    if item.get("actual_execution_date") is not None:
                        existing_action.actual_execution_date = item[
                            "actual_execution_date"
                        ]

                    updated_actions += 1

            session.commit()

            return {
                "ok": True,
                "errors": [],
                "created_sections": created_sections,
                "created_products": created_products,
                "created_statuses": created_statuses,
                "created_actions": created_actions,
                "updated_actions": updated_actions,
            }

        except Exception as error:
            session.rollback()

            return {
                "ok": False,
                "errors": [f"تعذر حفظ بيانات المبادرات: {error}"],
                "created_sections": 0,
                "created_products": 0,
                "created_statuses": 0,
                "created_actions": 0,
                "updated_actions": 0,
            }