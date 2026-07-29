from datetime import datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO

import pandas as pd
import streamlit as st
from sqlalchemy import select

from database.connection import SessionLocal
from database.models import (
    Department,
    Indicator,
    IndicatorResult,
    MeasurementRecord,
    Service,
)
from style import apply_theme


# =========================================================
# تطبيق الستايل المشترك كما هو، دون أي تعديل على style.py
# =========================================================

apply_theme()


# =========================================================
# ثوابت الصفحة
# =========================================================

CHOOSE_COLUMN = "-- اختاري العمود --"
NO_COLUMN = "غير موجود"

DEPARTMENT_FROM_COLUMN = "من عمود داخل الملف"
DEPARTMENT_FIXED = "قسم واحد لكل الملف"

TIME_FROM_DATE = "من عمود تاريخ"
TIME_FROM_COLUMNS = "من عمود السنة وعمود الفترة"
TIME_FIXED = "سنة وفترة ثابتة لكل الملف"

RAW_INDICATORS = "إجابات استبيان خام"
CALCULATED_INDICATORS = "مؤشرات محسوبة مسبقًا"
COMMENTS_ONLY = "تعليقات فقط"

TARGET_FIXED = "قيم ثابتة"
TARGET_FROM_COLUMNS = "من أعمدة داخل الملف"

PERCENTAGE_FROM_0_TO_100 = "القيم من 0 إلى 100"
PERCENTAGE_FROM_0_TO_1 = "القيم من 0 إلى 1"

IGNORED_COMMENTS = {
    "",
    "nan",
    "none",
    "null",
    "لا يوجد",
    "لا يوجد تعليق",
    "لا يوجد تعليق.",
    "لا توجد ملاحظات",
    "لا توجد ملاحظة",
}

INDICATOR_SETTINGS = {
    "CSAT": {
        "unit": "%",
        "min_value": Decimal("0"),
        "max_value": Decimal("100"),
    },
    "CES": {
        "unit": "%",
        "min_value": Decimal("0"),
        "max_value": Decimal("100"),
    },
    "NPS": {
        "unit": "Point",
        "min_value": Decimal("-100"),
        "max_value": Decimal("100"),
    },
}


# =========================================================
# دوال مساعدة
# =========================================================


def find_option_index(
    options: list[str],
    preferred_names: list[str],
) -> int:
    """اختيار اسم متوقع تلقائيًا إذا كان موجودًا."""

    for preferred_name in preferred_names:
        if preferred_name in options:
            return options.index(preferred_name)

    return 0


def find_existing_options(
    available_columns: list[str],
    preferred_names: list[str],
) -> list[str]:
    """إرجاع أسماء الأعمدة المتوقعة الموجودة فعلًا في الملف."""

    return [
        column
        for column in preferred_names
        if column in available_columns
    ]


def clean_text(value) -> str:
    """تحويل القيمة إلى نص نظيف."""

    if pd.isna(value):
        return ""

    return str(value).strip()


def get_invalid_excel_rows(
    dataframe: pd.DataFrame,
    invalid_mask: pd.Series,
) -> list[int]:
    """تحويل أرقام DataFrame إلى أرقام الصفوف الظاهرة في Excel."""

    invalid_indexes = dataframe.index[invalid_mask].tolist()

    return [
        int(index) + 2
        for index in invalid_indexes[:10]
    ]


def parse_decimal_value(
    value,
    field_name: str,
) -> Decimal | None:
    """قراءة رقم عادي أو نسبة مكتوبة مثل 85%."""

    if pd.isna(value):
        return None

    cleaned_value = (
        str(value)
        .strip()
        .replace("%", "")
        .replace(",", "")
    )

    if not cleaned_value:
        return None

    try:
        return Decimal(cleaned_value)

    except InvalidOperation as error:
        raise ValueError(
            f"القيمة الموجودة في '{field_name}' ليست رقمًا صحيحًا: {value}"
        ) from error


# =========================================================
# معالجة التاريخ والسنة والفترة
# =========================================================


def parse_date_column(series: pd.Series) -> pd.Series:
    """
    قراءة التواريخ النصية أو تواريخ Excel الرقمية.

    يدعم مثلًا:
    - 2025-07-15
    - 15/07/2025
    - 2025-07-15T00:00:00Z
    - أرقام Excel التسلسلية
    """

    result = pd.Series(
        pd.NaT,
        index=series.index,
        dtype="datetime64[ns]",
    )

    numeric_values = pd.to_numeric(
        series,
        errors="coerce",
    )

    numeric_mask = numeric_values.notna()

    if numeric_mask.any():
        excel_dates = pd.to_datetime(
            numeric_values.loc[numeric_mask],
            unit="D",
            origin="1899-12-30",
            errors="coerce",
        )

        result.loc[numeric_mask] = excel_dates.values

    text_mask = ~numeric_mask

    if text_mask.any():
        text_series = series.loc[text_mask]

        text_dates = pd.to_datetime(
            text_series,
            errors="coerce",
            utc=True,
        )

        remaining_mask = text_dates.isna()

        if remaining_mask.any():
            second_attempt = pd.to_datetime(
                text_series.loc[remaining_mask],
                errors="coerce",
                dayfirst=True,
                utc=True,
            )

            text_dates.loc[remaining_mask] = second_attempt

        text_dates = text_dates.dt.tz_convert(None)
        result.loc[text_mask] = text_dates.values

    return result


def period_from_month(month: int) -> str:
    """تحويل الشهر إلى نصف أول أو نصف ثانٍ."""

    if month <= 6:
        return "النصف الأول"

    return "النصف الثاني"


def normalize_arabic_text(value: str) -> str:
    """توحيد بسيط للنص العربي قبل المقارنة."""

    return (
        value
        .strip()
        .lower()
        .replace("أ", "ا")
        .replace("إ", "ا")
        .replace("آ", "ا")
        .replace("ة", "ه")
        .replace("ـ", "")
        .replace("_", " ")
        .replace("-", " ")
    )


def normalize_period_value(value) -> str | None:
    """تحويل القيم الشائعة للفترة إلى الصيغة المعتمدة في قاعدة البيانات."""

    if pd.isna(value):
        return None

    normalized = " ".join(
        normalize_arabic_text(str(value)).split()
    )

    first_half_values = {
        "1",
        "1.0",
        "h1",
        "half 1",
        "first half",
        "النصف الاول",
        "النصف الاول من السنه",
        "الفتره الاولى",
        "الفتره 1",
    }

    second_half_values = {
        "2",
        "2.0",
        "h2",
        "half 2",
        "second half",
        "النصف الثاني",
        "النصف الثاني من السنه",
        "الفتره الثانيه",
        "الفتره 2",
    }

    if normalized in first_half_values:
        return "النصف الأول"

    if normalized in second_half_values:
        return "النصف الثاني"

    return None


def period_order(period: str) -> int:
    """ترتيب الفترات زمنيًا."""

    if period == "النصف الأول":
        return 1

    if period == "النصف الثاني":
        return 2

    return 0


# =========================================================
# حساب المؤشرات من الإجابات الخام
# =========================================================


def calculate_positive_percentage(
    series: pd.Series,
) -> Decimal | None:
    """
    حساب نسبة الإجابات الإيجابية من مقياس 1 إلى 5.

    التقييمات 4 و5 إيجابية، والقيم خارج النطاق مثل 99 تُستبعد.
    """

    numeric_values = pd.to_numeric(
        series,
        errors="coerce",
    )

    valid_values = numeric_values[
        numeric_values.between(1, 5)
    ]

    if valid_values.empty:
        return None

    percentage = valid_values.ge(4).mean() * 100

    return Decimal(f"{percentage:.2f}")


def calculate_question_results(
    group: pd.DataFrame,
    selected_columns: list[str],
) -> dict[str, Decimal | None]:
    """حساب نتيجة مستقلة لكل سؤال CSAT أو CES مختار."""

    return {
        column_name: calculate_positive_percentage(
            group[column_name]
        )
        for column_name in selected_columns
    }


def calculate_average_result(
    question_results: dict[str, Decimal | None],
) -> Decimal | None:
    """حساب متوسط نتائج الأسئلة الصالحة."""

    valid_values = [
        value
        for value in question_results.values()
        if value is not None
    ]

    if not valid_values:
        return None

    average = sum(valid_values) / Decimal(len(valid_values))

    return average.quantize(Decimal("0.01"))


def calculate_nps(series: pd.Series) -> Decimal | None:
    """
    حساب NPS من مقياس 0 إلى 10.

    المروجون: 9 و10
    المحايدون: 7 و8
    غير المروجين: 0 إلى 6
    """

    numeric_values = pd.to_numeric(
        series,
        errors="coerce",
    )

    valid_values = numeric_values[
        numeric_values.between(0, 10)
    ]

    if valid_values.empty:
        return None

    promoters_percentage = valid_values.ge(9).mean() * 100
    detractors_percentage = valid_values.le(6).mean() * 100
    nps_value = promoters_percentage - detractors_percentage

    return Decimal(f"{nps_value:.2f}")


# =========================================================
# قراءة المؤشرات المحسوبة مسبقًا
# =========================================================


def read_unique_calculated_value(
    group: pd.DataFrame,
    column_name: str,
    indicator_name: str,
    min_value: Decimal,
    max_value: Decimal,
    percentage_scale: str,
) -> Decimal | None:
    """
    قراءة قيمة مؤشر محسوبة مسبقًا من المجموعة.

    يسمح بتكرار القيمة نفسها داخل المجموعة، لكنه يرفض وجود قيم مختلفة
    لنفس القسم والخدمة والسنة والفترة.
    """

    if column_name == NO_COLUMN:
        return None

    parsed_values: list[Decimal] = []

    for raw_value in group[column_name]:
        parsed_value = parse_decimal_value(
            raw_value,
            column_name,
        )

        if parsed_value is None:
            continue

        if (
            indicator_name in {"CSAT", "CES"}
            and percentage_scale == PERCENTAGE_FROM_0_TO_1
        ):
            parsed_value *= Decimal("100")

        parsed_values.append(
            parsed_value.quantize(Decimal("0.01"))
        )

    if not parsed_values:
        return None

    unique_values = set(parsed_values)

    if len(unique_values) > 1:
        raise ValueError(
            f"يوجد أكثر من قيمة مختلفة لمؤشر {indicator_name} "
            "لنفس القسم والخدمة والسنة والفترة."
        )

    value = next(iter(unique_values))

    if value < min_value or value > max_value:
        raise ValueError(
            f"قيمة {indicator_name} خارج النطاق المسموح: {value}."
        )

    return value


def read_unique_participants_count(
    group: pd.DataFrame,
    column_name: str,
) -> int:
    """قراءة عدد المشاركين من ملف المؤشرات المحسوبة."""

    if column_name == NO_COLUMN:
        return len(group)

    numeric_values = pd.to_numeric(
        group[column_name],
        errors="coerce",
    ).dropna()

    if numeric_values.empty:
        raise ValueError(
            "عمود عدد المشاركين لا يحتوي على قيمة صالحة."
        )

    if (numeric_values % 1 != 0).any():
        raise ValueError(
            "عدد المشاركين يجب أن يكون عددًا صحيحًا."
        )

    if (numeric_values < 0).any():
        raise ValueError(
            "عدد المشاركين لا يمكن أن يكون سالبًا."
        )

    unique_values = numeric_values.astype(int).unique()

    if len(unique_values) > 1:
        raise ValueError(
            "يوجد أكثر من عدد مشاركين مختلف لنفس القسم والخدمة والسنة والفترة."
        )

    return int(unique_values[0])


# =========================================================
# معالجة التعليقات
# =========================================================


def collect_comments(
    group: pd.DataFrame,
    comment_columns: list[str],
) -> str | None:
    """جمع التعليقات مع حذف الفارغ والمكرر."""

    comments: list[str] = []
    normalized_comments: set[str] = set()

    for column_name in comment_columns:
        for value in group[column_name]:
            if pd.isna(value):
                continue

            raw_text = str(value).strip()

            if not raw_text:
                continue

            for comment_line in raw_text.splitlines():
                comment = comment_line.strip()
                normalized_comment = comment.lower().strip()

                if normalized_comment in IGNORED_COMMENTS:
                    continue

                if normalized_comment in normalized_comments:
                    continue

                normalized_comments.add(normalized_comment)
                comments.append(comment)

    if not comments:
        return None

    return "\n".join(comments)


def append_review(
    record: MeasurementRecord,
    new_review: str | None,
) -> None:
    """إضافة التعليقات الجديدة إلى Review بدون تكرارها."""

    if not new_review:
        return

    if not record.review:
        record.review = new_review
        return

    existing_lines = {
        line.strip().lower()
        for line in record.review.splitlines()
        if line.strip()
    }

    lines_to_add: list[str] = []

    for line in new_review.splitlines():
        cleaned_line = line.strip()

        if not cleaned_line:
            continue

        normalized_line = cleaned_line.lower()

        if normalized_line in existing_lines:
            continue

        existing_lines.add(normalized_line)
        lines_to_add.append(cleaned_line)

    if lines_to_add:
        record.review += "\n" + "\n".join(lines_to_add)


# =========================================================
# تجهيز البيانات قبل الحفظ
# =========================================================


def prepare_upload_summary(
    dataframe: pd.DataFrame,
    service_column: str,
    response_id_column: str,
    department_source: str,
    department_column: str,
    fixed_department_name: str,
    time_source: str,
    date_column: str,
    year_column: str,
    period_column: str,
    selected_year: int,
    selected_period: str,
    indicator_mode: str,
    raw_csat_columns: list[str],
    raw_ces_columns: list[str],
    raw_nps_column: str,
    calculated_csat_column: str,
    calculated_ces_column: str,
    calculated_nps_column: str,
    participants_count_column: str,
    percentage_scale: str,
    target_source: str,
    fixed_targets: dict[str, Decimal],
    target_columns: dict[str, str],
    comment_columns: list[str],
) -> list[dict]:
    """
    تحويل الملف إلى سجلات مجمعة حسب:

    القسم + الخدمة + السنة + الفترة
    """

    working_dataframe = dataframe.copy()

    # -----------------------------------------------------
    # الخدمة
    # -----------------------------------------------------

    working_dataframe["_service"] = (
        working_dataframe[service_column]
        .apply(clean_text)
    )

    invalid_service_mask = (
        working_dataframe["_service"] == ""
    )

    if invalid_service_mask.any():
        invalid_rows = get_invalid_excel_rows(
            working_dataframe,
            invalid_service_mask,
        )

        raise ValueError(
            "يوجد اسم خدمة فارغ في الصفوف: "
            + "، ".join(map(str, invalid_rows))
        )

    # -----------------------------------------------------
    # القسم
    # -----------------------------------------------------

    if department_source == DEPARTMENT_FIXED:
        department_name = fixed_department_name.strip()

        if not department_name:
            raise ValueError(
                "اكتبي اسم القسم الذي يخص جميع صفوف الملف."
            )

        working_dataframe["_department"] = department_name

    else:
        working_dataframe["_department"] = (
            working_dataframe[department_column]
            .apply(clean_text)
        )

        invalid_department_mask = (
            working_dataframe["_department"] == ""
        )

        if invalid_department_mask.any():
            invalid_rows = get_invalid_excel_rows(
                working_dataframe,
                invalid_department_mask,
            )

            raise ValueError(
                "يوجد اسم قسم فارغ في الصفوف: "
                + "، ".join(map(str, invalid_rows))
            )

    # -----------------------------------------------------
    # السنة والفترة
    # -----------------------------------------------------

    if time_source == TIME_FROM_DATE:
        parsed_dates = parse_date_column(
            working_dataframe[date_column]
        )

        invalid_date_mask = parsed_dates.isna()

        if invalid_date_mask.any():
            invalid_rows = get_invalid_excel_rows(
                working_dataframe,
                invalid_date_mask,
            )

            raise ValueError(
                "تعذر قراءة التاريخ في الصفوف: "
                + "، ".join(map(str, invalid_rows))
            )

        working_dataframe["_year"] = (
            parsed_dates.dt.year.astype(int)
        )

        working_dataframe["_period"] = (
            parsed_dates.dt.month.apply(period_from_month)
        )

    elif time_source == TIME_FROM_COLUMNS:
        year_values = pd.to_numeric(
            working_dataframe[year_column],
            errors="coerce",
        )

        invalid_year_mask = (
            year_values.isna()
            | (year_values % 1 != 0)
            | ~year_values.between(2000, 2100)
        )

        if invalid_year_mask.any():
            invalid_rows = get_invalid_excel_rows(
                working_dataframe,
                invalid_year_mask,
            )

            raise ValueError(
                "قيمة السنة غير صحيحة في الصفوف: "
                + "، ".join(map(str, invalid_rows))
            )

        normalized_periods = (
            working_dataframe[period_column]
            .apply(normalize_period_value)
        )

        invalid_period_mask = normalized_periods.isna()

        if invalid_period_mask.any():
            invalid_rows = get_invalid_excel_rows(
                working_dataframe,
                invalid_period_mask,
            )

            raise ValueError(
                "قيمة الفترة غير معروفة في الصفوف: "
                + "، ".join(map(str, invalid_rows))
                + ". استخدمي النصف الأول أو النصف الثاني."
            )

        working_dataframe["_year"] = year_values.astype(int)
        working_dataframe["_period"] = normalized_periods

    else:
        working_dataframe["_year"] = int(selected_year)
        working_dataframe["_period"] = selected_period

    # -----------------------------------------------------
    # التجميع
    # -----------------------------------------------------

    grouped_dataframe = working_dataframe.groupby(
        [
            "_department",
            "_service",
            "_year",
            "_period",
        ],
        sort=True,
        dropna=False,
    )

    summary_rows: list[dict] = []

    for (
        department_name,
        service_name,
        year,
        period,
    ), group in grouped_dataframe:
        update_participants_count = True

        if indicator_mode == CALCULATED_INDICATORS:
            participants_count = read_unique_participants_count(
                group=group,
                column_name=participants_count_column,
            )

        elif indicator_mode == COMMENTS_ONLY:
            participants_count = len(group)
            update_participants_count = False

        elif response_id_column != NO_COLUMN:
            participants_count = int(
                group[response_id_column]
                .dropna()
                .nunique()
            )

            if participants_count == 0:
                participants_count = len(group)

        else:
            participants_count = len(group)

        review = collect_comments(
            group=group,
            comment_columns=comment_columns,
        )

        csat_value = None
        ces_value = None
        nps_value = None
        row_targets: dict[str, Decimal] = {}

        if indicator_mode == RAW_INDICATORS:
            csat_question_results = calculate_question_results(
                group=group,
                selected_columns=raw_csat_columns,
            )

            ces_question_results = calculate_question_results(
                group=group,
                selected_columns=raw_ces_columns,
            )

            csat_value = calculate_average_result(
                csat_question_results
            )

            ces_value = calculate_average_result(
                ces_question_results
            )

            if raw_nps_column != NO_COLUMN:
                nps_value = calculate_nps(
                    group[raw_nps_column]
                )

            for indicator_name, current_value in {
                "CSAT": csat_value,
                "CES": ces_value,
                "NPS": nps_value,
            }.items():
                if current_value is not None:
                    row_targets[indicator_name] = fixed_targets[
                        indicator_name
                    ]

        elif indicator_mode == CALCULATED_INDICATORS:
            csat_value = read_unique_calculated_value(
                group=group,
                column_name=calculated_csat_column,
                indicator_name="CSAT",
                min_value=Decimal("0"),
                max_value=Decimal("100"),
                percentage_scale=percentage_scale,
            )

            ces_value = read_unique_calculated_value(
                group=group,
                column_name=calculated_ces_column,
                indicator_name="CES",
                min_value=Decimal("0"),
                max_value=Decimal("100"),
                percentage_scale=percentage_scale,
            )

            nps_value = read_unique_calculated_value(
                group=group,
                column_name=calculated_nps_column,
                indicator_name="NPS",
                min_value=Decimal("-100"),
                max_value=Decimal("100"),
                percentage_scale=PERCENTAGE_FROM_0_TO_100,
            )

            for indicator_name, current_value in {
                "CSAT": csat_value,
                "CES": ces_value,
                "NPS": nps_value,
            }.items():
                if current_value is None:
                    continue

                if target_source == TARGET_FIXED:
                    row_targets[indicator_name] = fixed_targets[
                        indicator_name
                    ]

                else:
                    settings = INDICATOR_SETTINGS[indicator_name]
                    target_column = target_columns[indicator_name]

                    target_value = read_unique_calculated_value(
                        group=group,
                        column_name=target_column,
                        indicator_name=f"مستهدف {indicator_name}",
                        min_value=settings["min_value"],
                        max_value=settings["max_value"],
                        percentage_scale=(
                            percentage_scale
                            if indicator_name in {"CSAT", "CES"}
                            else PERCENTAGE_FROM_0_TO_100
                        ),
                    )

                    if target_value is None:
                        raise ValueError(
                            f"لا توجد قيمة مستهدفة صالحة لمؤشر {indicator_name}."
                        )

                    row_targets[indicator_name] = target_value

        summary_rows.append(
            {
                "department_name": str(department_name),
                "service_name": str(service_name),
                "year": int(year),
                "period": str(period),
                "participants_count": int(participants_count),
                "update_participants_count": update_participants_count,
                "review": review,
                "CSAT": csat_value,
                "CES": ces_value,
                "NPS": nps_value,
                "target_values": row_targets,
            }
        )

    summary_rows.sort(
        key=lambda row: (
            row["department_name"],
            row["service_name"],
            row["year"],
            period_order(row["period"]),
        )
    )

    return summary_rows


# =========================================================
# التعامل مع قاعدة البيانات
# =========================================================


def ensure_default_indicators(
    session,
) -> dict[str, Indicator]:
    """التأكد من وجود CSAT وCES وNPS في جدول Indicators."""

    indicators: dict[str, Indicator] = {}

    for indicator_name, settings in INDICATOR_SETTINGS.items():
        indicator = session.scalar(
            select(Indicator).where(
                Indicator.indicator_name == indicator_name
            )
        )

        if indicator is None:
            indicator = Indicator(
                indicator_name=indicator_name,
                unit=settings["unit"],
                min_value=settings["min_value"],
                max_value=settings["max_value"],
            )

            session.add(indicator)
            session.flush()

        indicators[indicator_name] = indicator

    return indicators


def get_previous_indicator_value(
    session,
    service_id: int,
    indicator_id: int,
    current_record_id: int,
    current_year: int,
    current_period: str,
) -> Decimal | None:
    """جلب قيمة المؤشر من أقرب فترة سابقة لنفس الخدمة."""

    previous_rows = session.execute(
        select(
            MeasurementRecord.year,
            MeasurementRecord.period,
            IndicatorResult.current_value,
        )
        .join(
            IndicatorResult,
            IndicatorResult.record_id
            == MeasurementRecord.record_id,
        )
        .where(
            MeasurementRecord.service_id == service_id,
            MeasurementRecord.record_id != current_record_id,
            IndicatorResult.indicator_id == indicator_id,
        )
    ).all()

    current_key = (
        current_year,
        period_order(current_period),
    )

    valid_previous_rows = []

    for (
        previous_year,
        previous_period,
        previous_value,
    ) in previous_rows:
        previous_key = (
            previous_year,
            period_order(previous_period),
        )

        if previous_key < current_key:
            valid_previous_rows.append(
                (
                    previous_key,
                    previous_value,
                )
            )

    if not valid_previous_rows:
        return None

    latest_previous_row = max(
        valid_previous_rows,
        key=lambda item: item[0],
    )

    return latest_previous_row[1]


def save_summary_to_database(
    summary_rows: list[dict],
) -> tuple[int, int]:
    """حفظ السجلات المجهزة في قاعدة البيانات."""

    inserted_records = 0
    updated_records = 0

    has_indicator_values = any(
        row["CSAT"] is not None
        or row["CES"] is not None
        or row["NPS"] is not None
        for row in summary_rows
    )

    with SessionLocal() as session:
        try:
            indicators: dict[str, Indicator] = {}

            if has_indicator_values:
                indicators = ensure_default_indicators(
                    session
                )

            for summary_row in summary_rows:
                department_name = summary_row[
                    "department_name"
                ]

                service_name = summary_row[
                    "service_name"
                ]

                # --------------------------------
                # القسم
                # --------------------------------

                department = session.scalar(
                    select(Department).where(
                        Department.department_name
                        == department_name
                    )
                )

                if department is None:
                    department = Department(
                        department_name=department_name
                    )

                    session.add(department)
                    session.flush()

                # --------------------------------
                # الخدمة
                # --------------------------------

                service = session.scalar(
                    select(Service).where(
                        Service.service_name == service_name,
                        Service.department_id
                        == department.department_id,
                    )
                )

                if service is None:
                    service = Service(
                        service_name=service_name,
                        department_id=department.department_id,
                    )

                    session.add(service)
                    session.flush()

                # --------------------------------
                # سجل القياس
                # --------------------------------

                record = session.scalar(
                    select(MeasurementRecord).where(
                        MeasurementRecord.service_id
                        == service.service_id,
                        MeasurementRecord.year
                        == summary_row["year"],
                        MeasurementRecord.period
                        == summary_row["period"],
                    )
                )

                if record is None:
                    record = MeasurementRecord(
                        service_id=service.service_id,
                        year=summary_row["year"],
                        period=summary_row["period"],
                        participants_count=summary_row[
                            "participants_count"
                        ],
                        review=summary_row["review"],
                    )

                    session.add(record)
                    session.flush()

                    inserted_records += 1

                else:
                    if summary_row[
                        "update_participants_count"
                    ]:
                        record.participants_count = summary_row[
                            "participants_count"
                        ]

                    append_review(
                        record=record,
                        new_review=summary_row["review"],
                    )

                    session.flush()

                    updated_records += 1

                # --------------------------------
                # نتائج المؤشرات
                # --------------------------------

                for indicator_name in (
                    "CSAT",
                    "CES",
                    "NPS",
                ):
                    current_value = summary_row[
                        indicator_name
                    ]

                    if current_value is None:
                        continue

                    target_value = summary_row[
                        "target_values"
                    ].get(indicator_name)

                    if target_value is None:
                        raise ValueError(
                            f"لم يتم تحديد مستهدف {indicator_name}."
                        )

                    indicator = indicators[
                        indicator_name
                    ]

                    previous_value = get_previous_indicator_value(
                        session=session,
                        service_id=service.service_id,
                        indicator_id=indicator.indicator_id,
                        current_record_id=record.record_id,
                        current_year=summary_row["year"],
                        current_period=summary_row["period"],
                    )

                    result = session.scalar(
                        select(IndicatorResult).where(
                            IndicatorResult.record_id
                            == record.record_id,
                            IndicatorResult.indicator_id
                            == indicator.indicator_id,
                        )
                    )

                    if result is None:
                        result = IndicatorResult(
                            record_id=record.record_id,
                            indicator_id=indicator.indicator_id,
                            prev_value=previous_value,
                            current_value=current_value,
                            target_value=target_value,
                        )

                        session.add(result)

                    else:
                        result.prev_value = previous_value
                        result.current_value = current_value
                        result.target_value = target_value

                    session.flush()

            session.commit()

            return inserted_records, updated_records

        except Exception:
            session.rollback()
            raise


# =========================================================
# واجهة Streamlit
# =========================================================

st.markdown(
    """
    <div dir="rtl" style="text-align: right;">
        <h1>رفع البيانات</h1>
        <p style="color: #7A7F94; font-size: 17px;">
            ارفع ملف Excel، وحدد وظيفة الأعمدة، ثم احفظ البيانات في قاعدة البيانات
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader(
    "اسحب ملف Excel هنا أو اضغط للاختيار",
    type=["xlsx", "xls"],
    key="data_upload_file_uploader",
)


if uploaded_file is not None:
    try:
        uploaded_bytes = uploaded_file.getvalue()

        dataframe = pd.read_excel(
            BytesIO(uploaded_bytes)
        )

        dataframe.columns = [
            str(column).strip()
            for column in dataframe.columns
        ]

    except Exception as error:
        st.error(
            f"تعذر قراءة ملف Excel: {error}"
        )
        st.stop()

    if dataframe.empty:
        st.warning(
            "ملف Excel لا يحتوي على بيانات."
        )
        st.stop()

    file_hash = sha256(
        uploaded_bytes
    ).hexdigest()

    widget_prefix = (
        f"upload_{file_hash[:12]}"
    )

    available_columns = (
        dataframe.columns.tolist()
    )

    st.success(
        f"تمت قراءة الملف بنجاح — "
        f"عدد الصفوف: {len(dataframe)}"
    )

    with st.expander(
        "معاينة الملف",
        expanded=False,
    ):
        st.dataframe(
            dataframe.head(20),
            use_container_width=True,
            hide_index=True,
        )

    # =====================================================
    # 1. البيانات الأساسية
    # =====================================================

    with st.container(border=True):
        st.markdown(
            "## 1. البيانات الأساسية"
        )

        st.caption(
            "حددي عمود الخدمة، وطريقة تحديد القسم، "
            "والسنة والفترة."
        )

        service_options = (
            [CHOOSE_COLUMN]
            + available_columns
        )

        response_id_options = (
            [NO_COLUMN]
            + available_columns
        )

        basic_col1, basic_col2 = (
            st.columns(2)
        )

        with basic_col1:
            service_column = st.selectbox(
                "عمود اسم الخدمة *",
                options=service_options,
                index=find_option_index(
                    service_options,
                    [
                        "اسم_الخدمة",
                        "اسم الخدمة",
                        "الخدمة",
                        "Service",
                        "Service Name",
                    ],
                ),
                key=(
                    f"{widget_prefix}_service"
                ),
            )

        with basic_col2:
            response_id_column = st.selectbox(
                "عمود رقم الاستجابة",
                options=response_id_options,
                index=find_option_index(
                    response_id_options,
                    [
                        "رقم_الاستجابة",
                        "رقم الاستجابة",
                        "Response ID",
                        "ID",
                    ],
                ),
                key=(
                    f"{widget_prefix}_response_id"
                ),
                help=(
                    "يُستخدم فقط مع الإجابات الخام لحساب "
                    "عدد المشاركين دون تكرار."
                ),
            )

        st.markdown(
            "#### تحديد القسم"
        )

        department_source = st.radio(
            "طريقة تحديد القسم",
            options=[
                DEPARTMENT_FROM_COLUMN,
                DEPARTMENT_FIXED,
            ],
            horizontal=True,
            key=(
                f"{widget_prefix}_department_source"
            ),
            label_visibility="collapsed",
        )

        department_column = CHOOSE_COLUMN
        fixed_department_name = ""

        if (
            department_source
            == DEPARTMENT_FROM_COLUMN
        ):
            department_options = (
                [CHOOSE_COLUMN]
                + available_columns
            )

            department_column = st.selectbox(
                "عمود اسم القسم *",
                options=department_options,
                index=find_option_index(
                    department_options,
                    [
                        "اسم_القسم",
                        "اسم القسم",
                        "القسم",
                        "Department",
                    ],
                ),
                key=(
                    f"{widget_prefix}_department_column"
                ),
            )

        else:
            fixed_department_name = st.text_input(
                "اسم القسم الذي يخص جميع صفوف الملف *",
                placeholder=(
                    "مثال: إدارة تجربة العميل"
                ),
                key=(
                    f"{widget_prefix}_fixed_department"
                ),
            )

        st.markdown(
            "#### تحديد السنة والفترة"
        )

        time_source = st.radio(
            "طريقة تحديد السنة والفترة",
            options=[
                TIME_FROM_DATE,
                TIME_FROM_COLUMNS,
                TIME_FIXED,
            ],
            horizontal=True,
            key=(
                f"{widget_prefix}_time_source"
            ),
            label_visibility="collapsed",
        )

        date_column = CHOOSE_COLUMN
        year_column = CHOOSE_COLUMN
        period_column = CHOOSE_COLUMN
        selected_year = datetime.now().year
        selected_period = "النصف الأول"

        if time_source == TIME_FROM_DATE:
            date_options = (
                [CHOOSE_COLUMN]
                + available_columns
            )

            date_column = st.selectbox(
                "عمود تاريخ الاستجابة *",
                options=date_options,
                index=find_option_index(
                    date_options,
                    [
                        "تاريخ_الاستجابة",
                        "تاريخ الاستجابة",
                        "التاريخ",
                        "Date",
                        "Response Date",
                    ],
                ),
                key=(
                    f"{widget_prefix}_date_column"
                ),
                help=(
                    "سيستخرج النظام السنة والنصف السنوي "
                    "تلقائيًا من التاريخ."
                ),
            )

        elif (
            time_source
            == TIME_FROM_COLUMNS
        ):
            time_col1, time_col2 = (
                st.columns(2)
            )

            year_options = (
                [CHOOSE_COLUMN]
                + available_columns
            )

            period_options = (
                [CHOOSE_COLUMN]
                + available_columns
            )

            with time_col1:
                year_column = st.selectbox(
                    "عمود السنة *",
                    options=year_options,
                    index=find_option_index(
                        year_options,
                        [
                            "السنة",
                            "السنه",
                            "العام",
                            "Year",
                        ],
                    ),
                    key=(
                        f"{widget_prefix}_year_column"
                    ),
                )

            with time_col2:
                period_column = st.selectbox(
                    "عمود الفترة *",
                    options=period_options,
                    index=find_option_index(
                        period_options,
                        [
                            "الفترة",
                            "الفتره",
                            "النصف",
                            "Period",
                        ],
                    ),
                    key=(
                        f"{widget_prefix}_period_column"
                    ),
                    help=(
                        "القيم المقبولة تشمل: النصف الأول، "
                        "النصف الثاني، H1، H2."
                    ),
                )

        else:
            fixed_time_col1, fixed_time_col2 = (
                st.columns(2)
            )

            with fixed_time_col1:
                selected_year = st.number_input(
                    "السنة *",
                    min_value=2000,
                    max_value=2100,
                    value=datetime.now().year,
                    step=1,
                    key=(
                        f"{widget_prefix}_fixed_year"
                    ),
                )

            with fixed_time_col2:
                selected_period = st.selectbox(
                    "الفترة *",
                    options=[
                        "النصف الأول",
                        "النصف الثاني",
                    ],
                    key=(
                        f"{widget_prefix}_fixed_period"
                    ),
                )

    # =====================================================
    # 2. المؤشرات
    # =====================================================

    with st.container(border=True):
        st.markdown(
            "## 2. المؤشرات"
        )

        indicator_mode = st.radio(
            "نوع البيانات الموجودة في الملف",
            options=[
                RAW_INDICATORS,
                CALCULATED_INDICATORS,
                COMMENTS_ONLY,
            ],
            horizontal=True,
            key=(
                f"{widget_prefix}_indicator_mode"
            ),
        )

        raw_csat_columns: list[str] = []
        raw_ces_columns: list[str] = []
        raw_nps_column = NO_COLUMN

        calculated_csat_column = NO_COLUMN
        calculated_ces_column = NO_COLUMN
        calculated_nps_column = NO_COLUMN
        participants_count_column = NO_COLUMN

        percentage_scale = PERCENTAGE_FROM_0_TO_100
        target_source = TARGET_FIXED

        fixed_targets: dict[str, Decimal] = {}
        target_columns: dict[str, str] = {}

        if indicator_mode == RAW_INDICATORS:
            st.caption(
                "اختاري أسئلة الاستبيان، وسيحسب النظام "
                "المؤشرات قبل حفظها."
            )

            default_csat_columns = find_existing_options(
                available_columns,
                [
                    "تقييم_1",
                    "CSAT",
                    "الرضا العام",
                ],
            )

            default_ces_columns = find_existing_options(
                available_columns,
                [
                    "تقييم_2",
                    "CES",
                    "سهولة الاستخدام",
                ],
            )

            raw_csat_columns = st.multiselect(
                "أسئلة CSAT",
                options=available_columns,
                default=default_csat_columns,
                key=(
                    f"{widget_prefix}_raw_csat"
                ),
            )

            raw_ces_columns = st.multiselect(
                "أسئلة CES",
                options=available_columns,
                default=default_ces_columns,
                key=(
                    f"{widget_prefix}_raw_ces"
                ),
            )

            nps_options = (
                [NO_COLUMN]
                + available_columns
            )

            raw_nps_column = st.selectbox(
                "عمود إجابات NPS",
                options=nps_options,
                index=find_option_index(
                    nps_options,
                    [
                        "تقييم_الترشيح_NPS",
                        "NPS",
                        "التوصية",
                    ],
                ),
                key=(
                    f"{widget_prefix}_raw_nps"
                ),
            )

            with st.expander(
                "كيف تُحسب المؤشرات؟"
            ):
                st.markdown(
                    """
                    - **CSAT وCES لكل سؤال:** نسبة التقييمات 4 و5 من مقياس 1–5.
                    - **القيمة العامة:** متوسط نتائج الأسئلة المختارة.
                    - **NPS:** نسبة المروجين 9–10 ناقص نسبة غير المروجين 0–6.
                    - القيم خارج النطاق، مثل 99، تُستبعد.
                    """
                )

            selected_raw_indicators = {
                "CSAT": bool(raw_csat_columns),
                "CES": bool(raw_ces_columns),
                "NPS": raw_nps_column != NO_COLUMN,
            }

            if any(selected_raw_indicators.values()):
                st.markdown(
                    "#### القيم المستهدفة"
                )

                target_col1, target_col2, target_col3 = (
                    st.columns(3)
                )

                with target_col1:
                    if selected_raw_indicators["CSAT"]:
                        value = st.number_input(
                            "مستهدف CSAT",
                            min_value=0.0,
                            max_value=100.0,
                            value=85.0,
                            step=1.0,
                            key=(
                                f"{widget_prefix}_raw_csat_target"
                            ),
                        )

                        fixed_targets["CSAT"] = Decimal(
                            str(value)
                        )

                with target_col2:
                    if selected_raw_indicators["CES"]:
                        value = st.number_input(
                            "مستهدف CES",
                            min_value=0.0,
                            max_value=100.0,
                            value=85.0,
                            step=1.0,
                            key=(
                                f"{widget_prefix}_raw_ces_target"
                            ),
                        )

                        fixed_targets["CES"] = Decimal(
                            str(value)
                        )

                with target_col3:
                    if selected_raw_indicators["NPS"]:
                        value = st.number_input(
                            "مستهدف NPS",
                            min_value=-100.0,
                            max_value=100.0,
                            value=50.0,
                            step=1.0,
                            key=(
                                f"{widget_prefix}_raw_nps_target"
                            ),
                        )

                        fixed_targets["NPS"] = Decimal(
                            str(value)
                        )

        elif indicator_mode == CALCULATED_INDICATORS:
            st.caption(
                "اختاري الأعمدة التي تحتوي على قيم المؤشرات "
                "المحسوبة مسبقًا. لن يعيد النظام حسابها."
            )

            calculated_options = (
                [NO_COLUMN]
                + available_columns
            )

            calc_col1, calc_col2, calc_col3 = (
                st.columns(3)
            )

            with calc_col1:
                calculated_csat_column = st.selectbox(
                    "عمود قيمة CSAT",
                    options=calculated_options,
                    index=find_option_index(
                        calculated_options,
                        [
                            "CSAT الحالي",
                            "CSAT",
                            "Current CSAT",
                        ],
                    ),
                    key=(
                        f"{widget_prefix}_calculated_csat"
                    ),
                )

            with calc_col2:
                calculated_ces_column = st.selectbox(
                    "عمود قيمة CES",
                    options=calculated_options,
                    index=find_option_index(
                        calculated_options,
                        [
                            "CES الحالي",
                            "CES",
                            "Current CES",
                        ],
                    ),
                    key=(
                        f"{widget_prefix}_calculated_ces"
                    ),
                )

            with calc_col3:
                calculated_nps_column = st.selectbox(
                    "عمود قيمة NPS",
                    options=calculated_options,
                    index=find_option_index(
                        calculated_options,
                        [
                            "NPS الحالي",
                            "NPS",
                            "Current NPS",
                        ],
                    ),
                    key=(
                        f"{widget_prefix}_calculated_nps"
                    ),
                )

            participants_options = (
                [NO_COLUMN]
                + available_columns
            )

            participants_count_column = st.selectbox(
                "عمود عدد المشاركين",
                options=participants_options,
                index=find_option_index(
                    participants_options,
                    [
                        "عدد المشاركين",
                        "عدد_المشاركين",
                        "Participants Count",
                        "Participants",
                    ],
                ),
                key=(
                    f"{widget_prefix}_participants_count"
                ),
                help=(
                    "إذا لم تختاري عمودًا، سيستخدم النظام "
                    "عدد صفوف كل خدمة وفترة."
                ),
            )

            percentage_scale = st.radio(
                "صيغة قيم CSAT وCES داخل Excel",
                options=[
                    PERCENTAGE_FROM_0_TO_100,
                    PERCENTAGE_FROM_0_TO_1,
                ],
                horizontal=True,
                key=(
                    f"{widget_prefix}_percentage_scale"
                ),
                help=(
                    "اختاري 0 إلى 1 إذا كانت قيمة 85% "
                    "تُقرأ في Excel كـ 0.85."
                ),
            )

            selected_calculated_indicators = {
                "CSAT": calculated_csat_column != NO_COLUMN,
                "CES": calculated_ces_column != NO_COLUMN,
                "NPS": calculated_nps_column != NO_COLUMN,
            }

            if any(
                selected_calculated_indicators.values()
            ):
                st.markdown(
                    "#### القيم المستهدفة"
                )

                target_source = st.radio(
                    "مصدر القيم المستهدفة",
                    options=[
                        TARGET_FIXED,
                        TARGET_FROM_COLUMNS,
                    ],
                    horizontal=True,
                    key=(
                        f"{widget_prefix}_target_source"
                    ),
                )

                if target_source == TARGET_FIXED:
                    target_col1, target_col2, target_col3 = (
                        st.columns(3)
                    )

                    with target_col1:
                        if selected_calculated_indicators["CSAT"]:
                            value = st.number_input(
                                "مستهدف CSAT",
                                min_value=0.0,
                                max_value=100.0,
                                value=85.0,
                                step=1.0,
                                key=(
                                    f"{widget_prefix}_calc_csat_target"
                                ),
                            )

                            fixed_targets["CSAT"] = Decimal(
                                str(value)
                            )

                    with target_col2:
                        if selected_calculated_indicators["CES"]:
                            value = st.number_input(
                                "مستهدف CES",
                                min_value=0.0,
                                max_value=100.0,
                                value=85.0,
                                step=1.0,
                                key=(
                                    f"{widget_prefix}_calc_ces_target"
                                ),
                            )

                            fixed_targets["CES"] = Decimal(
                                str(value)
                            )

                    with target_col3:
                        if selected_calculated_indicators["NPS"]:
                            value = st.number_input(
                                "مستهدف NPS",
                                min_value=-100.0,
                                max_value=100.0,
                                value=50.0,
                                step=1.0,
                                key=(
                                    f"{widget_prefix}_calc_nps_target"
                                ),
                            )

                            fixed_targets["NPS"] = Decimal(
                                str(value)
                            )

                else:
                    target_options = (
                        [CHOOSE_COLUMN]
                        + available_columns
                    )

                    target_col1, target_col2, target_col3 = (
                        st.columns(3)
                    )

                    with target_col1:
                        if selected_calculated_indicators["CSAT"]:
                            target_columns["CSAT"] = st.selectbox(
                                "عمود مستهدف CSAT",
                                options=target_options,
                                index=find_option_index(
                                    target_options,
                                    [
                                        "CSAT المستهدف",
                                        "Target CSAT",
                                    ],
                                ),
                                key=(
                                    f"{widget_prefix}_csat_target_column"
                                ),
                            )

                    with target_col2:
                        if selected_calculated_indicators["CES"]:
                            target_columns["CES"] = st.selectbox(
                                "عمود مستهدف CES",
                                options=target_options,
                                index=find_option_index(
                                    target_options,
                                    [
                                        "CES المستهدف",
                                        "Target CES",
                                    ],
                                ),
                                key=(
                                    f"{widget_prefix}_ces_target_column"
                                ),
                            )

                    with target_col3:
                        if selected_calculated_indicators["NPS"]:
                            target_columns["NPS"] = st.selectbox(
                                "عمود مستهدف NPS",
                                options=target_options,
                                index=find_option_index(
                                    target_options,
                                    [
                                        "NPS المستهدف",
                                        "Target NPS",
                                    ],
                                ),
                                key=(
                                    f"{widget_prefix}_nps_target_column"
                                ),
                            )

        else:
            st.info(
                "سيتم حفظ التعليقات وربطها بالقسم والخدمة "
                "والسنة والفترة دون إنشاء نتائج مؤشرات جديدة."
            )

    # =====================================================
    # 3. التعليقات
    # =====================================================

    with st.container(border=True):
        st.markdown(
            "## 3. التعليقات"
        )

        st.caption(
            "اختاري أعمدة التعليقات المطلوبة. "
            "سيتم حذف الفارغ والمكرر."
        )

        default_comment_columns = [
            column
            for column in available_columns
            if (
                "تعليق" in column
                or "comment" in column.lower()
                or "review" in column.lower()
            )
        ]

        comment_columns = st.multiselect(
            "أعمدة التعليقات",
            options=available_columns,
            default=default_comment_columns,
            key=(
                f"{widget_prefix}_comment_columns"
            ),
        )

    # =====================================================
    # التحقق والحفظ مباشرة
    # =====================================================

    save_button = st.button(
        "التحقق وحفظ البيانات",
        type="primary",
        use_container_width=True,
        key=(
            f"{widget_prefix}_save_data"
        ),
    )

    if save_button:
        errors: list[str] = []

        if service_column == CHOOSE_COLUMN:
            errors.append(
                "يجب اختيار عمود اسم الخدمة."
            )

        if (
            department_source
            == DEPARTMENT_FROM_COLUMN
            and department_column
            == CHOOSE_COLUMN
        ):
            errors.append(
                "يجب اختيار عمود اسم القسم."
            )

        if (
            department_source
            == DEPARTMENT_FIXED
            and not fixed_department_name.strip()
        ):
            errors.append(
                "يجب كتابة اسم القسم الذي يخص جميع صفوف الملف."
            )

        if (
            time_source == TIME_FROM_DATE
            and date_column == CHOOSE_COLUMN
        ):
            errors.append(
                "يجب اختيار عمود تاريخ الاستجابة."
            )

        if time_source == TIME_FROM_COLUMNS:
            if year_column == CHOOSE_COLUMN:
                errors.append(
                    "يجب اختيار عمود السنة."
                )

            if period_column == CHOOSE_COLUMN:
                errors.append(
                    "يجب اختيار عمود الفترة."
                )

        if indicator_mode == RAW_INDICATORS:
            overlapping_questions = (
                set(raw_csat_columns)
                .intersection(raw_ces_columns)
            )

            if overlapping_questions:
                errors.append(
                    "لا يمكن استخدام السؤال نفسه في "
                    "CSAT وCES معًا: "
                    + "، ".join(
                        sorted(overlapping_questions)
                    )
                )

            if (
                raw_nps_column != NO_COLUMN
                and (
                    raw_nps_column in raw_csat_columns
                    or raw_nps_column in raw_ces_columns
                )
            ):
                errors.append(
                    "لا يمكن استخدام عمود NPS نفسه "
                    "ضمن أسئلة CSAT أو CES."
                )

            has_raw_indicators = bool(
                raw_csat_columns
                or raw_ces_columns
                or raw_nps_column != NO_COLUMN
            )

            if (
                not has_raw_indicators
                and not comment_columns
            ):
                errors.append(
                    "اختاري مؤشرًا واحدًا على الأقل "
                    "أو عمودًا للتعليقات."
                )

        elif indicator_mode == CALCULATED_INDICATORS:
            selected_calculated_columns = [
                column
                for column in (
                    calculated_csat_column,
                    calculated_ces_column,
                    calculated_nps_column,
                )
                if column != NO_COLUMN
            ]

            if len(selected_calculated_columns) != len(
                set(selected_calculated_columns)
            ):
                errors.append(
                    "لا يمكن اختيار العمود نفسه لأكثر من مؤشر."
                )

            if (
                not selected_calculated_columns
                and not comment_columns
            ):
                errors.append(
                    "اختاري عمود مؤشر محسوب واحدًا على الأقل "
                    "أو عمودًا للتعليقات."
                )

            if target_source == TARGET_FROM_COLUMNS:
                for indicator_name, current_column in {
                    "CSAT": calculated_csat_column,
                    "CES": calculated_ces_column,
                    "NPS": calculated_nps_column,
                }.items():
                    if current_column == NO_COLUMN:
                        continue

                    target_column = target_columns.get(
                        indicator_name,
                        CHOOSE_COLUMN,
                    )

                    if target_column == CHOOSE_COLUMN:
                        errors.append(
                            f"يجب اختيار عمود مستهدف {indicator_name}."
                        )

        elif (
            indicator_mode == COMMENTS_ONLY
            and not comment_columns
        ):
            errors.append(
                "اختاري عمودًا واحدًا على الأقل للتعليقات."
            )

        if errors:
            for error_message in errors:
                st.error(error_message)

        else:
            try:
                with st.spinner(
                    "جاري التحقق من الملف وحفظ البيانات..."
                ):
                    summary_rows = prepare_upload_summary(
                        dataframe=dataframe,
                        service_column=service_column,
                        response_id_column=response_id_column,
                        department_source=department_source,
                        department_column=department_column,
                        fixed_department_name=fixed_department_name,
                        time_source=time_source,
                        date_column=date_column,
                        year_column=year_column,
                        period_column=period_column,
                        selected_year=int(selected_year),
                        selected_period=selected_period,
                        indicator_mode=indicator_mode,
                        raw_csat_columns=raw_csat_columns,
                        raw_ces_columns=raw_ces_columns,
                        raw_nps_column=raw_nps_column,
                        calculated_csat_column=(
                            calculated_csat_column
                        ),
                        calculated_ces_column=(
                            calculated_ces_column
                        ),
                        calculated_nps_column=(
                            calculated_nps_column
                        ),
                        participants_count_column=(
                            participants_count_column
                        ),
                        percentage_scale=percentage_scale,
                        target_source=target_source,
                        fixed_targets=fixed_targets,
                        target_columns=target_columns,
                        comment_columns=comment_columns,
                    )

                    inserted, updated = save_summary_to_database(
                        summary_rows
                    )

                st.success(
                    "تم حفظ البيانات في قاعدة البيانات بنجاح."
                )

                st.write(
                    f"السجلات الجديدة: **{inserted}**"
                )

                st.write(
                    f"السجلات التي تم تحديثها: **{updated}**"
                )

            except ValueError as error:
                st.error(str(error))

            except Exception as error:
                st.error(
                    "حدث خطأ أثناء حفظ البيانات: "
                    f"{error}"
                )