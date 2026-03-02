import React from 'react';
import { Route, Routes, useLocation, Navigate } from 'react-router-dom';
import Layout from './components/common/Layout';
import Dashboard from './pages/Dashboard';
import Students from './pages/Students';
import StudentProfile from './pages/StudentProfile';
import RiskFactors from './pages/RiskFactors';
import Interventions from './pages/Interventions';
import Analytics from './pages/Analytics';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import StudentPortal from './pages/StudentPortal';
import FacultyTools from './pages/FacultyTools';
import BusinessAnalytics from './pages/BusinessAnalytics';
import Login from './pages/Login';
import { useAuth } from './context/AuthContext';
import './App.css';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? children : <Navigate to="/login" replace />;
};

function App() {
  const location = useLocation();

  return (
    <Routes location={location} key={location.pathname}>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes location={location} key={location.pathname}>
                <Route path="/" element={<Dashboard />} />
                <Route path="/students" element={<Students />} />
                <Route path="/students/:id" element={<StudentProfile />} />
                <Route path="/student-portal" element={<StudentPortal />} />
                <Route path="/faculty-tools" element={<FacultyTools />} />
                <Route path="/risk-factors" element={<RiskFactors />} />
                <Route path="/interventions" element={<Interventions />} />
                <Route path="/insights" element={<Analytics />} />
                <Route path="/business-analytics" element={<BusinessAnalytics />} />
                <Route path="/reports" element={<Reports />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default App;
