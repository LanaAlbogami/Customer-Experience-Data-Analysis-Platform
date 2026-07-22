from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.connection import Base

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