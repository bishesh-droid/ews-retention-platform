"""
Student Schemas
--------------
Pydantic schemas for student data validation and serialization.
"""

from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, List, Any, Optional


class StudentBase(BaseModel):
    """Base student schema with engagement-based fields."""
    id: str
    org_defined_id: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    old_new_student: Optional[str] = None
    is_active: Optional[bool] = True
    parent_department_name: Optional[str] = None
    parent_department_code: Optional[str] = None


class StudentCreate(StudentBase):
    """Schema for creating a new student."""
    pass


class Student(StudentBase):
    """Full student schema with relationships."""
    predictions: List['Prediction'] = []
    interventions: List['Intervention'] = []

    model_config = ConfigDict(from_attributes=True)


class StudentMetricsResponse(BaseModel):
    """
    Student metrics response schema.

    BREAKING_CHANGE v1.1: "attendance_score" renamed to "exam_attendance_score"
    Frontend must update StudentProfile component to use new field name.
    """
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    org_defined_id: Optional[str] = None
    department: Optional[str] = None
    old_new_student: Optional[str] = None
    is_active: Optional[bool] = True
    risk_score: Optional[float] = None
    risk_category: Optional[str] = None
    retention_likelihood: Optional[str] = None
    dominant_risk_factor: Optional[str] = None
    risk_breakdown: Optional[Dict[str, Any]] = None
    content_completion_score: Optional[float] = None
    w1w2_completion_score: Optional[float] = None
    quiz_engagement_score: Optional[float] = None
    discussion_engagement_score: Optional[float] = None
    login_consistency_score: Optional[float] = None
    time_investment_score: Optional[float] = None
    assignment_score: Optional[float] = None
    graded_quiz_score: Optional[float] = None
    graded_assignment_score: Optional[float] = None
    exam_score: Optional[float] = None
    exam_attendance_rate: Optional[float] = None
    exam_attendance_score: Optional[float] = Field(
        None,
        description="Percentage of written exams attended (not LMS session attendance). "
                    "Null if no exams have been held this trimester."
    )
    zero_progress_ratio: Optional[float] = None
    progress_category: Optional[str] = None
    trend: Optional[str] = None
    total_courses: int = 0
    per_course_breakdown: List[Dict[str, Any]] = []
    academic_score: Optional[float] = None
    behavioral_score: Optional[float] = None
    stability_score: Optional[float] = None
    engagement_pattern: str = "on_track"
    engagement_pattern_label: str = "On track"
    is_ghost: bool = False
    ghost_type: Optional[str] = None
    requires_activation_outreach: bool = False
    score_basis: str = "rule_based_formula"


# Forward references
from backend.schemas.prediction import Prediction
from backend.schemas.intervention import Intervention

Student.model_rebuild()
