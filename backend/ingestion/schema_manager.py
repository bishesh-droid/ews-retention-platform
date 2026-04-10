"""
Schema Management
Type inference, schema locking, and validation
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np


class ColumnType(Enum):
    """Supported column types"""
    EMAIL = "EMAIL"
    PERCENTAGE = "PERCENTAGE"
    DATE = "DATE"
    DATETIME = "DATETIME"
    NUMERIC = "NUMERIC"
    INTEGER = "INTEGER"
    BOOLEAN = "BOOLEAN"
    CATEGORICAL = "CATEGORICAL"
    STRING = "STRING"


@dataclass
class ColumnConstraints:
    """Constraints for a column"""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    allowed_values: Optional[List[str]] = None
    date_format: Optional[str] = None

    def to_dict(self) -> Dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ColumnDefinition:
    """Schema definition for a single column"""
    index: int
    name: str
    original_name: str
    type: ColumnType
    nullable: bool
    constraints: ColumnConstraints

    def to_dict(self) -> Dict:
        return {
            'index': self.index,
            'name': self.name,
            'original_name': self.original_name,
            'type': self.type.value,
            'nullable': self.nullable,
            'constraints': self.constraints.to_dict()
        }


@dataclass
class DataSchema:
    """Complete schema for a data file"""
    source_file: str
    sheet_name: Optional[str]
    schema_version: str
    inferred_at: str
    total_columns: int
    total_rows_sampled: int
    columns: List[ColumnDefinition]

    def to_dict(self) -> Dict:
        return {
            'source_file': self.source_file,
            'sheet_name': self.sheet_name,
            'schema_version': self.schema_version,
            'inferred_at': self.inferred_at,
            'total_columns': self.total_columns,
            'total_rows_sampled': self.total_rows_sampled,
            'columns': [col.to_dict() for col in self.columns]
        }

    def save(self, schema_dir: str = "data/schemas"):
        """Save schema to JSON file"""
        Path(schema_dir).mkdir(parents=True, exist_ok=True)

        filename = Path(self.source_file).stem
        schema_path = Path(schema_dir) / f"{filename}_schema.json"

        with open(schema_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

        return schema_path

    @classmethod
    def load(cls, source_file: str, schema_dir: str = "data/schemas") -> Optional['DataSchema']:
        """Load schema from JSON file"""
        filename = Path(source_file).stem
        schema_path = Path(schema_dir) / f"{filename}_schema.json"

        if not schema_path.exists():
            return None

        with open(schema_path, 'r') as f:
            data = json.load(f)

        columns = []
        for col_data in data['columns']:
            col_type = ColumnType(col_data['type'])
            constraints = ColumnConstraints(**col_data.get('constraints', {}))
            columns.append(ColumnDefinition(
                index=col_data['index'],
                name=col_data['name'],
                original_name=col_data['original_name'],
                type=col_type,
                nullable=col_data['nullable'],
                constraints=constraints
            ))

        return cls(
            source_file=data['source_file'],
            sheet_name=data.get('sheet_name'),
            schema_version=data['schema_version'],
            inferred_at=data['inferred_at'],
            total_columns=data['total_columns'],
            total_rows_sampled=data['total_rows_sampled'],
            columns=columns
        )


class SchemaInferenceEngine:
    """Infer schema from sample data"""

    def __init__(self, sample_size: int = 1000):
        self.sample_size = sample_size
        self.email_pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

    def infer_schema(self, df: pd.DataFrame, source_file: str, sheet_name: Optional[str] = None) -> DataSchema:
        """
        Infer schema from DataFrame

        Args:
            df: DataFrame with data
            source_file: Source filename
            sheet_name: Sheet name (for Excel)

        Returns:
            DataSchema
        """
        # Sample data
        sample_size = min(self.sample_size, len(df))
        sample_df = df.head(sample_size)

        columns = []

        for idx, col_name in enumerate(df.columns):
            col_data = sample_df[col_name]

            # Infer type
            col_type, constraints = self._infer_column_type(col_data, col_name)

            # Check nullability
            nullable = col_data.isnull().any()

            columns.append(ColumnDefinition(
                index=idx,
                name=str(col_name),
                original_name=str(col_name),
                type=col_type,
                nullable=nullable,
                constraints=constraints
            ))

        return DataSchema(
            source_file=source_file,
            sheet_name=sheet_name,
            schema_version="1.0",
            inferred_at=datetime.now().isoformat(),
            total_columns=len(columns),
            total_rows_sampled=sample_size,
            columns=columns
        )

    def _infer_column_type(self, series: pd.Series, col_name: str) -> tuple[ColumnType, ColumnConstraints]:
        """Infer type and constraints for a column"""

        # Remove nulls for type detection
        non_null = series.dropna()

        if len(non_null) == 0:
            return ColumnType.STRING, ColumnConstraints()

        # Check for email pattern
        if self._is_email_column(non_null):
            return ColumnType.EMAIL, ColumnConstraints(pattern=self.email_pattern)

        # Check for percentage
        if self._is_percentage_column(non_null, col_name):
            return ColumnType.PERCENTAGE, ColumnConstraints(min_value=0.0, max_value=100.0)

        # Check for boolean
        if self._is_boolean_column(non_null):
            return ColumnType.BOOLEAN, ColumnConstraints(allowed_values=['true', 'false'])

        # Check for numeric BEFORE date to avoid numbers being parsed as timestamps
        if pd.api.types.is_numeric_dtype(non_null):
            # Integer vs float
            if pd.api.types.is_integer_dtype(non_null) or all(non_null == non_null.astype(int)):
                col_type = ColumnType.INTEGER
            else:
                col_type = ColumnType.NUMERIC

            min_val = float(non_null.min())
            max_val = float(non_null.max())

            # Add 10% buffer
            buffer = (max_val - min_val) * 0.1
            return col_type, ColumnConstraints(
                min_value=min_val - buffer,
                max_value=max_val + buffer
            )

        # Check for date (string columns that might contain dates)
        date_result = self._is_date_column(non_null)
        if date_result:
            date_format, has_time = date_result
            col_type = ColumnType.DATETIME if has_time else ColumnType.DATE
            return col_type, ColumnConstraints(date_format=date_format)

        # Check for categorical (limited unique values)
        unique_ratio = non_null.nunique() / len(non_null)
        if unique_ratio < 0.1 and non_null.nunique() < 50:
            allowed_values = [str(v) for v in non_null.unique()[:50]]
            return ColumnType.CATEGORICAL, ColumnConstraints(allowed_values=allowed_values)

        # Default to string
        return ColumnType.STRING, ColumnConstraints()

    def _is_email_column(self, series: pd.Series) -> bool:
        """Check if column contains emails"""
        if not pd.api.types.is_string_dtype(series):
            return False

        # Sample check
        sample = series.head(min(100, len(series)))
        matches = sample.astype(str).str.match(self.email_pattern)
        return matches.sum() / len(sample) > 0.8

    def _is_percentage_column(self, series: pd.Series, col_name: str) -> bool:
        """Check if column contains percentages"""

        # Check column name
        if any(kw in col_name.lower() for kw in ['percent', '%', 'pct', 'rate']):
            return True

        # Check for % symbols in string values
        if pd.api.types.is_string_dtype(series):
            sample = series.head(min(100, len(series))).astype(str)
            has_percent = sample.str.contains('%').sum()
            if has_percent / len(sample) > 0.5:
                return True

        # Check numeric range (0-1 or 0-100)
        if pd.api.types.is_numeric_dtype(series):
            min_val = series.min()
            max_val = series.max()

            # 0-1 range or 0-100 range
            if (0 <= min_val <= 1 and 0 <= max_val <= 1) or (0 <= min_val <= 100 and 0 <= max_val <= 100):
                return True

        return False

    def _is_date_column(self, series: pd.Series) -> Optional[tuple[str, bool]]:
        """Check if column contains dates"""

        # Try pandas datetime parsing
        try:
            sample = series.head(min(100, len(series)))
            parsed = pd.to_datetime(sample, errors='coerce')
            valid_ratio = parsed.notna().sum() / len(sample)

            if valid_ratio > 0.8:
                # Check if has time component
                has_time = any(t.time() != datetime.min.time() for t in parsed.dropna())
                date_format = "ISO8601"
                return (date_format, has_time)
        except Exception:
            pass

        return None

    def _is_boolean_column(self, series: pd.Series) -> bool:
        """Check if column contains booleans"""
        if pd.api.types.is_bool_dtype(series):
            return True

        unique_values = set(str(v).lower() for v in series.unique())
        bool_values = {'true', 'false', 't', 'f', 'yes', 'no', 'y', 'n', '1', '0'}

        return unique_values.issubset(bool_values)


class SchemaValidator:
    """Validate data against a locked schema"""

    def __init__(self, schema: DataSchema):
        self.schema = schema

    def validate_row(self, row: pd.Series) -> tuple[bool, List[str]]:
        """
        Validate a row against schema

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # Column count check
        if len(row) != self.schema.total_columns:
            errors.append(f"Column count mismatch: got {len(row)}, expected {self.schema.total_columns}")
            return (False, errors)

        # Validate each cell
        for col_def in self.schema.columns:
            value = row.iloc[col_def.index]

            cell_valid, cell_errors = self.validate_cell(value, col_def)
            if not cell_valid:
                errors.extend(cell_errors)

        return (len(errors) == 0, errors)

    def validate_cell(self, value: Any, col_def: ColumnDefinition) -> tuple[bool, List[str]]:
        """Validate a single cell"""
        errors = []

        # NULL check
        if pd.isna(value):
            if not col_def.nullable:
                errors.append(f"NULL value in required field '{col_def.name}'")
            return (len(errors) == 0, errors)

        # Type-specific validation
        if col_def.type == ColumnType.EMAIL:
            if col_def.constraints.pattern is not None and not re.match(col_def.constraints.pattern, str(value)):
                errors.append(f"Invalid email format: '{value}'")

        elif col_def.type == ColumnType.PERCENTAGE:
            try:
                num_val = float(value)
                min_v = col_def.constraints.min_value
                max_v = col_def.constraints.max_value
                if min_v is not None and max_v is not None and (num_val < min_v or num_val > max_v):
                    errors.append(
                        f"{col_def.name} out of bounds: {num_val} (allowed: {min_v}-{max_v})")
            except (ValueError, TypeError):
                errors.append(f"Non-numeric value in {col_def.name}: '{value}'")

        elif col_def.type in [ColumnType.NUMERIC, ColumnType.INTEGER]:
            try:
                num_val = float(value)

                # Check for NaN/Inf
                if not np.isfinite(num_val):
                    errors.append(f"Invalid numeric value: {value}")

                # Range check
                if col_def.constraints.min_value is not None and num_val < col_def.constraints.min_value:
                    errors.append(f"{col_def.name} below minimum: {num_val} < {col_def.constraints.min_value}")

                if col_def.constraints.max_value is not None and num_val > col_def.constraints.max_value:
                    errors.append(f"{col_def.name} above maximum: {num_val} > {col_def.constraints.max_value}")

            except (ValueError, TypeError):
                errors.append(f"Non-numeric value in {col_def.name}: '{value}'")

        elif col_def.type == ColumnType.CATEGORICAL:
            if col_def.constraints.allowed_values is not None and str(value) not in col_def.constraints.allowed_values:
                errors.append(f"Invalid category in {col_def.name}: '{value}' (allowed: {col_def.constraints.allowed_values})")

        return (len(errors) == 0, errors)

    def detect_schema_drift(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """Detect schema changes in new data"""
        drift: Dict[str, List[str]] = {
            'new_columns': [],
            'missing_columns': [],
            'type_changes': []
        }

        current_columns = set(df.columns)
        schema_columns = set(col.name for col in self.schema.columns)

        drift['new_columns'] = list(current_columns - schema_columns)
        drift['missing_columns'] = list(schema_columns - current_columns)

        return drift
