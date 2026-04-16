"""
Interventions API Routes
-----------------------
CRUD endpoints for intervention tracking used by the Interventions tab.
"""

from __future__ import annotations

import json
from datetime import date as date_type
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from backend.api.deps import get_db, get_current_user, require_role
from backend.core.constants import Role
from backend.database import Intervention, Student
from backend.utils.api import success_response

router = APIRouter(
    prefix="/interventions",
    tags=["interventions"],
    dependencies=[Depends(get_current_user)],
)

_READ_ROLES = [Role.ADMIN, Role.FACULTY, Role.RETENTION_TEAM]
_WRITE_ROLES = [Role.ADMIN, Role.FACULTY]


class InterventionCreateRequest(BaseModel):
    student_id: Optional[str] = None
    student_ids: Optional[List[str]] = None
    date: Optional[date_type] = None
    user: str
    action: str
    status: Optional[str] = "Pending"
    assigned_faculty: Optional[str] = None
    risk_score_at_trigger: Optional[float] = None
    threshold_category: Optional[str] = None
    channels: Optional[List[str]] = None
    assigned_team: Optional[str] = None


class InterventionUpdateRequest(BaseModel):
    status: Optional[str] = None
    assigned_faculty: Optional[str] = None
    assigned_team: Optional[str] = None
    effectiveness_score: Optional[float] = None
    ai_reasoning: Optional[str] = None


def _safe_parse_channels(raw: Optional[str]) -> List[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return []


def _serialize_channels(channels: Optional[List[str]]) -> Optional[str]:
    if channels is None:
        return None
    try:
        return json.dumps(channels)
    except Exception:
        return "[]"


def _to_dict(i: Intervention) -> Dict[str, Any]:
    s: Optional[Student] = i.student  # type: ignore[assignment]
    return {
        "id": i.id,
        "student_id": i.student_id,
        "date": i.date.isoformat() if i.date else None,
        "user": i.user,
        "action": i.action,
        "status": i.status or "Pending",
        "assigned_faculty": i.assigned_faculty,
        "ai_suggested": bool(i.ai_suggested) if i.ai_suggested is not None else False,
        "ai_reasoning": i.ai_reasoning,
        "effectiveness_score": i.effectiveness_score,
        "risk_score_at_trigger": i.risk_score_at_trigger,
        "threshold_category": i.threshold_category,
        "channels": _safe_parse_channels(i.channels),
        "assigned_team": i.assigned_team,
        "student": None
        if not s
        else {
            "id": s.id,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "department": s.parent_department_name,
        },
    }


@router.get("")
def list_interventions(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=2000),
    status: Optional[str] = Query(None),
    assigned_faculty: Optional[str] = Query(None),
    student_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _user=Depends(require_role(_READ_ROLES)),
):
    q = db.query(Intervention).options(joinedload(Intervention.student))

    if status:
        q = q.filter(Intervention.status == status)
    if assigned_faculty:
        q = q.filter(Intervention.assigned_faculty == assigned_faculty)
    if student_id:
        q = q.filter(Intervention.student_id == student_id)

    total = q.count()
    rows = q.order_by(desc(Intervention.date), desc(Intervention.id)).offset(skip).limit(limit).all()

    # Ensure relationship objects are available for serialization
    payload = {
        "interventions": [_to_dict(r) for r in rows],
        "total": total,
        "page": (skip // limit) + 1,
        "page_size": limit,
    }
    return success_response(payload, message="Interventions")


@router.post("")
def create_intervention(
    body: InterventionCreateRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_role(_WRITE_ROLES)),
):
    ids: List[str] = []
    if body.student_ids:
        ids = body.student_ids
    elif body.student_id:
        ids = [body.student_id]
    else:
        raise HTTPException(status_code=400, detail="student_id or student_ids is required")

    created: List[Intervention] = []
    for sid in ids:
        # Validate student exists (foreign key safety)
        exists = db.query(Student.id).filter(Student.id == sid).first()
        if not exists:
            raise HTTPException(status_code=404, detail=f"Student '{sid}' not found")

        row = Intervention(
            student_id=sid,
            date=body.date or date_type.today(),
            user=body.user,
            action=body.action,
            status=body.status or "Pending",
            assigned_faculty=body.assigned_faculty,
            risk_score_at_trigger=body.risk_score_at_trigger,  # type: ignore[arg-type]
            threshold_category=body.threshold_category,
            channels=_serialize_channels(body.channels),
            assigned_team=body.assigned_team,
        )
        db.add(row)
        created.append(row)

    db.commit()
    for r in created:
        db.refresh(r)

    payload = {"created": [_to_dict(r) for r in created], "count": len(created)}
    return success_response(payload, message="Intervention(s) created")


@router.patch("/{intervention_id}")
def update_intervention(
    intervention_id: int,
    body: InterventionUpdateRequest,
    db: Session = Depends(get_db),
    _user=Depends(require_role(_WRITE_ROLES)),
):
    row = db.query(Intervention).filter(Intervention.id == intervention_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Intervention not found")

    if body.status is not None:
        row.status = body.status
    if body.assigned_faculty is not None:
        row.assigned_faculty = body.assigned_faculty
    if body.assigned_team is not None:
        row.assigned_team = body.assigned_team
    if body.effectiveness_score is not None:
        row.effectiveness_score = body.effectiveness_score  # type: ignore[assignment]
    if body.ai_reasoning is not None:
        row.ai_reasoning = body.ai_reasoning

    db.add(row)
    db.commit()
    db.refresh(row)

    return success_response(_to_dict(row), message="Intervention updated")
