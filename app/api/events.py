from fastapi import APIRouter
from app.models.events import Event, EventIngestResponse, EventBatch, EventBatchResponse
from ingest import ingest_event

router = APIRouter(prefix="/api", tags=["events"])

@router.post("/ingest", response_model=EventIngestResponse)
def ingest(evt: Event):
    eid = ingest_event(evt.model_dump())
    return {"event_id": str(eid)}

@router.post("/ingest-batch", response_model=EventBatchResponse)
def ingest_batch(batch: EventBatch):
    ids = []
    for e in batch.events:
        eid = ingest_event(e.model_dump())
        ids.append(str(eid))
    return {"inserted": len(ids), "ids": ids}
