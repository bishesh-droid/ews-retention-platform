"""
Unit Tests for LLM Services
----------------------------
Tests for RAG engine, hallucination prevention, and audit logging.
"""

import pytest
from unittest.mock import Mock, MagicMock
from backend.services.ai.hallucination_guard import (
    HallucinationPrevention,
    ContentFilter,
    ConfidenceScorer,
)
from backend.services.infrastructure.audit_logger import (
    AuditLogger,
    RoleBasedAccessControl,
)


class TestHallucinationPrevention:
    """Test hallucination detection and prevention."""

    def setup_method(self):
        self.db = Mock()
        self.prevention = HallucinationPrevention(self.db)

    def test_valid_response_passes(self):
        """Test that valid, grounded response passes validation."""
        response = (
            "Student 1001 has a risk score of 75% based on recent attendance data."
        )
        allowed_data = {
            "student_data": {"id": "1001", "risk_score": 75},
            "attendance_rate": 0.80,
        }

        result = self.prevention.validate_response(response, allowed_data)

        assert result["is_valid"] is True
        assert result["confidence"] > 0.7

    def test_fabricated_student_id_fails(self):
        """Test that fabricated student IDs are detected."""
        response = "Student 9999 needs immediate intervention."
        allowed_data = {"student_data": {"id": "1001"}}

        result = self.prevention.validate_response(response, allowed_data)

        assert result["is_valid"] is False
        assert any(
            "student IDs not in source data" in issue for issue in result["issues"]
        )

    def test_too_much_uncertainty_reduces_confidence(self):
        """Test that excessive hedge words reduce confidence."""
        response = "Maybe the student might possibly could perhaps improve."
        allowed_data = {"student_data": {"id": "1001"}}

        result = self.prevention.validate_response(response, allowed_data)

        assert result["confidence"] < 0.8
        assert any(
            "uncertainty indicators" in warning for warning in result["warnings"]
        )


class TestContentFilter:
    """Test content filtering for inappropriate responses."""

    def test_appropriate_content_passes(self):
        """Test that appropriate educational content passes."""
        response = "You can improve your grades by attending more classes and completing assignments."

        result = ContentFilter.check_content(response)

        assert result["is_appropriate"] is True
        assert len(result["issues"]) == 0

    def test_inappropriate_phrases_blocked(self):
        """Test that harmful phrases are blocked."""
        response = "You're going to fail this class, you should drop out."

        result = ContentFilter.check_content(response)

        assert result["is_appropriate"] is False
        assert "I'm sorry" in result["filtered_response"]

    def test_sensitive_topics_flagged(self):
        """Test that sensitive topics trigger escalation."""
        response = "If you're struggling with depression, seek help."

        result = ContentFilter.check_content(response)

        assert result["needs_escalation"] is True
        assert any("mental health" in issue for issue in result["issues"])


class TestConfidenceScorer:
    """Test confidence scoring logic."""

    def test_high_confidence_score(self):
        """Test that complete, recent data yields high confidence."""
        result = ConfidenceScorer.calculate_confidence(
            data_completeness=0.95, data_recency=0.9, sample_size=150
        )

        assert result["level"] == "high"
        assert result["score"] >= 0.8

    def test_low_confidence_score(self):
        """Test that incomplete data yields low confidence."""
        result = ConfidenceScorer.calculate_confidence(
            data_completeness=0.3, data_recency=0.4, sample_size=10
        )

        assert result["level"] == "low"
        assert result["score"] < 0.6


class TestRoleBasedAccessControl:
    """Test RBAC for LLM features."""

    def test_student_can_only_access_own_data(self):
        """Students should only see their own data."""
        can_access = RoleBasedAccessControl.can_access_student_data(
            requesting_user_id="1001",
            requesting_user_role="student",
            target_student_id="1001",
        )

        assert can_access is True

        # Cannot access other student
        cannot_access = RoleBasedAccessControl.can_access_student_data(
            requesting_user_id="1001",
            requesting_user_role="student",
            target_student_id="1002",
        )

        assert cannot_access is False

    def test_faculty_can_access_assigned_students(self):
        """Faculty can access assigned students only."""
        can_access = RoleBasedAccessControl.can_access_student_data(
            requesting_user_id="faculty_001",
            requesting_user_role="faculty",
            target_student_id="1001",
            assigned_students=["1001", "1002", "1003"],
        )

        assert can_access is True

        # Cannot access unassigned student
        cannot_access = RoleBasedAccessControl.can_access_student_data(
            requesting_user_id="faculty_001",
            requesting_user_role="faculty",
            target_student_id="9999",
            assigned_students=["1001", "1002", "1003"],
        )

        assert cannot_access is False

    def test_admin_can_access_all_data(self):
        """Admins have full access."""
        can_access = RoleBasedAccessControl.can_access_student_data(
            requesting_user_id="admin_001",
            requesting_user_role="admin",
            target_student_id="1001",
        )

        assert can_access is True

    def test_sales_cannot_access_individual_students(self):
        """Sales team cannot see individual student data."""
        cannot_access = RoleBasedAccessControl.can_access_student_data(
            requesting_user_id="sales_001",
            requesting_user_role="sales",
            target_student_id="1001",
        )

        assert cannot_access is False

    def test_role_query_permissions(self):
        """Test that roles have correct query permissions."""
        student_queries = RoleBasedAccessControl.get_allowed_query_types("student")
        assert "explain_risk" in student_queries
        assert "institutional_insights" not in student_queries

        admin_queries = RoleBasedAccessControl.get_allowed_query_types("admin")
        assert "institutional_insights" in admin_queries
        assert "pattern_discovery" in admin_queries


class TestAuditLogger:
    """Test audit logging functionality."""

    def setup_method(self):
        self.db = MagicMock()
        self.logger = AuditLogger(self.db)

    def test_log_llm_query_creates_entry(self):
        """Test that LLM queries are logged."""
        self.logger.log_llm_query(
            user_id="1001",
            user_role="student",
            query_type="explain_risk",
            input_data={"student_id": "1001", "time_period": "recent"},
            response={"content": "Risk increased due to attendance"},
            confidence="high",
            sources=["attendance_records", "grade_data"],
        )

        # Verify db.add and db.flush were called
        assert self.db.add.called
        assert self.db.flush.called

    def test_compliance_report_structure(self):
        """Test compliance report generation."""
        from datetime import datetime

        # Mock query results
        mock_entries = [
            Mock(
                user_id="1001",
                user_role="student",
                query_type="explain_risk",
                confidence="high",
            ),
            Mock(
                user_id="1002",
                user_role="faculty",
                query_type="faculty_summary",
                confidence="medium",
            ),
        ]

        self.db.query.return_value.filter.return_value.all.return_value = mock_entries

        report = self.logger.get_compliance_report(
            start_date=datetime(2026, 1, 1), end_date=datetime(2026, 1, 31)
        )

        assert "total_queries" in report
        assert "queries_by_role" in report
        assert "confidence_distribution" in report


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
