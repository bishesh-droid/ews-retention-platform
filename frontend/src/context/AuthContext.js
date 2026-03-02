import React, { createContext, useContext, useState } from 'react';

const AuthContext = createContext(null);

const CREDENTIALS = { username: 'admin', password: 'admin123' };

export const AuthProvider = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState(
        () => sessionStorage.getItem('ews_auth') === 'true'
    );

    const login = (username, password) => {
        if (username === CREDENTIALS.username && password === CREDENTIALS.password) {
            sessionStorage.setItem('ews_auth', 'true');
            setIsAuthenticated(true);
            return true;
        }
        return false;
    };

    const logout = () => {
        sessionStorage.removeItem('ews_auth');
        setIsAuthenticated(false);
    };

    return (
        <AuthContext.Provider value={{ isAuthenticated, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
