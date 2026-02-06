import { useState, useCallback } from 'react';
import * as api from '../api';

/**
 * Custom hook for intervention-related operations
 *
 * Provides:
 * - Intervention recommendation fetching
 * - Intervention execution
 * - Intervention history
 */

export const INTERVENTION_TYPES = {
    NO_ACTION: {
        key: 'no_action',
        label: 'No Action Needed',
        color: '#10B981',
        threshold: 0.30
    },
    GENTLE_REMINDER: {
        key: 'gentle_reminder',
        label: 'Gentle Reminder',
        color: '#FBBF24',
        channels: ['email'],
        threshold: 0.60
    },
    MENTOR_OUTREACH: {
        key: 'mentor_outreach',
        label: 'Mentor Outreach',
        color: '#F59E0B',
        channels: ['email', 'call'],
        threshold: 0.80
    },
    URGENT_INTERVENTION: {
        key: 'urgent_intervention',
        label: 'Urgent Intervention',
        color: '#DC2626',
        channels: ['sales_call', 'whatsapp', 'incentive'],
        threshold: 1.0
    }
};

export const useIntervention = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    // Get intervention recommendation for a student
    const getRecommendation = useCallback(async (studentId) => {
        setLoading(true);
        setError(null);

        try {
            const response = await api.getDecision(studentId);
            return response.data;
        } catch (err) {
            setError(err.message);
            return null;
        } finally {
            setLoading(false);
        }
    }, []);

    // Execute an intervention
    const executeIntervention = useCallback(async (studentId, interventionType, notes = '') => {
        setLoading(true);
        setError(null);

        try {
            const response = await api.executeDecision({
                student_id: studentId,
                action_type: interventionType,
                notes
            });
            return response.data;
        } catch (err) {
            setError(err.message);
            return null;
        } finally {
            setLoading(false);
        }
    }, []);

    // Get intervention type based on risk score
    const getInterventionType = useCallback((riskScore) => {
        const score = riskScore / 100; // Convert percentage to probability

        if (score < INTERVENTION_TYPES.NO_ACTION.threshold) {
            return INTERVENTION_TYPES.NO_ACTION;
        } else if (score < INTERVENTION_TYPES.GENTLE_REMINDER.threshold) {
            return INTERVENTION_TYPES.GENTLE_REMINDER;
        } else if (score < INTERVENTION_TYPES.MENTOR_OUTREACH.threshold) {
            return INTERVENTION_TYPES.MENTOR_OUTREACH;
        } else {
            return INTERVENTION_TYPES.URGENT_INTERVENTION;
        }
    }, []);

    // Get pending interventions list
    const getPendingInterventions = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await api.getPendingDecisions();
            return response.data;
        } catch (err) {
            setError(err.message);
            return [];
        } finally {
            setLoading(false);
        }
    }, []);

    return {
        loading,
        error,
        getRecommendation,
        executeIntervention,
        getInterventionType,
        getPendingInterventions,
        INTERVENTION_TYPES
    };
};

export default useIntervention;
