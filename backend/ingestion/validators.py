"""
Input validation classes for ETL pipeline
"""

import re
from typing import Tuple, List


class StudentValidator:
    """Validate student records"""

    @staticmethod
    def validate_email(email: str) -> bool:
        """Ensure email follows expected format"""
        if not email:
            return False
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        return bool(re.match(pattern, str(email).lower()))

    @staticmethod
    def validate_student_record(record: dict) -> Tuple[bool, List[str]]:
        """Validate complete student record"""
        errors = []

        # Required fields
        if not record.get("student_id"):
            errors.append("Missing student_id")
        elif not StudentValidator.validate_email(record["student_id"]):
            errors.append(f"Invalid email format: {record['student_id']}")

        # Program validation
        if record.get("program") and record.get("program") not in ["BS", "MSc", None]:
            errors.append(f"Invalid program: {record.get('program')}")

        return (len(errors) == 0, errors)


class MetricValidator:
    """Validate metric values"""

    @staticmethod
    def validate_percentage(value, field_name: str) -> Tuple[bool, List[str]]:
        """Ensure percentage is 0-100"""
        errors = []

        if value is None:
            return (True, [])  # NULL is allowed

        try:
            val = float(value)
            if val < 0 or val > 100:
                errors.append(f"{field_name} out of bounds (0-100): {val}")
        except (ValueError, TypeError):
            errors.append(f"{field_name} not numeric: {value}")

        return (len(errors) == 0, errors)

    @staticmethod
    def validate_count(value, field_name: str, min_val=0) -> Tuple[bool, List[str]]:
        """Ensure count is non-negative integer"""
        errors = []

        if value is None:
            return (True, [])  # NULL is allowed

        try:
            val = int(value)
            if val < min_val:
                errors.append(f"{field_name} below minimum ({min_val}): {val}")
        except (ValueError, TypeError):
            errors.append(f"{field_name} not integer: {value}")

        return (len(errors) == 0, errors)

    @staticmethod
    def validate_score(value, max_score, field_name: str) -> Tuple[bool, List[str]]:
        """Validate score is within 0-max_score range"""
        errors = []

        if value is None:
            return (True, [])

        try:
            val = float(value)
            if val < 0 or val > max_score:
                errors.append(f"{field_name} out of bounds (0-{max_score}): {val}")
        except (ValueError, TypeError):
            errors.append(f"{field_name} not numeric: {value}")

        return (len(errors) == 0, errors)
