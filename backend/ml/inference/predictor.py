import pandas as pd
import numpy as np
import joblib
import os
import logging
from backend.ml.features.feature_engineering import create_features
from backend.ml.models.model_registry import ModelRegistry
from backend.ml.config import DEFAULT_MODEL_NAME
from backend.ml.utils.validation_utils import (
    validate_and_clamp_probability,
    validate_student_features,
    sanitize_student_features,
    validate_risk_score_dict,
    sanitize_risk_score_dict,
    get_safe_default_prediction,
    validate_student_data
)
from backend.ml.inference.risk_formula import (
    explain_risk_score,
    get_risk_contribution_breakdown,
    simulate_what_if
)

# Configure logger
logger = logging.getLogger(__name__)

model = None
model_type = None


def load_model():
    """Load the trained model via Registry"""
    global model, model_type
    try:
        model = ModelRegistry.load_model()
        # Basic heuristic to guess type if not stored, primarily for metadata
        model_type = "xgboost" if "xgboost" in str(type(model)).lower() else "random_forest"
        print(f"Model loaded successfully via Registry: {model_type}")
    except Exception as e:
        print(f"Error loading model: {e}")
        model = None


def compute_signal_scores(features_df):
    """
    Compute signal-level scores from engineered features
    
    Returns signal breakdown (0-1 scale):
    - academic_signal_score
    - engagement_signal_score
    - consistency_signal_score
    - intent_signal_score
    - responsiveness_signal_score
    """
    # Map features to signal categories
    # These are based on the feature names from create_features()
    
    # Academic: mpa_avg (GPA), absrate_avg (inversed)
    academic_features = [col for col in features_df.columns if 'mpa_avg' in col]
    absrate_features = [col for col in features_df.columns if 'absrate_avg' in col]
    
    # Engagement: derived from mpa and activity trends
    engagement_features = [col for col in features_df.columns if 'trend' in col and 'mpa' in col]
    
    # Consistency: absrate (inversed), mobility
    consistency_features = [col for col in features_df.columns if 'mobility' in col]
    
    # Intent: declining trends (negative slopes)
    intent_features = [col for col in features_df.columns if 'trend' in col]
    
    # Responsiveness: suspension data as proxy (inversed)
    responsiveness_features = [col for col in features_df.columns if 'nsusp' in col]
    
    # Calculate signal scores (normalize to 0-1)
    def normalize_score(values):
        """Normalize values to 0-1 range"""
        if len(values) == 0:
            return 0.5
        mean_val = np.mean(values)
        # Clamp to 0-1
        return max(0.0, min(1.0, mean_val))
    
    # Academic: Higher GPA = lower risk
    academic_vals = []
    if academic_features:
        academic_vals.extend(features_df[academic_features].values[0])
    academic_vals = [v/5.0 for v in academic_vals if not np.isnan(v)]  # Normalize GPA to 0-1
    academic_score = 1.0 - normalize_score(academic_vals)  # Invert: high GPA = low risk
    
    # Engagement: Positive trends = lower risk
    engagement_vals = []
    if engagement_features:
        engagement_vals.extend(features_df[engagement_features].values[0])
    engagement_vals = [abs(v) for v in engagement_vals if not np.isnan(v)]
    engagement_score = normalize_score(engagement_vals)
    
    # Consistency: Low absrate, low mobility = lower risk
    consistency_vals = []
    if absrate_features:
        consistency_vals.extend(features_df[absrate_features].values[0])
    if consistency_features:
        consistency_vals.extend(features_df[consistency_features].values[0])
    consistency_vals = [v for v in consistency_vals if not np.isnan(v)]
    consistency_score = normalize_score(consistency_vals)
    
    # Intent: Declining trends = higher risk
    intent_vals = []
    if intent_features:
        intent_vals.extend(features_df[intent_features].values[0])
    # Negative trends indicate declining performance
    declining_trends = [abs(min(0, v)) for v in intent_vals if not np.isnan(v)]
    intent_score = normalize_score(declining_trends)
    
    # Responsiveness: Low suspensions = lower risk
    responsiveness_vals = []
    if responsiveness_features:
        responsiveness_vals.extend(features_df[responsiveness_features].values[0])
    responsiveness_vals = [v for v in responsiveness_vals if not np.isnan(v)]
    responsiveness_score = normalize_score(responsiveness_vals)
    
    return {
        "academic_signal_score": round(academic_score, 3),
        "engagement_signal_score": round(engagement_score, 3),
        "consistency_signal_score": round(consistency_score, 3),
        "intent_signal_score": round(intent_score, 3),
        "responsiveness_signal_score": round(responsiveness_score, 3)
    }


def get_top_risk_factors(features_df, n=5):
    """
    Get top N risk factors based on feature values
    """
    # Simple heuristic: features with highest absolute values
    feature_values = {}
    for col in features_df.columns:
        val = features_df[col].values[0]
        if not np.isnan(val):
            feature_values[col] = abs(val)
    
    # Sort by value
    sorted_features = sorted(feature_values.items(), key=lambda x: x[1], reverse=True)
    
    top_factors = []
    for feature, value in sorted_features[:n]:
        top_factors.append({
            "feature": feature,
            "value": float(value),
            "contribution": float(value / max(feature_values.values(), default=1))
        })
    
    return top_factors


def predict_risk(student_data_df):
    """
    Predict dropout risk for a student with comprehensive validation.
    
    This function includes multiple safety layers:
    1. Input validation
    2. Feature validation and sanitization
    3. Model output validation and clamping
    4. Safe default fallback on errors
    
    Returns:
        Dictionary with:
        - risk_score: Overall risk (0-1, guaranteed valid)
        - prediction: Binary prediction (0=retained, 1=at risk)
        - signal_breakdown: Dict of signal scores (all 0-1)
        - top_risk_factors: List of top contributing features
        - prediction_error: Boolean flag (True if using fallback)
    
    GUARANTEE: risk_score will ALWAYS be in [0.0, 1.0], never NaN, Inf, or negative
    """
    # Validate model is loaded
    if model is None:
        logger.error("Model is not loaded. Cannot make predictions. Returning safe default.")
        return get_safe_default_prediction()
    
    # Validate input data
    if not validate_student_data(student_data_df):
        logger.error("Invalid student data. Returning safe default.")
        return get_safe_default_prediction()
    
    try:
        # Create features
        features_df = create_features(student_data_df)
        
        if features_df is None or features_df.empty:
            logger.error("Feature engineering returned empty DataFrame. Returning safe default.")
            return get_safe_default_prediction()
        
        X = features_df.drop('nograd', axis=1, errors='ignore')
        
        # Validate features - if invalid, try to sanitize
        if not validate_student_features(X):
            logger.warning("Features contain NaN/Inf. Attempting to sanitize...")
            X = sanitize_student_features(X)
            
            # Re-validate after sanitization
            if not validate_student_features(X):
                logger.error("Feature sanitization failed. Returning safe default.")
                return get_safe_default_prediction()
        
        # Get prediction from model
        try:
            risk_probability_array = model.predict_proba(X)[:, 1]
            binary_prediction_array = model.predict(X)
            
            # Extract scalar values
            risk_probability = risk_probability_array[0]
            binary_prediction = binary_prediction_array[0]
            
        except Exception as model_error:
            logger.error(f"Model prediction failed: {model_error}. Returning safe default.")
            return get_safe_default_prediction()
        
        # Validate and clamp risk probability
        risk_score = validate_and_clamp_probability(
            risk_probability, 
            default=0.5, 
            context="risk_score from model.predict_proba"
        )
        
        # Compute signal breakdowns
        try:
            signal_scores = compute_signal_scores(X)
            
            # Validate each signal score
            for signal_name, signal_value in signal_scores.items():
                signal_scores[signal_name] = validate_and_clamp_probability(
                    signal_value,
                    default=0.5,
                    context=f"signal_breakdown.{signal_name}"
                )
        except Exception as signal_error:
            logger.warning(f"Signal computation failed: {signal_error}. Using neutral defaults.")
            signal_scores = {
                'academic_signal_score': 0.5,
                'engagement_signal_score': 0.5,
                'consistency_signal_score': 0.5,
                'intent_signal_score': 0.5,
                'responsiveness_signal_score': 0.5
            }
        
        # Get top risk factors
        try:
            top_factors = get_top_risk_factors(X, n=5)
        except Exception as factors_error:
            logger.warning(f"Top risk factors computation failed: {factors_error}. Using empty list.")
            top_factors = []
        
        # Validate binary prediction
        try:
            prediction_int = int(binary_prediction)
            if prediction_int not in [0, 1]:
                logger.warning(f"Invalid binary prediction {prediction_int}, using threshold-based fallback")
                prediction_int = 1 if risk_score >= 0.5 else 0
        except (TypeError, ValueError) as pred_error:
            logger.warning(f"Binary prediction conversion failed: {pred_error}. Using threshold-based fallback.")
            prediction_int = 1 if risk_score >= 0.5 else 0
        
        # Construct result
        result = {
            'risk_score': risk_score,
            'prediction': prediction_int,
            'model_version': f"{model_type}_v1.0" if model_type else "unknown_v1.0",
            'signal_breakdown': signal_scores,
            'top_risk_factors': top_factors,
            'prediction_error': False
        }
        
        # Final validation of complete result
        if not validate_risk_score_dict(result):
            logger.error("Final validation failed. Sanitizing result...")
            result = sanitize_risk_score_dict(result)
        
        logger.info(f"Prediction successful. Risk score: {result['risk_score']:.3f}")
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error during prediction: {e}")
        import traceback
        traceback.print_exc()
        logger.error("Returning safe default prediction due to unexpected error.")
        return get_safe_default_prediction()


def predict_with_explanation(student_data_df):
    """
    Predict dropout risk with full explainable breakdown.

    This extends predict_risk() with:
    - Human-readable risk explanation
    - Contribution breakdown per signal
    - Category classification

    Returns:
        Dictionary with all predict_risk() fields plus:
        - explanation: Human-readable explanation
        - contribution_breakdown: Detailed breakdown per signal
        - risk_category: 'low', 'moderate', 'high', 'critical'
    """
    # Get base prediction
    prediction = predict_risk(student_data_df)

    if prediction.get('prediction_error'):
        # Don't try to explain errors
        prediction['explanation'] = "Unable to generate risk explanation due to prediction error."
        prediction['contribution_breakdown'] = []
        prediction['risk_category'] = 'unknown'
        return prediction

    # Add explainable breakdown
    try:
        explanation = explain_risk_score(
            prediction['risk_score'],
            prediction['signal_breakdown']
        )
        prediction['explanation'] = explanation['explanation']
        prediction['contribution_breakdown'] = explanation['breakdown']
        prediction['risk_category'] = explanation['risk_category']
        prediction['category_description'] = explanation['category_description']
        prediction['top_contributing_factors'] = explanation['top_factors']
    except Exception as e:
        logger.warning(f"Could not generate explanation: {e}")
        prediction['explanation'] = f"Risk score is {prediction['risk_score']*100:.0f}%."
        prediction['contribution_breakdown'] = []
        prediction['risk_category'] = 'unknown'

    return prediction


def simulate_risk_change(student_data_df, adjustments: dict):
    """
    Simulate how risk would change if certain signals improved.

    Args:
        student_data_df: Student data
        adjustments: Dict of signal adjustments, e.g.,
            {'academic_signal_score': 0.3} to simulate improved academics

    Returns:
        What-if simulation results
    """
    # Get current prediction
    current = predict_risk(student_data_df)

    if current.get('prediction_error'):
        return {
            'error': True,
            'message': 'Could not simulate - base prediction failed'
        }

    # Run what-if simulation
    try:
        simulation = simulate_what_if(
            current['signal_breakdown'],
            adjustments
        )
        return simulation
    except Exception as e:
        logger.error(f"What-if simulation failed: {e}")
        return {
            'error': True,
            'message': str(e)
        }


# Load model on module import
load_model()


if __name__ == '__main__':
    import numpy as np
    
    if model:
        print("\n--- Running Prediction Test ---")
        
        # Create sample student data
        sample_data = {
            'id': ['test_student_1'],
            'nograd': [0]
        }
        
        for year in range(1, 8):
            sample_data[f'absrate{year}'] = [np.random.uniform(0, 1)]
            sample_data[f'nsusp{year}'] = [np.random.randint(0, 3)]
            sample_data[f'mobility{year}'] = [np.random.randint(0, 2)]
            for q in range(1, 5):
                sample_data[f'q{q}mpa{year}'] = [np.random.uniform(2, 5)]
        
        sample_df = pd.DataFrame(sample_data)
        
        # Make prediction
        prediction_result = predict_risk(sample_df)
        
        if prediction_result:
            print(f"\nPrediction for test student:")
            print(f"  Risk Score: {prediction_result['risk_score']:.3f}")
            print(f"  Prediction (0=On Track, 1=At Risk): {prediction_result['prediction']}")
            print(f"  Model Version: {prediction_result['model_version']}")
            print(f"\nSignal Breakdown:")
            for signal, score in prediction_result['signal_breakdown'].items():
                print(f"  {signal}: {score:.3f}")
            print(f"\nTop Risk Factors:")
            for i, factor in enumerate(prediction_result['top_risk_factors'], 1):
                print(f"  {i}. {factor['feature']}: {factor['value']:.3f} (contribution: {factor['contribution']:.2%})")
    else:
        print("\nSkipping prediction test because model is not loaded.")

