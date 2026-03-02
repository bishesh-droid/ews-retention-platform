"""
Models facade
-------------
Re-exports ORM and schema models for a cleaner import surface.
"""

from backend.database.models import (  # noqa: F401
    academic,
    audit,
    canonical,
    course,
    enrollment,
    event,
    feature,
    goals_and_risks,
    intervention,
    llm,
    prediction,
    student,
    user,
)

from backend import schemas  # noqa: F401

__all__ = [
    "academic",
    "audit",
    "canonical",
    "course",
    "enrollment",
    "event",
    "feature",
    "goals_and_risks",
    "intervention",
    "llm",
    "prediction",
    "student",
    "user",
    "schemas",
]

