from sqlalchemy import select
from database.connection import SessionLocal
from database.models import Department, Service, MeasurementRecord, IndicatorResult, Indicator

import pandas as pd

from calculations import (
    calculate_csat,
    calculate_ces,
    calculate_nps,
)


def fetch_records_from_db():
    """يرجع قائمة بنفس شكل mock_records بالضبط، لكن من الداتابيز الحقيقية."""
    session = SessionLocal()
    try:
        rows = session.execute(
            select(MeasurementRecord, Service, Department)
            .join(Service, MeasurementRecord.service_id == Service.service_id)
            .join(Department, Service.department_id == Department.department_id)
        ).all()

        result = []
        for mrecord, service, dept in rows:
            row = {
                "department": dept.department_name,
                "service": service.service_name,
                "year": mrecord.year,
                "period": mrecord.period,
                "status": "معتمد",  # ملاحظة: ما فيه عمود status بجدولكم حاليًا، قيمة ثابتة مؤقتًا
            }

            indicator_rows = session.execute(
                select(IndicatorResult, Indicator)
                .join(Indicator, IndicatorResult.indicator_id == Indicator.indicator_id)
                .where(IndicatorResult.record_id == mrecord.record_id)
            ).all()

            for ind_result, indicator in indicator_rows:
                key = indicator.indicator_name.lower()  # "nps" / "ces" / "csat"
                row[f"{key}_prev"] = float(ind_result.prev_value or 0)
                row[f"{key}_current"] = float(ind_result.current_value)
                row[f"{key}_target"] = float(ind_result.target_value)

            result.append(row)
        return result
    finally:
        session.close()

# ----------------------------------------------------------------------
# تجهيز ملفات Excel قبل حفظها في قاعدة البيانات
# ----------------------------------------------------------------------

RAW_DATA = "raw"
CALCULATED_DATA = "calculated"


def _clean_text(value):
    """تحويل القيمة إلى نص نظيف."""

    if pd.isna(value):
        return ""

    return str(value).strip()


def _period_code(value):
    """
    تحويل الفترة إلى H1 أو H2،
    وهي الصيغة المستخدمة في قاعدة البيانات.
    """

    if pd.isna(value):
        return None

    cleaned = (
        str(value)
        .strip()
        .lower()
        .replace("_", " ")
        .replace("-", " ")
    )

    first_half = {
        "h1",
        "1",
        "1.0",
        "النصف الأول",
        "النصف الاول",
        "الفترة الأولى",
        "الفتره الاولى",
    }

    second_half = {
        "h2",
        "2",
        "2.0",
        "النصف الثاني",
        "الفترة الثانية",
        "الفتره الثانيه",
    }

    if cleaned in first_half:
        return "H1"

    if cleaned in second_half:
        return "H2"

    return None


def _period_from_month(month):
    """تحويل الشهر إلى H1 أو H2."""

    return "H1" if int(month) <= 6 else "H2"


def _read_numeric_value(value):
    """
    قراءة قيمة رقمية مثل:
    35
    -20
    85%
    """

    if pd.isna(value):
        return None

    cleaned = (
        str(value)
        .strip()
        .replace("%", "")
        .replace(",", "")
    )

    if not cleaned:
        return None

    try:
        return round(float(cleaned), 2)

    except ValueError as error:
        raise ValueError(
            f"القيمة ليست رقمية: {value}"
        ) from error


def _read_percentage_value(value):
    """
    قراءة نسبة محسوبة مسبقًا.

    يدعم:
    85
    85%
    0.85
    """

    number = _read_numeric_value(value)

    if number is None:
        return None

    if 0 <= number <= 1:
        number *= 100

    if number < 0 or number > 100:
        raise ValueError(
            f"النسبة يجب أن تكون بين 0 و100: {number}"
        )

    return round(number, 2)


def _read_nps_value(value):
    """قراءة قيمة NPS محسوبة مسبقًا."""

    number = _read_numeric_value(value)

    if number is None:
        return None

    if number < -100 or number > 100:
        raise ValueError(
            f"قيمة NPS يجب أن تكون بين -100 و100: {number}"
        )

    return round(number, 2)


def _single_group_value(
    group,
    column_name,
    reader,
    field_name,
):
    """
    قراءة قيمة واحدة من مجموعة.

    يسمح بتكرار القيمة نفسها،
    لكنه يرفض وجود قيم مختلفة لنفس الخدمة والفترة.
    """

    if not column_name:
        return None

    values = []

    for value in group[column_name]:
        parsed_value = reader(value)

        if parsed_value is not None:
            values.append(parsed_value)

    unique_values = list(dict.fromkeys(values))

    if not unique_values:
        return None

    if len(unique_values) > 1:
        raise ValueError(
            f"يوجد أكثر من قيمة لـ {field_name} "
            "لنفس الخدمة والسنة والفترة."
        )

    return unique_values[0]


def _average_question_scores(
    group,
    columns,
    calculation_function,
    minimum,
    maximum,
):
    """
    حساب المؤشر لكل سؤال،
    ثم حساب متوسط نتائج الأسئلة المختارة.
    """

    scores = []

    for column_name in columns:
        numeric_answers = pd.to_numeric(
            group[column_name],
            errors="coerce",
        )

        valid_answers = numeric_answers[
            numeric_answers.between(
                minimum,
                maximum,
            )
        ]

        score = calculation_function(
            valid_answers
        )

        if score is not None:
            scores.append(score)

    if not scores:
        return None

    return round(
        sum(scores) / len(scores),
        2,
    )


def _collect_comments(
    group,
    comment_columns,
):
    """جمع التعليقات وحذف الفارغ والمكرر."""

    ignored_comments = {
        "",
        "لا يوجد تعليق",
        "لا يوجد تعليق.",
        "لا توجد ملاحظات",
        "لا توجد ملاحظة",
        "nan",
        "none",
        "null",
    }

    comments = []
    existing_comments = set()

    for column_name in comment_columns:
        for value in group[column_name]:
            if pd.isna(value):
                continue

            comment = str(value).strip()

            normalized = comment.lower()

            if normalized in ignored_comments:
                continue

            if normalized in existing_comments:
                continue

            existing_comments.add(normalized)
            comments.append(comment)

    if not comments:
        return None

    return "\n".join(comments)


def prepare_uploaded_records(
    dataframe,
    data_mode,
    service_column,
    department_column=None,
    fixed_department=None,
    response_id_column=None,
    date_column=None,
    year_column=None,
    period_column=None,
    fixed_year=None,
    fixed_period=None,
    csat_columns=None,
    ces_columns=None,
    nps_column=None,
    calculated_csat_column=None,
    calculated_ces_column=None,
    calculated_nps_column=None,
    participants_column=None,
    comment_columns=None,
):
    """
    تجهيز ملف Excel للحفظ.

    data_mode:
        raw         -> إجابات استبيان خام
        calculated  -> مؤشرات محسوبة مسبقًا

    ترجع قائمة بالشكل المتوقع من:
        entry_backend.save_uploaded_records()
    """

    csat_columns = csat_columns or []
    ces_columns = ces_columns or []
    comment_columns = comment_columns or []

    data = dataframe.copy()

    # -----------------------------------------------------
    # الخدمة
    # -----------------------------------------------------

    data["_service"] = (
        data[service_column]
        .apply(_clean_text)
    )

    if (data["_service"] == "").any():
        raise ValueError(
            "يوجد صف بدون اسم خدمة."
        )

    # -----------------------------------------------------
    # القسم
    # -----------------------------------------------------

    if department_column:
        data["_department"] = (
            data[department_column]
            .apply(_clean_text)
        )

        if (data["_department"] == "").any():
            raise ValueError(
                "يوجد صف بدون اسم قسم."
            )

    elif fixed_department:
        data["_department"] = (
            str(fixed_department).strip()
        )

    else:
        raise ValueError(
            "يجب اختيار عمود القسم "
            "أو إدخال اسم قسم ثابت."
        )

    # -----------------------------------------------------
    # السنة والفترة
    # -----------------------------------------------------

    if date_column:
        parsed_dates = pd.to_datetime(
            data[date_column],
            errors="coerce",
            dayfirst=True,
        )

        if parsed_dates.isna().any():
            raise ValueError(
                "يوجد تاريخ غير صحيح في الملف."
            )

        data["_year"] = (
            parsed_dates.dt.year
        )

        data["_period"] = (
            parsed_dates.dt.month.apply(
                _period_from_month
            )
        )

    elif year_column and period_column:
        data["_year"] = pd.to_numeric(
            data[year_column],
            errors="coerce",
        )

        data["_period"] = (
            data[period_column]
            .apply(_period_code)
        )

        if data["_year"].isna().any():
            raise ValueError(
                "يوجد عام غير صحيح في الملف."
            )

        if data["_period"].isna().any():
            raise ValueError(
                "يوجد اسم فترة غير معروف في الملف."
            )

    elif fixed_year and fixed_period:
        data["_year"] = int(
            fixed_year
        )

        period = _period_code(
            fixed_period
        )

        if period is None:
            raise ValueError(
                "الفترة الثابتة غير صحيحة."
            )

        data["_period"] = period

    else:
        raise ValueError(
            "يجب تحديد التاريخ، "
            "أو عمودي السنة والفترة، "
            "أو سنة وفترة ثابتة."
        )

    # -----------------------------------------------------
    # تجميع البيانات
    # -----------------------------------------------------

    grouped_data = data.groupby(
        [
            "_department",
            "_service",
            "_year",
            "_period",
        ],
        dropna=False,
        sort=True,
    )

    prepared_records = []

    for (
        department,
        service,
        year,
        period,
    ), group in grouped_data:

        # -------------------------------------------------
        # عدد المشاركين
        # -------------------------------------------------

        if (
            data_mode == CALCULATED_DATA
            and participants_column
        ):
            participants = _single_group_value(
                group=group,
                column_name=participants_column,
                reader=_read_numeric_value,
                field_name="عدد المشاركين",
            )

            if participants is None:
                participants = 0

            participants = int(
                participants
            )

        elif response_id_column:
            participants = int(
                group[response_id_column]
                .dropna()
                .nunique()
            )

        else:
            participants = len(group)

        # -------------------------------------------------
        # المؤشرات
        # -------------------------------------------------

        if data_mode == RAW_DATA:
            csat_value = (
                _average_question_scores(
                    group=group,
                    columns=csat_columns,
                    calculation_function=(
                        calculate_csat
                    ),
                    minimum=1,
                    maximum=5,
                )
            )

            ces_value = (
                _average_question_scores(
                    group=group,
                    columns=ces_columns,
                    calculation_function=(
                        calculate_ces
                    ),
                    minimum=1,
                    maximum=5,
                )
            )

            nps_value = None

            if nps_column:
                numeric_nps = pd.to_numeric(
                    group[nps_column],
                    errors="coerce",
                )

                valid_nps = numeric_nps[
                    numeric_nps.between(
                        0,
                        10,
                    )
                ]

                nps_value = calculate_nps(
                    valid_nps
                )

        elif data_mode == CALCULATED_DATA:
            csat_value = _single_group_value(
                group=group,
                column_name=(
                    calculated_csat_column
                ),
                reader=(
                    _read_percentage_value
                ),
                field_name="CSAT",
            )

            ces_value = _single_group_value(
                group=group,
                column_name=(
                    calculated_ces_column
                ),
                reader=(
                    _read_numeric_value
                ),
                field_name="CES",
            )

            nps_value = _single_group_value(
                group=group,
                column_name=(
                    calculated_nps_column
                ),
                reader=_read_nps_value,
                field_name="NPS",
            )

        else:
            raise ValueError(
                "نوع بيانات المؤشرات غير معروف."
            )

        # -------------------------------------------------
        # التعليقات
        # -------------------------------------------------

        review = _collect_comments(
            group=group,
            comment_columns=(
                comment_columns
            ),
        )

        prepared_records.append(
            {
                "department": str(
                    department
                ).strip(),

                "service": str(
                    service
                ).strip(),

                "year": int(year),

                "period": period,

                "participants": (
                    participants
                ),

                "review": review,

                "indicators": {
                    "CSAT": csat_value,
                    "CES": ces_value,
                    "NPS": nps_value,
                },
            }
        )

    return prepared_records