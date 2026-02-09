"""
Student Schemas
--------------
Pydantic schemas for student data validation and serialization.
"""

from pydantic import BaseModel, ConfigDict
from typing import List, Optional


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


# Forward references
from backend.app.schemas.prediction import Prediction
from backend.app.schemas.intervention import Intervention

Student.model_rebuild()
