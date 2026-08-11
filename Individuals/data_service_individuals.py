from __future__ import annotations

import streamlit as st
from sqlalchemy import select

from database_individuals.connection import SessionLocal
from database_individuals.models import (
    IndividualDashboardCache,
    IndividualFactorResponse,
    IndividualIndicatorResponse,
    IndividualMeasurementRecord,
    IndividualProfile,
    SharedCSATFactor,
    SharedIndicator,
)


@st.cache_data(ttl=300, show_spinner="جاري تحميل بيانات الأفراد...")
def fetch_individual_dataset():
    """
    يرجع كل سجلات قياس الأفراد، كل صف يمثل استبيان فرد واحد لفترة
    معينة، مع إجابات العوامل والمؤشرات الخام (بدون أي حساب نسب هنا).

    الترتيب من الأحدث للأقدم (RecordID تنازليًا).

    ملاحظة أداء: نجيب كل الإجابات (عوامل + مؤشرات) بـ 3 استعلامات
    إجمالية بس (بدل استعلام منفصل لكل سجل)، ونربطها ببعض بلغة
    بايثون — هذا يقلل عدد رحلات قاعدة البيانات من آلاف لـ 3 بس.
    """
    with SessionLocal() as session:
        rows = session.execute(
            select(IndividualMeasurementRecord, IndividualProfile)
            .join(
                IndividualProfile,
                IndividualMeasurementRecord.individual_id
                == IndividualProfile.individual_id,
            )
            .order_by(IndividualMeasurementRecord.record_id.desc())
        ).all()

        factor_names_by_id = {
            factor.factor_id: factor.factor_name
            for factor in session.scalars(select(SharedCSATFactor)).all()
        }

        indicator_names_by_id = {
            indicator.indicator_id: indicator.indicator_name
            for indicator in session.scalars(select(SharedIndicator)).all()
        }

        # استعلام واحد يجيب كل إجابات العوامل لكل السجلات دفعة وحدة
        factor_ratings_by_record = {}
        for factor_response in session.scalars(
            select(IndividualFactorResponse)
        ).all():
            factor_name = factor_names_by_id.get(factor_response.factor_id)
            if not factor_name:
                continue
            factor_ratings_by_record.setdefault(
                factor_response.record_id, {}
            )[factor_name] = factor_response.rating_value

        # استعلام واحد يجيب كل إجابات المؤشرات لكل السجلات دفعة وحدة
        indicator_ratings_by_record = {}
        for indicator_response in session.scalars(
            select(IndividualIndicatorResponse)
        ).all():
            indicator_name = indicator_names_by_id.get(
                indicator_response.indicator_id
            )
            if not indicator_name:
                continue
            indicator_ratings_by_record.setdefault(
                indicator_response.record_id, {}
            )[indicator_name] = indicator_response.rating_value

        output = []

        for record, profile in rows:
            output.append({
                "record_id": record.record_id,
                "individual_id": profile.individual_id,
                "year": record.year,
                "period": record.period,
                "gender": profile.gender,
                "age_group": profile.age_group,
                "id_type": profile.id_type,
                "education": profile.education,
                "device": profile.device,
                "region": profile.region,
                "review": record.review,
                "factor_ratings": factor_ratings_by_record.get(
                    record.record_id, {}
                ),
                "indicator_ratings": indicator_ratings_by_record.get(
                    record.record_id, {}
                ),
            })

        return output


def fetch_factor_order():
    """أسماء عوامل CSAT الثمانية بترتيب العرض الصحيح."""
    with SessionLocal() as session:
        factors = session.scalars(
            select(SharedCSATFactor).order_by(
                SharedCSATFactor.display_order
            )
        ).all()

        return [factor.factor_name for factor in factors]


def fetch_indicator_names():
    """أسماء المؤشرات الأخرى (مثل NPS) المعرّفة لقاعدة الأفراد."""
    with SessionLocal() as session:
        indicators = session.scalars(select(SharedIndicator)).all()
        return [indicator.indicator_name for indicator in indicators]


# ==================================================
# دوال تجميع (Aggregation) — تحوّل الردود الخام لنِسب مئوية
# ==================================================

def calculate_top2box_percent(ratings):
    """
    نسبة CSAT: (عدد من قيّموا 4 أو 5) / الإجمالي × 100.
    يرجع None لو ما فيه أي تقييمات.
    """
    valid_ratings = [r for r in ratings if r is not None]

    if not valid_ratings:
        return None

    positive_count = sum(1 for r in valid_ratings if r >= 4)

    return round(100 * positive_count / len(valid_ratings), 2)


def calculate_nps_score(ratings):
    """
    NPS = % الموصين (9-10) - % غير الموصين (0-6).
    يرجع None لو ما فيه أي تقييمات.
    """
    valid_ratings = [r for r in ratings if r is not None]

    if not valid_ratings:
        return None

    total = len(valid_ratings)
    promoters = sum(1 for r in valid_ratings if r >= 9)
    detractors = sum(1 for r in valid_ratings if r <= 6)

    return round(100 * (promoters - detractors) / total, 2)


def calculate_ces_score(ratings):
    """
    CES = % الإجابات السهلة (4-5) − % الإجابات الصعبة (1-2)، على مقياس 1-5.
    يرجع None لو ما فيه أي تقييمات.
    """
    valid_ratings = [r for r in ratings if r is not None]

    if not valid_ratings:
        return None

    total = len(valid_ratings)
    easy = sum(1 for r in valid_ratings if r >= 4)
    difficult = sum(1 for r in valid_ratings if r <= 2)

    return round(100 * (easy - difficult) / total, 2)


def aggregate_records(records, factor_order, indicator_names):
    """
    يحسب من قائمة سجلات خام (مفلترة مسبقًا حسب الفلاتر):
    - نسبة CSAT لكل factor لحاله
    - CSAT العام = متوسط نسب الـ factors
    - نسبة/قيمة كل مؤشر آخر (مثل NPS)
    - عدد المشاركين الفعلي لكل factor ولكل مؤشر
    """
    result = {
        "participants_total": len(records),
        "factors": {},
        "indicators": {},
    }

    factor_percentages = []

    for factor_name in factor_order:
        ratings = [
            r["factor_ratings"][factor_name]
            for r in records
            if factor_name in r["factor_ratings"]
        ]

        percent = calculate_top2box_percent(ratings)

        result["factors"][factor_name] = {
            "current_value": percent,
            "participants_count": len(ratings),
        }

        if percent is not None:
            factor_percentages.append(percent)

    result["csat_current"] = (
        round(sum(factor_percentages) / len(factor_percentages), 2)
        if factor_percentages
        else None
    )

    for indicator_name in indicator_names:
        ratings = [
            r["indicator_ratings"][indicator_name]
            for r in records
            if indicator_name in r["indicator_ratings"]
        ]

        if indicator_name.upper() == "NPS":
            value = calculate_nps_score(ratings)
        elif indicator_name.upper() == "CES":
            value = calculate_ces_score(ratings)
        else:
            value = calculate_top2box_percent(ratings)

        result["indicators"][indicator_name] = {
            "current_value": value,
            "participants_count": len(ratings),
        }

    return result


# ==================================================
# قراءة النتيجة العامة الجاهزة (من جدول الكاش)
# ==================================================

def fetch_cached_overall_summary(factor_order, indicator_names):
    """
    يرجع النتيجة العامة (بدون فلاتر) من الجدول المخزّن مؤقتًا،
    بنفس شكل مخرجات aggregate_records() تمامًا — عشان الداشبورد
    يقدر يستخدمها مباشرة بدون أي تعديل.

    يرجع None لو الجدول فاضي (يعني لازم نرجع للحساب الحي العادي).
    """
    with SessionLocal() as session:
        rows = {
            row.metric_name: row
            for row in session.query(IndividualDashboardCache).all()
        }

    if not rows:
        return None

    overall_row = rows.get("CSAT_OVERALL")

    result = {
        "participants_total": (
            overall_row.participants_count if overall_row else 0
        ),
        "csat_current": (
            float(overall_row.current_value)
            if overall_row and overall_row.current_value is not None
            else None
        ),
        "factors": {},
        "indicators": {},
    }

    for factor_name in factor_order:
        row = rows.get(factor_name)
        result["factors"][factor_name] = {
            "current_value": (
                float(row.current_value)
                if row and row.current_value is not None
                else None
            ),
            "participants_count": row.participants_count if row else 0,
        }

    for indicator_name in indicator_names:
        row = rows.get(indicator_name)
        result["indicators"][indicator_name] = {
            "current_value": (
                float(row.current_value)
                if row and row.current_value is not None
                else None
            ),
            "participants_count": row.participants_count if row else 0,
        }

    return result