import { useState, useCallback, useMemo } from 'react';
import { useStudentData } from '../context/StudentContext';
import { validateRiskScore, sanitizePrediction } from '../utils/riskScoreValidator';
import * as api from '../api';

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

    // Fetch fresh prediction from API
    const refreshPrediction = useCallback(async (id) => {
        const targetId = id || studentId;
        if (!targetId) return null;

        setLoading(true);
        setError(null);

        try {
            const response = await api.getStudentPrediction(targetId);
            const sanitized = sanitizePrediction(response.data);
            return sanitized;
        } catch (err) {
            setError(err.message);
            return null;
        } finally {
            setLoading(false);
        }
    }, [studentId]);

    // Simulate what-if scenario
    const simulateWhatIf = useCallback(async (id, adjustments) => {
        const targetId = id || studentId;
        if (!targetId) return null;

        setLoading(true);
        setError(null);

        try {
            const response = await api.postWhatIfSimulation(targetId, adjustments);
            return response.data;
        } catch (err) {
            setError(err.message);
            return null;
        } finally {
            setLoading(false);
        }
    }, [studentId]);

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
