"""
Event Ingestion API Endpoints
Handles raw event collection from multiple sources.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

from backend.api.deps import get_db, get_current_user, require_resource_ownership
from backend.database import RawEvent

router = APIRouter(
    responses={404: {"description": "Not found"}},
    dependencies=[Depends(get_current_user)],
)


class RawEventCreate(BaseModel):
    student_id: str
    event_source: str
    event_type: str
    event_data: Optional[Dict[str, Any]] = None


def _create_event(event: RawEventCreate, expected_source: str, db: Session):
    if event.event_source != expected_source:
        raise HTTPException(status_code=400, detail=f"event_source must be '{expected_source}'")

    db_event = RawEvent(
        student_id=event.student_id,
        event_source=event.event_source,
        event_type=event.event_type,
        event_data=json.dumps(event.event_data) if event.event_data else "{}",
        timestamp=datetime.utcnow()
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return {"status": "success", "event_id": db_event.id, "message": f"{expected_source} event recorded"}


@router.post("/lms", status_code=201)
def ingest_lms_event(event: RawEventCreate, db: Session = Depends(get_db)):
    """Ingest LMS events: logins, assignments, deadlines, grades."""
    return _create_event(event, "lms", db)


@router.post("/zoom", status_code=201)
def ingest_zoom_event(event: RawEventCreate, db: Session = Depends(get_db)):
    """Ingest Zoom events: attendance, duration, join delays."""
    return _create_event(event, "zoom", db)


@router.post("/website", status_code=201)
def ingest_website_event(event: RawEventCreate, db: Session = Depends(get_db)):
    """Ingest website/app activity: page views, video watch %, clicks."""
    return _create_event(event, "website", db)


@router.post("/communication", status_code=201)
def ingest_communication_event(event: RawEventCreate, db: Session = Depends(get_db)):
    """Ingest WhatsApp/Email tracking: opens, replies, ignored messages."""
    return _create_event(event, "communication", db)


@router.post("/marketing", status_code=201)
def ingest_marketing_event(event: RawEventCreate, db: Session = Depends(get_db)):
    """Ingest marketing campaign data: lead source, campaign, cost."""
    return _create_event(event, "marketing", db)


@router.get("/{student_id}")
def get_student_events(
    student_id: str,
    event_source: str = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user=Depends(require_resource_ownership("student_id")),
):
    """
    Get raw events for a student, optionally filtered by source.

    FERPA-compliant: Only staff (faculty/admin) or the student themselves
    can access this endpoint.
    """
    query = db.query(RawEvent).filter(RawEvent.student_id == student_id)

    if event_source:
        query = query.filter(RawEvent.event_source == event_source)

    events = query.order_by(RawEvent.timestamp.desc()).limit(limit).all()

    return [
        {
            "id": e.id,
            "event_source": e.event_source,
            "event_type": e.event_type,
            "event_data": json.loads(e.event_data) if e.event_data else {},
            "timestamp": e.timestamp,
        }
        for e in events
    ]
