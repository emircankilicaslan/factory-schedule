from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List
from pydantic import BaseModel
import uvicorn

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class Operation(BaseModel):
    id: str
    workOrderId: str
    index: int
    machineId: str
    name: str
    start: datetime
    end: datetime

class WorkOrder(BaseModel):
    id: str
    product: str
    qty: int
    operations: List[Operation]

# Seed Data
work_orders = [
    WorkOrder(
        id="WO-1001",
        product="Widget A",
        qty=100,
        operations=[
            Operation(id="OP-1", workOrderId="WO-1001", index=1, machineId="M1", name="Cut",
                      start=datetime.fromisoformat("2025-08-20T09:00:00+00:00"),
                      end=datetime.fromisoformat("2025-08-20T10:00:00+00:00")),
            Operation(id="OP-2", workOrderId="WO-1001", index=2, machineId="M2", name="Assemble",
                      start=datetime.fromisoformat("2025-08-20T10:10:00+00:00"),
                      end=datetime.fromisoformat("2025-08-20T12:00:00+00:00"))
        ]
    ),
    WorkOrder(
        id="WO-1002",
        product="Widget B",
        qty=50,
        operations=[
            Operation(id="OP-3", workOrderId="WO-1002", index=1, machineId="M1", name="Cut",
                      start=datetime.fromisoformat("2025-08-20T09:30:00+00:00"),
                      end=datetime.fromisoformat("2025-08-20T10:30:00+00:00")),
            Operation(id="OP-4", workOrderId="WO-1002", index=2, machineId="M2", name="Assemble",
                      start=datetime.fromisoformat("2025-08-20T10:40:00+00:00"),
                      end=datetime.fromisoformat("2025-08-20T12:15:00+00:00"))
        ]
    )
]

@app.get("/workorders", response_model=List[WorkOrder])
def get_work_orders():
    return work_orders

@app.put("/update-operation/{op_id}")
def update_operation(op_id: str, start: datetime, end: datetime):
    # Find operation
    for wo in work_orders:
        for op in wo.operations:
            if op.id == op_id:
                # Validation R1: Precedence
                idx = op.index - 1
                if idx > 0:
                    prev_op = wo.operations[idx - 1]
                    if start < prev_op.end:
                        raise HTTPException(status_code=400, detail="Cannot start before previous operation ends")
                # Validation R2: Lane exclusivity
                for other_wo in work_orders:
                    for other_op in other_wo.operations:
                        if other_op.machineId == op.machineId and other_op.id != op.id:
                            if not (end <= other_op.start or start >= other_op.end):
                                raise HTTPException(status_code=400, detail="Overlap with other operation in lane")
                # Validation R3: No past
                if start < datetime.utcnow():
                    raise HTTPException(status_code=400, detail="Cannot start in the past")
                op.start = start
                op.end = end
                return {"message": "Operation updated"}
    raise HTTPException(status_code=404, detail="Operation not found")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
