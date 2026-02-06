"""
Load simulated student data from CSV into the database.

This script reads the simulated_data.csv file containing 1000 students
and loads them into the database with calculated risk predictions.
"""

import csv
import sys
from pathlib import Path
from datetime import datetime
import random

# Add parent directory to path to import database modules
sys.path.insert(0, str(Path(__file__).parent))

from backend.database import SessionLocal, Student, Prediction, init_db
from sqlalchemy import func

def calculate_risk_score(student_data):
    """
    Calculate risk score based on student features.
    Higher risk = higher chance of dropout (nograd=1)
    """
    # Base risk on nograd outcome (0 = graduated, 1 = did not graduate)
    base_risk = float(student_data.get('nograd', 0)) * 100
    
    # Add some variation to make it realistic (-10 to +10)
    variation = random.uniform(-10, 10)
    risk_score = max(0, min(100, base_risk + variation))
    
    return round(risk_score, 2)

def calculate_engagement_score(student_data):
    """Calculate engagement score from GPA and attendance data."""
    # Average the last year's GPA scores (q1mpa7, q2mpa7, q3mpa7, q4mpa7)
    gpa_scores = [
        float(student_data.get('q1mpa7', 2.5)),
        float(student_data.get('q2mpa7', 2.5)),
        float(student_data.get('q3mpa7', 2.5)),
        float(student_data.get('q4mpa7', 2.5))
    ]
    avg_gpa = sum(gpa_scores) / len(gpa_scores)
    
    # Convert GPA to engagement score (0-100)
    # Assuming GPA is on 0-5 scale
    engagement = (avg_gpa / 5.0) * 100
    
    # Factor in attendance (absrate7 - lower is better)
    absrate = float(student_data.get('absrate7', 5))
    attendance_factor = max(0, 100 - absrate * 5)  # Penalize high absence rates
    
    # Weighted average
    engagement_score = (engagement * 0.6 + attendance_factor * 0.4)
    
    return round(max(0, min(100, engagement_score)), 2)

def calculate_metrics(student_data):
    """Calculate attendance, assignments, and grades metrics."""
    # Attendance: based on absence rate (inverse)
    absrate = float(student_data.get('absrate7', 5))
    attendance = round(max(0, 100 - absrate * 5), 2)
    
    # Grades: based on average GPA from last year
    gpa_scores = [
        float(student_data.get('q1mpa7', 2.5)),
        float(student_data.get('q2mpa7', 2.5)),
        float(student_data.get('q3mpa7', 2.5)),
        float(student_data.get('q4mpa7', 2.5))
    ]
    avg_gpa = sum(gpa_scores) / len(gpa_scores)
    grades = round((avg_gpa / 5.0) * 100, 2)
    
    # Assignments: approximation based on grades and engagement
    assignments = round((grades + attendance) / 2, 2)
    
    return attendance, assignments, grades

def get_retention_likelihood(risk_score):
    """Determine retention likelihood category based on risk score."""
    if risk_score < 30:
        return "High"
    elif risk_score < 60:
        return "Medium"
    elif risk_score < 80:
        return "Low"
    else:
        return "Very Low"

def load_data_from_csv(csv_path, db):
    """Load student data from CSV file into database."""
    print(f"Reading CSV file: {csv_path}")
    
    students_loaded = 0
    students_skipped = 0
    predictions_created = 0
    
    with open(csv_path, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            student_id = row['id']
            
            # Check if student already exists
            existing_student = db.query(Student).filter(Student.id == student_id).first()
            if existing_student:
                print(f"  Skipping {student_id} (already exists)")
                students_skipped += 1
                continue
            
            # Create student record with all features
            student = Student(
                id=student_id,
                absrate1=float(row['absrate1']) if row['absrate1'] else None,
                absrate2=float(row['absrate2']) if row['absrate2'] else None,
                absrate3=float(row['absrate3']) if row['absrate3'] else None,
                absrate4=float(row['absrate4']) if row['absrate4'] else None,
                absrate5=float(row['absrate5']) if row['absrate5'] else None,
                absrate6=float(row['absrate6']) if row['absrate6'] else None,
                absrate7=float(row['absrate7']) if row['absrate7'] else None,
                nsusp1=float(row['nsusp1']) if row['nsusp1'] else None,
                nsusp2=float(row['nsusp2']) if row['nsusp2'] else None,
                nsusp3=float(row['nsusp3']) if row['nsusp3'] else None,
                nsusp4=float(row['nsusp4']) if row['nsusp4'] else None,
                nsusp5=float(row['nsusp5']) if row['nsusp5'] else None,
                nsusp6=float(row['nsusp6']) if row['nsusp6'] else None,
                nsusp7=float(row['nsusp7']) if row['nsusp7'] else None,
                mobility1=float(row['mobility1']) if row['mobility1'] else None,
                mobility2=float(row['mobility2']) if row['mobility2'] else None,
                mobility3=float(row['mobility3']) if row['mobility3'] else None,
                mobility4=float(row['mobility4']) if row['mobility4'] else None,
                mobility5=float(row['mobility5']) if row['mobility5'] else None,
                mobility6=float(row['mobility6']) if row['mobility6'] else None,
                mobility7=float(row['mobility7']) if row['mobility7'] else None,
                q1mpa1=float(row['q1mpa1']) if row['q1mpa1'] else None,
                q2mpa1=float(row['q2mpa1']) if row['q2mpa1'] else None,
                q3mpa1=float(row['q3mpa1']) if row['q3mpa1'] else None,
                q4mpa1=float(row['q4mpa1']) if row['q4mpa1'] else None,
                q1mpa2=float(row['q1mpa2']) if row['q1mpa2'] else None,
                q2mpa2=float(row['q2mpa2']) if row['q2mpa2'] else None,
                q3mpa2=float(row['q3mpa2']) if row['q3mpa2'] else None,
                q4mpa2=float(row['q4mpa2']) if row['q4mpa2'] else None,
                q1mpa3=float(row['q1mpa3']) if row['q1mpa3'] else None,
                q2mpa3=float(row['q2mpa3']) if row['q2mpa3'] else None,
                q3mpa3=float(row['q3mpa3']) if row['q3mpa3'] else None,
                q4mpa3=float(row['q4mpa3']) if row['q4mpa3'] else None,
                q1mpa4=float(row['q1mpa4']) if row['q1mpa4'] else None,
                q2mpa4=float(row['q2mpa4']) if row['q2mpa4'] else None,
                q3mpa4=float(row['q3mpa4']) if row['q3mpa4'] else None,
                q4mpa4=float(row['q4mpa4']) if row['q4mpa4'] else None,
                q1mpa5=float(row['q1mpa5']) if row['q1mpa5'] else None,
                q2mpa5=float(row['q2mpa5']) if row['q2mpa5'] else None,
                q3mpa5=float(row['q3mpa5']) if row['q3mpa5'] else None,
                q4mpa5=float(row['q4mpa5']) if row['q4mpa5'] else None,
                q1mpa6=float(row['q1mpa6']) if row['q1mpa6'] else None,
                q2mpa6=float(row['q2mpa6']) if row['q2mpa6'] else None,
                q3mpa6=float(row['q3mpa6']) if row['q3mpa6'] else None,
                q4mpa6=float(row['q4mpa6']) if row['q4mpa6'] else None,
                q1mpa7=float(row['q1mpa7']) if row['q1mpa7'] else None,
                q2mpa7=float(row['q2mpa7']) if row['q2mpa7'] else None,
                q3mpa7=float(row['q3mpa7']) if row['q3mpa7'] else None,
                q4mpa7=float(row['q4mpa7']) if row['q4mpa7'] else None,
                nograd=int(row['nograd']) if row['nograd'] else 0
            )
            
            db.add(student)
            students_loaded += 1
            
            # Create prediction for this student
            risk_score = calculate_risk_score(row)
            engagement_score = calculate_engagement_score(row)
            attendance, assignments, grades = calculate_metrics(row)
            retention_likelihood = get_retention_likelihood(risk_score)
            
            # Create signal scores (mock values for now)
            academic_signal = round(100 - risk_score * 0.4, 2)
            engagement_signal = round(engagement_score * 0.9, 2)
            consistency_signal = round(attendance * 0.8, 2)
            intent_signal = round((100 - risk_score) * 0.6, 2)
            responsiveness_signal = round(50 + random.uniform(-20, 20), 2)
            
            prediction = Prediction(
                student_id=student_id,
                risk_score=risk_score,
                engagement_score=engagement_score,
                retention_likelihood=retention_likelihood,
                attendance=attendance,
                assignments=assignments,
                grades=grades,
                academic_signal_score=academic_signal,
                engagement_signal_score=engagement_signal,
                consistency_signal_score=consistency_signal,
                intent_signal_score=intent_signal,
                responsiveness_signal_score=responsiveness_signal,
                model_version="simulated_v1.0",
                top_risk_factors=f"nograd={row['nograd']}, absrate7={row['absrate7']}",
                prediction_timestamp=datetime.utcnow()
            )
            
            db.add(prediction)
            predictions_created += 1
            
            # Commit in batches of 100 for efficiency
            if students_loaded % 100 == 0:
                db.commit()
                print(f"  Loaded {students_loaded} students...")
    
    # Final commit
    db.commit()
    
    return students_loaded, students_skipped, predictions_created

def main():
    """Main execution function."""
    print("=" * 60)
    print("EWS Retention Platform - Data Loader")
    print("=" * 60)
    
    # Initialize database
    print("\nInitializing database...")
    init_db()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Check existing data
        existing_count = db.query(func.count(Student.id)).scalar()
        print(f"Current students in database: {existing_count}")
        
        # Path to CSV file
        csv_path = Path(__file__).parent / "data" / "simulated_data.csv"
        
        if not csv_path.exists():
            print(f"\nERROR: CSV file not found at {csv_path}")
            return
        
        print(f"\nLoading data from: {csv_path}")
        print("-" * 60)
        
        # Load the data
        loaded, skipped, predictions = load_data_from_csv(csv_path, db)
        
        print("-" * 60)
        print(f"\n✓ Data loading complete!")
        print(f"  Students loaded: {loaded}")
        print(f"  Students skipped: {skipped}")
        print(f"  Predictions created: {predictions}")
        
        # Final count
        final_count = db.query(func.count(Student.id)).scalar()
        print(f"  Total students in database: {final_count}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
