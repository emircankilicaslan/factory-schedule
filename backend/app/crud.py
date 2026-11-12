from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models


def get_workorders(db: Session) -> List[models.WorkOrder]:
    stmt = select(models.WorkOrder).order_by(models.WorkOrder.id)
    return list(db.scalars(stmt).all())


def get_operation(db: Session, op_id: str) -> Optional[models.Operation]:
    return db.get(models.Operation, op_id)


def get_workorder_operations(db: Session, work_order_id: str) -> List[models.Operation]:
    stmt = (
        select(models.Operation)
        .where(models.Operation.work_order_id == work_order_id)
        .order_by(models.Operation.index)
    )
    return list(db.scalars(stmt).all())


def get_operations_by_machine(
    db: Session, machine_id: str, exclude_id: Optional[str] = None
) -> List[models.Operation]:
    stmt = select(models.Operation).where(models.Operation.machine_id == machine_id)
    ops = list(db.scalars(stmt).all())
    return [o for o in ops if o.id != exclude_id] if exclude_id else ops