/**
 * Risk Score Validation Utilities
 * =================================
 * 
 * Frontend validation functions to ensure risk scores are always displayed
 * in valid range and never show invalid values like -1%.
 */

/**
 * Validate and clamp a risk score to valid range [0, 100]
 * 
 * @param {number|null|undefined} score - Risk score to validate (expected 0-100)
 * @param {number} defaultValue - Default value if validation fails (default: 50)
 * @returns {number} Valid risk score in range [0, 100]
 * 
 * @example
 * validateRiskScore(75) // Returns 75
 * validateRiskScore(-1) // Returns 0 (clamped)
 * validateRiskScore(null) // Returns 50 (default)
 * validateRiskScore(150) // Returns 100 (clamped)
 */
export const validateRiskScore = (score, defaultValue = 50) => {
    // Handle null/undefined
    if (score === null || score === undefined) {
        console.warn(`Invalid risk score: ${score}, using default: ${defaultValue}`);
        return defaultValue;
    }

    // Handle NaN
    if (isNaN(score)) {
        console.warn(`Invalid risk score (NaN), using default: ${defaultValue}`);
        return defaultValue;
    }

    // Convert to number
    const numScore = Number(score);

    // Handle Infinity
    if (!isFinite(numScore)) {
        console.warn(`Invalid risk score (Infinity), using default: ${defaultValue}`);
        return defaultValue;
    }

    // Clamp to [0, 100] range
    if (numScore < 0) {
        console.warn(`Negative risk score ${numScore} detected, clamping to 0`);
        return 0;
    }

    if (numScore > 100) {
        console.warn(`Risk score ${numScore} > 100 detected, clamping to 100`);
        return 100;
    }

    return Math.round(numScore);
};

/**
 * Validate a prediction object has all required fields with valid values
 * 
 * @param {object} prediction - Prediction object to validate
 * @returns {boolean} True if prediction is valid, false otherwise
 */
export const isValidPrediction = (prediction) => {
    if (!prediction || typeof prediction !== 'object') {
        return false;
    }

    // Check risk_score exists and is valid
    if (!('risk_score' in prediction)) {
        return false;
    }

    const riskScore = prediction.risk_score;

    // Reject invalid risk scores
    if (riskScore === null || riskScore === undefined || isNaN(riskScore) || !isFinite(riskScore)) {
        return false;
    }

    // Reject out-of-range risk scores (allow small tolerance for backend 0-1 values)
    const numScore = Number(riskScore);
    if (numScore < -0.01 || numScore > 100.1) {
        return false;
    }

    return true;
};

/**
 * Get a safe default prediction when prediction is missing or invalid
 * 
 * @returns {object} Safe default prediction object
 */
export const getSafeDefaultPrediction = () => ({
    risk_score: 50,  // Neutral risk
    risk_score_raw: 0.5,
    risk_level: 'unknown',
    retention_prediction: 'Unknown',
    engagement_score: 50,
    prediction_available: false,
    prediction_error: true,
    signal_breakdown: {
        academic_signal_score: 0.5,
        engagement_signal_score: 0.5,
        consistency_signal_score: 0.5,
        intent_signal_score: 0.5,
        responsiveness_signal_score: 0.5
    }
});

/**
 * Convert backend probability (0-1) to frontend percentage (0-100)
 * 
 * @param {number} probability - Probability value from backend (0-1)
 * @returns {number} Percentage value for frontend display (0-100)
 */
export const probabilityToPercentage = (probability) => {
    if (probability === null || probability === undefined || isNaN(probability)) {
        console.warn(`Invalid probability: ${probability}, returning 50%`);
        return 50;
    }

    const num = Number(probability);

    // If value is already in percentage range (> 1), assume it's already a percentage
    if (num > 1) {
        return validateRiskScore(num);
    }

    // Convert 0-1 to 0-100
    return validateRiskScore(num * 100);
};

/**
 * Sanitize a prediction object by validating and fixing all risk scores
 * 
 * @param {object} prediction - Prediction object (may have invalid values)
 * @returns {object} Sanitized prediction object with all valid values
 */
export const sanitizePrediction = (prediction) => {
    if (!prediction || typeof prediction !== 'object') {
        console.warn('Invalid prediction object, using safe default');
        return getSafeDefaultPrediction();
    }

    const sanitized = { ...prediction };

    // Sanitize risk_score
    if ('risk_score' in sanitized) {
        sanitized.risk_score = validateRiskScore(sanitized.risk_score);
    } else {
        sanitized.risk_score = 50;
    }

    // Sanitize engagement_score
    if ('engagement_score' in sanitized) {
        sanitized.engagement_score = validateRiskScore(sanitized.engagement_score);
    }

    // Ensure prediction_available flag exists
    if (!('prediction_available' in sanitized)) {
        sanitized.prediction_available = true;
    }

    // Sanitize signal_breakdown if present
    if (sanitized.signal_breakdown && typeof sanitized.signal_breakdown === 'object') {
        const signals = sanitized.signal_breakdown;
        Object.keys(signals).forEach(key => {
            // Signals are 0-1, convert to 0-100 for display
            signals[key] = probabilityToPercentage(signals[key]);
        });
    }

    return sanitized;
};
