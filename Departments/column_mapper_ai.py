# -*- coding: utf-8 -*-
"""
column_mapper_ai.py
-------------------
مطابقة أسماء أعمدة Excel مع حقول رفع بيانات الجهات باستخدام Gemini.

مهم:
يتم إرسال أسماء الأعمدة وأسماء عوامل CSAT فقط.
لا يتم إرسال بيانات الصفوف أو إجابات العملاء أو التعليقات.
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

class FactorMapping(BaseModel):
    factor_name: str
    column_name: str | None


class SectionColumnMapping(BaseModel):
    service_column: str | None
    section_column: str | None

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

    response_id_column: str | None
    participants_column: str | None

    factor_mappings: list[FactorMapping]

    ces_columns: list[str]
    nps_column: str | None
    bps_column: str | None

    warnings: list[str]


# ==================================================
# تنظيف نتيجة Gemini
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
    result: SectionColumnMapping,
    columns: list[str],
    factors: list[str],
) -> dict[str, Any]:
    allowed = set(columns)

    factor_result: dict[str, str | None] = {}

    for item in result.factor_mappings:
        if item.factor_name not in factors:
            continue

        factor_result[item.factor_name] = (
            _valid_column(
                item.column_name,
                allowed,
            )
        )

    ces_columns: list[str] = []

    for column in result.ces_columns:
        safe_column = _valid_column(
            column,
            allowed,
        )

        if (
            safe_column
            and safe_column not in ces_columns
        ):
            ces_columns.append(
                safe_column
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
        "service_column":
            _valid_column(
                result.service_column,
                allowed,
            ),

        "section_column":
            _valid_column(
                result.section_column,
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

        "response_id_column":
            _valid_column(
                result.response_id_column,
                allowed,
            ),

        "participants_column":
            _valid_column(
                result.participants_column,
                allowed,
            ),

        "factor_mappings": {
            factor_name:
                factor_result.get(
                    factor_name
                )
            for factor_name in factors
        },

        "ces_columns":
            ces_columns,

        "nps_column":
            _valid_column(
                result.nps_column,
                allowed,
            ),

        "bps_column":
            _valid_column(
                result.bps_column,
                allowed,
            ),

        "warnings": [
            str(item).strip()
            for item in result.warnings
            if str(item).strip()
        ],
    }


# ==================================================
# المطابقة باستخدام Gemini
# ==================================================

def map_section_columns_with_ai(
    column_names: list[str],
    factor_names: list[str],
    data_mode: str,
) -> dict[str, Any]:
    """
    يرسل إلى Gemini:
    - أسماء أعمدة Excel فقط.
    - أسماء عوامل CSAT المطلوبة.
    - نوع البيانات raw أو calculated.

    لا يتم إرسال محتوى الصفوف.
    """

    if not GEMINI_API_KEY:
        raise ValueError(
            "مفتاح GEMINI_API_KEY غير موجود. "
            f"ملف البيئة المستخدم: {ENV_PATH}"
        )

    if data_mode not in {
        "raw",
        "calculated",
    }:
        raise ValueError(
            "data_mode يجب أن يكون raw أو calculated."
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

    prompt = f"""
أنت نظام لمطابقة أسماء أعمدة Excel مع حقول منصة تجربة العميل.

نوع البيانات:
{data_mode}

أسماء أعمدة Excel المتاحة:
{columns_text}

عوامل CSAT المطلوبة:
{factors_text}

التزم بالقواعد التالية بدقة:

1. استخدم فقط أسماء الأعمدة الموجودة في قائمة أعمدة Excel حرفيًا.
2. لا تطلب ولا تفترض أي قيم من داخل الصفوف.
3. لا تطابق أعمدة التعليقات أو الملاحظات؛ المستخدم سيختارها بنفسه.
4. service_column:
   عمود اسم الخدمة.
5. section_column:
   عمود القسم أو الإدارة إذا وجد.
6. time_mode:
   - date: يوجد عمود تاريخ يمكن استخراج السنة والنصف منه.
   - combined: السنة والفترة موجودتان في عمود واحد.
   - separate: السنة والفترة في عمودين منفصلين.
   - unknown: لا يمكن تحديد الطريقة بثقة.
7. إذا كان data_mode = raw:
   - اربط كل عامل CSAT بعمود إجابات خام من 1 إلى 5.
   - حدد أعمدة CES الخام إن وجدت.
   - حدد عمود NPS الخام إن وجد.
   - حدد response_id_column إن وجد.
   - participants_column يجب أن يكون null.
   - bps_column يجب أن يكون null.
8. إذا كان data_mode = calculated:
   - اربط كل عامل CSAT بعمود نتيجته المحسوبة.
   - حدد نتيجة CES إن وجدت.
   - حدد نتيجة NPS إن وجدت.
   - حدد نتيجة BPS إن وجدت.
   - حدد عدد المشاركين إن وجد.
   - response_id_column يجب أن يكون null.
9. لا تستخدم العمود نفسه لأكثر من عامل أو مؤشر.
10. إذا كان العمود عامًا مثل Q1 أو Question 1 بلا وصف كافٍ:
    لا تخمن، أرجع null وأضف تحذيرًا.
11. أرجع factor_mappings لكل عامل مطلوب،
    حتى لو كانت column_name = null.
12. إذا لم تجد حقلًا بثقة، استخدم null بدل التخمين.
"""

    interaction = client.interactions.create(
        model=GEMINI_MODEL,
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema":
                SectionColumnMapping.model_json_schema(),
        },
        store=False,
    )

    if not interaction.output_text:
        raise ValueError(
            "لم يرجع Gemini نتيجة للمطابقة."
        )

    try:
        parsed = (
            SectionColumnMapping
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
    )
