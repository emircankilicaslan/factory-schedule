
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from . import models

def get_workorders(db: Session) -> List[models.WorkOrder]:
    stmt = select(models.WorkOrder).order_by(models.WorkOrder.id)
    return db.scalars(stmt).all()

def get_operation(db: Session, op_id: str) -> Optional[models.Operation]:
    return db.get(models.Operation, op_id)

def get_operations_by_machine(db: Session, machine_id: str, exclude_id: Optional[str]=None) -> List[models.Operation]:
    stmt = select(models.Operation).where(models.Operation.machine_id == machine_id)
    ops = db.scalars(stmt).all()
    if exclude_id:
        ops = [o for o in ops if o.id != exclude_id]
    return ops
