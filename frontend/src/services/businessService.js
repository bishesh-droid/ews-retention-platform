/**
 * Business Service
 *
 * Handles all business intelligence API interactions.
 * Provides metrics for executive dashboards and reporting.
 */

import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
        'X-User-Role': 'admin'  // Default to admin for business endpoints
    }
});

/**
 * Get retention metrics
 */
export const getRetentionMetrics = async (period = 'current_semester') => {
    try {
        const response = await api.get(`/business/metrics/retention?period=${period}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching retention metrics:', error);
        throw error;
    }
};

/**
 * Get revenue at risk analysis
 */
export const getRevenueAtRisk = async () => {
    try {
        const response = await api.get('/business/metrics/revenue-at-risk');
        return response.data;
    } catch (error) {
        console.error('Error fetching revenue at risk:', error);
        throw error;
    }
};

/**
 * Get intervention ROI analysis
 */
export const getInterventionROI = async (period = 'quarterly') => {
    try {
        const response = await api.get(`/business/metrics/intervention-roi?period=${period}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching intervention ROI:', error);
        throw error;
    }
};

/**
 * Get retention funnel data
 */
export const getRetentionFunnel = async (period = 'current_semester') => {
    try {
        const response = await api.get(`/business/funnel?period=${period}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching retention funnel:', error);
        throw error;
    }
};

/**
 * Get executive summary
 */
export const getExecutiveSummary = async () => {
    try {
        const response = await api.get('/business/executive-summary');
        return response.data;
    } catch (error) {
        console.error('Error fetching executive summary:', error);
        throw error;
    }
};

/**
 * Get all business metrics at once
 */
export const getAllBusinessMetrics = async () => {
    try {
        const [retention, revenue, roi, funnel] = await Promise.all([
            getRetentionMetrics(),
            getRevenueAtRisk(),
            getInterventionROI(),
            getRetentionFunnel()
        ]);

        return {
            retention,
            revenue,
            roi,
            funnel,
            fetchedAt: new Date().toISOString()
        };
    } catch (error) {
        console.error('Error fetching all business metrics:', error);
        throw error;
    }
};

export default {
    getRetentionMetrics,
    getRevenueAtRisk,
    getInterventionROI,
    getRetentionFunnel,
    getExecutiveSummary,
    getAllBusinessMetrics
};
