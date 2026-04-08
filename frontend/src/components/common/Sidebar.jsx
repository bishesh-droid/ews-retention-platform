import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Logo from './Logo';
import {
    FaChartPie,
    FaUsers,
    FaExclamationTriangle,
    FaChartLine,
    FaClipboardList,
    FaFileAlt,
    FaCog,
    FaSignOutAlt,
    FaChartBar,
    FaUserGraduate
} from 'react-icons/fa';

const SidebarItem = ({ to, icon: Icon, label }) => {
    return (
        <NavLink
            to={to}
            className="flex items-center gap-3 py-3 rounded-xl transition-all duration-200"
            style={({ isActive }) => ({
                textDecoration: 'none',
                backgroundColor: isActive ? 'rgba(124, 58, 237, 0.18)' : 'transparent',
                color: isActive ? 'var(--primary-light)' : 'var(--text-muted)',
                borderLeft: isActive ? '3px solid var(--primary-color)' : '3px solid transparent',
                paddingLeft: isActive ? '13px' : '16px',
                paddingRight: '16px',
                boxShadow: isActive ? '0 0 20px rgba(139,92,246,0.15)' : 'none',
                transition: 'all 0.2s ease',
            })}
            onMouseEnter={e => {
                if (!e.currentTarget.classList.contains('active')) {
                    e.currentTarget.style.backgroundColor = 'rgba(124,58,237,0.08)';
                    e.currentTarget.style.color = 'var(--text-secondary)';
                }
            }}
            onMouseLeave={e => {
                if (!e.currentTarget.classList.contains('active')) {
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.color = 'var(--text-muted)';
                }
            }}
        >
            <Icon size={18} className="shrink-0" />
            <span className="font-medium whitespace-nowrap">{label}</span>
        </NavLink>
    );
};

const Sidebar = () => {
    const { logout } = useAuth();
    const navigate = useNavigate();

    const handleSignOut = () => {
        logout();
        navigate('/login');
    };

    const navItems = [
        { to: "/", icon: FaChartPie, label: "Overview" },
        { to: "/students", icon: FaUsers, label: "Students" },
        { to: "/student-portal", icon: FaUserGraduate, label: "Portal" },
        { to: "/faculty-tools", icon: FaClipboardList, label: "Faculty" },
        { to: "/risk-factors", icon: FaExclamationTriangle, label: "Risk Factors" },
        { to: "/interventions", icon: FaClipboardList, label: "Interventions" },
        { to: "/insights", icon: FaChartLine, label: "Analytics" },
        { to: "/business-analytics", icon: FaChartBar, label: "Business Intel" },
        { to: "/reports", icon: FaFileAlt, label: "Reports" },
        { to: "/settings", icon: FaCog, label: "Settings" },
    ];

    return (
        <aside
            className="w-72 min-w-[18rem] h-screen sticky top-0 flex flex-col p-6 overflow-y-auto overflow-x-hidden"
            style={{
                backgroundColor: 'var(--glass-bg)',
                backdropFilter: 'blur(12px)',
                WebkitBackdropFilter: 'blur(12px)',
                borderRight: '1px solid var(--border-color)',
                transition: 'background-color 0.25s ease, border-color 0.25s ease',
            }}
        >
            <div className="mb-10 px-2">
                <Logo size={38} textSize="lg" />
            </div>

            <nav className="flex flex-col gap-2 flex-grow">
                {navItems.map((item) => (
                    <SidebarItem key={item.to} {...item} />
                ))}
            </nav>

            <div className="mt-10 pt-6" style={{ borderTop: '1px solid var(--border-color)' }}>
                <button
                    onClick={handleSignOut}
                    className="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 w-full"
                    style={{ color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}
                    onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'rgba(239,68,68,0.1)'; e.currentTarget.style.color = '#F87171'; }}
                    onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}
                >
                    <FaSignOutAlt size={18} />
                    <span className="font-medium">Sign Out</span>
                </button>
            </div>
        </aside>
    );
};

export default Sidebar;
