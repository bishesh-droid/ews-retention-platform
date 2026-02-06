/**
 * Risk Threshold Constants
 *
 * Centralized configuration for risk categorization.
 * These should match the backend configuration in backend/config.py
 */

// Risk score thresholds (0-100 scale for frontend)
export const RISK_THRESHOLDS = {
    CRITICAL: 85,    // >= 85% = Critical risk
    HIGH: 70,        // >= 70% = High risk
    MODERATE: 40,    // >= 40% = Moderate risk
    LOW: 0           // < 40% = Low risk
};

// Intervention thresholds (0-100 scale)
export const INTERVENTION_THRESHOLDS = {
    NO_ACTION: 30,        // < 30% = No intervention needed
    GENTLE_REMINDER: 60,  // 30-60% = Automated email reminder
    MENTOR_OUTREACH: 80,  // 60-80% = Faculty mentor outreach
    URGENT: 80            // >= 80% = Urgent sales intervention
};

// Risk category definitions
export const RISK_CATEGORIES = {
    CRITICAL: {
        key: 'critical',
        label: 'Critical',
        description: 'Immediate attention required',
        color: '#DC2626',
        bgColor: 'rgba(220, 38, 38, 0.1)',
        threshold: RISK_THRESHOLDS.CRITICAL
    },
    HIGH: {
        key: 'high',
        label: 'High Risk',
        description: 'Significant risk of dropout',
        color: '#F59E0B',
        bgColor: 'rgba(245, 158, 11, 0.1)',
        threshold: RISK_THRESHOLDS.HIGH
    },
    MODERATE: {
        key: 'moderate',
        label: 'Moderate',
        description: 'Some warning signs present',
        color: '#FBBF24',
        bgColor: 'rgba(251, 191, 36, 0.1)',
        threshold: RISK_THRESHOLDS.MODERATE
    },
    LOW: {
        key: 'low',
        label: 'Low Risk',
        description: 'On track for success',
        color: '#10B981',
        bgColor: 'rgba(16, 185, 129, 0.1)',
        threshold: RISK_THRESHOLDS.LOW
    }
};

// Helper function to get category from risk score
export const getRiskCategory = (riskScore) => {
    if (riskScore >= RISK_THRESHOLDS.CRITICAL) return RISK_CATEGORIES.CRITICAL;
    if (riskScore >= RISK_THRESHOLDS.HIGH) return RISK_CATEGORIES.HIGH;
    if (riskScore >= RISK_THRESHOLDS.MODERATE) return RISK_CATEGORIES.MODERATE;
    return RISK_CATEGORIES.LOW;
};

// Helper function to get intervention type from risk score
export const getInterventionType = (riskScore) => {
    if (riskScore < INTERVENTION_THRESHOLDS.NO_ACTION) return 'no_action';
    if (riskScore < INTERVENTION_THRESHOLDS.GENTLE_REMINDER) return 'gentle_reminder';
    if (riskScore < INTERVENTION_THRESHOLDS.MENTOR_OUTREACH) return 'mentor_outreach';
    return 'urgent_intervention';
};

export default {
    RISK_THRESHOLDS,
    INTERVENTION_THRESHOLDS,
    RISK_CATEGORIES,
    getRiskCategory,
    getInterventionType
};
