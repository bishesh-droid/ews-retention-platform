import pandas as pd
import os
import json
import logging
from backend.ml.inference.predictor import predict_risk
from backend.ml.utils.validation_utils import (
    validate_and_clamp_probability,
    validate_and_clamp_risk_score,
    get_safe_default_prediction
)
from backend.services.core.decision_engine import (
    get_intervention_recommendation,
    should_trigger_intervention,
    calculate_intervention_priority
)

# Configure logger
logger = logging.getLogger(__name__)


def calculate_student_risk(student_data, include_decisions=False):
    """
    Calculate risk score for a single student using the ML model.
    
    This function ensures that a valid prediction is ALWAYS returned,
    using safe defaults if the ML model fails.
    
    Args:
        student_data: Dictionary with student information
        include_decisions: If True, include intervention recommendations
        
    Returns:
        Dictionary with risk score (0-100 percentage), signal breakdowns, and optional decisions.
        NEVER returns None - always returns a valid dictionary with safe defaults.
    """
    # Validate input
    if not student_data or not isinstance(student_data, dict):
        logger.warning(f"Invalid student_data: {type(student_data)}. Using safe defaults.")
        student_data = {}
    
    try:
        student_df = pd.DataFrame([student_data])
        result = predict_risk(student_df)
        
        # Check if prediction failed (should not happen with new predictor, but be safe)
        if not result or not isinstance(result, dict):
            logger.error("predict_risk returned invalid result. Using safe default.")
            result = get_safe_default_prediction()
        
        # Extract and validate risk_score (now in 0-100 percentage scale)
        risk_score = result.get('risk_score', 50.0)
        risk_score = validate_and_clamp_risk_score(
            risk_score, 
            default=50.0, 
            context="risk_score in calculate_student_risk"
        )
        
        # Calculate engagement score (heuristic based on student metrics)
        try:
            engagement_score = calculate_engagement_heuristic(student_data)
            engagement_score = validate_and_clamp_probability(
                engagement_score,
                default=0.5,
                context="engagement_score (probability)"
            )
            # Convert engagement to percentage for consistency
            engagement_score_pct = engagement_score * 100.0
        except Exception as eng_error:
            logger.warning(f"Engagement score calculation failed: {eng_error}. Using default 50.0")
            engagement_score_pct = 50.0
        
        # Determine retention likelihood category based on risk_score (0-100 scale)
        if risk_score < 30.0:
            retention_likelihood = "High"
        elif risk_score < 60.0:
            retention_likelihood = "Moderate"
        else:
            retention_likelihood = "Low"
        
        # Build response with validated values
        response = {
            'risk_score': round(risk_score, 2),  # Percentage 0-100
            'engagement_score': round(engagement_score_pct, 2),  # Percentage 0-100
            'retention_likelihood': retention_likelihood,
            'attendance': student_data.get('absrate7', 0.0),
            'assignments': student_data.get('q4mpa7', 0.0),
            'grades': student_data.get('q4mpa7', 0.0),
            'model_version': result.get('model_version', 'unknown'),
            'signal_breakdown': result.get('signal_breakdown', {}),  # Signals remain 0-1
            'top_risk_factors': result.get('top_risk_factors', []),
            'prediction_error': result.get('prediction_error', False)
        }
        
        # Add intervention recommendations if requested
        if include_decisions:
            try:
                intervention = get_intervention_recommendation(risk_score)
                priority = calculate_intervention_priority(risk_score)
                
                response['intervention_recommendation'] = {
                    'threshold_category': intervention['threshold_category'],
                    'action_type': intervention['action_type'],
                    'channels': intervention['channels'],
                    'assigned_team': intervention['assigned_team'],
                    'priority': priority,
                    'urgency': intervention['urgency'],
                    'description': intervention['description']
                }
            except Exception as decision_error:
                logger.error(f"Intervention recommendation failed: {decision_error}")
                response['intervention_recommendation'] = {
                    'threshold_category': 'unknown',
                    'action_type': 'no_action',
                    'channels': [],
                    'assigned_team': 'none',
                    'priority': 'low',
                    'urgency': 'none',
                    'description': 'Unable to generate recommendation'
                }
        
        return response
        
    except Exception as e:
        logger.error(f"Error calculating risk for student: {e}")
        import traceback
        traceback.print_exc()
        
        # Return safe default response instead of None
        logger.warning("Returning safe default response due to error")
        safe_default = get_safe_default_prediction()
        
        return {
            'risk_score': safe_default['risk_score'],
            'engagement_score': 0.5,
            'retention_likelihood': 'Unknown',
            'attendance': student_data.get('absrate7', 0.0) if student_data else 0.0,
            'assignments': student_data.get('q4mpa7', 0.0) if student_data else 0.0,
            'grades': student_data.get('q4mpa7', 0.0) if student_data else 0.0,
            'model_version': safe_default['model_version'],
            'signal_breakdown': safe_default['signal_breakdown'],
            'top_risk_factors': [],
            'prediction_error': True
        }


def calculate_engagement_heuristic(student_data):
    """Calculate a simple engagement score based on available metrics."""
    score = 0.0
    count = 0
    
    # Use absence rate (inverted)
    if 'absrate7' in student_data and student_data['absrate7'] is not None:
        score += (1 - min(student_data['absrate7'], 1.0))
        count += 1
    
    # Use GPA
    if 'q4mpa7' in student_data and student_data['q4mpa7'] is not None:
        score += (student_data['q4mpa7'] / 5.0)
        count += 1
    
    return score / count if count > 0 else 0.5


def batch_predict(students_data, include_decisions=False):
    """
    Generate predictions for multiple students.
    
    Args:
        students_data: List of student dictionaries
        include_decisions: If True, include intervention recommendations
        
    Returns:
        List of prediction dictionaries
    """
    predictions = []
    for student in students_data:
        prediction = calculate_student_risk(student, include_decisions=include_decisions)
        if prediction:
            prediction['student_id'] = student.get('id', 'unknown')
            predictions.append(prediction)
    return predictions


def get_signal_summary(predictions):
    """
    Aggregate signal scores across multiple students.
    
    Args:
        predictions: List of prediction dictionaries
        
    Returns:
        Dictionary with average scores per signal category
    """
    import numpy as np
    
    if not predictions:
        return {}
    
    signals = ['academic_signal_score', 'engagement_signal_score', 
               'consistency_signal_score', 'intent_signal_score', 
               'responsiveness_signal_score']
    
    summary = {}
    for signal in signals:
        scores = []
        for pred in predictions:
            if 'signal_breakdown' in pred and signal in pred['signal_breakdown']:
                scores.append(pred['signal_breakdown'][signal])
        
        if scores:
            summary[signal] = {
                'mean': round(np.mean(scores), 3),
                'median': round(np.median(scores), 3),
                'min': round(np.min(scores), 3),
                'max': round(np.max(scores), 3)
            }
    
    return summary
