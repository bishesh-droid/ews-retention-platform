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
                backgroundColor: isActive ? 'rgba(124, 58, 237, 0.25)' : 'transparent',
                color: isActive ? '#C4B5FD' : '#9B8FC0',
                borderLeft: isActive ? '3px solid #8B5CF6' : '3px solid transparent',
                paddingLeft: isActive ? '13px' : '16px',
                paddingRight: '16px',
                boxShadow: isActive ? '0 0 20px rgba(139,92,246,0.2)' : 'none',
            })}
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
            style={{ backgroundColor: 'rgba(11,7,20,0.6)', backdropFilter: 'blur(12px)', borderRight: '1px solid rgba(139,92,246,0.1)' }}
        >
            <div className="mb-10 px-2">
                <Logo size={38} textSize="lg" />
            </div>

            <nav className="flex flex-col gap-2 flex-grow">
                {navItems.map((item) => (
                    <SidebarItem key={item.to} {...item} />
                ))}
            </nav>

            <div className="mt-10 pt-6" style={{ borderTop: '1px solid rgba(139,92,246,0.15)' }}>
                <button
                    onClick={handleSignOut}
                    className="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 w-full"
                    style={{ color: '#9B8FC0' }}
                    onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'rgba(239,68,68,0.1)'; e.currentTarget.style.color = '#F87171'; }}
                    onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = '#9B8FC0'; }}
                >
                    <FaSignOutAlt size={18} />
                    <span className="font-medium">Sign Out</span>
                </button>
            </div>
        </aside>
    );
};

export default Sidebar;
