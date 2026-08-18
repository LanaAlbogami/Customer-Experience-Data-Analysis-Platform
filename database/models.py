from decimal import Decimal

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from database.connection import Base


# ==================================================
# Government Entities
# ==================================================

# Government entities are independent from sections.
# The same shared sections/services can be measured for many entities.
class GovernmentEntity(Base):
    __tablename__ = "GovernmentEntities"

    entity_id: Mapped[int] = mapped_column(
        "EntityID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    entity_name: Mapped[str] = mapped_column(
        "EntityName",
        String(150),
        nullable=False,
        unique=True,
    )

    # One entity can have many measurement records.
    measurement_records: Mapped[
        list["MeasurementRecord"]
    ] = relationship(
        back_populates="entity",
    )


# ==================================================
# Sections
# ==================================================

# Sections are shared reference data.
# Example:
#   1 -> Deem
#   2 -> DT
#   3 -> IDART
#   4 -> NB
#   5 -> NP
#
# A section is NOT duplicated for every government entity.
class Section(Base):
    __tablename__ = "Section"

    section_id: Mapped[int] = mapped_column(
        "SectionID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Since the section is shared globally,
    # its name must be unique in the Section table.
    section_name: Mapped[str] = mapped_column(
        "SectionName",
        String(100),
        nullable=False,
        unique=True,
    )

    # One shared section has many services.
    services: Mapped[
        list["Service"]
    ] = relationship(
        back_populates="section",
    )


# ==================================================
# Services
# ==================================================

# Each service belongs to one shared section.
class Service(Base):
    __tablename__ = "Service"

    __table_args__ = (
        UniqueConstraint(
            "SectionID",
            "ServiceName",
            name="uq_service_section_name",
        ),
    )

    service_id: Mapped[int] = mapped_column(
        "ServiceID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    section_id: Mapped[int] = mapped_column(
        "SectionID",
        Integer,
        ForeignKey("Section.SectionID"),
        nullable=False,
    )

    service_name: Mapped[str] = mapped_column(
        "ServiceName",
        String(150),
        nullable=False,
    )

    section: Mapped[
        "Section"
    ] = relationship(
        back_populates="services",
    )

    measurement_records: Mapped[
        list["MeasurementRecord"]
    ] = relationship(
        back_populates="service",
    )


# ==================================================
# Measurement Records
# ==================================================

# One record = one government entity + one service
# measured in one specific year and period.
#
# EntityID belongs HERE rather than inside Section,
# because sections/services are shared across entities.
class MeasurementRecord(Base):
    __tablename__ = "MeasurementRecords"

    __table_args__ = (
        UniqueConstraint(
            "EntityID",
            "ServiceID",
            "Year",
            "Period",
            name="uq_measurement_entity_service_year_period",
        ),
    )

    record_id: Mapped[int] = mapped_column(
        "RecordID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Which government entity this measurement belongs to.
    entity_id: Mapped[int] = mapped_column(
        "EntityID",
        Integer,
        ForeignKey("GovernmentEntities.EntityID"),
        nullable=False,
    )

    # Which shared service this record measures.
    service_id: Mapped[int] = mapped_column(
        "ServiceID",
        Integer,
        ForeignKey("Service.ServiceID"),
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

    participants_count: Mapped[int] = mapped_column(
        "ParticipantsCount",
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    review: Mapped[
        str | None
    ] = mapped_column(
        "Review",
        Text,
        nullable=True,
    )

    entity: Mapped[
        "GovernmentEntity"
    ] = relationship(
        back_populates="measurement_records",
    )

    service: Mapped[
        "Service"
    ] = relationship(
        back_populates="measurement_records",
    )

    indicator_results: Mapped[
        list["IndicatorResult"]
    ] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
    )

    factor_results: Mapped[
        list["FactorResult"]
    ] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
    )


# ==================================================
# Indicators
# ==================================================

class Indicator(Base):
    __tablename__ = "Indicators"

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

    min_value: Mapped[Decimal] = mapped_column(
        "MinValue",
        Numeric(10, 2),
        nullable=False,
    )

    max_value: Mapped[Decimal] = mapped_column(
        "MaxValue",
        Numeric(10, 2),
        nullable=False,
    )

    is_factor_based: Mapped[bool] = mapped_column(
        "IsFactorBased",
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )

    results: Mapped[
        list["IndicatorResult"]
    ] = relationship(
        back_populates="indicator",
    )


# ==================================================
# Indicator Results
# ==================================================

class IndicatorResult(Base):
    __tablename__ = "IndicatorResults"

    __table_args__ = (
        UniqueConstraint(
            "RecordID",
            "IndicatorID",
            name="uq_indicator_result_record_indicator",
        ),
    )

    result_id: Mapped[int] = mapped_column(
        "ResultID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    record_id: Mapped[int] = mapped_column(
        "RecordID",
        Integer,
        ForeignKey("MeasurementRecords.RecordID"),
        nullable=False,
    )

    indicator_id: Mapped[int] = mapped_column(
        "IndicatorID",
        Integer,
        ForeignKey("Indicators.IndicatorID"),
        nullable=False,
    )

    prev_value: Mapped[
        Decimal | None
    ] = mapped_column(
        "PrevValue",
        Numeric(10, 2),
        nullable=True,
    )

    current_value: Mapped[Decimal] = mapped_column(
        "CurrentValue",
        Numeric(10, 2),
        nullable=False,
    )

    target_value: Mapped[
        Decimal | None
    ] = mapped_column(
        "TargetValue",
        Numeric(10, 2),
        nullable=True,
    )

    record: Mapped[
        "MeasurementRecord"
    ] = relationship(
        back_populates="indicator_results",
    )

    indicator: Mapped[
        "Indicator"
    ] = relationship(
        back_populates="results",
    )


# ==================================================
# Factors
# ==================================================

class Factor(Base):
    __tablename__ = "Factors"

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

    results: Mapped[
        list["FactorResult"]
    ] = relationship(
        back_populates="factor",
    )


# ==================================================
# Factor Results
# ==================================================

class FactorResult(Base):
    __tablename__ = "FactorResults"

    __table_args__ = (
        UniqueConstraint(
            "RecordID",
            "FactorID",
            name="uq_factor_result_record_factor",
        ),
    )

    factor_result_id: Mapped[int] = mapped_column(
        "FactorResultID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    record_id: Mapped[int] = mapped_column(
        "RecordID",
        Integer,
        ForeignKey("MeasurementRecords.RecordID"),
        nullable=False,
    )

    factor_id: Mapped[int] = mapped_column(
        "FactorID",
        Integer,
        ForeignKey("Factors.FactorID"),
        nullable=False,
    )

    participants_count: Mapped[
        int | None
    ] = mapped_column(
        "ParticipantsCount",
        Integer,
        nullable=True,
    )

    prev_value: Mapped[
        Decimal | None
    ] = mapped_column(
        "PrevValue",
        Numeric(10, 2),
        nullable=True,
    )

    current_value: Mapped[Decimal] = mapped_column(
        "CurrentValue",
        Numeric(10, 2),
        nullable=False,
    )

    target_value: Mapped[
        Decimal | None
    ] = mapped_column(
        "TargetValue",
        Numeric(10, 2),
        nullable=True,
    )

    record: Mapped[
        "MeasurementRecord"
    ] = relationship(
        back_populates="factor_results",
    )

    factor: Mapped[
        "Factor"
    ] = relationship(
        back_populates="results",
    )
