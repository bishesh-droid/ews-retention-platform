/**
 * Student Service
 *
 * Handles all student-related API interactions.
 * Provides a clean interface for fetching and managing student data.
 */

import axios from 'axios';
import { apiClient } from '../context/AuthContext';
import { validateRiskScore, sanitizePrediction } from '../utils/riskScoreValidator';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

// Use the shared apiClient from AuthContext so auth interceptors (token attachment,
// automatic refresh on 401) apply to all student service requests.
const api = apiClient || axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json'
    }
});

/**
 * Get all students with optional limit
 */
export const getAllStudents = async (limit = 1500) => {
    try {
        const response = await api.get(`/students/?limit=${limit}`);
        return response.data;
    } catch (error) {
        console.error('Error fetching students:', error);
        throw error;
    }
};

/**
 * Get a single student by ID
 */
export const getStudentById = async (studentId) => {
    try {
        const response = await api.get(`/students/${studentId}`);
        return response.data;
    } catch (error) {
        console.error(`Error fetching student ${studentId}:`, error);
        throw error;
    }
};

/**
 * Get student count
 */
export const getStudentCount = async () => {
    try {
        const response = await api.get('/students/count');
        return response.data.count;
    } catch (error) {
        console.error('Error fetching student count:', error);
        throw error;
    }
};

/**
 * Get prediction for a single student
 */
export const getStudentPrediction = async (studentId) => {
    try {
        const response = await api.get(`/predictions/${studentId}`);
        return sanitizePrediction(response.data);
    } catch (error) {
        console.error(`Error fetching prediction for student ${studentId}:`, error);
        throw error;
    }
};

/**
 * Get batch predictions for all students
 */
export const getBatchPredictions = async (limit = 1500) => {
    try {
        const response = await api.get(`/predictions/batch?limit=${limit}`);
        const predictions = response.data.predictions || {};

        // Sanitize all predictions
        const sanitized = {};
        for (const [id, pred] of Object.entries(predictions)) {
            sanitized[id] = sanitizePrediction(pred);
        }

        return sanitized;
    } catch (error) {
        console.error('Error fetching batch predictions:', error);
        throw error;
    }
};

/**
 * Merge students with their predictions
 */
export const getStudentsWithPredictions = async (limit = 1500) => {
    try {
        const [students, predictions] = await Promise.all([
            getAllStudents(limit),
            getBatchPredictions(limit)
        ]);

        return students.map(student => {
            const prediction = predictions[student.id] || {};
            const first = (student.first_name || '').trim();
            const last = (student.last_name || '').trim();
            const fullName = `${first} ${last}`.trim();
            return {
                ...student,
                name: student.name || fullName || student.id,
                risk_score: validateRiskScore(prediction.risk_score, 50),
                engagement_score: prediction.engagement_score || 50,
                retention_likelihood: prediction.retention_likelihood || 'Unknown',
                signal_breakdown: prediction.signal_breakdown || {},
                top_risk_factors: prediction.top_risk_factors || []
            };
        });
    } catch (error) {
        console.error('Error fetching students with predictions:', error);
        throw error;
    }
};

/**
 * Search students by query
 */
export const searchStudents = async (query, students) => {
    const searchTerm = query.toLowerCase();
    return students.filter(student =>
        student.id.toString().includes(searchTerm) ||
        (student.name && student.name.toLowerCase().includes(searchTerm))
    );
};

export default {
    getAllStudents,
    getStudentById,
    getStudentCount,
    getStudentPrediction,
    getBatchPredictions,
    getStudentsWithPredictions,
    searchStudents
};
