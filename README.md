
# Factory Scheduler (FastAPI + React)

web app that visualizes factory work orders on a simple Gantt-style timeline.

## Tech
- Backend: FastAPI, SQLAlchemy, Postgres
- Frontend: React (Vite) + vis-timeline
- DB Seeding: `seed.json`

## Run with Docker Compose

```bash
docker compose up --build
```
- Backend: http://localhost:8000
- Frontend: http://localhost:5173
- DB: Postgres on localhost:5432 (`app/app`, db `factory`)

If there is no data on first boot, backend seeds from `seed.json` automatically.

## API

### GET `/workorders` → 200 OK
Returns all work orders with their operations ordered by `index`.

**Response (excerpt):**
```json
[
  {
    "id": "WO-1001",
    "product": "Widget A",
    "qty": 100,
    "operations": [
      {
        "id": "OP-1",
        "workOrderId": "WO-1001",
        "index": 1,
        "machineId": "M1",
        "name": "Cut",
        "start": "2025-08-20T09:00:00+00:00",
        "end": "2025-08-20T10:00:00+00:00"
      }
    ]
  }
]
```

### PATCH `/operations/{op_id}` → 200 OK
Update a single operation's `start` and `end` (ISO-8601 UTC).

**Payload:**
```json
{ "start": "2025-08-20T10:10:00Z", "end": "2025-08-20T12:00:00Z" }
```

**Validations:**  
- **R1 — Precedence**: op k must start at/after op k-1 ends.  
- **R2 — Lane exclusivity**: no overlaps on same `machineId`.  
- **R3 — No past**: start cannot be before **now**.

**Errors (examples):**
```json
{
  "detail": "R1 violation: Operation OP-2 must start at or after previous operation ends (OP-1 ends 2025-08-20T10:00:00+00:00)."
}
```
```json
{
  "detail": "R2 violation: Overlaps with operation OP-3 on machine M1 (2025-08-20T09:30:00+00:00–2025-08-20T10:30:00+00:00)."
}
```
```json
{
  "detail": "R3 violation: Start 2025-08-20T08:59:00+00:00 is before now 2025-08-21T12:34:56+00:00."
}
```

## Frontend UX
- Lanes are derived from unique `machineId`s.
- Bars show **`WO-ID · operation name`**.
- A vertical **now** line is visible.
- Click any operation → all operations with the same `workOrderId` highlight.  
- Click blank space or **Clear highlight** to remove highlight.
- Buttons on each card let you nudge an operation by ±10 minutes to test validations.

## Local Dev (optional)

### Backend
```bash
cd backend
export DATABASE_URL=postgresql+psycopg2://app:app@localhost:5432/factory
uvicorn app.main:app --reload
```
Seed/reset:
```bash
python -m app.seed  # reads ../seed.json
```

### Frontend
```bash
cd frontend
npm install
VITE_API_BASE=http://localhost:8000 npm run dev
```

## Notes
- Times are stored as timezone-aware UTC in Postgres and returned as ISO-8601.
- Only same-lane drag/drop would be needed for the bonus; here we offer ±10 min buttons to exercise the update API.
