
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from .database import Base

class WorkOrder(Base):
    __tablename__ = "work_orders"
    id = Column(String, primary_key=True, index=True)
    product = Column(String, nullable=False)
    qty = Column(Integer, nullable=False)

    operations = relationship("Operation", back_populates="work_order", cascade="all, delete-orphan", order_by="Operation.index")

class Operation(Base):
    __tablename__ = "operations"
    id = Column(String, primary_key=True, index=True)
    work_order_id = Column(String, ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    index = Column(Integer, nullable=False)
    machine_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    start = Column(DateTime(timezone=True), nullable=False)
    end = Column(DateTime(timezone=True), nullable=False)

    work_order = relationship("WorkOrder", back_populates="operations")
