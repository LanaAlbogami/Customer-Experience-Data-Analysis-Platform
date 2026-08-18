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

# Base class that all models inherit from (defined in connection.py)
from database.connection import Base


# ==================================================
# Government Entities
# ==================================================

# Government entities are the highest level in the hierarchy.
# One government entity can contain multiple sections.
class GovernmentEntity(Base):
    __tablename__ = "GovernmentEntities"

    # Unique ID for each government entity
    entity_id: Mapped[int] = mapped_column(
        "EntityID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Government entity name must be unique
    entity_name: Mapped[str] = mapped_column(
        "EntityName",
        String(150),
        nullable=False,
        unique=True,
    )

    # One entity can have many sections
    sections: Mapped[list["Section"]] = relationship(
        back_populates="entity",
    )


# ==================================================
# Sections
# ==================================================

# Sections belong to a government entity
# and group services together.
class Section(Base):
    __tablename__ = "Section"

    # The same section name cannot be repeated
    # within the same government entity.
    # However, two different entities may have
    # sections with the same name.
    __table_args__ = (
        UniqueConstraint(
            "EntityID",
            "SectionName",
            name="uq_section_entity_name",
        ),
    )

    # Unique ID for each section
    section_id: Mapped[int] = mapped_column(
        "SectionID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Links this section to its government entity
    entity_id: Mapped[int] = mapped_column(
        "EntityID",
        Integer,
        ForeignKey("GovernmentEntities.EntityID"),
        nullable=False,
    )

    # Section name
    section_name: Mapped[str] = mapped_column(
        "SectionName",
        String(100),
        nullable=False,
    )

    # The government entity this section belongs to
    entity: Mapped["GovernmentEntity"] = relationship(
        back_populates="sections",
    )

    # One section has many services
    services: Mapped[list["Service"]] = relationship(
        back_populates="section",
    )


# ==================================================
# Services
# ==================================================

# Each service belongs to exactly one section
class Service(Base):
    __tablename__ = "Service"

    # Prevent duplicate service names within the same section
    __table_args__ = (
        UniqueConstraint(
            "SectionID",
            "ServiceName",
            name="uq_service_section_name",
        ),
    )

    # Unique ID for each service
    service_id: Mapped[int] = mapped_column(
        "ServiceID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Links this service to its parent section
    section_id: Mapped[int] = mapped_column(
        "SectionID",
        Integer,
        ForeignKey("Section.SectionID"),
        nullable=False,
    )

    # Service name
    service_name: Mapped[str] = mapped_column(
        "ServiceName",
        String(150),
        nullable=False,
    )

    # The section this service belongs to
    section: Mapped["Section"] = relationship(
        back_populates="services",
    )

    # One service can have many measurement records over time
    measurement_records: Mapped[
        list["MeasurementRecord"]
    ] = relationship(
        back_populates="service",
    )


# ==================================================
# Measurement Records
# ==================================================

# One record = one service measured in a specific year and period
class MeasurementRecord(Base):
    __tablename__ = "MeasurementRecords"

    # A service can only have one record
    # per year + period combination
    __table_args__ = (
        UniqueConstraint(
            "ServiceID",
            "Year",
            "Period",
            name="uq_measurement_service_year_period",
        ),
    )

    # Unique ID for each measurement record
    record_id: Mapped[int] = mapped_column(
        "RecordID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Which service this record measures
    service_id: Mapped[int] = mapped_column(
        "ServiceID",
        Integer,
        ForeignKey("Service.ServiceID"),
        nullable=False,
    )

    # The year the measurement was taken
    year: Mapped[int] = mapped_column(
        "Year",
        Integer,
        nullable=False,
    )

    # The period within the year
    # e.g. H1 / H2
    period: Mapped[str] = mapped_column(
        "Period",
        String(20),
        nullable=False,
    )

    # How many people took part in this measurement
    participants_count: Mapped[int] = mapped_column(
        "ParticipantsCount",
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )

    # Optional free-text review/comment
    review: Mapped[str | None] = mapped_column(
        "Review",
        Text,
        nullable=True,
    )

    # The service this record belongs to
    service: Mapped["Service"] = relationship(
        back_populates="measurement_records",
    )

    # Indicator results tied to this record
    # Deleting the record also deletes its indicator results
    indicator_results: Mapped[
        list["IndicatorResult"]
    ] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
    )

    # Factor results tied to this record
    # Deleting the record also deletes its factor results
    factor_results: Mapped[
        list["FactorResult"]
    ] = relationship(
        back_populates="record",
        cascade="all, delete-orphan",
    )


# ==================================================
# Indicators
# ==================================================

# Indicators being tracked, such as CSAT, CES, NPS, BPS
#
# IsFactorBased = True
#   -> current value is calculated from the underlying
#      factor results (e.g. CSAT)
#
# IsFactorBased = False
#   -> value stands on its own / is entered directly
#      (e.g. CES, NPS, BPS)
class Indicator(Base):
    __tablename__ = "Indicators"

    # Unique ID for each indicator
    indicator_id: Mapped[int] = mapped_column(
        "IndicatorID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Indicator name must be unique
    indicator_name: Mapped[str] = mapped_column(
        "IndicatorName",
        String(100),
        nullable=False,
        unique=True,
    )

    # Unit used by the indicator
    # e.g. %, points
    unit: Mapped[str] = mapped_column(
        "Unit",
        String(30),
        nullable=False,
    )

    # Lowest possible value
    min_value: Mapped[Decimal] = mapped_column(
        "MinValue",
        Numeric(10, 2),
        nullable=False,
    )

    # Highest possible value
    max_value: Mapped[Decimal] = mapped_column(
        "MaxValue",
        Numeric(10, 2),
        nullable=False,
    )

    # True  = calculated from factor results
    # False = entered/calculated independently
    is_factor_based: Mapped[bool] = mapped_column(
        "IsFactorBased",
        Boolean,
        nullable=False,
        default=False,
        server_default=text("0"),
    )

    # All results recorded for this indicator
    results: Mapped[
        list["IndicatorResult"]
    ] = relationship(
        back_populates="indicator",
    )


# ==================================================
# Indicator Results
# ==================================================

# Stores previous, current, and target values
# for each indicator within each measurement record
class IndicatorResult(Base):
    __tablename__ = "IndicatorResults"

    # Each indicator can only appear once per record
    __table_args__ = (
        UniqueConstraint(
            "RecordID",
            "IndicatorID",
            name="uq_indicator_result_record_indicator",
        ),
    )

    # Unique ID for each indicator result
    result_id: Mapped[int] = mapped_column(
        "ResultID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Which measurement record this result belongs to
    record_id: Mapped[int] = mapped_column(
        "RecordID",
        Integer,
        ForeignKey("MeasurementRecords.RecordID"),
        nullable=False,
    )

    # Which indicator this result represents
    indicator_id: Mapped[int] = mapped_column(
        "IndicatorID",
        Integer,
        ForeignKey("Indicators.IndicatorID"),
        nullable=False,
    )

    # Value from the previous period
    prev_value: Mapped[Decimal | None] = mapped_column(
        "PrevValue",
        Numeric(10, 2),
        nullable=True,
    )

    # Value measured in the current period
    current_value: Mapped[Decimal] = mapped_column(
        "CurrentValue",
        Numeric(10, 2),
        nullable=False,
    )

    # Target value
    target_value: Mapped[Decimal | None] = mapped_column(
        "TargetValue",
        Numeric(10, 2),
        nullable=True,
    )

    # The measurement record this result belongs to
    record: Mapped["MeasurementRecord"] = relationship(
        back_populates="indicator_results",
    )

    # The indicator this result belongs to
    indicator: Mapped["Indicator"] = relationship(
        back_populates="results",
    )


# ==================================================
# Factors
# ==================================================

# The fixed CSAT factors.
# The actual factor names are inserted by seed_data.py.
class Factor(Base):
    __tablename__ = "Factors"

    # Unique ID for each factor
    factor_id: Mapped[int] = mapped_column(
        "FactorID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Factor name must be unique
    factor_name: Mapped[str] = mapped_column(
        "FactorName",
        String(150),
        nullable=False,
        unique=True,
    )

    # Controls the order in which factors are displayed
    display_order: Mapped[int] = mapped_column(
        "DisplayOrder",
        Integer,
        nullable=False,
        unique=True,
    )

    # All results recorded for this factor
    results: Mapped[
        list["FactorResult"]
    ] = relationship(
        back_populates="factor",
    )


# ==================================================
# Factor Results
# ==================================================

# Stores the result of each factor
# for each measurement record
class FactorResult(Base):
    __tablename__ = "FactorResults"

    # Each factor can only appear once per record
    __table_args__ = (
        UniqueConstraint(
            "RecordID",
            "FactorID",
            name="uq_factor_result_record_factor",
        ),
    )

    # Unique ID for each factor result
    factor_result_id: Mapped[int] = mapped_column(
        "FactorResultID",
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # Which measurement record this result belongs to
    record_id: Mapped[int] = mapped_column(
        "RecordID",
        Integer,
        ForeignKey("MeasurementRecords.RecordID"),
        nullable=False,
    )

    # Which factor this result is for
    factor_id: Mapped[int] = mapped_column(
        "FactorID",
        Integer,
        ForeignKey("Factors.FactorID"),
        nullable=False,
    )

    # Number of valid responses used
    # to calculate this factor's score
    participants_count: Mapped[int | None] = mapped_column(
        "ParticipantsCount",
        Integer,
        nullable=True,
    )

    # Value from the previous period
    prev_value: Mapped[Decimal | None] = mapped_column(
        "PrevValue",
        Numeric(10, 2),
        nullable=True,
    )

    # Value measured in the current period
    current_value: Mapped[Decimal] = mapped_column(
        "CurrentValue",
        Numeric(10, 2),
        nullable=False,
    )

    # Target value
    target_value: Mapped[Decimal | None] = mapped_column(
        "TargetValue",
        Numeric(10, 2),
        nullable=True,
    )

    # The measurement record this result belongs to
    record: Mapped["MeasurementRecord"] = relationship(
        back_populates="factor_results",
    )

    # The factor this result belongs to
    factor: Mapped["Factor"] = relationship(
        back_populates="results",
    )