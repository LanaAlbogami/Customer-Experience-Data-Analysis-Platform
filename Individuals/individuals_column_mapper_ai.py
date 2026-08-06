# -*- coding: utf-8 -*-
"""
individuals/individuals_column_mapper_ai.py
-------------------------------------------
مطابقة أسماء أعمدة Excel مع حقول قاعدة بيانات الأفراد.

لا يرسل هذا الملف صفوف Excel أو القيم أو التعليقات إلى OpenAI.
المرسل فقط:
- أسماء الأعمدة
- أسماء عوامل CSAT من قاعدة البيانات
- أسماء المؤشرات من قاعدة البيانات
"""

from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()


def _nullable_string_schema() -> dict[str, Any]:
    return {
        "anyOf": [
            {"type": "string"},
            {"type": "null"},
        ]
    }


def _response_schema() -> dict[str, Any]:
    nullable_string = _nullable_string_schema()

    return {
        "type": "object",
        "properties": {
            "individual_id_column": nullable_string,
            "time_mode": {
                "type": "string",
                "enum": [
                    "date",
                    "combined",
                    "separate",
                    "unknown",
                ],
            },
            "date_column": nullable_string,
            "combined_time_column": nullable_string,
            "year_column": nullable_string,
            "period_column": nullable_string,
            "gender_column": nullable_string,
            "age_group_column": nullable_string,
            "id_type_column": nullable_string,
            "education_column": nullable_string,
            "device_column": nullable_string,
            "region_column": nullable_string,
            "factor_mappings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "factor_name": {
                            "type": "string"
                        },
                        "column_name": nullable_string,
                    },
                    "required": [
                        "factor_name",
                        "column_name",
                    ],
                    "additionalProperties": False,
                },
            },
            "indicator_mappings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "indicator_name": {
                            "type": "string"
                        },
                        "column_name": nullable_string,
                    },
                    "required": [
                        "indicator_name",
                        "column_name",
                    ],
                    "additionalProperties": False,
                },
            },
            "warnings": {
                "type": "array",
                "items": {
                    "type": "string"
                },
            },
        },
        "required": [
            "individual_id_column",
            "time_mode",
            "date_column",
            "combined_time_column",
            "year_column",
            "period_column",
            "gender_column",
            "age_group_column",
            "id_type_column",
            "education_column",
            "device_column",
            "region_column",
            "factor_mappings",
            "indicator_mappings",
            "warnings",
        ],
        "additionalProperties": False,
    }


def _safe_column(
    value: Any,
    available_columns: set[str],
) -> str | None:
    if not isinstance(value, str):
        return None

    value = value.strip()

    if value in available_columns:
        return value

    return None


def _sanitize_mapping(
    mapping: dict[str, Any],
    column_names: list[str],
    factor_names: list[str],
    indicator_names: list[str],
) -> dict[str, Any]:
    available_columns = set(column_names)

    sanitized = {
        "individual_id_column": _safe_column(
            mapping.get("individual_id_column"),
            available_columns,
        ),
        "time_mode": mapping.get(
            "time_mode",
            "unknown",
        ),
        "date_column": _safe_column(
            mapping.get("date_column"),
            available_columns,
        ),
        "combined_time_column": _safe_column(
            mapping.get("combined_time_column"),
            available_columns,
        ),
        "year_column": _safe_column(
            mapping.get("year_column"),
            available_columns,
        ),
        "period_column": _safe_column(
            mapping.get("period_column"),
            available_columns,
        ),
        "gender_column": _safe_column(
            mapping.get("gender_column"),
            available_columns,
        ),
        "age_group_column": _safe_column(
            mapping.get("age_group_column"),
            available_columns,
        ),
        "id_type_column": _safe_column(
            mapping.get("id_type_column"),
            available_columns,
        ),
        "education_column": _safe_column(
            mapping.get("education_column"),
            available_columns,
        ),
        "device_column": _safe_column(
            mapping.get("device_column"),
            available_columns,
        ),
        "region_column": _safe_column(
            mapping.get("region_column"),
            available_columns,
        ),
        "factor_mappings": {},
        "indicator_mappings": {},
        "warnings": [
            str(warning).strip()
            for warning in mapping.get(
                "warnings",
                [],
            )
            if str(warning).strip()
        ],
    }

    if sanitized["time_mode"] not in {
        "date",
        "combined",
        "separate",
        "unknown",
    }:
        sanitized["time_mode"] = "unknown"

    returned_factors = mapping.get(
        "factor_mappings",
        [],
    )

    factors_by_name = {}

    if isinstance(returned_factors, list):
        for item in returned_factors:
            if not isinstance(item, dict):
                continue

            factor_name = item.get(
                "factor_name"
            )

            if factor_name not in factor_names:
                continue

            factors_by_name[
                factor_name
            ] = _safe_column(
                item.get("column_name"),
                available_columns,
            )

    sanitized["factor_mappings"] = {
        factor_name: factors_by_name.get(
            factor_name
        )
        for factor_name in factor_names
    }

    returned_indicators = mapping.get(
        "indicator_mappings",
        [],
    )

    indicators_by_name = {}

    if isinstance(returned_indicators, list):
        for item in returned_indicators:
            if not isinstance(item, dict):
                continue

            indicator_name = item.get(
                "indicator_name"
            )

            if indicator_name not in indicator_names:
                continue

            indicators_by_name[
                indicator_name
            ] = _safe_column(
                item.get("column_name"),
                available_columns,
            )

    sanitized["indicator_mappings"] = {
        indicator_name: indicators_by_name.get(
            indicator_name
        )
        for indicator_name in indicator_names
    }

    return sanitized


def map_individual_columns_with_ai(
    column_names: list[str],
    factor_names: list[str],
    indicator_names: list[str],
) -> dict[str, Any]:
    """
    مطابقة أسماء أعمدة ملف الأفراد.

    لا ترسل الدالة أي صفوف أو قيم من ملف Excel.
    """
    api_key = os.getenv(
        "OPENAI_API_KEY"
    )

    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY غير موجود في ملف .env."
        )

    model = os.getenv(
        "OPENAI_MODEL",
        "gpt-5-mini",
    )

    client = OpenAI(
        api_key=api_key
    )

    payload = {
        "excel_column_names": column_names,
        "individual_csat_factors": factor_names,
        "individual_indicators": indicator_names,
    }

    instructions = """
أنت نظام لمطابقة أسماء أعمدة Excel مع حقول استبيانات الأفراد.

قواعد إلزامية:
1. استخدم فقط اسم عمود موجود حرفيًا في excel_column_names.
2. لا تستخدم محتوى الصفوف؛ المتاح لك أسماء الأعمدة فقط.
3. لا تطابق أعمدة التعليقات أو الملاحظات أو الاقتراحات. المستخدم يختارها يدويًا.
4. لا تخمن عند عدم وضوح الاسم. أرجع null وأضف تحذيرًا مختصرًا.
5. individual_id_column يُختار فقط عندما يدل الاسم بوضوح على IndividualID أو معرف فرد محفوظ في النظام. لا تعتبر رقم الاستجابة أو رقم الهوية IndividualID.
6. طريقة الزمن:
   - date: يوجد عمود تاريخ يمكن استخراج السنة والربع منه.
   - combined: السنة والربع في عمود واحد.
   - separate: السنة وعمود الربع منفصلان.
   - unknown: لا توجد دلالة كافية.
7. البيانات الديموغرافية:
   - gender_column: الجنس.
   - age_group_column: الفئة العمرية.
   - id_type_column: نوع الهوية، وليس رقم الهوية.
   - education_column: المستوى التعليمي.
   - device_column: الجهاز أو نوع الجهاز.
   - region_column: المنطقة.
8. factor_mappings يجب أن يحتوي عنصرًا لكل عامل موجود في individual_csat_factors، وبنفس الاسم حرفيًا. column_name يكون null إذا لم توجد مطابقة واضحة.
9. indicator_mappings يجب أن يحتوي عنصرًا لكل مؤشر موجود في individual_indicators، وبنفس الاسم حرفيًا. column_name يكون null إذا لم توجد مطابقة واضحة.
10. لا تستخدم العمود نفسه لأكثر من عامل أو مؤشر.
11. أعمدة مثل Q1 وQ2 دون وصف دلالي واضح لا تكفي للمطابقة.
"""

    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=json.dumps(
            payload,
            ensure_ascii=False,
        ),
        text={
            "format": {
                "type": "json_schema",
                "name": (
                    "individual_excel_column_mapping"
                ),
                "description": (
                    "مطابقة أسماء أعمدة Excel مع حقول بيانات الأفراد"
                ),
                "strict": True,
                "schema": _response_schema(),
            }
        },
        store=False,
    )

    if not response.output_text:
        raise ValueError(
            "لم يرجع OpenAI نتيجة للمطابقة."
        )

    try:
        mapping = json.loads(
            response.output_text
        )

    except json.JSONDecodeError as error:
        raise ValueError(
            "تعذر قراءة نتيجة مطابقة الأعمدة."
        ) from error

    return _sanitize_mapping(
        mapping=mapping,
        column_names=column_names,
        factor_names=factor_names,
        indicator_names=indicator_names,
    )
