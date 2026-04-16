"""
Recommendations API Endpoints
Generates rule-based recommendations for students.

Security: IDOR protection via ResourceOwnershipChecker ensures:
- Students can only access their own recommendations
- Faculty/Admin/Retention team can access any student's recommendations
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import get_db, require_resource_ownership, User
from backend.services.student_service import StudentService
from backend.utils.api import success_response

logger = logging.getLogger(__name__)

router = APIRouter(
    responses={404: {"description": "Not found"}},
)


@router.get("/{student_id}")
def get_recommendations_for_student(
    student_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_resource_ownership()),
):
    """Returns a list of recommendations for a given student.

    Security: ResourceOwnershipChecker enforces:
    - role == "student": can only access own student_id (matched by email)
    - role in ["faculty", "admin", "retention team"]: can access any student
    - is_superuser == True: bypasses all checks

    Returns 403 Forbidden if a student attempts to access another student's data.
    All access attempts are logged for FERPA compliance.
    """
    # Log access attempt for audit trail (FERPA compliance)
    logger.info(
        "Recommendations access: user=%s role=%s student_id=%s",
        current_user.email, current_user.role, student_id
    )

    student = StudentService.get_student_by_id(db, student_id)
    if student is None:
        logger.warning(f"Recommendations requested for non-existent student: {student_id}")
        raise HTTPException(status_code=404, detail="Student not found")

    risk = student["risk_score"]
    recommendations = []

    # Content completion recommendations
    if student.get("content_completion_score", 0) < 30:
        recommendations.append({
            "type": "content",
            "priority": "high",
            "title": "Increase Content Engagement",
            "description": (
                "You have completed less than 30% of course content. "
                "Try to complete at least 2-3 modules per week."
            ),
        })

    # Quiz recommendations
    if student.get("graded_quiz_score", 0) < 50:
        recommendations.append({
            "type": "academic",
            "priority": "high",
            "title": "Improve Quiz Performance",
            "description": (
                "Your quiz scores are below average. "
                "Review course materials before attempting quizzes."
            ),
        })

    # Login recommendations
    if student.get("login_consistency_score", 0) < 20:
        recommendations.append({
            "type": "engagement",
            "priority": "medium",
            "title": "Log In More Frequently",
            "description": (
                "Regular platform access helps maintain learning momentum. "
                "Try logging in at least 3 times per week."
            ),
        })

    # Discussion recommendations
    if student.get("discussion_engagement_score", 0) < 10:
        recommendations.append({
            "type": "social",
            "priority": "low",
            "title": "Participate in Discussions",
            "description": "Engaging in course discussions helps deepen understanding and connects you with peers.",
        })

    # Exam attendance
    if student.get("exam_attendance_rate", 0) < 80:
        recommendations.append({
            "type": "attendance",
            "priority": "high",
            "title": "Attend All Exams",
            "description": (
                "Missing exams significantly impacts your academic standing. "
                "Ensure you attend all scheduled exams."
            ),
        })

    # If low risk, give positive feedback
    if risk < 30 and not recommendations:
        recommendations.append({
            "type": "positive",
            "priority": "low",
            "title": "Keep Up the Great Work!",
            "description": (
                "You're performing well. Continue your current study habits "
                "and consider mentoring other students."
            ),
        })

    return success_response(
        recommendations,
        message="Student recommendations",
        meta={"pagination": {"total": len(recommendations)}},
    )
