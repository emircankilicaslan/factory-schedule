import os
import json
from datetime import datetime
from dateutil import parser
from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import WorkOrder, Operation

def run_seed(path: str = None):
    # Eğer path verilmemişse, seed.py ile aynı klasördeki seed.json'u kullan
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "seed.json")

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    with SessionLocal() as db:
        for wo in data:
            w = WorkOrder(id=wo["id"], product=wo["product"], qty=wo["qty"])
            db.add(w)
            for op in wo["operations"]:
                o = Operation(
                    id=op["id"],
                    work_order_id=op["workOrderId"],
                    index=op["index"],
                    machine_id=op["machineId"],
                    name=op["name"],
                    start=parser.isoparse(op["start"]),
                    end=parser.isoparse(op["end"]),
                )
                db.add(o)
        db.commit()

if __name__ == "__main__":
    run_seed()
