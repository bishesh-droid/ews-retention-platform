import { useState, useCallback, useMemo } from 'react';
import { useStudentData } from '../context/StudentContext';
import { validateRiskScore, sanitizePrediction } from '../utils/riskScoreValidator';
import { getStudentDetails, getMLPrediction } from '../services/api';

/**
 * Custom hook for student risk-related operations
 *
 * Provides:
 * - Risk score retrieval and validation
 * - Risk category classification
 * - Risk change detection
 * - What-if simulation
 */

export const RISK_CATEGORIES = {
    CRITICAL: { min: 85, label: 'Critical', color: '#DC2626' },
    HIGH: { min: 70, label: 'High Risk', color: '#F59E0B' },
    MODERATE: { min: 40, label: 'Moderate', color: '#FBBF24' },
    LOW: { min: 0, label: 'Low Risk', color: '#10B981' }
};

export const useStudentRisk = (studentId = null) => {
    const { students } = useStudentData();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Get student by ID
    const student = useMemo(() => {
        if (!studentId) return null;
        return students.find(s => s.id === parseInt(studentId)) || null;
    }, [students, studentId]);

    // Get validated risk score
    const riskScore = useMemo(() => {
        if (!student) return null;
        return validateRiskScore(student.risk_score, 50);
    }, [student]);

    // Get risk category
    const riskCategory = useMemo(() => {
        if (riskScore === null) return null;

        if (riskScore >= RISK_CATEGORIES.CRITICAL.min) return RISK_CATEGORIES.CRITICAL;
        if (riskScore >= RISK_CATEGORIES.HIGH.min) return RISK_CATEGORIES.HIGH;
        if (riskScore >= RISK_CATEGORIES.MODERATE.min) return RISK_CATEGORIES.MODERATE;
        return RISK_CATEGORIES.LOW;
    }, [riskScore]);

    // Categorize a risk score
    const categorizeRisk = useCallback((score) => {
        const validScore = validateRiskScore(score, 50);
        if (validScore >= RISK_CATEGORIES.CRITICAL.min) return RISK_CATEGORIES.CRITICAL;
        if (validScore >= RISK_CATEGORIES.HIGH.min) return RISK_CATEGORIES.HIGH;
        if (validScore >= RISK_CATEGORIES.MODERATE.min) return RISK_CATEGORIES.MODERATE;
        return RISK_CATEGORIES.LOW;
    }, []);

    // Get students by risk category
    const getStudentsByCategory = useCallback((category) => {
        return students.filter(s => {
            const score = validateRiskScore(s.risk_score, 50);
            const studentCategory = categorizeRisk(score);
            return studentCategory.label === category.label;
        });
    }, [students, categorizeRisk]);

    // Get risk distribution
    const riskDistribution = useMemo(() => {
        const distribution = {
            critical: 0,
            high: 0,
            moderate: 0,
            low: 0
        };

        students.forEach(s => {
            const score = validateRiskScore(s.risk_score, 50);
            if (score >= RISK_CATEGORIES.CRITICAL.min) distribution.critical++;
            else if (score >= RISK_CATEGORIES.HIGH.min) distribution.high++;
            else if (score >= RISK_CATEGORIES.MODERATE.min) distribution.moderate++;
            else distribution.low++;
        });

        return distribution;
    }, [students]);

    // Fetch fresh prediction from API (rules-based + ML)
    const refreshPrediction = useCallback(async (id) => {
        const targetId = id || studentId;
        if (!targetId) return null;

        setLoading(true);
        setError(null);

        try {
            const [studentResp, mlResp] = await Promise.all([
                getStudentDetails(targetId),
                getMLPrediction(targetId),
            ]);

            if (!studentResp.success || !studentResp.data) {
                throw new Error(studentResp.message || 'Failed to load student');
            }

            const s = studentResp.data;
            const ruleRiskScore = typeof s.risk_score === 'number' ? s.risk_score : 0;
            const engagementScore = typeof s.engagement_score === 'number' ? s.engagement_score : 0;
            const retentionLikelihood = s.retention_likelihood ?? 'Unknown';

            const rulePrediction = {
                student_id: s.id,
                risk_score: validateRiskScore(ruleRiskScore, 50),
                engagement_score: engagementScore,
                retention_likelihood: retentionLikelihood,
                signal_breakdown: s.signal_breakdown || {},
                top_risk_factors: s.top_risk_factors || [],
            };

            let mlPrediction = null;
            if (mlResp && mlResp.success && mlResp.data) {
                mlPrediction = sanitizePrediction(mlResp.data);
            }

            return { rulePrediction, mlPrediction };
        } catch (err) {
            setError(err.message);
            return null;
        } finally {
            setLoading(false);
        }
    }, [studentId]);

    // Simulate what-if scenario (placeholder; backend endpoint not yet wired)
    const simulateWhatIf = useCallback(async () => {
        console.warn('simulateWhatIf is not implemented against a real backend endpoint yet.');
        return null;
    }, []);

    return {
        // Data
        student,
        riskScore,
        riskCategory,
        riskDistribution,

        // State
        loading,
        error,

        // Methods
        categorizeRisk,
        getStudentsByCategory,
        refreshPrediction,
        simulateWhatIf,

        // Constants
        RISK_CATEGORIES
    };
};

export default useStudentRisk;
