"""
Test suite for data validation components
"""
import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

from backend.ingestion.file_validator import FileValidator, ValidationStatus
from backend.ingestion.schema_manager import SchemaInferenceEngine, ColumnType
from backend.ingestion.quarantine import QuarantineManager
from backend.ingestion.row_validators import RowValidator, NumericGuard, TimestampGuard


class TestFileValidator:
    """Test file-level validation"""
    
    def test_reject_empty_file(self, tmp_path):
        """Empty files should be rejected"""
        empty_file = tmp_path / "empty.xlsx"
        empty_file.touch()
        
        validator = FileValidator()
        result = validator.validate_file(str(empty_file))
        
        assert result.status == ValidationStatus.REJECTED
        assert "0 bytes" in result.messages[0]
    
    def test_reject_invalid_extension(self, tmp_path):
        """Files with wrong extension should be rejected"""
        invalid_file = tmp_path / "data.txt"
        invalid_file.write_text("test")
        
        validator = FileValidator()
        result = validator.validate_file(str(invalid_file))
        
        assert result.status == ValidationStatus.REJECTED
        assert "Invalid extension" in result.messages[0]
    
    def test_normalize_header(self):
        """Test header normalization"""
        validator = FileValidator()
        
        headers = ["  Student Email   ", "Quiz Score (%)", "2023 Grade", "Email", "Email"]
        normalized = validator.normalize_header(headers)
        
        assert normalized[0] == "student_email"
        assert normalized[1] == "quiz_score"  # Parentheses stripped by regex
        assert normalized[2] == "col_2023_grade"
        assert normalized[3] == "email"
        assert normalized[4] == "email_1"  # Duplicate handling


class TestSchemaInference:
    """Test schema inference and validation"""
    
    def test_infer_email_column(self):
        """Should detect email columns"""
        engine = SchemaInferenceEngine()
        
        df = pd.DataFrame({
            'student_email': ['john@example.com', 'jane@example.com', 'bob@example.com']
        })
        
        schema = engine.infer_schema(df, 'test.csv')
        
        assert len(schema.columns) == 1
        assert schema.columns[0].type == ColumnType.EMAIL
        assert schema.columns[0].constraints.pattern is not None
    
    def test_infer_percentage_column(self):
        """Should detect percentage columns"""
        engine = SchemaInferenceEngine()
        
        df = pd.DataFrame({
            'attendance_percentage': [85.0, 90.5, 78.0, 95.0]
        })
        
        schema = engine.infer_schema(df, 'test.csv')
        
        assert schema.columns[0].type == ColumnType.PERCENTAGE
        assert schema.columns[0].constraints.min_value == 0.0
        assert schema.columns[0].constraints.max_value == 100.0
    
    def test_infer_numeric_constraints(self):
        """Should infer min/max for numeric columns"""
        engine = SchemaInferenceEngine()
        
        # Use large float values and neutral column name
        df = pd.DataFrame({
            'measurement': [1065.5, 1178.3, 1182.9, 1191.1, 1188.7]
        })
        
        schema = engine.infer_schema(df, 'test.csv')
        
        col = schema.columns[0]
        assert col.type in [ColumnType.NUMERIC, ColumnType.INTEGER]
        assert col.constraints.min_value < 1065.5  # Buffer below min
        assert col.constraints.max_value > 1191.1  # Buffer above max


class TestRowValidation:
    """Test row-level validation"""
    
    def test_detect_excel_errors(self):
        """Should detect Excel error values"""
        row = pd.Series({
            'student_email': 'john@example.com',
            'quiz_score': '#DIV/0!',
            'attendance': 85
        })
        
        errors = RowValidator.detect_excel_errors(row)
        
        assert len(errors) > 0
        assert 'quiz_score=#DIV/0!' in errors[0]
    
    def test_normalize_special_values(self):
        """Should normalize N/A and null-like strings"""
        row = pd.Series({
            'col1': 'N/A',
            'col2': 'NULL',
            'col3': '  ',
            'col4': 'valid_value'
        })
        
        normalized = RowValidator.normalize_special_values(row)
        
        assert pd.isna(normalized['col1'])
        assert pd.isna(normalized['col2'])
        assert pd.isna(normalized['col3'])
        assert normalized['col4'] == 'valid_value'


class TestNumericGuards:
    """Test numeric validation"""
    
    def test_detect_nan_inf(self):
        """Should detect NaN and Infinity"""
        import numpy as np
        
        assert NumericGuard.detect_infinity_nan(float('nan'))
        assert NumericGuard.detect_infinity_nan(float('inf'))
        assert NumericGuard.detect_infinity_nan(float('-inf'))
        assert not NumericGuard.detect_infinity_nan(42.5)
    
    def test_check_negative_where_invalid(self):
        """Should flag negative values in percentage/count columns"""
        assert NumericGuard.check_negative_where_invalid(-5, 'attendance_percentage')
        assert NumericGuard.check_negative_where_invalid(-1, 'login_count')
        assert not NumericGuard.check_negative_where_invalid(-5, 'temperature_change')
    
    def test_validate_percentage_range(self):
        """Should validate percentage bounds (0-100)"""
        is_valid, msg = NumericGuard.validate_percentage_range(105, 'completion_percentage')
        assert not is_valid
        assert "cannot exceed 100" in msg
        
        is_valid, msg = NumericGuard.validate_percentage_range(-5, 'attendance_percent')
        assert not is_valid
        assert "cannot be negative" in msg
        
        is_valid, msg = NumericGuard.validate_percentage_range(85.5, 'success_percentage')
        assert is_valid


class TestTimestampGuards:
    """Test timestamp validation"""
    
    def test_check_future_dates(self):
        """Should detect unreasonable future dates"""
        future = datetime.now() + timedelta(days=30)
        assert TimestampGuard.check_future_dates(future, grace_period_days=7)
        
        near_future = datetime.now() + timedelta(days=3)
        assert not TimestampGuard.check_future_dates(near_future, grace_period_days=7)
    
    def test_check_ancient_dates(self):
        """Should detect unreasonably old dates"""
        ancient = datetime(1990, 1, 1)
        assert TimestampGuard.check_ancient_dates(ancient)
        
        recent = datetime(2020, 1, 1)
        assert not TimestampGuard.check_ancient_dates(recent)
    
    def test_check_excel_epoch_bug(self):
        """Should detect Excel epoch dates"""
        excel_epoch = datetime(1900, 1, 1)
        assert TimestampGuard.check_excel_epoch_bug(excel_epoch)
        
        normal_date = datetime(2025, 2, 10)
        assert not TimestampGuard.check_excel_epoch_bug(normal_date)


class TestQuarantine:
    """Test quarantine management"""
    
    def test_quarantine_row(self):
        """Should track quarantined rows"""
        qm = QuarantineManager()
        
        qm.quarantine_row(
            row_data={'student_email': 'test@example.com', 'score': 'invalid'},
            reason='TYPE_MISMATCH',
            source_file='quiz.xlsx',
            row_number=45,
            failed_column='score',
            failure_message='Non-numeric value'
        )
        
        assert len(qm.quarantined_rows) == 1
        assert qm.quarantined_rows[0].row_number == 45
        assert qm.quarantined_rows[0].quarantine_reason == 'TYPE_MISMATCH'
    
    def test_quarantine_summary(self):
        """Should generate correct summary statistics"""
        qm = QuarantineManager()
        qm.total_rows_processed = 100
        
        # Add quarantined rows
        for i in range(5):
            qm.quarantine_row(
                row_data={'col': 'value'},
                reason='VALIDATION_ERROR',
                source_file='test.xlsx',
                row_number=i,
                failed_column='col'
            )
        
        summary = qm.get_summary()
        
        assert summary.total_quarantined == 5
        assert summary.quarantine_rate == 5.0  # 5/100 * 100
        assert 'test.xlsx' in summary.by_file
        assert summary.by_file['test.xlsx'] == 5


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
