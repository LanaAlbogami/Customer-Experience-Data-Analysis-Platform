# -*- coding: utf-8 -*-
"""
individuals_column_mapper_ai.py
-------------------------------
مطابقة أسماء أعمدة Excel مع حقول بيانات الأفراد باستخدام Gemini.

مهم:
يتم إرسال أسماء الأعمدة + أسماء عوامل CSAT + أسماء المؤشرات فقط.
لا يتم إرسال محتوى الصفوف أو إجابات العملاء أو التعليقات.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from dotenv import find_dotenv, load_dotenv
from google import genai
from pydantic import BaseModel


# ==================================================
# تحميل .env
# ==================================================

def _get_env_path() -> Path:
    current_file = Path(__file__).resolve()

    candidates = [
        Path.cwd() / ".env",
        current_file.parent / ".env",
        current_file.parent.parent / ".env",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    found = find_dotenv(
        filename=".env",
        usecwd=True,
    )

    if found:
        return Path(found)

    raise RuntimeError(
        "لم يتم العثور على ملف .env. "
        "تأكدي أنه موجود في مجلد المشروع بجانب main.py."
    )


ENV_PATH = _get_env_path()

load_dotenv(
    dotenv_path=ENV_PATH,
    override=True,
)

GEMINI_API_KEY = os.getenv(
    "GEMINI_API_KEY",
    "",
).strip()

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
).strip()


# ==================================================
# شكل النتيجة المطلوبة من Gemini
# ==================================================

class NamedColumnMapping(BaseModel):
    name: str
    column_name: str | None


class IndividualColumnMapping(BaseModel):
    individual_id_column: str | None

    time_mode: Literal[
        "date",
        "combined",
        "separate",
        "unknown",
    ]

    date_column: str | None
    combined_time_column: str | None
    year_column: str | None
    period_column: str | None

    gender_column: str | None
    age_group_column: str | None
    id_type_column: str | None
    education_column: str | None
    device_column: str | None
    region_column: str | None

    factor_mappings: list[NamedColumnMapping]
    indicator_mappings: list[NamedColumnMapping]

    warnings: list[str]


# ==================================================
# أدوات التحقق من نتيجة Gemini
# ==================================================

def _valid_column(
    value: Any,
    allowed: set[str],
) -> str | None:
    if not isinstance(value, str):
        return None

    value = value.strip()

    if value in allowed:
        return value

    return None


def _sanitize(
    result: IndividualColumnMapping,
    columns: list[str],
    factor_names: list[str],
    indicator_names: list[str],
) -> dict[str, Any]:
    allowed = set(columns)

    factor_result: dict[str, str | None] = {}

    for item in result.factor_mappings:
        if item.name not in factor_names:
            continue

        factor_result[item.name] = _valid_column(
            item.column_name,
            allowed,
        )

    indicator_result: dict[str, str | None] = {}

    for item in result.indicator_mappings:
        if item.name not in indicator_names:
            continue

        indicator_result[item.name] = _valid_column(
            item.column_name,
            allowed,
        )

    time_mode = result.time_mode

    if time_mode not in {
        "date",
        "combined",
        "separate",
        "unknown",
    }:
        time_mode = "unknown"

    return {
        "individual_id_column":
            _valid_column(
                result.individual_id_column,
                allowed,
            ),

        "time_mode":
            time_mode,

        "date_column":
            _valid_column(
                result.date_column,
                allowed,
            ),

        "combined_time_column":
            _valid_column(
                result.combined_time_column,
                allowed,
            ),

        "year_column":
            _valid_column(
                result.year_column,
                allowed,
            ),

        "period_column":
            _valid_column(
                result.period_column,
                allowed,
            ),

        "gender_column":
            _valid_column(
                result.gender_column,
                allowed,
            ),

        "age_group_column":
            _valid_column(
                result.age_group_column,
                allowed,
            ),

        "id_type_column":
            _valid_column(
                result.id_type_column,
                allowed,
            ),

        "education_column":
            _valid_column(
                result.education_column,
                allowed,
            ),

        "device_column":
            _valid_column(
                result.device_column,
                allowed,
            ),

        "region_column":
            _valid_column(
                result.region_column,
                allowed,
            ),

        "factor_mappings": {
            factor_name:
                factor_result.get(
                    factor_name
                )
            for factor_name in factor_names
        },

        "indicator_mappings": {
            indicator_name:
                indicator_result.get(
                    indicator_name
                )
            for indicator_name in indicator_names
        },

        "warnings": [
            str(item).strip()
            for item in result.warnings
            if str(item).strip()
        ],
    }


# ==================================================
# المطابقة باستخدام Gemini
# ==================================================

def map_individual_columns_with_ai(
    column_names: list[str],
    factor_names: list[str],
    indicator_names: list[str],
) -> dict[str, Any]:
    """
    يرسل إلى Gemini أسماء الأعمدة فقط،
    بالإضافة إلى أسماء عوامل CSAT وأسماء المؤشرات المطلوبة.
    """

    if not GEMINI_API_KEY:
        raise ValueError(
            "مفتاح GEMINI_API_KEY غير موجود. "
            f"ملف البيئة المستخدم: {ENV_PATH}"
        )

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    columns_text = "\n".join(
        f"- {column}"
        for column in column_names
    )

    factors_text = "\n".join(
        f"- {factor}"
        for factor in factor_names
    )

    indicators_text = "\n".join(
        f"- {indicator}"
        for indicator in indicator_names
    )

    prompt = f"""
أنت نظام لمطابقة أسماء أعمدة Excel مع حقول بيانات الأفراد
في منصة تجربة العميل.

أسماء أعمدة Excel المتاحة:
{columns_text}

عوامل CSAT المطلوبة:
{factors_text}

المؤشرات المطلوبة:
{indicators_text}

التزم بالقواعد التالية بدقة:

1. استخدم فقط أسماء الأعمدة الموجودة في قائمة Excel حرفيًا.
2. لا تطلب ولا تفترض أي قيمة من داخل الصفوف.
3. لا تطابق أعمدة التعليقات أو الملاحظات؛ المستخدم سيختارها بنفسه.
4. individual_id_column:
   اربطه فقط إذا كان هناك عمود معرف فرد واضح مثل:
   IndividualID أو Individual ID.
   لا تستخدم ResponseId بدلًا منه إلا إذا كان واضحًا أنه معرف الفرد.
5. time_mode:
   - date: يوجد عمود تاريخ يمكن استخراج السنة والربع منه.
   - combined: السنة والربع موجودان في عمود واحد.
   - separate: السنة والربع في عمودين منفصلين.
   - unknown: لا يمكن تحديد الطريقة بثقة.
6. طابق الحقول الديموغرافية إن وجدت:
   - gender_column = الجنس
   - age_group_column = الفئة العمرية
   - id_type_column = نوع الهوية
   - education_column = المستوى التعليمي
   - device_column = الجهاز أو نوع الجهاز
   - region_column = المنطقة
7. اربط كل عامل CSAT بعمود الإجابة الخاص به.
8. اربط كل مؤشر مطلوب بعمود الإجابة الخاص به.
9. لا تستخدم العمود نفسه لأكثر من عامل أو مؤشر.
10. إذا كان العمود عامًا مثل Q1 أو Question 1 بلا وصف كافٍ:
    لا تخمن، أرجع null وأضف تحذيرًا.
11. أرجع factor_mappings لكل عامل مطلوب،
    حتى لو كانت column_name = null.
12. أرجع indicator_mappings لكل مؤشر مطلوب،
    حتى لو كانت column_name = null.
13. إذا لم تجد حقلًا بثقة، استخدم null بدل التخمين.
14. لا تعتبر أعمدة مثل "ملاحظات إضافية" عوامل أو مؤشرات.
"""

    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema":
                IndividualColumnMapping.model_json_schema(),
        },
        store=False,
    )

    if not interaction.output_text:
        raise ValueError(
            "لم يرجع Gemini نتيجة للمطابقة."
        )

    try:
        parsed = (
            IndividualColumnMapping
            .model_validate_json(
                interaction.output_text
            )
        )

    except Exception as error:
        raise ValueError(
            "تعذر قراءة نتيجة مطابقة Gemini."
        ) from error

    return _sanitize(
        parsed,
        column_names,
        factor_names,
        indicator_names,
    )
