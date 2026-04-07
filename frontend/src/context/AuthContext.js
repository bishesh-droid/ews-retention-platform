import React, { createContext, useContext, useState } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

export const API_BASE_URL =
    (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) ||
    process.env.REACT_APP_API_BASE_URL ||
    process.env.REACT_APP_API_URL ||
    'http://localhost:8000/api/v1';

export const AuthProvider = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState(
        () => sessionStorage.getItem('ews_jwt') !== null
    );
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const login = async (username, password) => {
        setLoading(true);
        setError(null);
        try {
            const params = new URLSearchParams();
            params.append('username', username);
            params.append('password', password);

            const response = await axios.post(`${API_BASE_URL}/auth/login`, params, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
            });

            const { access_token } = response.data;
            if (!access_token) {
                throw new Error('No access token received');
            }

            sessionStorage.setItem('ews_jwt', access_token);
            setIsAuthenticated(true);
            return { success: true };
        } catch (err) {
            const message = err.response?.data?.detail || err.message || 'Login failed';
            setError(message);
            return { success: false, error: message };
        } finally {
            setLoading(false);
        }
    };

    const logout = () => {
        sessionStorage.removeItem('ews_jwt');
        setIsAuthenticated(false);
        setError(null);
    };

    return (
        <AuthContext.Provider value={{ isAuthenticated, login, logout, loading, error }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
