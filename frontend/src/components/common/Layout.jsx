import React from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
    FaChartPie,
    FaUsers,
    FaUserGraduate,
    FaExclamationTriangle,
    FaChartLine,
    FaClipboardList,
    FaFileAlt,
    FaCog,
    FaSignOutAlt,
    FaChartBar
} from 'react-icons/fa';
import { variants, transition } from '../../utils/motionConfig';

const SidebarItem = ({ to, icon: Icon, label, delay }) => {
    return (
        <NavLink
            to={to}
            className={({ isActive }) =>
                `d-flex align-items-center gap-3 px-3 py-3 rounded-3 text-decoration-none transition-all ${isActive
                    ? 'bg-primary-subtle text-primary fw-semibold shadow-sm'
                    : 'text-secondary hover-bg-surface-hover'
                }`
            }
            style={({ isActive }) => ({
                backdropFilter: isActive ? 'blur(8px)' : 'none',
                background: isActive ? 'rgba(43, 43, 136, 0.1)' : 'transparent',
                borderLeft: isActive ? '3px solid var(--primary-color)' : '3px solid transparent',
            })}
        >
            <Icon size={18} className={({ isActive }) => isActive ? 'text-primary' : 'text-muted'} />
            <span>{label}</span>
            {/* Active Indicator Glow */}
        </NavLink>
    );
};

const Layout = ({ children }) => {
    const location = useLocation();

    const navItems = [
        { to: "/", icon: FaChartPie, label: "Dashboard" },
        { to: "/student-portal", icon: FaUserGraduate, label: "Student Portal" },
        { to: "/faculty-tools", icon: FaClipboardList, label: "Faculty Tools" },
        { to: "/students", icon: FaUsers, label: "Students" },
        { to: "/risk-factors", icon: FaExclamationTriangle, label: "Risk Factors" },
        { to: "/interventions", icon: FaClipboardList, label: "Interventions" },
        { to: "/insights", icon: FaChartLine, label: "Analytics" },
        { to: "/business-analytics", icon: FaChartBar, label: "Business Intel" },
        { to: "/reports", icon: FaFileAlt, label: "Reports" },
        { to: "/settings", icon: FaCog, label: "Settings" },
    ];

    return (
        <div className="d-flex" style={{ backgroundColor: 'var(--bg-color)', minHeight: '100vh', color: 'var(--text-primary)' }}>

            {/* Sidebar - Fixed */}
            <motion.aside
                initial={{ x: -50, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                transition={{ duration: 0.5 }}
                className="d-none d-lg-flex flex-column p-4 position-fixed h-100"
                style={{
                    width: 'var(--sidebar-width)',
                    borderRight: '1px solid var(--border-color)',
                    background: 'rgba(var(--surface-color), 0.5)',
                    backdropFilter: 'blur(20px)',
                    zIndex: 1000
                }}
            >
                <div className="mb-5 d-flex align-items-center gap-2 px-2">
                    <div className="bg-primary rounded-circle p-2 d-flex justify-content-center align-items-center text-white shadow-glow">
                        <FaUserGraduate size={20} />
                    </div>
                    <span className="fw-bold fs-5 tracking-tight text-gradient">EWS Dashboard</span>
                </div>

                <nav className="d-flex flex-column gap-2 flex-grow-1">
                    {navItems.map((item, index) => (
                        <SidebarItem key={item.to} {...item} delay={index * 0.1} />
                    ))}
                </nav>

                <div className="mt-auto pt-4 border-top border-secondary-subtle">
                    <button className="btn btn-link text-decoration-none text-muted d-flex align-items-center gap-2 px-2">
                        <FaSignOutAlt /> Sign Out
                    </button>
                </div>
            </motion.aside>

            {/* Main Content Area */}
            <main
                className="flex-grow-1 p-4"
                style={{
                    marginLeft: 'var(--sidebar-width)', // Offset for fixed sidebar
                    width: 'calc(100% - var(--sidebar-width))'
                }}
            >
                {/* Top Header / Breadcrumbs could go here */}

                <AnimatePresence mode="wait">
                    <motion.div
                        key={location.pathname}
                        initial="hidden"
                        animate="visible"
                        exit="exit"
                        variants={variants.fadeIn}
                        className="h-100"
                    >
                        {children}
                    </motion.div>
                </AnimatePresence>
            </main>
        </div>
    );
};

export default Layout;
