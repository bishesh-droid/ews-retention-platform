from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from backend.database import Goal, Enrollment
from backend.schemas.student import Student

class GoalsService:
    @staticmethod
    def create_goal(db: Session, student_id: str, goal_type: str, title: str, target_value: float, end_date: datetime):
        """
        Creates a new goal for a student.
        """
        db_goal = Goal(
            student_id=student_id,
            type=goal_type,
            title=title,
            target_value=target_value,
            end_date=end_date,
            status="active"
        )
        db.add(db_goal)
        # Caller commits the transaction.
        db.flush()
        db.refresh(db_goal)
        return db_goal

    @staticmethod
    def update_goal_progress(db: Session, student_id: str):
        """
        Aggregates weekly data and updates goal current_value and status.
        """
        active_goals = db.query(Goal).filter(
            Goal.student_id == student_id,
            Goal.status == "active"
        ).all()

        if not active_goals:
            return

        # Fetch recent enrollment metrics for aggregation
        enrollments = db.query(Enrollment).filter(Enrollment.student_id == student_id).all()
        
        for goal in active_goals:
            # Update progress based on type
            if goal.type == "login":
                goal.current_value = sum(e.num_logins for e in enrollments)
            elif goal.type == "assignment":
                goal.current_value = sum(e.num_assignment_submissions for e in enrollments)
            elif goal.type == "attendance":
                # logic for attendance percentage...
                pass
            
            # Check if goal reached
            if goal.current_value >= goal.target_value:
                goal.status = "completed"
            elif goal.end_date < datetime.utcnow():
                goal.status = "failed"
            
            db.add(goal)
        # Caller commits the transaction.
        db.flush()

    @staticmethod
    def get_student_goals(db: Session, student_id: str) -> List[Goal]:
        """
        Retrieves all goals for a student with calculated progress %.
        """
        goals = db.query(Goal).filter(Goal.student_id == student_id).all()
        # Add a dynamic property logic in frontend or here
        return goals
        
