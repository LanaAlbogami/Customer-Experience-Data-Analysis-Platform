from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database_individuals.connection import Base


# القيم المقبولة لعمود الفترة (يخزن نص عربي مباشرة، بدون كود مختصر)
VALID_PERIODS = (
    "الربع الأول",
    "الربع الثاني",
    "الربع الثالث",
    "الربع الرابع",
)


# ==================================================
# ملف الأفراد
# البيانات الديموغرافية والتصنيفية لكل فرد
# ==================================================
class IndividualProfile(Base):
    __tablename__ = "IndividualProfiles"

    individual_id: Mapped[int] = mapped_column(
        "IndividualID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    gender: Mapped[str | None] = mapped_column(
        "Gender",
        String(20),
        nullable=True,
    )

    age_group: Mapped[str | None] = mapped_column(
        "AgeGroup",
        String(30),
        nullable=True,
    )

    id_type: Mapped[str | None] = mapped_column(
        "IDType",
        String(50),
        nullable=True,
    )

    education: Mapped[str | None] = mapped_column(
        "Education",
        String(100),
        nullable=True,
    )

    device: Mapped[str | None] = mapped_column(
        "Device",
        String(50),
        nullable=True,
    )

    region: Mapped[str | None] = mapped_column(
        "Region",
        String(100),
        nullable=True,
    )

    measurement_records: Mapped[list["IndividualMeasurementRecord"]] = relationship(
        back_populates="individual"
    )


# ==================================================
# سجلات القياس
# كل سجل يمثل استبيان واحد عبّاه فرد معين في سنة وفترة محددة
# ==================================================
class IndividualMeasurementRecord(Base):
    __tablename__ = "IndividualMeasurementRecords"

    __table_args__ = (
        UniqueConstraint(
            "IndividualID",
            "Year",
            "Period",
            name="uq_individual_record_year_period",
        ),
        CheckConstraint(
            "Period IN ('الربع الأول', 'الربع الثاني', "
            "'الربع الثالث', 'الربع الرابع')",
            name="ck_individual_record_period",
        ),
    )

    record_id: Mapped[int] = mapped_column(
        "RecordID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    individual_id: Mapped[int] = mapped_column(
        "IndividualID",
        Integer,
        ForeignKey("IndividualProfiles.IndividualID"),
        nullable=False,
    )

    year: Mapped[int] = mapped_column(
        "Year",
        Integer,
        nullable=False,
    )

    period: Mapped[str] = mapped_column(
        "Period",
        String(20),
        nullable=False,
    )

    review: Mapped[str | None] = mapped_column(
        "Review",
        Text,
        nullable=True,
    )

    individual: Mapped["IndividualProfile"] = relationship(
        back_populates="measurement_records"
    )

    factor_responses: Mapped[list["IndividualFactorResponse"]] = relationship(
        back_populates="record"
    )

    indicator_responses: Mapped[list["IndividualIndicatorResponse"]] = relationship(
        back_populates="record"
    )


# ==================================================
# عوامل CSAT الثمانية الثابتة (نفس الأسماء المستخدمة بقاعدة الجهات)
# ==================================================
class SharedCSATFactor(Base):
    __tablename__ = "SharedCSATFactors"

    factor_id: Mapped[int] = mapped_column(
        "FactorID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    factor_name: Mapped[str] = mapped_column(
        "FactorName",
        String(150),
        nullable=False,
        unique=True,
    )

    display_order: Mapped[int] = mapped_column(
        "DisplayOrder",
        Integer,
        nullable=False,
        unique=True,
    )

    responses: Mapped[list["IndividualFactorResponse"]] = relationship(
        back_populates="factor"
    )


# ==================================================
# إجابة كل فرد لكل عامل من عوامل CSAT (بيانات خام، رقم من 1 إلى 5)
# CSAT% لأي عامل أو بشكل عام يُحسب وقت الاستعلام من هذا الجدول،
# ولا يُخزَّن جاهزًا هنا.
# ==================================================
class IndividualFactorResponse(Base):
    __tablename__ = "IndividualFactorResponses"

    __table_args__ = (
        UniqueConstraint(
            "RecordID",
            "FactorID",
            name="uq_individual_factor_response",
        ),
        CheckConstraint(
            "RatingValue BETWEEN 1 AND 5",
            name="ck_individual_factor_rating_range",
        ),
    )

    response_id: Mapped[int] = mapped_column(
        "ResponseID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    record_id: Mapped[int] = mapped_column(
        "RecordID",
        Integer,
        ForeignKey("IndividualMeasurementRecords.RecordID"),
        nullable=False,
    )

    factor_id: Mapped[int] = mapped_column(
        "FactorID",
        Integer,
        ForeignKey("SharedCSATFactors.FactorID"),
        nullable=False,
    )

    rating_value: Mapped[int] = mapped_column(
        "RatingValue",
        Integer,
        nullable=False,
    )

    record: Mapped["IndividualMeasurementRecord"] = relationship(
        back_populates="factor_responses"
    )

    factor: Mapped["SharedCSATFactor"] = relationship(
        back_populates="responses"
    )


# ==================================================
# المؤشرات الأخرى (CES, NPS...) بدون CSAT
# CSAT هنا محسوب بالكامل من IndividualFactorResponses أعلاه
# ==================================================
class SharedIndicator(Base):
    __tablename__ = "SharedIndicators"

    indicator_id: Mapped[int] = mapped_column(
        "IndicatorID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    indicator_name: Mapped[str] = mapped_column(
        "IndicatorName",
        String(100),
        nullable=False,
        unique=True,
    )

    unit: Mapped[str] = mapped_column(
        "Unit",
        String(30),
        nullable=False,
    )

    min_value: Mapped[int] = mapped_column(
        "MinValue",
        Integer,
        nullable=False,
    )

    max_value: Mapped[int] = mapped_column(
        "MaxValue",
        Integer,
        nullable=False,
    )

    responses: Mapped[list["IndividualIndicatorResponse"]] = relationship(
        back_populates="indicator"
    )


# ==================================================
# إجابة كل فرد لكل مؤشر آخر غير CSAT (بيانات خام)
# ==================================================
class IndividualIndicatorResponse(Base):
    __tablename__ = "IndividualIndicatorResponses"

    __table_args__ = (
        UniqueConstraint(
            "RecordID",
            "IndicatorID",
            name="uq_individual_indicator_response",
        ),
    )

    response_id: Mapped[int] = mapped_column(
        "ResponseID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    record_id: Mapped[int] = mapped_column(
        "RecordID",
        Integer,
        ForeignKey("IndividualMeasurementRecords.RecordID"),
        nullable=False,
    )

    indicator_id: Mapped[int] = mapped_column(
        "IndicatorID",
        Integer,
        ForeignKey("SharedIndicators.IndicatorID"),
        nullable=False,
    )

    rating_value: Mapped[int] = mapped_column(
        "RatingValue",
        Integer,
        nullable=False,
    )

    record: Mapped["IndividualMeasurementRecord"] = relationship(
        back_populates="indicator_responses"
    )

    indicator: Mapped["SharedIndicator"] = relationship(
        back_populates="responses"
    )


# ==================================================
# جدول النتائج المخزّنة مؤقتًا (Cache)
# يخزن النتيجة العامة (بدون فلاتر) لكل factor ومؤشر، عشان الداشبورد
# يقرأها جاهزة بدل ما يعيد حسابها من الصفر كل مرة تُفتح فيها الصفحة.
# يُحدَّث بعد كل رفع بيانات جديدة عن طريق refresh_individual_cache.py
# ==================================================
class IndividualDashboardCache(Base):
    __tablename__ = "IndividualDashboardCache"

    cache_id: Mapped[int] = mapped_column(
        "CacheID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    metric_name: Mapped[str] = mapped_column(
        "MetricName",
        String(150),
        nullable=False,
        unique=True,
    )

    current_value: Mapped[float | None] = mapped_column(
        "CurrentValue",
        Numeric(10, 2),
        nullable=True,
    )

    participants_count: Mapped[int] = mapped_column(
        "ParticipantsCount",
        Integer,
        nullable=False,
        default=0,
    )

    updated_at: Mapped[str | None] = mapped_column(
        "UpdatedAt",
        String(30),
        nullable=True,
    )