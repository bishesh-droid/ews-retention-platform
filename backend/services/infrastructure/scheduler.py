"""
Scheduler Service
Automates daily/weekly tasks:
- Feature computation
- Risk prediction generation
- Model retraining
"""

import schedule
import time
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database import SessionLocal, Student
from services.feature_service import compute_all_features
from models.predict import predict_risk
from models.train_model import train_and_save_model
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def compute_features_for_all_students():
    """
    Daily job: Compute engineered features forall students
    """
    logger.info("[SCHEDULER] Starting daily feature computation...")
    db = SessionLocal()
    
    try:
        students = db.query(Student).all()
        success_count = 0
        failure_count = 0
        
        for student in students:
            try:
                features = compute_all_features(student.id, db)
                if features:
                    db.add(features)
                    success_count += 1
                else:
                    failure_count += 1
            except Exception as e:
                logger.error(f"Failed to compute features for student {student.id}: {e}")
                failure_count += 1
        
        db.commit()
        logger.info(f"[SCHEDULER] Feature computation complete. Success: {success_count}, Failed: {failure_count}")
    
    except Exception as e:
        logger.error(f"[SCHEDULER] Feature computation job failed: {e}")
        db.rollback()
    finally:
        db.close()


def generate_daily_predictions():
    """
    Daily job: Generate risk predictions for all students
    """
    logger.info("[SCHEDULER] Starting daily risk prediction generation...")
    db = SessionLocal()
    
    try:
        from database import Prediction
        students = db.query(Student).all()
        success_count = 0
        
        for student in students:
            try:
                from services.ews_engine import calculate_student_risk
                student_data = {
                    'id': student.id,
                    'absrate7': student.absrate7,
                    'q4mpa7': student.q4mpa7,
                    'nsusp7': student.nsusp7,
                    'mobility7': student.mobility7,
                }
                
                prediction = calculate_student_risk(student_data, include_decisions=False)
                
                if prediction:
                    # Save prediction to database
                    db_prediction = Prediction(
                        student_id=student.id,
                        risk_score=prediction['risk_score'],
                        engagement_score=prediction['engagement_score'],
                        retention_likelihood=prediction['retention_likelihood'],
                        attendance=prediction['attendance'],
                        assignments=prediction['assignments'],
                        grades=prediction['grades'],
                        model_version=prediction.get('model_version'),
                        prediction_timestamp=datetime.utcnow()
                    )
                    
                    # Add signal breakdowns if available
                    if 'signal_breakdown' in prediction:
                        signals = prediction['signal_breakdown']
                        db_prediction.academic_signal_score = signals.get('academic_signal_score')
                        db_prediction.engagement_signal_score = signals.get('engagement_signal_score')
                        db_prediction.consistency_signal_score = signals.get('consistency_signal_score')
                        db_prediction.intent_signal_score = signals.get('intent_signal_score')
                        db_prediction.responsiveness_signal_score = signals.get('responsiveness_signal_score')
                    
                    db.add(db_prediction)
                    success_count += 1
            
            except Exception as e:
                logger.error(f"Failed to generate prediction for student {student.id}: {e}")
        
        db.commit()
        logger.info(f"[SCHEDULER] Prediction generation complete. Generated {success_count} predictions.")
    
    except Exception as e:
        logger.error(f"[SCHEDULER] Prediction generation job failed: {e}")
        db.rollback()
    finally:
        db.close()


def retrain_model_weekly():
    """
    Weekly job: Retrain ML model with feedback loop data
    """
    logger.info("[SCHEDULER] Starting weekly model retraining...")
    
    try:
        # Use student data path
        data_path = 'frontend/public/data/student_data_test.csv'
        
        # Train XGBoost model
        train_and_save_model(data_path, use_xgboost=True)
        
        logger.info("[SCHEDULER] Model retraining complete!")
    
    except Exception as e:
        logger.error(f"[SCHEDULER] Model retraining failed: {e}")


def start_scheduler():
    """
    Initialize and start the scheduler
    """
    logger.info("[SCHEDULER] Initializing scheduled jobs...")
    
    # Daily jobs at 2 AM
    schedule.every().day.at("02:00").do(compute_features_for_all_students)
    schedule.every().day.at("03:00").do(generate_daily_predictions)
    
    # Weekly job on Sunday at 4 AM
    schedule.every().sunday.at("04:00").do(retrain_model_weekly)
    
    logger.info("[SCHEDULER] Scheduled jobs:")
    logger.info("  - Feature computation: Daily at 02:00")
    logger.info("  - Prediction generation: Daily at 03:00")
    logger.info("  - Model retraining: Weekly on Sunday at 04:00")
    
    # Run scheduler loop
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute


if __name__ == "__main__":
    logger.info("[SCHEDULER] Starting scheduler service...")
    start_scheduler()
