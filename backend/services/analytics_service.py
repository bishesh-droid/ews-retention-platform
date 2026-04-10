from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

from backend.config import trimester_week_number, CURRENT_SEMESTER_NAME
from backend.database import RiskSnapshot, Prediction


_COHORT_CACHE: Dict[str, Tuple[datetime, Dict[str, Any]]] = {}
_COHORT_CACHE_TTL_SECONDS = 60


class AnalyticsService:
    @staticmethod
    def capture_risk_snapshot(
        db: Session,
        student_id: str,
        risk_score: float,
        engagement_score: float,
        week_number: Optional[int] = None,
    ):
        """
        Creates a new risk snapshot and calculates velocity/acceleration.
        """
        # Get last snapshot
        last_snapshot = db.query(RiskSnapshot).filter(
            RiskSnapshot.student_id == student_id
        ).order_by(RiskSnapshot.timestamp.desc()).first()

        velocity = 0.0
        acceleration = 0.0

        if last_snapshot:
            # Velocity = change in risk score
            velocity = risk_score - float(last_snapshot.risk_score)  # type: ignore[arg-type]
            # Acceleration = change in velocity
            acceleration = velocity - float(last_snapshot.velocity or 0.0)  # type: ignore[arg-type]

        wn = week_number if week_number is not None else trimester_week_number()
        snapshot = RiskSnapshot(
            student_id=student_id,
            risk_score=risk_score,  # type: ignore[arg-type]
            velocity=velocity,  # type: ignore[arg-type]
            acceleration=acceleration,  # type: ignore[arg-type]
            engagement_score=engagement_score,  # type: ignore[arg-type]
            week_number=wn,
            semester_name=CURRENT_SEMESTER_NAME,
            timestamp=datetime.utcnow(),
        )
        db.add(snapshot)
        # Caller commits the transaction.
        db.flush()
        db.refresh(snapshot)
        return snapshot

    @staticmethod
    def get_risk_trends(db: Session, student_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Calculates 7-day and 30-day trend slopes and identifies anomalies.
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        snapshots = db.query(RiskSnapshot).filter(
            RiskSnapshot.student_id == student_id,
            RiskSnapshot.timestamp >= start_date
        ).order_by(RiskSnapshot.timestamp.asc()).all()

        if not snapshots:
            return {"trend": "stable", "slope": 0, "snapshots": []}

        # Simple linear regression (slope) for the trend
        # x = time (days from start), y = risk_score
        y_values = [float(s.risk_score or 0) for s in snapshots]  # type: ignore[arg-type]
        x_values = range(len(y_values))

        if len(x_values) > 1:
            mean_x = sum(x_values) / len(x_values)
            mean_y = sum(y_values) / len(y_values)
            numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values))
            denominator = sum((x - mean_x) ** 2 for x in x_values)
            slope = numerator / denominator if denominator != 0 else 0
        else:
            slope = 0

        # Anomaly detection: Sudden drop in engagement
        engagement_scores = [float(s.engagement_score or 0) for s in snapshots]  # type: ignore[arg-type]
        is_anomaly = False
        if len(engagement_scores) >= 2:
            last_change = engagement_scores[-1] - engagement_scores[-2]
            if last_change < -0.3:  # 30% drop in engagement is an anomaly
                is_anomaly = True

        return {
            "student_id": student_id,
            "current_risk": y_values[-1],
            "slope": slope,
            "trend": "increasing" if slope > 0.01 else "decreasing" if slope < -0.01 else "stable",
            "is_anomaly": is_anomaly,
            "snapshots": [
                {
                    "timestamp": s.timestamp.isoformat() if s.timestamp else None,
                    "date": s.timestamp.date().isoformat() if s.timestamp else None,
                    "risk_score": s.risk_score,
                    "velocity": s.velocity,
                    "acceleration": s.acceleration,
                    "week_number": s.week_number,
                    "semester": s.semester_name,
                } for s in snapshots
            ]
        }

    @staticmethod
    def get_top_risk_velocity(db: Session, limit: int = 10):
        """
        Identify students with the fastest growing risk scores.
        """
        latest_snapshots = db.query(RiskSnapshot).order_by(
            RiskSnapshot.student_id, RiskSnapshot.timestamp.desc()
        ).distinct(RiskSnapshot.student_id).all()

        sorted_snapshots = sorted(latest_snapshots, key=lambda x: float(x.velocity or 0), reverse=True)  # type: ignore[arg-type]
        return sorted_snapshots[:limit]

    @staticmethod
    def get_kpi_cards(db: Session, filters: Dict[str, Any] = None):
        """
        Aggregate key performance indicators for the dashboard.
        """
        # Apply filters to base query if provided (department, semester, etc.)
        # For simplicity, we'll implement core logic first

        # 1. Top 10 At-Risk Students
        cache_key = "kpi_cards"
        now = datetime.utcnow()

        # Return cached result if still within TTL
        cached = _COHORT_CACHE.get(cache_key)
        if cached:
            cached_at, data = cached
            if (now - cached_at).total_seconds() <= _COHORT_CACHE_TTL_SECONDS:
                return data

        top_at_risk = db.query(Prediction).order_by(Prediction.risk_score.desc()).limit(10).all()

        # 2. Biggest Attendance Drop (Velocity in attendance)
        # We'd need historical attendance snapshots similarly to risk scores

        # 3. Engagement Decline Alerts (Anomalies)
        anomalies_count = db.query(RiskSnapshot).filter(
            RiskSnapshot.timestamp >= datetime.utcnow() - timedelta(days=7),
            RiskSnapshot.velocity > 0.2  # Arbitrary spike threshold
        ).count()

        result = {
            "top_at_risk": [
                {"student_id": p.student_id, "risk_score": p.risk_score} for p in top_at_risk
            ],
            "engagement_alerts": anomalies_count,
            "system_health": "stable"  # Placeholder
        }

        # Cache cohort summary for a short period to reduce DB load
        _COHORT_CACHE[cache_key] = (now, result)
        return result

    @staticmethod
    def get_drill_down(db: Session, metric: str, filters: Dict[str, Any] = None):
        """
        Provide detailed data for a specific KPI metric.
        """
        if metric == "top-risk":
            return db.query(Prediction).order_by(Prediction.risk_score.desc()).limit(20).all()
        # Add more drill-down logic
        return []
