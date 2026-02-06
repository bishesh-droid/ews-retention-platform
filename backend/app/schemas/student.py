"""
Student Schemas
--------------
Pydantic schemas for student data validation and serialization.
"""

from pydantic import BaseModel, ConfigDict
from typing import List, Optional


class StudentBase(BaseModel):
    """Base student schema with all academic metrics."""
    id: str
    absrate1: Optional[float] = None
    absrate2: Optional[float] = None
    absrate3: Optional[float] = None
    absrate4: Optional[float] = None
    absrate5: Optional[float] = None
    absrate6: Optional[float] = None
    absrate7: Optional[float] = None
    nsusp1: Optional[float] = None
    nsusp2: Optional[float] = None
    nsusp3: Optional[float] = None
    nsusp4: Optional[float] = None
    nsusp5: Optional[float] = None
    nsusp6: Optional[float] = None
    nsusp7: Optional[float] = None
    mobility1: Optional[float] = None
    mobility2: Optional[float] = None
    mobility3: Optional[float] = None
    mobility4: Optional[float] = None
    mobility5: Optional[float] = None
    mobility6: Optional[float] = None
    mobility7: Optional[float] = None
    q1mpa1: Optional[float] = None
    q2mpa1: Optional[float] = None
    q3mpa1: Optional[float] = None
    q4mpa1: Optional[float] = None
    q1mpa2: Optional[float] = None
    q2mpa2: Optional[float] = None
    q3mpa2: Optional[float] = None
    q4mpa2: Optional[float] = None
    q1mpa3: Optional[float] = None
    q2mpa3: Optional[float] = None
    q3mpa3: Optional[float] = None
    q4mpa3: Optional[float] = None
    q1mpa4: Optional[float] = None
    q2mpa4: Optional[float] = None
    q3mpa4: Optional[float] = None
    q4mpa4: Optional[float] = None
    q1mpa5: Optional[float] = None
    q2mpa5: Optional[float] = None
    q3mpa5: Optional[float] = None
    q4mpa5: Optional[float] = None
    q1mpa6: Optional[float] = None
    q2mpa6: Optional[float] = None
    q3mpa6: Optional[float] = None
    q4mpa6: Optional[float] = None
    q1mpa7: Optional[float] = None
    q2mpa7: Optional[float] = None
    q3mpa7: Optional[float] = None
    q4mpa7: Optional[float] = None
    nograd: Optional[int] = None


class StudentCreate(StudentBase):
    """Schema for creating a new student."""
    pass


class Student(StudentBase):
    """Full student schema with relationships."""
    predictions: List['Prediction'] = []
    interventions: List['Intervention'] = []
    
    model_config = ConfigDict(from_attributes=True)


# Forward references will be resolved after importing prediction and intervention schemas
from backend.app.schemas.prediction import Prediction
from backend.app.schemas.intervention import Intervention

Student.model_rebuild()
