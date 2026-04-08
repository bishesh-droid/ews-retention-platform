
import random
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.database.connection import SessionLocal, engine
from backend.database.models import (
    User, Student, Prediction, Intervention, RiskSnapshot, Goal,
    LLMInsight, AIExplanation, PatternDiscovery, StudentResponse, AuditLog
)
import bcrypt

def get_password_hash(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def seed_data():
    db = SessionLocal()
    try:
        # 1. Create Users (Faculty and Admin)
        if db.query(User).count() == 0:
            print("Seeding users...")
            users = [
                User(
                    username="admin",
                    email="admin@example.com",
                    hashed_password=get_password_hash("admin123"),
                    role="Admin",
                    is_superuser=True
                ),
                User(
                    username="faculty1",
                    email="faculty1@example.com",
                    hashed_password=get_password_hash("faculty123"),
                    role="Faculty"
                ),
                User(
                    username="retention1",
                    email="retention1@example.com",
                    hashed_password=get_password_hash("retention123"),
                    role="Retention Team"
                )
            ]
            db.add_all(users)
            db.commit()

        # Get some students
        students = db.query(Student).limit(100).all()
        if not students:
            print("No students found in database. Please run ingestion first.")
            return

        student_ids = [s.id for s in students]

        # 2. Create Predictions
        if db.query(Prediction).count() == 0:
            print("Seeding predictions...")
            predictions = []
            for sid in student_ids:
                risk_score = random.uniform(0.1, 0.95)
                engagement_score = random.uniform(0.2, 0.9)
                retention_likelihood = "high" if risk_score < 0.3 else "medium" if risk_score < 0.7 else "low"
                
                predictions.append(Prediction(
                    student_id=sid,
                    risk_score=risk_score * 100, # Frontend expects 0-100
                    engagement_score=engagement_score * 100,
                    retention_likelihood=retention_likelihood,
                    academic_signal_score=random.uniform(0.3, 0.9),
                    engagement_signal_score=random.uniform(0.2, 0.8),
                    consistency_signal_score=random.uniform(0.4, 0.9),
                    intent_signal_score=random.uniform(0.3, 0.85),
                    responsiveness_signal_score=random.uniform(0.2, 0.9),
                    model_version="xgboost_v1.0",
                    top_risk_factors=json.dumps(["Low attendance", "Declining quiz scores", "Late submissions"][:random.randint(1, 3)])
                ))
            db.add_all(predictions)
            db.commit()

        # 3. Create Risk Snapshots (for trends)
        if db.query(RiskSnapshot).count() == 0:
            print("Seeding risk snapshots...")
            snapshots = []
            for sid in student_ids[:20]:
                base_risk = random.uniform(30, 80)
                for i in range(5):
                    snapshots.append(RiskSnapshot(
                        student_id=sid,
                        risk_score=base_risk + random.uniform(-10, 10),
                        velocity=random.uniform(-5, 5),
                        engagement_score=random.uniform(40, 90),
                        timestamp=datetime.utcnow() - timedelta(days=i*7)
                    ))
            db.add_all(snapshots)
            db.commit()

        # 4. Create Interventions
        from backend.database.models.intervention import Intervention as InterventionModel
        if db.query(InterventionModel).count() == 0:
            print("Seeding interventions...")
            interventions = []
            actions = ["Gentle Reminder", "Mentor Outreach", "Urgent Call", "Tutoring Session", "Financial Counseling"]
            faculties = ["Dr. Smith", "Prof. Johnson", "Dr. Lee", "Coach Miller"]
            
            for sid in student_ids[:30]:
                risk_at_trigger = random.uniform(40, 95)
                status = random.choice(["Pending", "In Progress", "Completed"])
                interventions.append(InterventionModel(
                    student_id=sid,
                    date=(datetime.utcnow() - timedelta(days=random.randint(1, 30))).date(),
                    user="admin",
                    action=random.choice(actions),
                    status=status,
                    assigned_faculty=random.choice(faculties),
                    ai_suggested=random.choice([True, False]),
                    ai_reasoning="Student showing significant decline in engagement over the last 2 weeks.",
                    effectiveness_score=random.uniform(0.1, 0.9) if status == "Completed" else None,
                    risk_score_at_trigger=risk_at_trigger,
                    threshold_category="urgent" if risk_at_trigger > 80 else "mentor_outreach",
                    channels=json.dumps(["email", "whatsapp"]),
                    assigned_team=random.choice(["faculty", "automated", "counselor"])
                ))
            db.add_all(interventions)
            db.commit()

        # 5. Create Goals
        if db.query(Goal).count() == 0:
            print("Seeding goals...")
            goals = []
            goal_types = ["login", "study_hours", "assignment", "attendance"]
            for sid in student_ids[:15]:
                g_type = random.choice(goal_types)
                target = random.uniform(80, 100)
                goals.append(Goal(
                    student_id=sid,
                    type=g_type,
                    title=f"Improve {g_type.capitalize()}",
                    target_value=target,
                    current_value=random.uniform(target-20, target),
                    end_date=datetime.utcnow() + timedelta(days=30),
                    status="active"
                ))
            db.add_all(goals)
            db.commit()

        # 6. Create LLM Insights
        if db.query(LLMInsight).count() == 0:
            print("Seeding LLM insights...")
            insights = [
                LLMInsight(
                    insight_type="pattern",
                    title="Mid-semester Engagement Drop",
                    content="A significant pattern of engagement decline is observed in the 3rd year BS Data Science cohort between weeks 6 and 8.",
                    confidence="high",
                    visibility="admin_only",
                    created_at=datetime.utcnow().date()
                ),
                LLMInsight(
                    insight_type="opportunity",
                    title="Tutoring Success in CS101",
                    content="Students who attended at least one tutoring session showed a 15% higher retention rate compared to their peers in the same risk band.",
                    confidence="medium",
                    visibility="public",
                    created_at=datetime.utcnow().date()
                )
            ]
            db.add_all(insights)
            db.commit()

        # 7. Create AI Explanations
        if db.query(AIExplanation).count() == 0:
            print("Seeding AI explanations...")
            explanations = []
            for sid in student_ids[:10]:
                explanations.append(AIExplanation(
                    student_id=sid,
                    explanation_type="risk_change",
                    content="Your risk score increased because your last three assignments were submitted 24+ hours after the deadline.",
                    confidence="high",
                    created_at=datetime.utcnow().date()
                ))
            db.add_all(explanations)
            db.commit()

        # 8. Create Pattern Discoveries
        if db.query(PatternDiscovery).count() == 0:
            print("Seeding pattern discoveries...")
            patterns = [
                PatternDiscovery(
                    pattern_type="systemic_issue",
                    title="Mobile App Access Latency",
                    description="Students in remote regions are experiencing 5s+ latency on mobile login, leading to 20% fewer daily logins.",
                    severity="medium",
                    affected_cohort=json.dumps(["Regional Cohorts"]),
                    discovered_at=datetime.utcnow().date()
                )
            ]
            db.add_all(patterns)
            db.commit()

        # 9. Create Audit Logs for Reports
        if db.query(AuditLog).filter(AuditLog.action_type == "report_generated").count() == 0:
            print("Seeding report audit logs...")
            report_logs = []
            report_names = [
                ("Monthly Risk Summary", 1),
                ("High-Risk Students Report", 2),
                ("Intervention Impact Report", 3),
                ("Department Performance Report", 4)
            ]
            for i in range(10):
                name, tid = random.choice(report_names)
                report_logs.append(AuditLog(
                    user_id=1, # admin
                    user_role="Admin",
                    action_type="report_generated",
                    timestamp=datetime.utcnow() - timedelta(days=random.randint(1, 60)),
                    details={
                        "template_id": tid,
                        "template_name": name,
                        "format": random.choice(["PDF", "Excel", "CSV"]),
                        "file_name": f"{name.replace(' ', '_')}_{i}.pdf",
                        "size_bytes": random.randint(1024*100, 1024*1024*2),
                        "status": "ready"
                    }
                ))
            db.add_all(report_logs)
            db.commit()

        print("Seeding completed successfully!")

    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
