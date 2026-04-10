"""
Row-Level Validation Guards
Extended validation for row integrity, numeric bounds, and timestamps
"""
from datetime import datetime, timedelta
from typing import List, Tuple
import pandas as pd
import numpy as np


class RowValidator:
    """Validate complete row integrity"""

    @staticmethod
    def validate_row_integrity(row: pd.Series, schema) -> Tuple[bool, List[str]]:
        """
        Comprehensive row validation

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # Column count consistency
        expected_cols = schema.total_columns
        actual_cols = len(row)

        if actual_cols != expected_cols:
            errors.append(f"Column count mismatch: got {actual_cols}, expected {expected_cols}")
            return (False, errors)

        return (True, [])

    @staticmethod
    def check_column_count(row: pd.Series, expected: int) -> bool:
        """Verify column count matches expectation"""
        return len(row) == expected

    @staticmethod
    def check_required_fields(row: pd.Series, required_fields: List[str]) -> List[str]:
        """
        Check that required fields are present and not null

        Returns:
            List of missing field names
        """
        missing = []

        for field in required_fields:
            if field not in row.index or pd.isna(row[field]):
                missing.append(field)

        return missing

    @staticmethod
    def detect_excel_errors(row: pd.Series) -> List[str]:
        """
        Detect Excel error values (#DIV/0!, #VALUE!, etc.)

        Returns:
            List of columns containing Excel errors
        """
        excel_errors = ['#DIV/0!', '#VALUE!', '#REF!', '#NAME?', '#NUM!', '#N/A', '#NULL!']

        problematic_cols = []

        for col_name, value in row.items():
            if isinstance(value, str) and value in excel_errors:
                problematic_cols.append(f"{col_name}={value}")

        return problematic_cols

    @staticmethod
    def normalize_special_values(row: pd.Series) -> pd.Series:
        """
        Normalize special string values to proper nulls

        Converts: 'N/A', 'null', 'NULL', 'None', '', '  ' → None
        """
        special_nulls = ['N/A', 'n/a', 'NA', '#N/A', 'null', 'NULL', 'None', 'none', '-']

        normalized = row.copy()

        for idx, value in normalized.items():
            if isinstance(value, str):
                # Trim whitespace
                trimmed = value.strip()

                # Check if whitespace-only
                if trimmed == '':
                    normalized[idx] = None
                # Check if special null value
                elif trimmed in special_nulls:
                    normalized[idx] = None

        return normalized


class NumericGuard:
    """Numeric value validation and safety checks"""

    @staticmethod
    def check_bounds(value: float, min_val: float, max_val: float) -> bool:
        """Check if value is within bounds"""
        return min_val <= value <= max_val

    @staticmethod
    def detect_infinity_nan(value) -> bool:
        """
        Detect NaN or Infinity

        Returns:
            True if value is NaN or Inf
        """
        try:
            return not np.isfinite(float(value))
        except (ValueError, TypeError):
            return False

    @staticmethod
    def check_negative_where_invalid(value: float, column_name: str) -> bool:
        """
        Check for negative values in columns where they're invalid

        Args:
            value: Numeric value
            column_name: Column name

        Returns:
            True if value is negative and shouldn't be
        """
        # Columns that should never be negative
        non_negative_patterns = [
            'attendance', 'percentage', 'score', 'count', 'login',
            'duration', 'time', 'session', 'view', 'post', 'read'
        ]

        if value < 0:
            return any(pattern in column_name.lower() for pattern in non_negative_patterns)

        return False

    @staticmethod
    def validate_percentage_range(value: float, column_name: str) -> Tuple[bool, str]:
        """
        Validate percentage is 0-100

        Returns:
            (is_valid, error_message)
        """
        if 'percent' in column_name.lower() or '%' in column_name:
            if value < 0:
                return (False, f"Percentage cannot be negative: {value}")
            if value > 100:
                return (False, f"Percentage cannot exceed 100: {value}")

        return (True, "")

    @staticmethod
    def detect_unit_mismatch(series: pd.Series, expected_max: float, tolerance: float = 10.0) -> bool:
        """
        Detect if values are in wrong units (e.g., seconds instead of minutes)

        Args:
            series: Numeric series
            expected_max: Expected maximum value
            tolerance: Tolerance multiplier

        Returns:
            True if likely unit mismatch
        """
        max_val = series.max()

        # If max is way higher than expected, likely wrong units
        if max_val > expected_max * tolerance:
            return True

        return False


class TimestampGuard:
    """Timestamp validation and sanity checks"""

    @staticmethod
    def check_future_dates(date: datetime, grace_period_days: int = 7) -> bool:
        """
        Check if date is unreasonably in the future

        Args:
            date: Date to check
            grace_period_days: Days into future that's acceptable

        Returns:
            True if date is too far in future
        """
        max_future = datetime.now() + timedelta(days=grace_period_days)
        return date > max_future

    @staticmethod
    def check_ancient_dates(date: datetime, earliest: datetime = datetime(2000, 1, 1)) -> bool:
        """
        Check if date is unreasonably old

        Returns:
            True if date is before earliest allowed date
        """
        return date < earliest

    @staticmethod
    def check_excel_epoch_bug(date: datetime) -> bool:
        """
        Detect Excel epoch bug (dates at 1900-01-01 or 1904-01-01)

        Returns:
            True if date matches Excel epoch
        """
        excel_epochs = [
            datetime(1900, 1, 1),
            datetime(1904, 1, 1),
            datetime(1899, 12, 31)  # Sometimes off by one
        ]

        return date in excel_epochs

    @staticmethod
    def validate_date_range(date: datetime, min_date: datetime, max_date: datetime) -> Tuple[bool, str]:
        """
        Validate date is within expected range

        Returns:
            (is_valid, error_message)
        """
        if date < min_date:
            return (False, f"Date {date} before minimum {min_date}")

        if date > max_date:
            return (False, f"Date {date} after maximum {max_date}")

        return (True, "")

    @staticmethod
    def check_chronological_order(dates: List[datetime], strict: bool = True) -> Tuple[bool, List[int]]:
        """
        Check if dates are in chronological order

        Args:
            dates: List of dates
            strict: If True, require strictly increasing; if False, allow equal

        Returns:
            (is_valid, indices_of_violations)
        """
        violations = []

        for i in range(len(dates) - 1):
            if strict:
                if dates[i] >= dates[i + 1]:
                    violations.append(i)
            else:
                if dates[i] > dates[i + 1]:
                    violations.append(i)

        return (len(violations) == 0, violations)


class RequiredFieldValidator:
    """Validate presence of critical fields"""

    # Define required fields per data type
    REQUIRED_FIELDS = {
        'academic': ['student_id', 'course_id'],
        'engagement': ['student_id', 'metric_date'],
        'attendance': ['student_id', 'session_date'],
        'roster': ['student_id', 'student_name']
    }

    @staticmethod
    def validate_required_fields(row: pd.Series, data_type: str) -> Tuple[bool, List[str]]:
        """
        Validate that required fields are present

        Args:
            row: Data row
            data_type: Type of data ('academic', 'engagement', etc.)

        Returns:
            (is_valid, missing_fields)
        """
        required = RequiredFieldValidator.REQUIRED_FIELDS.get(data_type, [])
        missing = []

        for field in required:
            if field not in row.index or pd.isna(row[field]):
                missing.append(field)

        return (len(missing) == 0, missing)

    @staticmethod
    def validate_student_identifier(value: str) -> Tuple[bool, str]:
        """
        Validate student identifier (email)

        Returns:
            (is_valid, error_message)
        """
        if pd.isna(value) or not value:
            return (False, "Student identifier is null or empty")

        # Check for email format
        if '@' not in str(value):
            return (False, f"Student identifier missing @ symbol: '{value}'")

        # Check for domain
        parts = str(value).split('@')
        if len(parts) != 2 or not parts[1]:
            return (False, f"Invalid email format: '{value}'")

        return (True, "")
