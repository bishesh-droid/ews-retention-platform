/**
 * Centralized API service layer
 *
 * All network access should go through this module so that:
 * - Base URL is configured in one place
 * - Errors are handled consistently
 * - Callers receive a standardized response structure
 *
 * Environment configuration (in order of precedence):
 * - VITE_API_BASE_URL  (for Vite builds)
 * - REACT_APP_API_BASE_URL (for Create React App)
 * - REACT_APP_API_URL (existing fallback)
 * - http://localhost:8000/api/v1 (default)
 */

import axios from 'axios';

// Resolve base URL from multiple environment conventions
let viteBaseUrl;
try {
  // Guarded access so this still parses in non-Vite builds
  // eslint-disable-next-line no-undef
  if (typeof import.meta !== 'undefined' && import.meta.env && import.meta.env.VITE_API_BASE_URL) {
    // eslint-disable-next-line no-undef
    viteBaseUrl = import.meta.env.VITE_API_BASE_URL;
  }
} catch {
  viteBaseUrl = undefined;
}

const CRA_BASE_URL =
  process.env.REACT_APP_API_BASE_URL ||
  process.env.REACT_APP_API_URL ||
  undefined;

export const API_BASE_URL = viteBaseUrl || CRA_BASE_URL || 'http://localhost:8000/api/v1';

const http = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Enable for httpOnly cookie support
});

// Lightweight global toast utility (no component changes required)
const showGlobalToast = (message) => {
  if (!message) return;
  try {
    let container = document.getElementById('global-api-toast');
    if (!container) {
      container = document.createElement('div');
      container.id = 'global-api-toast';
      container.style.position = 'fixed';
      container.style.bottom = '20px';
      container.style.right = '20px';
      container.style.zIndex = '9999';
      container.style.background = 'rgba(15,23,42,0.95)';
      container.style.color = '#f9fafb';
      container.style.padding = '10px 16px';
      container.style.borderRadius = '999px';
      container.style.boxShadow = '0 10px 30px rgba(15,23,42,0.5)';
      container.style.fontSize = '13px';
      container.style.fontFamily = 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
      container.style.display = 'none';
      container.style.maxWidth = '320px';
      container.style.whiteSpace = 'nowrap';
      container.style.overflow = 'hidden';
      container.style.textOverflow = 'ellipsis';
      document.body.appendChild(container);
    }
    container.textContent = message;
    container.style.display = 'block';

    clearTimeout(container._hideTimer);
    container._hideTimer = setTimeout(() => {
      container.style.display = 'none';
    }, 4000);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error('Failed to show toast:', err);
  }
};

// Note: JWT token is now managed by AuthContext and attached via its own interceptor.
// This interceptor can be used for additional headers if needed.
http.interceptors.request.use(
  (config) => {
    // Token attachment is handled by AuthContext's apiClient interceptor
    // This ensures tokens are never stored in localStorage/sessionStorage
    return config;
  },
  (error) => Promise.reject(error),
);

// Global response interceptor for centralized error handling
// Note: 401 handling with token refresh is managed by AuthContext
http.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;

    // Always log detailed error for debugging
    // eslint-disable-next-line no-console
    console.error('HTTP error response:', {
      status,
      url: error?.config?.url,
      method: error?.config?.method,
      data: error?.response?.data,
    });

    // Note: 401 Unauthorized is handled by AuthContext with automatic token refresh
    // Only handle non-401 errors here
    if (status === 401) {
      // Let AuthContext handle 401 with token refresh
      // Only redirect if we're not on the login page already
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        // AuthContext will handle the redirect after refresh attempt fails
        console.warn('Authentication required — token refresh will be attempted');
      }
    } else if (status >= 500) {
      // Show a non-blocking toast notification for server errors
      showGlobalToast('A server error occurred. Please try again later.');
    }

    return Promise.reject(error);
  },
);

/**
 * Standardized client-side response shape.
 *
 * {
 *   success: boolean,
 *   message: string,
 *   data: any,
 *   meta?: object,
 *   error?: {
 *     status?: number,
 *     message: string,
 *     details?: any,
 *   }
 * }
 */
const buildSuccess = (payload) => {
  if (!payload) {
    return {
      success: true,
      message: 'OK',
      data: null,
      meta: {},
    };
  }

  // If backend already returns the standardized envelope, pass it through
  if (typeof payload.success === 'boolean' && 'data' in payload) {
    return {
      success: payload.success,
      message: payload.message ?? (payload.success ? 'OK' : 'Error'),
      data: payload.data,
      meta: payload.meta ?? {},
      error: payload.success
        ? undefined
        : {
            status: payload.statusCode,
            message: payload.message,
            details: payload.data,
          },
    };
  }

  // Legacy/raw payload – wrap it
  return {
    success: true,
    message: 'OK',
    data: payload,
    meta: {},
  };
};

const buildError = (error) => {
  const status = error?.response?.status;
  const backend = error?.response?.data;

  // If backend sent a standardized error envelope, normalize it
  if (backend && typeof backend.success === 'boolean' && backend.success === false) {
    return {
      success: false,
      message: backend.message || 'Request failed',
      data: backend.data ?? null,
      meta: backend.meta ?? {},
      error: {
        status,
        message: backend.message || 'Request failed',
        details: backend.data,
      },
    };
  }

  // Generic / network error wrapper
  const messageFromBackend =
    backend?.message ||
    backend?.error?.message ||
    error?.message ||
    'Request failed';

  return {
    success: false,
    message: messageFromBackend,
    data: null,
    meta: {},
    error: {
      status,
      message: messageFromBackend,
      details: backend || error?.toString(),
    },
  };
};

const safeRequest = async (fn) => {
  try {
    const res = await fn();
    return buildSuccess(res.data);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error('API request error:', err);
    return buildError(err);
  }
};

/**
 * Get high-level cohort / KPI summary for dashboards.
 *
 * Aggregates multiple backend endpoints into a single summary:
 * - /business/metrics/retention
 * - /business/metrics/intervention-roi
 *
 * Derived fields:
 * - overallRiskPercent: (1 - retention_rate) * 100
 * - highRiskCount: retention.high_risk_count
 * - interventionRate: estimated_recovered / interventions_triggered (percent)
 * - engagementTrend: -gap_to_target * 100  (positive = above target)
 * - modelVersion: currently not available (null placeholder)
 */
export const getCohortSummary = async () => {
  try {
    const [retentionRes, roiRes] = await Promise.all([
      http.get('/business/metrics/retention'),
      http.get('/business/metrics/intervention-roi'),
    ]);

    const normalize = (payload) =>
      payload && typeof payload.success === 'boolean' && 'data' in payload
        ? payload.data
        : payload;

    const retention = normalize(retentionRes.data) || {};
    const roi = normalize(roiRes.data) || {};

    const retentionRate = typeof retention.retention_rate === 'number' ? retention.retention_rate : 0;
    const overallRiskPercent = Math.round((1 - retentionRate) * 100);

    const highRiskCount = typeof retention.high_risk_count === 'number' ? retention.high_risk_count : 0;

    const interventionsTriggered =
      typeof roi.interventions_triggered === 'number' ? roi.interventions_triggered : 0;
    const estimatedRecovered =
      typeof roi.estimated_recovered === 'number' ? roi.estimated_recovered : 0;
    const interventionRate =
      interventionsTriggered > 0
        ? Math.round((estimatedRecovered / interventionsTriggered) * 100)
        : 0;

    const gapToTarget =
      typeof retention.gap_to_target === 'number' ? retention.gap_to_target : 0;
    const engagementTrend = Math.round(-gapToTarget * 100);

    const modelVersion = null;

    const combined = {
      overallRiskPercent,
      highRiskCount,
      interventionRate,
      engagementTrend,
      modelVersion,
      retention,
      interventionRoi: roi,
    };

    return buildSuccess(combined);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error('Error loading cohort summary:', err);
    return buildError(err);
  }
};

/**
 * Get paginated student list with risk/engagement metrics.
 *
 * Backed by: GET /students/students?skip=&limit=&sort_by=&order=
 */
export const getStudentList = (page = 1, limit = 50, sortBy = 'risk_score', order = 'desc') => {
  const safePage = Number.isFinite(page) && page > 0 ? page : 1;
  const safeLimit = Number.isFinite(limit) && limit > 0 ? limit : 50;
  const skip = (safePage - 1) * safeLimit;
  const safeSortBy = typeof sortBy === 'string' && sortBy.length > 0 ? sortBy : 'risk_score';
  const safeOrder = order === 'asc' || order === 'ascending' ? 'asc' : 'desc';

  return safeRequest(() =>
    http.get('/students/students', {
      params: {
        skip,
        limit: safeLimit,
        sort_by: safeSortBy,
        order: safeOrder,
      },
    }),
  );
};

/**
 * Get detailed information for a single student.
 *
 * Backed by: GET /students/students/{studentId}
 */
export const getStudentDetails = (studentId) =>
  safeRequest(() => http.get(`/students/students/${encodeURIComponent(studentId)}`));

/**
 * Get ML-based dropout prediction for a student.
 *
 * Backed by: GET /ml/predict/{student_id}
 */
export const getMLPrediction = (studentId) =>
  safeRequest(() => http.get(`/ml/predict/${encodeURIComponent(studentId)}`));

/**
 * Get weekly engagement summary for a single student.
 *
 * NOTE: This assumes a backend route of the form:
 *   GET /students/students/{studentId}/weekly-summary
 * If your API differs, update the path here while keeping the
 * response envelope (success/message/data) consistent.
 */
export const getWeeklySummary = (studentId) =>
  safeRequest(() =>
    http.get(`/students/students/${encodeURIComponent(studentId)}/weekly-summary`),
  );

/**
 * Get risk trend points for a student (portal-friendly).
 *
 * Backed by: GET /students/students/{studentId}/risk-trend?limit=
 */
export const getStudentRiskTrend = (studentId, limit = 8) =>
  safeRequest(() =>
    http.get(`/students/students/${encodeURIComponent(studentId)}/risk-trend`, {
      params: { limit },
    }),
  );

/**
 * Analytics (cohort-level) endpoints under /students/analytics/*
 */
export const getCohortRiskTrends = (weeks = 8) =>
  safeRequest(() => http.get('/students/analytics/risk-trends', { params: { weeks } }));

export const getCohortEngagementTrends = (weeks = 8) =>
  safeRequest(() => http.get('/students/analytics/engagement-trends', { params: { weeks } }));

export const getCohortPerformanceTrends = (weeks = 8) =>
  safeRequest(() => http.get('/students/analytics/performance-trends', { params: { weeks } }));

export const getInterventionEffectivenessSummary = (weeks = 12) =>
  safeRequest(() => http.get('/students/analytics/intervention-effectiveness', { params: { weeks } }));

/**
 * Get risk distribution across the cohort.
 *
 * Backed by: GET /students/risk-distribution
 */
export const getRiskDistribution = () =>
  safeRequest(() => http.get('/students/risk-distribution'));

/**
 * Get pending interventions across the institution.
 *
 * Backed by: GET /decisions/pending/list
 */
export const getInterventions = (options = {}) => {
  const { priority, assigned_team: assignedTeam, limit = 50 } = options || {};

  return safeRequest(() =>
    http.get('/decisions/pending/list', {
      params: {
        priority: priority || undefined,
        assigned_team: assignedTeam || undefined,
        limit,
      },
    }),
  );
};

/**
 * Faculty-facing APIs
 */
export const getFacultyStudents = (limit = 200) =>
  safeRequest(() => http.get('/faculty/students', { params: { limit } }));

export const getFacultyAtRiskStudents = (threshold = 60, limit = 200) =>
  safeRequest(() =>
    http.get('/faculty/at-risk', {
      params: { threshold, limit },
    }),
  );

export const getFacultyAlerts = (limit = 100) =>
  safeRequest(() => http.get('/faculty/alerts', { params: { limit } }));

/**
 * Batch risk predictions with signal breakdown for the cohort.
 *
 * Backed by: GET /predictions/batch?limit=&include_decisions=
 */
export const getBatchPredictions = (limit = 500) =>
  safeRequest(() =>
    http.get('/predictions/batch', {
      params: { limit, include_decisions: false },
    }),
  );

/**
 * Business Intelligence (BI) endpoints
 */
export const getDepartmentComparison = () =>
  safeRequest(() => http.get('/business/departments/comparison'));

export const getRetentionForecast = (horizonMonths = 6) =>
  safeRequest(() => http.get('/business/forecast/retention', { params: { horizon_months: horizonMonths } }));

export const getCohortHeatmap = () =>
  safeRequest(() => http.get('/business/cohort-heatmap'));

export const getRetentionMetrics = (period = 'current_semester') =>
  safeRequest(() => http.get('/business/metrics/retention', { params: { period } }));

export const getRevenueAtRiskMetrics = () =>
  safeRequest(() => http.get('/business/metrics/revenue-at-risk'));

export const getInterventionRoiMetrics = (period = 'quarterly') =>
  safeRequest(() => http.get('/business/metrics/intervention-roi', { params: { period } }));

export const getRetentionFunnel = (period = 'current_semester') =>
  safeRequest(() => http.get('/business/funnel', { params: { period } }));

/**
 * Reports & Exports
 */
export const getReportTemplates = () =>
  safeRequest(() => http.get('/reports/templates'));

export const getGeneratedReports = (limit = 50) =>
  safeRequest(() => http.get('/reports/generated', { params: { limit } }));

export const generateReport = (payload) =>
  safeRequest(() => http.post('/reports/generate', payload));

export const downloadGeneratedReportFile = async (reportId) => {
  try {
    const res = await http.get(`/reports/download/${encodeURIComponent(reportId)}`, {
      responseType: 'blob',
    });
    const blob = res.data;
    const disposition = res.headers?.['content-disposition'] || res.headers?.get?.('content-disposition');
    let filename = 'report';
    if (typeof disposition === 'string') {
      const match = disposition.match(/filename="([^"]+)"/i) || disposition.match(/filename=([^;]+)/i);
      if (match && match[1]) filename = match[1].replace(/"/g, '').trim();
    }
    return { success: true, blob, filename };
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error('Download report error:', err);
    return buildError(err);
  }
};

/**
 * User profile & settings
 */
export const getCurrentProfile = () =>
  safeRequest(() => http.get('/auth/me'));

export const updateCurrentProfile = (payload) =>
  safeRequest(() => http.put('/auth/me', payload));

/**
 * Interventions CRUD (Interventions tab)
 */
export const getAllInterventions = (options = {}) => {
  const { skip = 0, limit = 500, status, assigned_faculty: assignedFaculty, student_id: studentId } = options || {};
  return safeRequest(() =>
    http.get('/interventions', {
      params: {
        skip,
        limit,
        status: status || undefined,
        assigned_faculty: assignedFaculty || undefined,
        student_id: studentId || undefined,
      },
    }),
  );
};

export const createIntervention = (payload) =>
  safeRequest(() => http.post('/interventions', payload));

export const updateIntervention = (interventionId, payload) =>
  safeRequest(() => http.patch(`/interventions/${encodeURIComponent(interventionId)}`, payload));

/**
 * Trigger data ingestion via admin endpoint.
 * Returns 202 Accepted immediately with a task ID for polling.
 */
export const triggerIngestion = async (file = null) => {
  const formData = new FormData();
  if (file) formData.append('file', file);

  // Note: Token is attached by AuthContext's axios interceptor automatically
  // We use the axios instance for consistency
  const token = typeof window !== 'undefined' && window.__AUTH_TOKEN__ ? window.__AUTH_TOKEN__ : '';
  const response = await fetch(`${API_BASE_URL}/admin/ingest`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: file ? formData : undefined,
    credentials: 'include', // Include httpOnly cookies
  });

  if (response.status === 202) {
    const data = await response.json();
    return { accepted: true, taskId: data.task_id, message: data.message };
  }
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.error?.message || err.message || 'Ingestion failed');
  }
  return response.json();
};

/**
 * Poll ingestion task status until completion or timeout.
 */
export const pollIngestionStatus = async (taskId, maxAttempts = 30, intervalMs = 2000) => {
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((r) => setTimeout(r, intervalMs));
    const token = typeof window !== 'undefined' && window.__AUTH_TOKEN__ ? window.__AUTH_TOKEN__ : '';
    const res = await fetch(`${API_BASE_URL}/admin/ingest/status/${encodeURIComponent(taskId)}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      credentials: 'include', // Include httpOnly cookies
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || 'Failed to check ingestion status');
    }
    const data = await res.json();
    if (data.status === 'success' || data.status === 'failed') return data;
  }
  throw new Error('Ingestion status polling timed out');
};

const api = {
  getCohortSummary,
  getStudentList,
  getStudentDetails,
  getMLPrediction,
  getWeeklySummary,
  getStudentRiskTrend,
  getCohortRiskTrends,
  getCohortEngagementTrends,
  getCohortPerformanceTrends,
  getInterventionEffectivenessSummary,
  getRiskDistribution,
  getInterventions,
  getFacultyStudents,
  getFacultyAtRiskStudents,
  getFacultyAlerts,
  getBatchPredictions,
  getDepartmentComparison,
  getRetentionForecast,
  getCohortHeatmap,
  getRetentionMetrics,
  getRevenueAtRiskMetrics,
  getInterventionRoiMetrics,
  getRetentionFunnel,
  getReportTemplates,
  getGeneratedReports,
  generateReport,
  downloadGeneratedReportFile,
  getCurrentProfile,
  updateCurrentProfile,
  getAllInterventions,
  createIntervention,
  updateIntervention,
  triggerIngestion,
  pollIngestionStatus,
};

export default api;

