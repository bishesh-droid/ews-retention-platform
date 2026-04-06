"""
LLM Audit Logging Utility
--------------------------
Tracks all LLM queries, responses, and user interactions for:
- Compliance reporting
- Quality improvement
- Security monitoring
- Bias detection
"""

from sqlalchemy.orm import Session
from datetime import datetime
from backend.database import LLMQuery
import json
from typing import Dict, Any, List, Optional


class AuditLogger:
    """Centralized audit logging for LLM interactions."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_llm_query(
        self,
        user_id: str,
        user_role: str,
        query_type: str,
        input_data: Dict[str, Any],
        response: Any,
        confidence: str,
        sources: List[str]
    ) -> int:
        """
        Log an LLM query for audit trail.
        
        Args:
            user_id: ID of user making the request
            user_role: Role of user ('student', 'faculty', 'admin', 'sales')
            query_type: Type of query ('explain_risk', 'advice', etc.)
            input_data: Input parameters as dict
            response: LLM response (can be dict or string)
            confidence: Confidence level ('high', 'medium', 'low')
            sources: List of data sources used
            
        Returns:
            ID of created audit log entry
        """
        # Convert response to string if it's a dict
        response_str = response if isinstance(response, str) else json.dumps(response)
        
        audit_entry = LLMQuery(
            user_id=user_id,
            user_role=user_role,
            query_type=query_type,
            input_data=json.dumps(input_data),
            response=response_str,
            confidence=confidence,
            sources=json.dumps(sources),
            timestamp=datetime.now().date()
        )
        
        self.db.add(audit_entry)
        # Caller commits the transaction.
        self.db.flush()
        self.db.refresh(audit_entry)
        
        return audit_entry.id
    
    def get_user_llm_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Retrieve LLM interaction history for a user.
        
        Args:
            user_id: User ID to retrieve history for
            limit: Maximum number of entries to return
            
        Returns:
            List of audit log entries
        """
        entries = (
            self.db.query(LLMQuery)
            .filter(LLMQuery.user_id == user_id)
            .order_by(LLMQuery.timestamp.desc())
            .limit(limit)
            .all()
        )
        
        return [
            {
                "id": entry.id,
                "query_type": entry.query_type,
                "confidence": entry.confidence,
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                "sources": json.loads(entry.sources) if entry.sources else []
            }
            for entry in entries
        ]
    
    def get_compliance_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, Any]:
        """
        Generate compliance report for LLM usage.
        
        Args:
            start_date: Start of reporting period
            end_date: End of reporting period
            
        Returns:
            Dictionary with compliance metrics
        """
        entries = (
            self.db.query(LLMQuery)
            .filter(
                LLMQuery.timestamp >= start_date.date(),
                LLMQuery.timestamp <= end_date.date()
            )
            .all()
        )
        
        # Calculate metrics
        total_queries = len(entries)
        queries_by_role = {}
        queries_by_type = {}
        confidence_distribution = {"high": 0, "medium": 0, "low": 0}
        
        for entry in entries:
            # By role
            role = entry.user_role
            queries_by_role[role] = queries_by_role.get(role, 0) + 1
            
            # By type
            qtype = entry.query_type
            queries_by_type[qtype] = queries_by_type.get(qtype, 0) + 1
            
            # Confidence distribution
            conf = entry.confidence
            if conf in confidence_distribution:
                confidence_distribution[conf] += 1
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "total_queries": total_queries,
            "queries_by_role": queries_by_role,
            "queries_by_type": queries_by_type,
            "confidence_distribution": confidence_distribution,
            "unique_users": len(set(e.user_id for e in entries))
        }
    
    def detect_anomalous_usage(self) -> List[Dict[str, Any]]:
        """
        Detect potentially anomalous LLM usage patterns.
        
        Returns:
            List of anomalies detected
        """
        # Implementation can include:
        # - Excessive queries from single user
        # - Unusual query patterns
        # - Low confidence queries repeatedly
        # - Access pattern violations
        
        anomalies = []
        
        # Example: Check for users with excessive low-confidence queries
        from sqlalchemy import func
        
        low_confidence_users = (
            self.db.query(
                LLMQuery.user_id,
                func.count(LLMQuery.id).label('count')
            )
            .filter(LLMQuery.confidence == 'low')
            .group_by(LLMQuery.user_id)
            .having(func.count(LLMQuery.id) > 10)
            .all()
        )
        
        for user_id, count in low_confidence_users:
            anomalies.append({
                "type": "excessive_low_confidence",
                "user_id": user_id,
                "count": count,
                "description": f"User has {count} low-confidence LLM queries"
            })
        
        return anomalies


class RoleBasedAccessControl:
    """
    Role-based access control for LLM features.
    Ensures students only see their data, faculty see assigned students, etc.
    """
    
    @staticmethod
    def can_access_student_data(
        requesting_user_id: str,
        requesting_user_role: str,
        target_student_id: str,
        assigned_students: Optional[List[str]] = None
    ) -> bool:
        """
        Check if user can access another student's data.
        
        Args:
            requesting_user_id: ID of user making request
            requesting_user_role: Role  ('student', 'faculty', 'admin', 'sales')
            target_student_id: ID of student whose data is being accessed
            assigned_students: List of student IDs assigned to faculty (if applicable)
            
        Returns:
            True if access is allowed, False otherwise
        """
        # Student can only see their own data
        if requesting_user_role == 'student':
            return requesting_user_id == target_student_id
        
        # Faculty can see assigned students
        if requesting_user_role == 'faculty':
            if assigned_students is None:
                return False
            return target_student_id in assigned_students
        
        # Admin can see all student data
        if requesting_user_role == 'admin':
            return True
        
        # Sales cannot see individual student data
        if requesting_user_role == 'sales':
            return False
        
        # Default deny
        return False
    
    @staticmethod
    def can_access_cohort_data(user_role: str) -> bool:
        """Check if user can access cohort-level data."""
        return user_role in ['admin', 'sales']
    
    @staticmethod
    def can_access_revenue_data(user_role: str) -> bool:
        """Check if user can access revenue/financial data."""
        return user_role in ['admin', 'sales']
    
    @staticmethod
    def can_access_institutional_insights(user_role: str) -> bool:
        """Check if user can access system-wide insights."""
        return user_role == 'admin'
    
    @staticmethod
    def get_allowed_query_types(user_role: str) -> List[str]:
        """
        Get list of allowed LLM query types for a role.
        
        Returns:
            List of allowed query type strings
        """
        permissions = {
            'student': [
                'explain_risk',
                'student_advice',
                'what_if_simulation',
                'weekly_brief'
            ],
            'faculty': [
                'faculty_summary',
                'intervention_suggestions',
                'prioritize_students',
                'similar_students'
            ],
            'admin': [
                'institutional_insights',
                'pattern_discovery',
                'generate_report_narrative',
                'intervention_effectiveness',
                'cohort_analysis'
            ],
            'sales': [
                'revenue_risk_translation',
                'dropout_pattern_explanation',
                'cohort_analysis'
            ]
        }
        
        return permissions.get(user_role, [])
