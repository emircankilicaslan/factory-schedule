
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import List

class OperationBase(BaseModel):
    id: str
    workOrderId: str = Field(alias="work_order_id")
    index: int
    machineId: str = Field(alias="machine_id")
    name: str
    start: datetime
    end: datetime

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

class Operation(OperationBase):
    pass

class WorkOrderBase(BaseModel):
    id: str
    product: str
    qty: int

class WorkOrder(WorkOrderBase):
    operations: List[Operation] = []

    model_config = ConfigDict(from_attributes=True)

class OperationUpdate(BaseModel):
    start: datetime
    end: datetime
