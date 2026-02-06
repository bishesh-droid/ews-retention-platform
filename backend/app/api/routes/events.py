"""
Event Ingestion API Endpoints
Handles raw event collection from multiple sources:
- LMS (logins, assignments, grades)
- Zoom (attendance, duration)
- Website/App (page views, videos)
- Communication (email, WhatsApp)
- Marketing (campaigns, lead source)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
import json

from backend.app.database import get_db
from backend.app.models import RawEvent
from backend.app import schemas

router = APIRouter(
    responses={404: {"description": "Not found"}},
)


@router.post("/lms", status_code=201)
def ingest_lms_event(event: schemas.RawEventCreate, db: Session = Depends(get_db)):
    """
    Ingest LMS events: logins, assignments, deadlines, grades
    
    Example event_data:
    {
        "assignment_id": "A101",
        "score": 85,
        "max_score": 100,
        "submitted_late": false,
        "deadline": "2026-02-01T23:59:00Z"
    }
    """
    if event.event_source != "lms":
        raise HTTPException(status_code=400, detail="event_source must be 'lms'")
    
    db_event = RawEvent(
        student_id=event.student_id,
        event_source=event.event_source,
        event_type=event.event_type,
        event_data=json.dumps(event.event_data),
        timestamp=datetime.utcnow()
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    return {"status": "success", "event_id": db_event.id, "message": "LMS event recorded"}


@router.post("/zoom", status_code=201)
def ingest_zoom_event(event: schemas.RawEventCreate, db: Session = Depends(get_db)):
    """
    Ingest Zoom events: attendance, duration, join delays
    
    Example event_data:
    {
        "class_id": "CS101_Lecture5",
        "duration_minutes": 45,
        "join_delay_minutes": 2,
        "left_early": false
    }
    """
    if event.event_source != "zoom":
        raise HTTPException(status_code=400, detail="event_source must be 'zoom'")
    
    db_event = RawEvent(
        student_id=event.student_id,
        event_source=event.event_source,
        event_type=event.event_type,
        event_data=json.dumps(event.event_data),
        timestamp=datetime.utcnow()
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    return {"status": "success", "event_id": db_event.id, "message": "Zoom event recorded"}


@router.post("/website", status_code=201)
def ingest_website_event(event: schemas.RawEventCreate, db: Session = Depends(get_db)):
    """
    Ingest website/app activity: page views, video watch %, clicks
    
    Example event_data:
    {
        "video_id": "V101",
        "watch_percentage": 85,
        "total_duration_minutes": 20,
        "completed": false
    }
    """
    if event.event_source != "website":
        raise HTTPException(status_code=400, detail="event_source must be 'website'")
    
    db_event = RawEvent(
        student_id=event.student_id,
        event_source=event.event_source,
        event_type=event.event_type,
        event_data=json.dumps(event.event_data),
        timestamp=datetime.utcnow()
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    return {"status": "success", "event_id": db_event.id, "message": "Website event recorded"}


@router.post("/communication", status_code=201)
def ingest_communication_event(event: schemas.RawEventCreate, db: Session = Depends(get_db)):
    """
    Ingest WhatsApp/Email tracking: opens, replies, ignored messages
    
    Example event_data:
    {
        "message_id": "E2026_001",
        "channel": "email",
        "opened": true,
        "replied": false,
        "opened_at": "2026-02-05T09:15:00Z"
    }
    """
    if event.event_source != "communication":
        raise HTTPException(status_code=400, detail="event_source must be 'communication'")
    
    db_event = RawEvent(
        student_id=event.student_id,
        event_source=event.event_source,
        event_type=event.event_type,
        event_data=json.dumps(event.event_data),
        timestamp=datetime.utcnow()
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    return {"status": "success", "event_id": db_event.id, "message": "Communication event recorded"}


@router.post("/marketing", status_code=201)
def ingest_marketing_event(event: schemas.RawEventCreate, db: Session = Depends(get_db)):
    """
    Ingest marketing campaign data: lead source, campaign, cost
    
    Example event_data:
    {
        "campaign_name": "Feb_2026_Promotion",
        "source": "facebook_ads",
        "cost_per_lead": 15.50,
        "conversion_stage": "enrolled"
    }
    """
    if event.event_source != "marketing":
        raise HTTPException(status_code=400, detail="event_source must be 'marketing'")
    
    db_event = RawEvent(
        student_id=event.student_id,
        event_source=event.event_source,
        event_type=event.event_type,
        event_data=json.dumps(event.event_data),
        timestamp=datetime.utcnow()
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    return {"status": "success", "event_id": db_event.id, "message": "Marketing event recorded"}


@router.get("/{student_id}", response_model=list)
def get_student_events(
    student_id: str,
    event_source: str = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get raw events for a student, optionally filtered by source
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
            "timestamp": e.timestamp
        }
        for e in events
    ]
