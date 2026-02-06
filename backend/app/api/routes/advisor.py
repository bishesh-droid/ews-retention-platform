"""
AI Academic Advisor API Routes

Endpoints for AI-powered academic advising features:
- Study plan generation
- Faculty summaries
- Motivational messages
- Advisor context retrieval
"""

from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from backend.app.services.ai.study_plan_generator import generate_study_plan
from backend.app.services.ai.faculty_summary import generate_faculty_summary
from backend.app.services.ai.advisor_context import build_advisor_context
from backend.app.database.session import get_db
from backend.app.database.queries import get_student_by_id, get_prediction_by_student_id

router = APIRouter(prefix="/advisor", tags=["AI Academic Advisor"])


# Request/Response Models
class StudyPlanRequest(BaseModel):
    preferences: Optional[Dict[str, Any]] = None


class StudyPlanResponse(BaseModel):
    success: bool
    student_id: Optional[str]
    generated_at: str
    plan_duration_weeks: int
    plan: Dict[str, Any]
    context_summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class FacultySummaryResponse(BaseModel):
    success: bool
    student_id: Optional[str]
    generated_at: str
    summary: Dict[str, Any]
    data_sources: List[str]
    error: Optional[str] = None


class AdvisorContextResponse(BaseModel):
    student_id: Optional[str]
    context_generated_at: str
    student_profile: Dict[str, Any]
    risk_assessment: Dict[str, Any]
    academic_history: Dict[str, Any]
    intervention_history: Dict[str, Any]
    advisor_hints: List[str]


class MotivationalMessageResponse(BaseModel):
    success: bool
    student_id: str
    message: str
    tone: str
    generated_at: str


# Helper function to validate user role
def validate_role(user_role: str, allowed_roles: List[str]) -> bool:
    """Validate that user has required role."""
    return user_role.lower() in [r.lower() for r in allowed_roles]


@router.post(
    "/study-plan/{student_id}",
    response_model=StudyPlanResponse,
    summary="Generate personalized study plan",
    description="""
    Generate a personalized 4-week study plan for a student.

    The plan includes:
    - Weekly focus areas and goals
    - Daily schedule recommendations
    - Specific actionable steps
    - Progress milestones

    Accessible by: student (for self), faculty, admin
    """
)
async def get_study_plan(
    student_id: str,
    request: Optional[StudyPlanRequest] = None,
    x_user_role: str = Header(default="student", alias="X-User-Role")
):
    """Generate a personalized study plan for a student."""
    # Validate role
    if not validate_role(x_user_role, ['student', 'faculty', 'admin']):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized role. Only student, faculty, or admin can access study plans."
        )

    # Get student data
    db = next(get_db())
    try:
        student = get_student_by_id(db, student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

        # Convert to dict
        student_data = {c.name: getattr(student, c.name) for c in student.__table__.columns}

        # Get prediction data
        prediction = get_prediction_by_student_id(db, student_id)
        prediction_data = None
        if prediction:
            prediction_data = {
                'risk_score': prediction.risk_score,
                'engagement_score': prediction.engagement_score,
                'signal_breakdown': {
                    'academic_signal_score': prediction.academic_signal_score or 0.5,
                    'engagement_signal_score': prediction.engagement_signal_score or 0.5,
                    'consistency_signal_score': prediction.consistency_signal_score or 0.5,
                    'intent_signal_score': prediction.intent_signal_score or 0.5,
                    'responsiveness_signal_score': prediction.responsiveness_signal_score or 0.5
                }
            }

        # Generate study plan
        preferences = request.preferences if request else None
        result = await generate_study_plan(
            student_data=student_data,
            prediction_data=prediction_data,
            preferences=preferences
        )

        return StudyPlanResponse(**result)

    finally:
        db.close()


@router.post(
    "/faculty-summary/{student_id}",
    response_model=FacultySummaryResponse,
    summary="Generate faculty-appropriate student summary",
    description="""
    Generate a professional summary for faculty use.

    This summary:
    - Does NOT expose raw risk scores or dropout predictions
    - Focuses on observable patterns and behaviors
    - Provides conversation starters for meetings
    - Suggests appropriate support resources

    Accessible by: faculty, admin only
    """
)
async def get_faculty_summary(
    student_id: str,
    include_talking_points: bool = True,
    x_user_role: str = Header(default="faculty", alias="X-User-Role")
):
    """Generate a faculty-appropriate student summary."""
    # Validate role - faculty/admin only
    if not validate_role(x_user_role, ['faculty', 'admin']):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized role. Only faculty or admin can access faculty summaries."
        )

    # Get student data
    db = next(get_db())
    try:
        student = get_student_by_id(db, student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

        student_data = {c.name: getattr(student, c.name) for c in student.__table__.columns}

        # Get prediction data
        prediction = get_prediction_by_student_id(db, student_id)
        prediction_data = None
        if prediction:
            prediction_data = {
                'risk_score': prediction.risk_score,
                'signal_breakdown': {
                    'academic_signal_score': prediction.academic_signal_score or 0.5,
                    'engagement_signal_score': prediction.engagement_signal_score or 0.5,
                    'consistency_signal_score': prediction.consistency_signal_score or 0.5,
                    'intent_signal_score': prediction.intent_signal_score or 0.5,
                    'responsiveness_signal_score': prediction.responsiveness_signal_score or 0.5
                }
            }

        # Generate summary
        result = await generate_faculty_summary(
            student_data=student_data,
            prediction_data=prediction_data,
            include_talking_points=include_talking_points
        )

        return FacultySummaryResponse(**result)

    finally:
        db.close()


@router.get(
    "/context/{student_id}",
    response_model=AdvisorContextResponse,
    summary="Get advisor context for a student",
    description="""
    Retrieve the structured context used by the AI advisor.

    This endpoint is useful for:
    - Debugging advisor behavior
    - Understanding what data the advisor has access to
    - Building custom advisor integrations

    Note: Sensitive data (raw risk scores) excluded unless admin.

    Accessible by: faculty, admin
    """
)
async def get_advisor_context(
    student_id: str,
    x_user_role: str = Header(default="faculty", alias="X-User-Role")
):
    """Get the advisor context for a student."""
    if not validate_role(x_user_role, ['faculty', 'admin']):
        raise HTTPException(
            status_code=403,
            detail="Unauthorized role. Only faculty or admin can access advisor context."
        )

    db = next(get_db())
    try:
        student = get_student_by_id(db, student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

        student_data = {c.name: getattr(student, c.name) for c in student.__table__.columns}

        prediction = get_prediction_by_student_id(db, student_id)
        prediction_data = None
        if prediction:
            prediction_data = {
                'risk_score': prediction.risk_score,
                'signal_breakdown': {
                    'academic_signal_score': prediction.academic_signal_score or 0.5,
                    'engagement_signal_score': prediction.engagement_signal_score or 0.5,
                    'consistency_signal_score': prediction.consistency_signal_score or 0.5,
                    'intent_signal_score': prediction.intent_signal_score or 0.5,
                    'responsiveness_signal_score': prediction.responsiveness_signal_score or 0.5
                }
            }

        # Build context (include sensitive for admin)
        include_sensitive = x_user_role.lower() == 'admin'
        context = build_advisor_context(
            student_data=student_data,
            prediction_data=prediction_data,
            include_sensitive=include_sensitive
        )

        return AdvisorContextResponse(**context)

    finally:
        db.close()


@router.post(
    "/motivational-message/{student_id}",
    response_model=MotivationalMessageResponse,
    summary="Generate motivational message for student",
    description="""
    Generate a personalized, encouraging message for a student.

    The message is tailored based on:
    - Current academic standing
    - Recent trends (improvement or challenges)
    - Previous interaction history

    Accessible by: student (for self), faculty, admin, automated systems
    """
)
async def get_motivational_message(
    student_id: str,
    tone: str = "encouraging",  # encouraging, supportive, celebratory
    x_user_role: str = Header(default="student", alias="X-User-Role")
):
    """Generate a motivational message for a student."""
    db = next(get_db())
    try:
        student = get_student_by_id(db, student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Student {student_id} not found")

        student_data = {c.name: getattr(student, c.name) for c in student.__table__.columns}

        prediction = get_prediction_by_student_id(db, student_id)

        # Generate contextual message
        message = _generate_motivational_message(student_data, prediction, tone)

        return MotivationalMessageResponse(
            success=True,
            student_id=student_id,
            message=message,
            tone=tone,
            generated_at=__import__('datetime').datetime.now().isoformat()
        )

    finally:
        db.close()


def _generate_motivational_message(
    student_data: Dict,
    prediction,
    tone: str
) -> str:
    """Generate a motivational message based on student context."""
    gpa = student_data.get('q4mpa7', 3.0)
    risk_score = prediction.risk_score if prediction else 0.5

    if tone == "celebratory" and gpa > 3.5:
        return (
            "Congratulations on your excellent academic performance! "
            "Your hard work and dedication are clearly paying off. "
            "Keep up the fantastic work!"
        )
    elif risk_score < 0.3:
        return (
            "You're doing great! Your consistent effort is showing in your results. "
            "Remember to maintain your study habits and don't hesitate to reach out "
            "if you ever need support."
        )
    elif risk_score < 0.6:
        return (
            "Every step forward counts, no matter how small. "
            "You have the potential to succeed, and we're here to support you. "
            "Consider reaching out to your advisor to discuss strategies for improvement."
        )
    else:
        return (
            "We believe in your ability to overcome challenges. "
            "You're not alone in this journey - your success matters to us. "
            "Let's work together to identify the support you need to thrive."
        )
