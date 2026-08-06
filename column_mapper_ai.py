# -*- coding: utf-8 -*-
"""مطابقة أسماء أعمدة Excel مع حقول رفع بيانات الأقسام باستخدام OpenAI."""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI


def _nullable_string() -> dict[str, Any]:
    return {"anyOf": [{"type": "string"}, {"type": "null"}]}


def _schema() -> dict[str, Any]:
    nullable = _nullable_string()
    return {
        "type": "object",
        "properties": {
            "service_column": nullable,
            "section_column": nullable,
            "time_mode": {
                "type": "string",
                "enum": ["date", "combined", "separate", "unknown"],
            },
            "date_column": nullable,
            "combined_time_column": nullable,
            "year_column": nullable,
            "period_column": nullable,
            "response_id_column": nullable,
            "participants_column": nullable,
            "factor_mappings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "factor_name": {"type": "string"},
                        "column_name": nullable,
                    },
                    "required": ["factor_name", "column_name"],
                    "additionalProperties": False,
                },
            },
            "ces_columns": {
                "type": "array",
                "items": {"type": "string"},
            },
            "nps_column": nullable,
            "bps_column": nullable,
            "warnings": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": [
            "service_column",
            "section_column",
            "time_mode",
            "date_column",
            "combined_time_column",
            "year_column",
            "period_column",
            "response_id_column",
            "participants_column",
            "factor_mappings",
            "ces_columns",
            "nps_column",
            "bps_column",
            "warnings",
        ],
        "additionalProperties": False,
    }


def _valid_column(value: Any, allowed: set[str]) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if value in allowed else None


def _sanitize(
    result: dict[str, Any],
    columns: list[str],
    factors: list[str],
) -> dict[str, Any]:
    allowed = set(columns)
    factor_result = {}

    for item in result.get("factor_mappings", []):
        if not isinstance(item, dict):
            continue
        name = item.get("factor_name")
        if name in factors:
            factor_result[name] = _valid_column(
                item.get("column_name"),
                allowed,
            )

    ces_columns = []
    for column in result.get("ces_columns", []):
        safe = _valid_column(column, allowed)
        if safe and safe not in ces_columns:
            ces_columns.append(safe)

    time_mode = result.get("time_mode", "unknown")
    if time_mode not in {"date", "combined", "separate", "unknown"}:
        time_mode = "unknown"

    return {
        "service_column": _valid_column(result.get("service_column"), allowed),
        "section_column": _valid_column(result.get("section_column"), allowed),
        "time_mode": time_mode,
        "date_column": _valid_column(result.get("date_column"), allowed),
        "combined_time_column": _valid_column(
            result.get("combined_time_column"),
            allowed,
        ),
        "year_column": _valid_column(result.get("year_column"), allowed),
        "period_column": _valid_column(result.get("period_column"), allowed),
        "response_id_column": _valid_column(
            result.get("response_id_column"),
            allowed,
        ),
        "participants_column": _valid_column(
            result.get("participants_column"),
            allowed,
        ),
        "factor_mappings": {
            name: factor_result.get(name)
            for name in factors
        },
        "ces_columns": ces_columns,
        "nps_column": _valid_column(result.get("nps_column"), allowed),
        "bps_column": _valid_column(result.get("bps_column"), allowed),
        "warnings": [
            str(item)
            for item in result.get("warnings", [])
            if str(item).strip()
        ],
    }


def map_section_columns_with_ai(
    column_names: list[str],
    factor_names: list[str],
    data_mode: str,
) -> dict[str, Any]:
    """
    يرسل أسماء الأعمدة فقط إلى OpenAI.

    data_mode:
        raw         بيانات استبيان خام.
        calculated  نتائج محسوبة مسبقًا.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY غير موجود في ملف .env.")

    client = OpenAI(api_key=api_key)
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")

    payload = {
        "data_mode": data_mode,
        "excel_column_names": column_names,
        "required_csat_factors": factor_names,
    }

    instructions = """
أنت نظام لمطابقة أسماء أعمدة Excel مع حقول منصة تجربة العميل.

التزم بما يلي:
- استخدم فقط أسماء الأعمدة الموجودة في excel_column_names حرفيًا.
- لا ترسل أو تطلب أي قيم من الصفوف؛ المطلوب تحليل أسماء الأعمدة فقط.
- لا تطابق أعمدة التعليقات أو الملاحظات؛ المستخدم يختارها بنفسه.
- service_column لاسم الخدمة، وsection_column للقسم أو الإدارة.
- time_mode:
  date لعمود تاريخ، combined لعمود سنة وفترة واحد،
  separate لعمودي سنة وفترة، unknown عند عدم الوضوح.
- في raw: اربط كل عامل بعمود إجابات 1 إلى 5، وحدد CES وNPS الخام
  ورقم الاستجابة إن وجد. اجعل participants_column وbps_column null.
- في calculated: اربط كل عامل بعمود نتيجته، وحدد نتائج CES وNPS وBPS
  وعدد المشاركين. اجعل response_id_column null.
- لا تستخدم العمود نفسه لأكثر من عامل أو مؤشر.
- إذا كان الاسم عامًا مثل Q1 بلا وصف فلا تخمن؛ أرجع null مع تحذير.
- أرجع factor_mappings لكل عامل حتى لو كانت column_name null.
"""

    response = client.responses.create(
        model=model,
        instructions=instructions,
        input=json.dumps(payload, ensure_ascii=False),
        text={
            "format": {
                "type": "json_schema",
                "name": "section_column_mapping",
                "strict": True,
                "schema": _schema(),
            }
        },
        store=False,
    )

    if not response.output_text:
        raise ValueError("لم يرجع OpenAI نتيجة للمطابقة.")

    try:
        parsed = json.loads(response.output_text)
    except json.JSONDecodeError as error:
        raise ValueError("تعذر قراءة نتيجة المطابقة.") from error

    return _sanitize(parsed, column_names, factor_names)