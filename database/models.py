from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal

from connection import Base

class Department(Base):
     __tablename__ = "Department"
     department_id: Mapped[int] = mapped_column(
      "DepartmentID",  
      Integer,
      primary_key=True,
      autoincrement =True,
     )

     department_name: Mapped[str] = mapped_column(
      "DepartmentName",
      String(100),
      nullable=False,    
     )

     services: Mapped[list["Service"]] = relationship(
          back_populates="department"
     )


class Service(Base):
     __tablename__ = "Service"
     service_id: Mapped[int] = mapped_column(
      "ServiceID",
      Integer,
      primary_key=True,
      autoincrement=True,
     )

     department_id: Mapped[int] = mapped_column(
      "DepartmentID",
      Integer,
      ForeignKey("Department.DepartmentID"),
      nullable=False,  
     )

     service_name: Mapped[str] = mapped_column(
      "ServiceName",
      String(150),
      nullable=False,   
     )

     department: Mapped["Department"] = relationship(
          back_populates="services"
     )

     measurement_records: Mapped[list["MeasurementRecord"]] = relationship(
        back_populates="service"
     )

class MeasurementRecord(Base):
    __tablename__ = "MeasurementRecords"
    record_id: Mapped[int] = mapped_column(
      "RecordID",
      Integer,
      primary_key=True,
      autoincrement=True,     
     )

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
      nullable=True,     
     )

    review: Mapped[str | None] = mapped_column(
      "Review",
      Text,
      nullable=True,     
     )

    service: Mapped["Service"] = relationship(
        back_populates="measurement_records"
    )

    indicator_results: Mapped[list["IndicatorResult"]] = relationship(
          back_populates="record"
     )     



class IndicatorResult(Base):
     __tablename__="IndicatorResults"
     result_id: Mapped[int] = mapped_column(
      "ResultID",
      Integer,
      primary_key=True,
      autoincrement=True     
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

     prev_value: Mapped[Decimal | None] = mapped_column(
      "PrevValue",
      Numeric(10, 2),    
      nullable=True,
     )

     current_value: Mapped[Decimal] = mapped_column(
      "CurrentValue",
      Numeric(10, 2),    
      nullable=False,
     )

     target_value: Mapped[Decimal] = mapped_column(
      "TargetValue",
      Numeric(10, 2),    
      nullable=False,
     )

     record: Mapped["MeasurementRecord"] = relationship(
          back_populates="indicator_results"
     )

     indicator: Mapped["Indicator"] = relationship(
          back_populates="results"
     )

          

class Indicator(Base):
     __tablename__="Indicators"
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

     results: Mapped[list["IndicatorResult"]] = relationship(
          back_populates="indicator"
     ) 
