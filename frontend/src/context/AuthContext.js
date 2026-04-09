/**
 * AuthContext — Secure JWT Authentication
 * ========================================
 *
 * Security features:
 * - Access token stored in memory only (not localStorage/sessionStorage)
 * - Refresh token stored in httpOnly cookie (handled by browser)
 * - Automatic token refresh on 401 responses
 * - XSS-resistant token storage
 *
 * Token Flow:
 * 1. Login: POST /auth/login → returns access_token + sets refresh_token cookie
 * 2. API calls: Attach access_token via Authorization header
 * 3. 401 response: Attempt silent refresh via /auth/refresh
 * 4. Refresh fails: Redirect to /login
 */

import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

// API base URL resolution (Vite + CRA compatible)
export const API_BASE_URL =
    (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) ||
    process.env.REACT_APP_API_BASE_URL ||
    process.env.REACT_APP_API_URL ||
    'http://localhost:8000/api/v1';

// Create axios instance with credentials enabled (for httpOnly cookies)
const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: true, // Required for httpOnly cookie handling
});

// Token refresh state management
let isRefreshing = false;
let refreshSubscribers = [];

/**
 * Subscribe to token refresh completion
 * @param {Function} callback - Called with new access token
 */
const subscribeTokenRefresh = (callback) => {
    refreshSubscribers.push(callback);
};

/**
 * Notify all subscribers that token has been refreshed
 * @param {string} newToken - New access token
 */
const onTokenRefreshed = (newToken) => {
    refreshSubscribers.forEach((callback) => callback(newToken));
    refreshSubscribers = [];
};

export const AuthProvider = ({ children }) => {
    // Store access token in memory only (XSS-resistant)
    const accessTokenRef = useRef(null);
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [isLoading, setIsLoading] = useState(true);
    const [user, setUser] = useState(null);
    const [error, setError] = useState(null);

    /**
     * Store access token in memory
     */
    const setAccessToken = useCallback((token) => {
        accessTokenRef.current = token;
        setIsAuthenticated(!!token);
    }, []);

    /**
     * Login with username/password
     * Calls POST /auth/login and stores access token in memory
     */
    const login = useCallback(async (username, password) => {
        setError(null);
        try {
            const params = new URLSearchParams();
            params.append('username', username);
            params.append('password', password);

            const response = await apiClient.post('/auth/login', params, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
            });

            const { access_token } = response.data;
            if (!access_token) {
                throw new Error('No access token received from server');
            }

            // Store access token in memory only (NOT in localStorage/sessionStorage)
            setAccessToken(access_token);

            // Fetch user profile after successful login
            try {
                const profileRes = await apiClient.get('/auth/me', {
                    headers: { Authorization: `Bearer ${access_token}` },
                });
                setUser(profileRes.data);
            } catch (profileErr) {
                console.warn('Failed to fetch user profile after login:', profileErr);
            }

            return { success: true };
        } catch (err) {
            const message = err.response?.data?.detail || err.message || 'Login failed';
            setError(message);
            setIsAuthenticated(false);
            return { success: false, error: message };
        }
    }, [setAccessToken]);

    /**
     * Refresh access token using httpOnly refresh cookie
     * Calls POST /auth/refresh
     */
    const refreshToken = useCallback(async () => {
        if (isRefreshing) {
            // Wait for existing refresh to complete
            return new Promise((resolve) => {
                subscribeTokenRefresh((newToken) => {
                    resolve(newToken);
                });
            });
        }

        isRefreshing = true;

        try {
            // Call refresh endpoint — httpOnly cookie is sent automatically
            const response = await apiClient.post('/auth/refresh');
            const { access_token } = response.data;

            if (!access_token) {
                throw new Error('No access token received from refresh');
            }

            // Update in-memory token
            setAccessToken(access_token);
            onTokenRefreshed(access_token);

            return access_token;
        } catch (err) {
            // Refresh failed — clear auth state
            setAccessToken(null);
            setUser(null);
            setIsAuthenticated(false);
            throw err;
        } finally {
            isRefreshing = false;
        }
    }, [setAccessToken]);

    /**
     * Logout user
     * Calls POST /auth/logout to clear httpOnly cookie
     */
    const logout = useCallback(async () => {
        try {
            // Notify backend to clear refresh token cookie
            await apiClient.post('/auth/logout');
        } catch (err) {
            console.warn('Logout request failed (token may already be expired):', err);
        } finally {
            // Always clear local state
            accessTokenRef.current = null;
            setIsAuthenticated(false);
            setUser(null);
            setError(null);

            // Redirect to login
            if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
                window.location.href = '/login';
            }
        }
    }, []);

    /**
     * Get current access token (for API calls)
     */
    const getAccessToken = useCallback(() => {
        return accessTokenRef.current;
    }, []);

    // Setup axios interceptors on mount
    useEffect(() => {
        // Request interceptor: attach access token to all requests
        const requestInterceptor = apiClient.interceptors.request.use(
            (config) => {
                const token = accessTokenRef.current;
                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                }
                return config;
            },
            (error) => Promise.reject(error)
        );

        // Response interceptor: handle 401 with automatic token refresh
        const responseInterceptor = apiClient.interceptors.response.use(
            (response) => response,
            async (error) => {
                const originalRequest = error.config;

                // Handle 401 Unauthorized
                if (error.response?.status === 401 && !originalRequest._retry) {
                    originalRequest._retry = true;

                    try {
                        // Attempt token refresh
                        const newToken = await refreshToken();

                        // Retry original request with new token
                        originalRequest.headers.Authorization = `Bearer ${newToken}`;
                        return apiClient(originalRequest);
                    } catch (refreshError) {
                        // Refresh failed — redirect to login
                        logout();
                        return Promise.reject(refreshError);
                    }
                }

                // Handle other errors
                return Promise.reject(error);
            }
        );

        // Cleanup interceptors on unmount
        return () => {
            apiClient.interceptors.request.eject(requestInterceptor);
            apiClient.interceptors.response.eject(responseInterceptor);
        };
    }, [refreshToken, logout]);

    // Check for existing session on mount (via refresh token cookie)
    useEffect(() => {
        const initAuth = async () => {
            try {
                // Try to refresh token on app load (validates httpOnly cookie)
                await refreshToken();

                // Fetch user profile if refresh succeeded
                const token = accessTokenRef.current;
                if (token) {
                    const profileRes = await apiClient.get('/auth/me', {
                        headers: { Authorization: `Bearer ${token}` },
                    });
                    setUser(profileRes.data);
                }
            } catch (err) {
                // No valid session — user needs to login
                console.log('No existing session found');
            } finally {
                setIsLoading(false);
            }
        };

        initAuth();
    }, [refreshToken]);

    const value = {
        isAuthenticated,
        isLoading,
        user,
        error,
        login,
        logout,
        refreshToken,
        getAccessToken,
        apiClient, // Expose for direct API calls with interceptors
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

/**
 * Hook to access auth context
 */
export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

/**
 * Axios instance with auth interceptors pre-configured
 * Use this for API calls that need automatic token refresh
 */
export { apiClient };

export default AuthContext;
