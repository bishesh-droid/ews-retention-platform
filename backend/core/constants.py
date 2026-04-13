"""
Core Constants for EWS Retention Platform

This module centralizes all string constants to prevent typos and enable
type-safe role checking across the codebase.
"""


class Role:
    """
    Role constants for authorization.

    All role checks should use these constants instead of hardcoded strings
to prevent typos and enable IDE autocompletion.
    """
    STUDENT = "student"
    FACULTY = "faculty"
    ADMIN = "admin"
    RETENTION_TEAM = "retention team"

    @classmethod
    def all(cls) -> set:
        """Return set of all valid roles."""
        return {cls.STUDENT, cls.FACULTY, cls.ADMIN, cls.RETENTION_TEAM}

    @classmethod
    def staff_roles(cls) -> list:
        """Return list of staff roles (non-student)."""
        return [cls.FACULTY, cls.ADMIN, cls.RETENTION_TEAM]
