from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from database_Initiatives.connection import Base

class Section(Base):
    """ORM Model representing the Sections table."""
    __tablename__ = "sections"

    section_id = Column(Integer, primary_key=True, autoincrement=True, name="section_ID")
    section_name = Column(String(255), nullable=False, name="section_name")

    # Define relationships with Products and Actions
    products = relationship("Product", back_populates="section", cascade="all, delete-orphan")
    actions = relationship("Action", back_populates="section", cascade="all, delete-orphan")


class Product(Base):
    """ORM Model representing the Products table linked to Sections."""
    __tablename__ = "products"

    product_id = Column(Integer, primary_key=True, autoincrement=True, name="product_ID")
    product_name = Column(String(255), nullable=False, name="product_name")
    section_id = Column(Integer, ForeignKey("sections.section_ID", ondelete="CASCADE"), nullable=False, name="section_ID")

    # Define relationships with Section and Actions
    section = relationship("Section", back_populates="products")
    actions = relationship("Action", back_populates="product", cascade="all, delete-orphan")


class Status(Base):
    """ORM Model representing the Status table."""
    __tablename__ = "status"

    status_id = Column(Integer, primary_key=True, autoincrement=True, name="status_ID")
    status_name = Column(String(255), nullable=False, name="status_name")

    # Define relationship with Actions
    actions = relationship("Action", back_populates="status")


class Action(Base):
    """ORM Model representing the Actions table linked to Sections, Products, and Status."""
    __tablename__ = "actions"

    action_id = Column(Integer, primary_key=True, autoincrement=True, name="action_ID")
    action_name = Column(String(255), nullable=False, name="action_name")
    creation_date = Column(Date, nullable=True)
    start_date = Column(Date, nullable=True)
    expected_execution_date = Column(Date, nullable=True, name="Expected execution date")
    
    section_id = Column(Integer, ForeignKey("sections.section_ID", ondelete="CASCADE"), nullable=False, name="section_ID")
    product_id = Column(Integer, ForeignKey("products.product_ID", ondelete="CASCADE"), nullable=False, name="product_ID")
    status_id = Column(Integer, ForeignKey("status.status_ID", ondelete="CASCADE"), nullable=False, name="status_ID")

    # Define relationships back to parent tables
    section = relationship("Section", back_populates="actions")
    product = relationship("Product", back_populates="actions")
    status = relationship("Status", back_populates="actions")