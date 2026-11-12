from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import crud, models
from app.database import Base, get_db
from app.main import app
from app.seed import run_seed, shift_to_now

FUTURE = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) + timedelta(days=30)


def iso(hours: float) -> str:
    return (FUTURE + timedelta(hours=hours)).isoformat()


@pytest.fixture()
def client():
    """Her test için temiz, bellek içi SQLite; uygulama veritabanı bağımlılığı bununla değiştirilir."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    with Session() as db:
        wo1 = models.WorkOrder(id="WO-1", product="A", qty=10)
        wo2 = models.WorkOrder(id="WO-2", product="B", qty=5)
        db.add_all([wo1, wo2])
        db.add_all([
            models.Operation(id="OP-1", work_order_id="WO-1", index=1, machine_id="M1", name="Cut",
                             start=FUTURE + timedelta(hours=1), end=FUTURE + timedelta(hours=2)),
            models.Operation(id="OP-2", work_order_id="WO-1", index=2, machine_id="M2", name="Assemble",
                             start=FUTURE + timedelta(hours=3), end=FUTURE + timedelta(hours=4)),
            models.Operation(id="OP-3", work_order_id="WO-2", index=1, machine_id="M1", name="Cut",
                             start=FUTURE + timedelta(hours=5), end=FUTURE + timedelta(hours=6)),
        ])
        db.commit()

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_workorders_are_listed_with_ordered_operations(client):
    data = client.get("/workorders").json()
    assert [w["id"] for w in data] == ["WO-1", "WO-2"]
    ops = data[0]["operations"]
    assert [o["id"] for o in ops] == ["OP-1", "OP-2"]
    assert {"workOrderId", "machineId", "index"} <= ops[0].keys()  # camelCase çıktı


def test_valid_patch_updates_the_operation(client):
    r = client.patch("/operations/OP-2", json={"start": iso(3.5), "end": iso(4.5)})
    assert r.status_code == 200
    assert r.json()["id"] == "OP-2"
    stored = next(o for w in client.get("/workorders").json() for o in w["operations"] if o["id"] == "OP-2")
    assert stored["start"].startswith((FUTURE + timedelta(hours=3, minutes=30)).strftime("%Y-%m-%dT%H:30"))


def test_unknown_operation_is_404(client):
    assert client.patch("/operations/NOPE", json={"start": iso(1), "end": iso(2)}).status_code == 404


def test_r1_precedence_violation_is_409(client):
    r = client.patch("/operations/OP-2", json={"start": iso(1.5), "end": iso(2.5)})
    assert r.status_code == 409 and "R1" in r.json()["detail"]


def test_r1_cannot_push_operation_past_its_successor(client):
    r = client.patch("/operations/OP-1", json={"start": iso(1), "end": iso(3.5)})
    assert r.status_code == 409 and "R1" in r.json()["detail"]


def test_r2_lane_overlap_is_409(client):
    r = client.patch("/operations/OP-3", json={"start": iso(1.5), "end": iso(2.5)})  # OP-1 ile M1'de çakışır
    assert r.status_code == 409 and "R2" in r.json()["detail"]


def test_r3_past_start_is_409(client):
    past = datetime.now(timezone.utc) - timedelta(days=1)
    r = client.patch("/operations/OP-3", json={"start": past.isoformat(), "end": (past + timedelta(hours=1)).isoformat()})
    assert r.status_code == 409 and "R3" in r.json()["detail"]


def test_invalid_interval_is_422(client):
    assert client.patch("/operations/OP-3", json={"start": iso(6), "end": iso(5)}).status_code == 422
    assert client.patch("/operations/OP-3", json={"start": "bozuk"}).status_code == 422


def test_failed_update_does_not_change_data(client):
    before = client.get("/workorders").json()
    client.patch("/operations/OP-2", json={"start": iso(1.5), "end": iso(2.5)})
    assert client.get("/workorders").json() == before


def test_seed_accepts_timestamps_without_timezone():
    data = [{"id": "W", "product": "p", "qty": 1, "operations": [
        {"id": "O1", "workOrderId": "W", "index": 1, "machineId": "M1", "name": "x",
         "start": "2025-08-20T09:00:00", "end": "2025-08-20T10:00:00Z"}]}]
    out = shift_to_now(data, datetime(2030, 5, 5, 14, 20, tzinfo=timezone.utc))
    assert out[0]["operations"][0]["start"].startswith("2030-05-05T15:00:00")


def test_seed_shifts_times_into_the_future_and_keeps_relative_durations():
    data = [{"id": "W", "product": "p", "qty": 1, "operations": [
        {"id": "O1", "workOrderId": "W", "index": 1, "machineId": "M1", "name": "x",
         "start": "2025-08-20T09:00:00Z", "end": "2025-08-20T10:00:00Z"},
        {"id": "O2", "workOrderId": "W", "index": 2, "machineId": "M2", "name": "y",
         "start": "2025-08-20T10:10:00Z", "end": "2025-08-20T12:00:00Z"}]}]
    now = datetime(2030, 5, 5, 14, 20, tzinfo=timezone.utc)
    out = shift_to_now(data, now)
    ops = out[0]["operations"]
    from dateutil import parser
    assert parser.isoparse(ops[0]["start"]) == datetime(2030, 5, 5, 15, 0, tzinfo=timezone.utc)
    assert parser.isoparse(ops[1]["start"]) - parser.isoparse(ops[0]["end"]) == timedelta(minutes=10)