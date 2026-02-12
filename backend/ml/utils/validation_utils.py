"""
Validation Utilities for Risk Score Pipeline
=============================================

Centralized validation functions to ensure:
- Risk scores are always in valid range [0, 100] (percentage scale)
- Signal scores are in valid range [0, 1] (probability scale)
- No NaN, Inf, or None values propagate through the system
- All validation failures are logged for debugging
- Safe defaults are provided when validation fails

IMPORTANT SCALE CONVENTION:
- risk_score: 0-100 (percentage, for end-user display)
- signal scores: 0-1 (probabilities, internal use)
"""

import numpy as np
import pandas as pd
import logging
from typing import Union, Dict, Any, Optional

# Configure logger
logger = logging.getLogger(__name__)


def validate_and_clamp_probability(
    value: Union[float, int, None], 
    default: float = 0.5,
    context: str = "probability"
) -> float:
    """
    Validate and clamp a value to ensure it's a valid probability in [0, 1].
    
    **Use this for SIGNAL SCORES only** (internal probabilities).
    For risk scores, use validate_and_clamp_risk_score() instead.
    
    Args:
        value: The value to validate (expected to be a probability)
        default: Default value to return if validation fails (default: 0.5 for neutral)
        context: Context string for logging (e.g., "academic_signal", "confidence")
    
    Returns:
        float: A valid probability in [0.0, 1.0]
    
    Examples:
        >>> validate_and_clamp_probability(0.75)
        0.75
        >>> validate_and_clamp_probability(-0.1)  # Logs warning, returns 0.0
        0.0
        >>> validate_and_clamp_probability(1.5)   # Logs warning, returns 1.0
        1.0
        >>> validate_and_clamp_probability(None)  # Logs warning, returns 0.5
        0.5
    """
    # Handle None
    if value is None:
        logger.warning(f"Invalid {context}: None value detected, using default: {default}")
        return max(0.0, min(1.0, float(default)))
    
    # Convert to float
    try:
        value_float = float(value)
    except (TypeError, ValueError) as e:
        logger.warning(f"Invalid {context}: Cannot convert to float: {value}, error: {e}, using default: {default}")
        return max(0.0, min(1.0, float(default)))
    
    # Check for NaN
    if np.isnan(value_float):
        logger.warning(f"Invalid {context}: NaN detected, using default: {default}")
        return max(0.0, min(1.0, float(default)))
    
    # Check for Infinity
    if np.isinf(value_float):
        logger.warning(f"Invalid {context}: Infinity detected ({value_float}), using default: {default}")
        return max(0.0, min(1.0, float(default)))
    
    # Clamp to [0, 1] range
    if value_float < 0.0:
        logger.warning(f"Invalid {context}: negative value {value_float} detected, clamping to 0.0")
        return 0.0
    
    if value_float > 1.0:
        logger.warning(f"Invalid {context}: value {value_float} > 1.0 detected, clamping to 1.0")
        return 1.0
    
    return value_float


def validate_and_clamp_risk_score(
    value: Union[float, int, None],
    default: float = 50.0,
    context: str = "risk_score"
) -> float:
    """
    Validate and clamp a value to ensure it's a valid risk score in [0, 100].
    
    **Use this for RISK SCORES** (percentage scale for end-user display).
    For signal scores, use validate_and_clamp_probability() instead.
    
    Args:
        value: The value to validate (expected to be a percentage 0-100)
        default: Default value to return if validation fails (default: 50.0 for neutral)
        context: Context string for logging (e.g., "risk_score", "engagement_score")
    
    Returns:
        float: A valid risk score in [0.0, 100.0]
    
    Examples:
        >>> validate_and_clamp_risk_score(75.5)
        75.5
        >>> validate_and_clamp_risk_score(-10)  # Logs warning, returns 0.0
        0.0
        >>> validate_and_clamp_risk_score(150)  # Logs warning, returns 100.0
        100.0
        >>> validate_and_clamp_risk_score(None)  # Logs warning, returns 50.0
        50.0
    """
    # Handle None
    if value is None:
        logger.warning(f"Invalid {context}: None value detected, using default: {default}")
        return max(0.0, min(100.0, float(default)))
    
    # Convert to float
    try:
        value_float = float(value)
    except (TypeError, ValueError) as e:
        logger.warning(f"Invalid {context}: Cannot convert to float: {value}, error: {e}, using default: {default}")
        return max(0.0, min(100.0, float(default)))
    
    # Check for NaN
    if np.isnan(value_float):
        logger.warning(f"Invalid {context}: NaN detected, using default: {default}")
        return max(0.0, min(100.0, float(default)))
    
    # Check for Infinity
    if np.isinf(value_float):
        logger.warning(f"Invalid {context}: Infinity detected ({value_float}), using default: {default}")
        return max(0.0, min(100.0, float(default)))
    
    # Clamp to [0, 100] range
    if value_float < 0.0:
        logger.warning(f"Invalid {context}: negative value {value_float} detected, clamping to 0.0")
        return 0.0
    
    if value_float > 100.0:
        logger.warning(f"Invalid {context}: value {value_float} > 100.0 detected, clamping to 100.0")
        return 100.0
    
    return value_float



def validate_student_features(features_df: pd.DataFrame) -> bool:
    """
    Validate that a feature DataFrame has no NaN or Inf values.
    
    Args:
        features_df: DataFrame with student features
    
    Returns:
        bool: True if all features are valid, False otherwise
    
    Side effects:
        Logs warnings for any invalid features found
    """
    if features_df is None or features_df.empty:
        logger.error("Feature validation failed: DataFrame is None or empty")
        return False
    
    # Check for NaN values
    nan_columns = features_df.columns[features_df.isna().any()].tolist()
    if nan_columns:
        logger.warning(f"Feature validation: NaN values found in columns: {nan_columns}")
        return False
    
    # Check for Inf values
    numeric_columns = features_df.select_dtypes(include=[np.number]).columns
    inf_columns = []
    for col in numeric_columns:
        if np.isinf(features_df[col]).any():
            inf_columns.append(col)
    
    if inf_columns:
        logger.warning(f"Feature validation: Inf values found in columns: {inf_columns}")
        return False
    
    return True


def sanitize_student_features(features_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and sanitize student features by replacing NaN/Inf with safe defaults.
    
    Args:
        features_df: DataFrame with student features (may contain NaN/Inf)
    
    Returns:
        pd.DataFrame: Sanitized DataFrame with no NaN/Inf values
    """
    if features_df is None or features_df.empty:
        logger.error("Cannot sanitize None or empty DataFrame")
        return features_df
    
    sanitized_df = features_df.copy()
    
    # Replace Inf with NaN first
    sanitized_df.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    # Fill NaN with median (or 0 if median is NaN)
    for col in sanitized_df.columns:
        if sanitized_df[col].isna().any():
            median_val = sanitized_df[col].median()
            fill_value = median_val if not np.isnan(median_val) else 0.0
            sanitized_df[col].fillna(fill_value, inplace=True)
            logger.info(f"Sanitized column '{col}': filled NaN with {fill_value}")
    
    return sanitized_df


def validate_risk_score_dict(result: Dict[str, Any]) -> bool:
    """
    Validate an entire risk prediction result dictionary.
    
    Args:
        result: Dictionary containing risk prediction results
    
    Returns:
        bool: True if all required fields are valid, False otherwise
    
    Expected keys:
        - risk_score: float in [0, 100]  # PERCENTAGE SCALE
        - prediction: int (0 or 1)
        - signal_breakdown: dict with scores in [0, 1]  # PROBABILITY SCALE
    """
    if result is None:
        logger.error("Risk score validation failed: result is None")
        return False
    
    if not isinstance(result, dict):
        logger.error(f"Risk score validation failed: result is not a dict, got {type(result)}")
        return False
    
    # Validate risk_score (0-100 scale)
    if 'risk_score' not in result:
        logger.error("Risk score validation failed: 'risk_score' key missing")
        return False
    
    risk_score = result['risk_score']
    if not isinstance(risk_score, (int, float)):
        logger.error(f"Risk score validation failed: risk_score is not numeric, got {type(risk_score)}")
        return False
    
    if np.isnan(risk_score) or np.isinf(risk_score):
        logger.error(f"Risk score validation failed: risk_score is NaN or Inf: {risk_score}")
        return False
    
    if risk_score < 0.0 or risk_score > 100.0:
        logger.error(f"Risk score validation failed: risk_score out of range [0, 100]: {risk_score}")
        return False
    
    # Validate signal_breakdown if present (0-1 scale)
    if 'signal_breakdown' in result:
        signals = result['signal_breakdown']
        if signals and isinstance(signals, dict):
            for signal_name, signal_value in signals.items():
                if not isinstance(signal_value, (int, float)):
                    logger.warning(f"Signal '{signal_name}' is not numeric: {signal_value}")
                    continue
                
                if np.isnan(signal_value) or np.isinf(signal_value):
                    logger.warning(f"Signal '{signal_name}' is NaN or Inf: {signal_value}")
                    return False
                
                if signal_value < 0.0 or signal_value > 1.0:
                    logger.warning(f"Signal '{signal_name}' out of range [0, 1]: {signal_value}")
                    return False
    
    return True


def sanitize_risk_score_dict(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize a risk prediction result dictionary by clamping all values.
    
    Args:
        result: Dictionary containing risk prediction results
    
    Returns:
        Dict[str, Any]: Sanitized result dictionary with all values in valid ranges
    """
    if result is None or not isinstance(result, dict):
        logger.error("Cannot sanitize invalid result dictionary")
        return get_safe_default_prediction()
    
    sanitized = result.copy()
    
    # Sanitize risk_score (0-100 scale)
    if 'risk_score' in sanitized:
        sanitized['risk_score'] = validate_and_clamp_risk_score(
            sanitized['risk_score'], 
            default=50.0, 
            context="risk_score"
        )
    else:
        logger.warning("risk_score missing from result, adding default")
        sanitized['risk_score'] = 50.0
    
    # Sanitize signal_breakdown (0-1 scale)
    if 'signal_breakdown' in sanitized and isinstance(sanitized['signal_breakdown'], dict):
        for signal_name in sanitized['signal_breakdown']:
            sanitized['signal_breakdown'][signal_name] = validate_and_clamp_probability(
                sanitized['signal_breakdown'][signal_name],
                default=0.5,
                context=f"signal_breakdown.{signal_name}"
            )
    
    return sanitized


def get_safe_default_prediction() -> Dict[str, Any]:
    """
    Return a safe default prediction when prediction fails completely.
    
    Returns:
        Dict[str, Any]: Safe default prediction with neutral risk score
    """
    return {
        'risk_score': 50.0,  # Neutral risk (PERCENTAGE SCALE 0-100)
        'prediction': 0,     # Assume retained
        'model_version': 'fallback_default_v1.0',
        'signal_breakdown': {
            'academic_signal_score': 0.5,
            'engagement_signal_score': 0.5,
            'consistency_signal_score': 0.5,
            'intent_signal_score': 0.5,
            'responsiveness_signal_score': 0.5
        },
        'top_risk_factors': [],
        'prediction_error': True
    }


def validate_student_data(student_data: Union[pd.DataFrame, Dict[str, Any]]) -> bool:
    """
    Validate student data before passing to prediction pipeline.
    
    Args:
        student_data: Student data as DataFrame or dict
    
    Returns:
        bool: True if valid, False otherwise
    """
    if student_data is None:
        logger.error("Student data validation failed: data is None")
        return False
    
    if isinstance(student_data, pd.DataFrame):
        if student_data.empty:
            logger.error("Student data validation failed: DataFrame is empty")
            return False
    elif isinstance(student_data, dict):
        if not student_data:
            logger.error("Student data validation failed: dict is empty")
            return False
    else:
        logger.error(f"Student data validation failed: invalid type {type(student_data)}")
        return False
    
    return True
