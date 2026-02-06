"""
Student Service for EWS Retention Platform.

This service integrates feature engineering and risk scoring to provide
comprehensive student data and analytics based on CSV columns.
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.services.feature_engineering import FeatureEngineer
from backend.app.services.risk_scoring import RiskScorer
from backend.app.models.student import Student
from backend.app.models.intervention import Intervention


class StudentService:
    """
    Service for retrieving and calculating student metrics.
    """
    
    @staticmethod
    def get_interventions_by_student_id(db: Session, student_id: str) -> List[Intervention]:
        """
        Get all interventions for a specific student.

        Args:
            db: Database session
            student_id: The ID of the student
        
        Returns:
            A list of Intervention ORM objects.
        """
        return db.query(Intervention).filter(Intervention.student_id == student_id).all()
    
    @staticmethod
    def student_to_dict(student: Student) -> Dict:
        """
        Convert Student ORM object to dictionary with all CSV columns.
        
        Args:
            student: Student database model
            
        Returns:
            Dictionary with all student data
        """
        return {
            'id': student.id,
            # Year 1
            'absrate1': student.absrate1,
            'nsusp1': student.nsusp1,
            'mobility1': student.mobility1,
            'q1mpa1': student.q1mpa1,
            'q2mpa1': student.q2mpa1,
            'q3mpa1': student.q3mpa1,
            'q4mpa1': student.q4mpa1,
            # Year 2
            'absrate2': student.absrate2,
            'nsusp2': student.nsusp2,
            'mobility2': student.mobility2,
            'q1mpa2': student.q1mpa2,
            'q2mpa2': student.q2mpa2,
            'q3mpa2': student.q3mpa2,
            'q4mpa2': student.q4mpa2,
            # Year 3
            'absrate3': student.absrate3,
            'nsusp3': student.nsusp3,
            'mobility3': student.mobility3,
            'q1mpa3': student.q1mpa3,
            'q2mpa3': student.q2mpa3,
            'q3mpa3': student.q3mpa3,
            'q4mpa3': student.q4mpa3,
            # Year 4
            'absrate4': student.absrate4,
            'nsusp4': student.nsusp4,
            'mobility4': student.mobility4,
            'q1mpa4': student.q1mpa4,
            'q2mpa4': student.q2mpa4,
            'q3mpa4': student.q3mpa4,
            'q4mpa4': student.q4mpa4,
            # Year 5
            'absrate5': student.absrate5,
            'nsusp5': student.nsusp5,
            'mobility5': student.mobility5,
            'q1mpa5': student.q1mpa5,
            'q2mpa5': student.q2mpa5,
            'q3mpa5': student.q3mpa5,
            'q4mpa5': student.q4mpa5,
            # Year 6
            'absrate6': student.absrate6,
            'nsusp6': student.nsusp6,
            'mobility6': student.mobility6,
            'q1mpa6': student.q1mpa6,
            'q2mpa6': student.q2mpa6,
            'q3mpa6': student.q3mpa6,
            'q4mpa6': student.q4mpa6,
            # Year 7
            'absrate7': student.absrate7,
            'nsusp7': student.nsusp7,
            'mobility7': student.mobility7,
            'q1mpa7': student.q1mpa7,
            'q2mpa7': student.q2mpa7,
            'q3mpa7': student.q3mpa7,
            'q4mpa7': student.q4mpa7,
            # Outcome
            'nograd': student.nograd
        }
    
    @staticmethod
    def calculate_student_metrics(student_data: Dict) -> Dict:
        """
        Calculate all metrics for a single student.
        
        Args:
            student_data: Dictionary with CSV columns
            
        Returns:
            Dictionary with calculated metrics and risk score
        """
        # Calculate features
        features = FeatureEngineer.calculate_all_features(student_data)
        
        # Calculate risk score
        risk_score = RiskScorer.calculate_risk_score(features)
        
        # Get risk metadata
        risk_category = RiskScorer.get_risk_category(risk_score)
        retention_likelihood = RiskScorer.get_retention_likelihood(risk_score)
        dominant_factor = RiskScorer.get_dominant_risk_factor(features)
        risk_breakdown = RiskScorer.get_risk_breakdown(features)
        
        return {
            'id': student_data['id'],
            'risk_score': risk_score,
            'risk_category': risk_category,
            'retention_likelihood': retention_likelihood,
            'dominant_risk_factor': dominant_factor,
            'risk_breakdown': risk_breakdown,
            'attendance_score': features['attendance_score'],
            'academic_score': features['academic_score'],
            'behavioral_score': features['behavioral_score'],
            'stability_score': features['stability_score'],
            'trend': features['trend'],
            'graduated': features['graduated'],
            'year_by_year': features['year_by_year']
        }
    
    @staticmethod
    def get_student_by_id(db: Session, student_id: str) -> Optional[Dict]:
        """
        Get student with calculated metrics by ID.
        
        Args:
            db: Database session
            student_id: Student identifier
            
        Returns:
            Student metrics dictionary or None if not found
        """
        student = db.query(Student).filter(Student.id == student_id).first()
        
        if not student:
            return None
        
        student_data = StudentService.student_to_dict(student)
        return StudentService.calculate_student_metrics(student_data)
    
    @staticmethod
    def get_all_students(db: Session, skip: int = 0, limit: int = 100,
                        sort_by: str = 'risk_score', order: str = 'desc',
                        risk_min: Optional[float] = None,
                        risk_max: Optional[float] = None) -> List[Dict]:
        """
        Get all students with calculated metrics and filtering.
        
        Args:
            db: Database session
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            sort_by: Field to sort by
            order: Sort order ('asc' or 'desc')
            risk_min: Minimum risk score filter
            risk_max: Maximum risk score filter
            
        Returns:
            List of student metrics dictionaries
        """
        # Get all students from database
        students = db.query(Student).all()
        
        # Calculate metrics for all students
        student_metrics = []
        for student in students:
            student_data = StudentService.student_to_dict(student)
            metrics = StudentService.calculate_student_metrics(student_data)
            student_metrics.append(metrics)
        
        # Apply risk score filtering
        if risk_min is not None:
            student_metrics = [s for s in student_metrics if s['risk_score'] >= risk_min]
        if risk_max is not None:
            student_metrics = [s for s in student_metrics if s['risk_score'] <= risk_max]
        
        # Sort
        reverse = (order == 'desc')
        if sort_by in ['risk_score', 'attendance_score', 'academic_score', 'behavioral_score', 'stability_score']:
            student_metrics.sort(key=lambda x: x[sort_by], reverse=reverse)
        elif sort_by == 'id':
            student_metrics.sort(key=lambda x: x['id'], reverse=reverse)
        
        # Pagination
        return student_metrics[skip:skip + limit]
    
    @staticmethod
    def get_overview_stats(db: Session) -> Dict:
        """
        Get overview statistics for the dashboard.
        
        Args:
            db: Database session
            
        Returns:
            Overview statistics dictionary
        """
        # Get all students
        students = db.query(Student).all()
        total_students = len(students)
        
        if total_students == 0:
            return {
                'total_students': 0,
                'at_risk_students': 0,
                'average_risk_score': 0,
                'risk_distribution': {'low': 0, 'medium': 0, 'high': 0},
                'graduation_rate': 0
            }
        
        # Calculate metrics for all students
        risk_scores = []
        risk_categories = {'low': 0, 'medium': 0, 'high': 0}
        graduated_count = 0
        
        for student in students:
            student_data = StudentService.student_to_dict(student)
            metrics = StudentService.calculate_student_metrics(student_data)
            
            risk_scores.append(metrics['risk_score'])
            risk_categories[metrics['risk_category']] += 1
            
            if metrics['graduated']:
                graduated_count += 1
        
        average_risk = sum(risk_scores) / len(risk_scores)
        at_risk_count = risk_categories['high']
        graduation_rate = (graduated_count / total_students) * 100
        
        return {
            'total_students': total_students,
            'at_risk_students': at_risk_count,
            'average_risk_score': round(average_risk, 2),
            'risk_distribution': risk_categories,
            'graduation_rate': round(graduation_rate, 2)
        }
    
    @staticmethod
    def get_analytics_data(db: Session) -> Dict:
        """
        Get analytics data for trends and correlations.
        
        Args:
            db: Database session
            
        Returns:
            Analytics data dictionary
        """
        students = db.query(Student).all()
        
        # Yearly averages
        yearly_attendance = {i: [] for i in range(1, 8)}
        yearly_academic = {i: [] for i in range(1, 8)}
        
        all_metrics = []
        
        for student in students:
            student_data = StudentService.student_to_dict(student)
            metrics = StudentService.calculate_student_metrics(student_data)
            all_metrics.append(metrics)
            
            # Collect yearly data
            for year_data in metrics['year_by_year']:
                year = year_data['year']
                if year_data['absence_rate'] is not None:
                    yearly_attendance[year].append(100 - year_data['absence_rate'])
                
                quarterly_avg = [q for q in year_data['quarterly_scores'] if q is not None]
                if quarterly_avg:
                    yearly_academic[year].append(sum(quarterly_avg) / len(quarterly_avg))
        
        # Calculate averages
        attendance_by_year = [
            {'year': year, 'avg_rate': round(sum(vals) / len(vals), 2) if vals else 0}
            for year, vals in yearly_attendance.items()
        ]
        
        academic_by_year = [
            {'year': year, 'avg_gpa': round(sum(vals) / len(vals), 2) if vals else 0}
            for year, vals in yearly_academic.items()
        ]
        
        # Simple correlations (Pearson would require scipy, using simple approach)
        return {
            'attendance_by_year': attendance_by_year,
            'academic_by_year': academic_by_year,
            'total_analyzed': len(students)
        }
