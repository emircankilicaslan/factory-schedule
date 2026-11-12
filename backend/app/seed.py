import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from dateutil import parser

from .database import Base, SessionLocal, engine
from .models import Operation, WorkOrder

DEFAULT_SEED = os.path.join(os.path.dirname(__file__), "seed.json")


def parse_utc(value: str) -> datetime:
    """ISO-8601 metni ayrıştırır; saat dilimi yoksa UTC kabul eder (örnek veri dosyası karışık olabilir)."""
    dt = parser.isoparse(value)
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


def load_seed(path: Optional[str] = None) -> List[dict]:
    with open(path or os.getenv("SEED_FILE") or DEFAULT_SEED, "r", encoding="utf-8") as f:
        return json.load(f)


def shift_to_now(data: List[dict], now: Optional[datetime] = None) -> List[dict]:
    """Örnek verideki zamanları, ilk operasyon bir sonraki tam saatte başlayacak şekilde ötelemek için kullanılır.

    Böylece demo her zaman gelecekte kalır ve R3 ("geçmiş yasak") kuralı yüzünden güncelleme denemeleri
    baştan reddedilmez. Operasyonlar arasındaki göreli süreler korunur.
    """
    now = now or datetime.now(timezone.utc)
    starts = [parse_utc(op["start"]) for wo in data for op in wo["operations"]]
    if not starts:
        return data
    target = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    delta = target - min(starts)
    for wo in data:
        for op in wo["operations"]:
            op["start"] = (parse_utc(op["start"]) + delta).isoformat()
            op["end"] = (parse_utc(op["end"]) + delta).isoformat()
    return data


def run_seed(path: Optional[str] = None, reset: bool = True, shift: bool = True) -> None:
    data = load_seed(path)
    if shift:
        data = shift_to_now(data)

    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        for wo in data:
            db.add(WorkOrder(id=wo["id"], product=wo["product"], qty=wo["qty"]))
            for op in wo["operations"]:
                db.add(
                    Operation(
                        id=op["id"],
                        work_order_id=op["workOrderId"],
                        index=op["index"],
                        machine_id=op["machineId"],
                        name=op["name"],
                        start=parse_utc(op["start"]),
                        end=parse_utc(op["end"]),
                    )
                )
        db.commit()


if __name__ == "__main__":
    run_seed()