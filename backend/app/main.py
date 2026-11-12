import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from . import crud, rules, schemas
from .database import Base, SessionLocal, engine, get_db
from .seed import run_seed


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Açılışta tabloları oluşturur; veritabanı boşsa örnek veriyi yükler."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        empty = not crud.get_workorders(db)
    if empty:
        run_seed(reset=False)
    yield


app = FastAPI(title="Factory Scheduler API", lifespan=lifespan)

origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/workorders", response_model=List[schemas.WorkOrder], response_model_by_alias=False)
def get_work_orders(db: Session = Depends(get_db)):
    """Tüm iş emirleri; operasyonlar `index` sırasındadır."""
    return crud.get_workorders(db)


@app.patch("/operations/{op_id}", response_model=schemas.Operation, response_model_by_alias=False)
def update_operation(op_id: str, body: schemas.OperationUpdate, db: Session = Depends(get_db)):
    """Bir operasyonun başlangıç/bitişini günceller. Kural ihlalinde 409, geçersiz aralıkta 422 döner."""
    op = crud.get_operation(db, op_id)
    if op is None:
        raise HTTPException(status_code=404, detail="Operation not found")

    siblings = crud.get_workorder_operations(db, op.work_order_id)
    previous = next((o for o in siblings if o.index == op.index - 1), None)
    following = next((o for o in siblings if o.index == op.index + 1), None)
    lane_ops = crud.get_operations_by_machine(db, op.machine_id, exclude_id=op.id)

    try:
        op.start, op.end = rules.validate_update(
            body.start, body.end, previous, following, lane_ops, now=datetime.now(timezone.utc)
        )
    except rules.RuleViolation as e:
        status = 422 if e.code == "INVALID" else 409
        raise HTTPException(status_code=status, detail=e.message)

    db.commit()
    db.refresh(op)
    return op