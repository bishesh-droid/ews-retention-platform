from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from backend.database import User, AuditLog, IngestionRun
from backend.api import deps
from backend.schemas.auth import UserOut
from backend.database.models.student import Student
from backend.config import INTERVENTION_THRESHOLDS
from backend.database.models.goals_and_risks import RiskSnapshot

router = APIRouter()


@router.get("/users", response_model=List[UserOut])
def list_users(
    current_user: deps.User = Depends(deps.require_role(["Admin"])),
    db: Session = Depends(deps.get_db)
):
    """
    List all system users (Admin only).
    """
    return db.query(User).all()


@router.get("/audit-logs")
def get_audit_logs(
    current_user: deps.User = Depends(deps.require_role(["Admin"])),
    db: Session = Depends(deps.get_db)
):
    """
    Get system audit trail (Admin only).
    """
    return db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()


@router.get("/ingestion-runs")
def list_ingestion_runs(
    current_user: deps.User = Depends(deps.require_role(["Admin"])),
    db: Session = Depends(deps.get_db),
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
):
    """
    List ingestion runs with pagination (Admin only).

    Returns list of IngestionRun records ordered by run_at DESC.
    """
    runs = (
        db.query(IngestionRun)
        .order_by(IngestionRun.run_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": run.id,
            "run_at": run.run_at.isoformat() if run.run_at else None,
            "triggered_by": run.triggered_by,
            "status": run.status,
            "duration_seconds": run.duration_seconds,
            "students_created": run.students_created,
            "students_updated": run.students_updated,
            "enrollments_updated": run.enrollments_updated,
            "graded_components_added": run.graded_components_added,
            "error_count": len(run.errors) if run.errors else 0,
            "files_processed": run.files_processed or [],
        }
        for run in runs
    ]


@router.get("/course-registry")
def list_course_registry(
    current_user: deps.User = Depends(deps.require_role(["Admin"])),
    db: Session = Depends(deps.get_db),
):
    """
    List all CourseContentRegistry entries (Admin only).
    """
    from backend.database.models.course_content_registry import CourseContentRegistry

    rows = db.query(CourseContentRegistry).order_by(
        CourseContentRegistry.semester_name,
        CourseContentRegistry.course_offering_code,
    ).all()

    return [
        {
            "course_code": r.course_offering_code,
            "course_name": r.course_name,
            "semester": r.semester_name,
            "content_required": r.content_required,
            "last_updated_at": r.last_updated_at.isoformat() if r.last_updated_at else None,
            "source_file": r.source_file,
        }
        for r in rows
    ]


@router.put("/course-registry/{course_code}")
def update_course_registry(
    course_code: str,
    request: dict,
    current_user: deps.User = Depends(deps.require_role(["Admin"])),
    db: Session = Depends(deps.get_db),
):
    """
    Manually override content_required for a course (Admin only).

    Body: {"semester_name": str, "content_required": int, "reason": str}
    """
    from backend.database.models.course_content_registry import CourseContentRegistry
    import logging

    logger = logging.getLogger(__name__)

    semester_name = request.get("semester_name")
    content_required = request.get("content_required")
    reason = request.get("reason", "No reason provided")

    if not semester_name or not isinstance(content_required, int):
        raise HTTPException(status_code=400, detail="semester_name and content_required required")

    existing = (
        db.query(CourseContentRegistry)
        .filter_by(course_offering_code=course_code, semester_name=semester_name)
        .first()
    )

    if existing:
        old_value = existing.content_required
        existing.content_required = content_required
        existing.source_file = f"manual_override_by_{current_user.username}"
        action = "updated"
    else:
        existing = CourseContentRegistry(
            course_offering_code=course_code,
            course_name=course_code,
            semester_name=semester_name,
            content_required=content_required,
            source_file=f"manual_override_by_{current_user.username}",
        )
        db.add(existing)
        old_value = None
        action = "created"

    db.commit()

    username = getattr(current_user, "username", "unknown")
    log_msg = (
        f"Manual override by {username}: {course_code} {semester_name} "
        f"content_required set to {content_required}. Reason: {reason}"
    )
    logger.info(log_msg)

    return {
        "course_code": course_code,
        "semester": semester_name,
        "content_required": content_required,
        "action": action,
        "previous_value": old_value,
        "message": log_msg,
    }


@router.get("/intervention-effectiveness")
def get_intervention_effectiveness(
    current_user: deps.User = Depends(deps.require_role(["Admin"])),
    db: Session = Depends(deps.get_db),
    semester: Optional[str] = None,
    program: Optional[str] = None,
    week_from: Optional[int] = None,
    week_to: Optional[int] = None,
):
    """
    Get intervention effectiveness summary (Admin only).
    
    Returns metrics on recommendation review rates, acted-on rates, and outcomes.
    """
    from backend.database.models.intervention_log import InterventionLog
    from sqlalchemy import func

    query = db.query(InterventionLog)
    
    if semester:
        query = query.filter(InterventionLog.semester_name == semester)
    if week_from:
        query = query.filter(InterventionLog.week_number >= week_from)
    if week_to:
        query = query.filter(InterventionLog.week_number <= week_to)
    
    # Join with Student for program filtering
    if program is not None:
        # Validate and sanitize program filter (SEC-8)
        program_clean = program.strip()
        if len(program_clean) > 100:
            raise HTTPException(400, "program filter value too long")
        # SQLAlchemy's .ilike() is parameterized — the pattern is bound as a parameter,
        # not injected into the SQL string. Length check prevents log flooding and ReDoS.
        query = query.join(Student, InterventionLog.student_org_id == Student.org_defined_id)
        query = query.filter(Student.parent_department_name.ilike(f"%{program_clean}%"))
    
    all_logs = query.all()
    
    if not all_logs:
        return {
            "total_recommendations": 0,
            "reviewed": 0,
            "review_rate": 0.0,
            "acted_on": 0,
            "acted_on_rate": 0.0,
            "dismissed": 0,
            "pending_review": 0,
            "outcomes": {"improved": 0, "unchanged": 0, "worsened": 0, "pending": 0},
            "improvement_rate_among_acted": 0.0,
            "avg_risk_delta_after_action": 0.0,
            "by_intervention_type": {},
            "by_engagement_pattern": {},
        }
    
    total = len(all_logs)
    reviewed = sum(1 for log in all_logs if log.reviewed)
    acted_on = sum(1 for log in all_logs if log.acted_on is True)
    dismissed = sum(1 for log in all_logs if log.acted_on is False)
    pending = sum(1 for log in all_logs if log.acted_on is None)
    
    outcomes = {"improved": 0, "unchanged": 0, "worsened": 0, "pending": 0}
    total_delta = 0.0
    acted_with_outcome = 0
    
    for log in all_logs:
        if log.outcome:
            outcomes[log.outcome] = outcomes.get(log.outcome, 0) + 1
        if log.acted_on and log.outcome_delta is not None:
            total_delta += log.outcome_delta
            acted_with_outcome += 1
    
    # By intervention type
    type_stats = {}
    for log in all_logs:
        itype = log.intervention_type or "unknown"
        if itype not in type_stats:
            type_stats[itype] = {"count": 0, "acted": 0, "improved": 0}
        type_stats[itype]["count"] += 1
        if log.acted_on:
            type_stats[itype]["acted"] += 1
        if log.outcome == "improved":
            type_stats[itype]["improved"] += 1
    
    by_type = {}
    for itype, stats in type_stats.items():
        by_type[itype] = {
            "count": stats["count"],
            "acted_rate": round(stats["acted"] / stats["count"], 3) if stats["count"] > 0 else 0,
            "improvement_rate": round(stats["improved"] / stats["acted"], 3) if stats["acted"] > 0 else 0,
        }
    
    # By engagement pattern
    pattern_stats = {}
    for log in all_logs:
        pattern = log.engagement_pattern or "unknown"
        if pattern not in pattern_stats:
            pattern_stats[pattern] = {"count": 0, "improved": 0}
        pattern_stats[pattern]["count"] += 1
        if log.outcome == "improved":
            pattern_stats[pattern]["improved"] += 1
    
    by_pattern = {}
    for pattern, stats in pattern_stats.items():
        acted_count = sum(1 for log in all_logs if log.engagement_pattern == pattern and log.acted_on)
        by_pattern[pattern] = {
            "count": stats["count"],
            "improvement_rate": round(stats["improved"] / acted_count, 3) if acted_count > 0 else 0,
        }
    
    improved_among_acted = outcomes["improved"] if acted_on > 0 else 0
    avg_delta = total_delta / acted_with_outcome if acted_with_outcome > 0 else 0
    
    return {
        "total_recommendations": total,
        "reviewed": reviewed,
        "review_rate": round(reviewed / total, 3) if total > 0 else 0.0,
        "acted_on": acted_on,
        "acted_on_rate": round(acted_on / total, 3) if total > 0 else 0.0,
        "dismissed": dismissed,
        "pending_review": pending,
        "outcomes": outcomes,
        "improvement_rate_among_acted": round(improved_among_acted / acted_on, 3) if acted_on > 0 else 0.0,
        "avg_risk_delta_after_action": round(avg_delta, 1),
        "by_intervention_type": by_type,
        "by_engagement_pattern": by_pattern,
    }


@router.get("/ingestion-runs/{run_id}/summary")
def get_ingestion_run_summary(
    run_id: int,
    current_user: deps.User = Depends(deps.require_role(["Admin"])),
    db: Session = Depends(deps.get_db),
):
    """
    Get detailed summary of a specific ingestion run (Admin only).

    Includes:
    - Full IngestionRun record
    - Students with significant risk score changes (>10 points) vs previous run
    """
    run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Ingestion run not found")

    # Find previous run for comparison
    previous_run = (
        db.query(IngestionRun)
        .filter(IngestionRun.id < run_id)
        .filter(IngestionRun.status.in_(["success", "partial"]))
        .order_by(IngestionRun.id.desc())
        .first()
    )

    significant_risk_changes = []

    if previous_run:
        # Find students with risk score delta > 10
        # Query latest RiskSnapshot for each student at time of this run
        current_snapshots = (
            db.query(
                RiskSnapshot.student_id,
                RiskSnapshot.risk_score,
                Student.first_name,
                Student.last_name,
                Student.org_defined_id,
            )
            .join(Student, RiskSnapshot.student_id == Student.id)
            .filter(RiskSnapshot.timestamp >= run.run_at)
            .filter(RiskSnapshot.timestamp < (previous_run.run_at if previous_run else run.run_at))
            .all()
        )

        # Get previous snapshots for those students
        if current_snapshots:
            student_ids = [s.student_id for s in current_snapshots]
            prev_snapshots = (
                db.query(RiskSnapshot.student_id, RiskSnapshot.risk_score)
                .filter(RiskSnapshot.student_id.in_(student_ids))
                .filter(RiskSnapshot.timestamp < run.run_at)
                .order_by(RiskSnapshot.timestamp.desc())
                .all()
            )
            prev_by_student = {s.student_id: s.risk_score for s in prev_snapshots}

            for snap in current_snapshots:
                prev_score = prev_by_student.get(snap.student_id, snap.risk_score)
                delta = abs(snap.risk_score - prev_score)
                if delta > 10:
                    significant_risk_changes.append({
                        "org_id": snap.org_defined_id,
                        "name": f"{snap.first_name} {snap.last_name}".strip(),
                        "previous_score": round(prev_score, 1) if prev_score else None,
                        "current_score": round(snap.risk_score, 1),
                        "delta": round(delta, 1),
                    })

    return {
        "id": run.id,
        "run_at": run.run_at.isoformat() if run.run_at else None,
        "triggered_by": run.triggered_by,
        "status": run.status,
        "duration_seconds": run.duration_seconds,
        "students_created": run.students_created,
        "students_updated": run.students_updated,
        "enrollments_created": run.enrollments_created,
        "enrollments_updated": run.enrollments_updated,
        "graded_components_added": run.graded_components_added,
        "risk_scores_updated": run.risk_scores_updated,
        "files_processed": run.files_processed or [],
        "errors": run.errors or [],
        "significant_risk_changes": sorted(
            significant_risk_changes,
            key=lambda x: x["delta"],
            reverse=True,
        )[:50],  # Limit to top 50
    }


@router.get("/config/thresholds")
async def get_thresholds(
    current_user: deps.User = Depends(deps.require_role(["Admin"])),
):
    """
    Get current risk threshold configuration.
    
    Returns the active threshold values so the frontend can stay synced
    without requiring code changes when thresholds are adjusted.
    """
    return {
        "no_action": INTERVENTION_THRESHOLDS["no_action"],
        "gentle": INTERVENTION_THRESHOLDS["gentle_reminder"],
        "mentor": INTERVENTION_THRESHOLDS["mentor_outreach"],
        "urgent": INTERVENTION_THRESHOLDS["urgent"],
    }


@router.get("/evaluate-scorer")
def evaluate_scorer(
    threshold: float = Query(60.0, ge=0, le=100),
    compare_thresholds: bool = Query(False),
    current_user: deps.User = Depends(deps.require_role(["Admin"])),
    db: Session = Depends(deps.get_db),
):
    """
    Evaluate rule-based risk scorer against labeled T1 outcomes (Admin only).
    
    Returns evaluation metrics comparing risk scores to actual outcomes
    (dropped/deferred vs completed/active).
    
    Parameters:
    - threshold: Risk score threshold for "at risk" classification (default 60.0)
    - compare_thresholds: If True, evaluate at multiple thresholds (50, 60, 70, 80)
    
    The evaluation requires final_outcome fields to be populated via data ingestion.
    """
    import sys
    import os
    
    # Add project root to path for imports
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    
    from backend.ml.training.evaluate import load_labeled_data, run_evaluation
    
    df = load_labeled_data(db)
    
    if len(df) == 0:
        return {
            "error": "No labeled outcomes found",
            "message": "Run data ingestion first to populate final_outcome fields via infer_outcomes_from_exam_data()",
            "evaluated_students": 0,
        }
    
    if compare_thresholds:
        thresholds = [50.0, 60.0, 70.0, 80.0]
        results = []
        for thresh in thresholds:
            metrics = run_evaluation(df, threshold=thresh)
            results.append({
                "threshold": thresh,
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "f1_score": metrics["f1_score"],
                "specificity": metrics["specificity"],
            })
        
        return {
            "evaluated_students": len(df),
            "outcome_breakdown": metrics.get("outcome_breakdown", {}),
            "threshold_comparison": results,
            "message": "Evaluation complete. Compare thresholds to find optimal precision/recall balance.",
        }
    else:
        metrics = run_evaluation(df, threshold=threshold)
        
        return {
            "threshold": threshold,
            "evaluated_students": metrics["total_students"],
            "actual_at_risk": metrics["actual_at_risk"],
            "predicted_at_risk": metrics["predicted_at_risk"],
            "metrics": {
                "precision": metrics["precision"],
                "recall": metrics["recall"],
                "specificity": metrics["specificity"],
                "f1_score": metrics["f1_score"],
                "roc_auc": metrics.get("roc_auc"),
            },
            "confusion_matrix": metrics["confusion_matrix"],
            "outcome_breakdown": metrics["outcome_breakdown"],
            "cli_command": f"python -m backend.ml.training.evaluate --threshold {threshold}",
            "message": "Evaluation complete. Use --compare-thresholds to test multiple thresholds.",
        }
