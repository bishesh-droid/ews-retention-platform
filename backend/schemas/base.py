"""
Base schema classes with shared functionality.
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, field_validator, ConfigDict


class BaseResponse(BaseModel):
    """
    Base response model with automatic datetime serialization.

    All response models should inherit from this class to ensure
    consistent ISO 8601 datetime formatting with timezone info.
    """

    model_config = ConfigDict(from_attributes=True)

    @field_validator("*", mode="before")
    @classmethod
    def convert_datetimes(cls, v: Any) -> Any:
        """Convert datetime objects to ISO 8601 format with UTC timezone."""
        if isinstance(v, datetime):
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            return v.isoformat()
        return v
