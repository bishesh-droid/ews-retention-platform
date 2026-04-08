/**
 * Risk Threshold Constants
 *
 * Centralized configuration for risk categorization.
 * These match the backend INTERVENTION_THRESHOLDS in backend/config/__init__.py
 */

// Intervention thresholds (0-100 scale) - synced with backend
export const RISK_THRESHOLDS = {
  NO_ACTION: 30,    // matches THRESHOLD_NO_ACTION in config
  GENTLE: 40,       // matches THRESHOLD_GENTLE
  MENTOR: 60,       // matches THRESHOLD_MENTOR
  URGENT: 80,       // matches THRESHOLD_URGENT
};

/**
 * Get risk category with label and color based on score.
 * Matches backend intervention threshold logic.
 */
export const getRiskCategory = (score) => {
  if (score >= RISK_THRESHOLDS.URGENT) return { label: "Critical", color: "danger" };
  if (score >= RISK_THRESHOLDS.MENTOR) return { label: "High", color: "warning" };
  if (score >= RISK_THRESHOLDS.GENTLE) return { label: "Medium", color: "info" };
  if (score >= RISK_THRESHOLDS.NO_ACTION) return { label: "Watch", color: "secondary" };
  return { label: "On track", color: "success" };
};

/**
 * Get intervention type from risk score.
 * Maps to the backend intervention decision logic.
 */
export const getInterventionType = (riskScore) => {
  if (riskScore < RISK_THRESHOLDS.NO_ACTION) return 'no_action';
  if (riskScore < RISK_THRESHOLDS.GENTLE) return 'gentle_reminder';
  if (riskScore < RISK_THRESHOLDS.MENTOR) return 'mentor_outreach';
  return 'urgent_intervention';
};

// Legacy exports for backward compatibility during transition
export const INTERVENTION_THRESHOLDS = {
  NO_ACTION: RISK_THRESHOLDS.NO_ACTION,
  GENTLE_REMINDER: RISK_THRESHOLDS.GENTLE,
  MENTOR_OUTREACH: RISK_THRESHOLDS.MENTOR,
  URGENT: RISK_THRESHOLDS.URGENT,
};

export default {
    RISK_THRESHOLDS,
    INTERVENTION_THRESHOLDS,
    getRiskCategory,
    getInterventionType
};
