# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import find_dotenv, load_dotenv


# ==================================================
# تحميل .env
# ==================================================

def _get_env_path() -> Path | None:
    current_file = Path(__file__).resolve()

    candidates = [
        Path.cwd() / ".env",
        current_file.parent / ".env",
        current_file.parent.parent / ".env",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    found = find_dotenv(filename=".env", usecwd=True)
    if found:
        return Path(found)

    return None


ENV_PATH = _get_env_path()

if ENV_PATH is not None:
    load_dotenv(dotenv_path=ENV_PATH, override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()


# الحقول التي نطابقها. المفتاح = الاسم البرمجي، القيمة = كلمات مفتاحية للتخمين.
FIELD_KEYWORDS: dict[str, list[str]] = {
    "number_column": [
        "رقم المبادرة", "رقم المبادره", "رقم", "المعرف", "المعرّف",
        "رمز المبادرة", "رمز", "الرقم", "رقم الطلب", "معرف المبادرة",
        "initiative number", "initiative id", "number", "no", "code",
        "ref", "id",
    ],
    "section_column": [
        "قسم", "القسم", "الاقسام", "الأقسام", "قطاع", "القطاع",
        "ادارة", "الادارة", "الإدارة", "section", "department", "sector",
    ],
    "product_column": [
        "منتج", "المنتج", "المنتجات", "خدمة", "الخدمة", "الخدمات",
        "product", "service",
    ],
    "status_column": [
        "حالة المبادرة", "حالة", "الحالة", "الوضع", "المرحلة",
        "status", "state", "stage",
    ],
    "initiative_column": [
        "عنوان المبادرة", "اسم المبادرة", "عنوان", "مبادرة", "المبادرة",
        "المبادرات", "اجراء", "إجراء", "الاجراء", "الإجراء", "المهمة",
        "العمل", "النشاط", "initiative", "action", "task", "activity", "name",
    ],
    "creation_date_column": [
        "تاريخ الانشاء", "تاريخ الإنشاء", "الانشاء", "الإنشاء", "تاريخ الادخال",
        "creation", "created", "create date",
    ],
    "start_date_column": [
        "تاريخ البدء", "تاريخ البداية", "البدء", "البداية", "تاريخ الانطلاق",
        "start", "begin", "kickoff",
    ],
    "expected_execution_date_column": [
        "تاريخ التنفيذ", "التنفيذ المتوقع", "تاريخ التنفيذ المتوقع", "المتوقع",
        "تاريخ الانتهاء المتوقع", "الاستحقاق", "expected execution",
        "expected", "execution", "due", "target",
    ],
    "actual_execution_date_column": [
        "التاريخ الفعلي", "التنفيذ الفعلي", "تاريخ التنفيذ الفعلي",
        "الفعلي", "تاريخ الانتهاء الفعلي", "تاريخ الانجاز", "الإنجاز",
        "actual execution", "actual", "completion", "completed", "done date",
    ],
}


def _empty_result() -> dict[str, Any]:
    return {
        "number_column": None,
        "section_column": None,
        "product_column": None,
        "initiative_column": None,
        "status_column": None,
        "creation_date_column": None,
        "start_date_column": None,
        "expected_execution_date_column": None,
        "actual_execution_date_column": None,
        "warnings": [],
    }


def _normalize(text: str) -> str:
    """تبسيط النص للمقارنة: حروف صغيرة، وتوحيد الألف، وإزالة الرموز."""
    text = str(text).strip().lower()
    text = (
        text.replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ة", "ه")
        .replace("_", " ")
        .replace("-", " ")
    )
    return " ".join(text.split())


# ==================================================
# المطابقة المحلية بالكلمات المفتاحية (بدون اتصال)
# ==================================================

def map_initiative_columns_heuristic(
    column_names: list[str],
) -> dict[str, Any]:
    """تخمين مبدئي لأسماء الأعمدة اعتمادًا على الكلمات المفتاحية فقط."""
    result = _empty_result()
    used_columns: set[str] = set()

    normalized_columns = [
        (column, _normalize(column)) for column in column_names
    ]

    for field_name, keywords in FIELD_KEYWORDS.items():
        best_column = None
        best_score = 0

        for original, normalized in normalized_columns:
            if original in used_columns:
                continue

            # النتيجة مرجّحة بطول الكلمة المفتاحية: الكلمات الأكثر تحديدًا
            # (مثل "تاريخ التنفيذ المتوقع") تتغلّب على الكلمات العامة المشتركة
            # (مثل "التنفيذ") حتى لا يختلط "المتوقع" بـ "الفعلي".
            score = 0
            for keyword in keywords:
                keyword_normalized = _normalize(keyword)

                if keyword_normalized == normalized:
                    score = max(score, 1000 + len(keyword_normalized))
                elif keyword_normalized in normalized:
                    score = max(score, 100 + len(keyword_normalized))
                elif normalized in keyword_normalized:
                    score = max(score, 10 + len(normalized))

            if score > best_score:
                best_score = score
                best_column = original

        if best_column is not None:
            result[field_name] = best_column
            used_columns.add(best_column)

    return result


# ==================================================
# المطابقة باستخدام Gemini (مع رجوع تلقائي للمطابقة المحلية)
# ==================================================

def _map_with_gemini(column_names: list[str]) -> dict[str, Any]:
    """محاولة المطابقة عبر Gemini. ترفع استثناءً عند أي فشل."""
    from google import genai
    from pydantic import BaseModel

    class InitiativeColumnMapping(BaseModel):
        number_column: str | None
        section_column: str | None
        product_column: str | None
        initiative_column: str | None
        status_column: str | None
        creation_date_column: str | None
        start_date_column: str | None
        expected_execution_date_column: str | None
        actual_execution_date_column: str | None
        warnings: list[str]

    client = genai.Client(api_key=GEMINI_API_KEY)

    columns_text = "\n".join(f"- {column}" for column in column_names)

    prompt = f"""
أنت نظام لمطابقة أسماء أعمدة Excel مع حقول بيانات المبادرات
في منصة تجربة العميل.

أسماء أعمدة Excel المتاحة:
{columns_text}

التزم بالقواعد التالية بدقة:

1. استخدم فقط أسماء الأعمدة الموجودة في القائمة أعلاه حرفيًا.
2. لا تفترض أي قيمة من داخل الصفوف.
3. طابق الحقول التالية:
   - number_column = رقم المبادرة أو معرّفها أو رمزها.
   - section_column = اسم القسم أو الإدارة أو القطاع.
   - product_column = اسم المنتج أو الخدمة.
   - initiative_column = اسم المبادرة أو الإجراء أو المهمة.
   - status_column = حالة المبادرة (مثل: منجزة، قيد التنفيذ).
   - creation_date_column = تاريخ الإنشاء (اختياري).
   - start_date_column = تاريخ البدء (اختياري).
   - expected_execution_date_column = تاريخ التنفيذ المتوقع (اختياري).
   - actual_execution_date_column = التاريخ الفعلي للتنفيذ أو الإنجاز (اختياري).
4. إذا لم تجد حقلًا بثقة، استخدم null بدل التخمين، وأضف تحذيرًا مناسبًا.
5. لا تستخدم العمود نفسه لأكثر من حقل.
6. ميّز بدقة بين "المتوقع" و"الفعلي": عمود التنفيذ المتوقع يختلف عن
   عمود التنفيذ الفعلي، ولا تضعهما في نفس الحقل.
"""

    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": InitiativeColumnMapping.model_json_schema(),
        },
        store=False,
    )

    if not interaction.output_text:
        raise ValueError("لم يرجع Gemini نتيجة للمطابقة.")

    parsed = InitiativeColumnMapping.model_validate_json(
        interaction.output_text
    )

    allowed = set(column_names)

    def valid(value: Any) -> str | None:
        if isinstance(value, str) and value.strip() in allowed:
            return value.strip()
        return None

    return {
        "number_column": valid(parsed.number_column),
        "section_column": valid(parsed.section_column),
        "product_column": valid(parsed.product_column),
        "initiative_column": valid(parsed.initiative_column),
        "status_column": valid(parsed.status_column),
        "creation_date_column": valid(parsed.creation_date_column),
        "start_date_column": valid(parsed.start_date_column),
        "expected_execution_date_column": valid(
            parsed.expected_execution_date_column
        ),
        "actual_execution_date_column": valid(
            parsed.actual_execution_date_column
        ),
        "warnings": [
            str(item).strip()
            for item in parsed.warnings
            if str(item).strip()
        ],
    }


def map_initiative_columns_with_ai(
    column_names: list[str],
) -> dict[str, Any]:
    """
    يحاول المطابقة عبر Gemini أولًا، وإذا لم يتوفّر المفتاح أو فشل الاتصال
    يرجع تلقائيًا إلى المطابقة المحلية بالكلمات المفتاحية.

    يضيف حقل "source" ليعرف الاستدعاء أي طريقة استُخدمت:
        "ai"        عند نجاح Gemini
        "heuristic" عند استخدام المطابقة المحلية
    """
    if GEMINI_API_KEY:
        try:
            result = _map_with_gemini(column_names)
            result["source"] = "ai"
            return result
        except Exception as error:
            fallback = map_initiative_columns_heuristic(column_names)
            fallback["source"] = "heuristic"
            fallback.setdefault("warnings", []).append(
                "تعذّر استخدام الذكاء الاصطناعي، تم استخدام المطابقة "
                f"التلقائية بدلًا منه ({error})."
            )
            return fallback

    result = map_initiative_columns_heuristic(column_names)
    result["source"] = "heuristic"
    return result