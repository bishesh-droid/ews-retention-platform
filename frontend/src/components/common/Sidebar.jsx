import React from 'react';
import { NavLink } from 'react-router-dom';
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

const SidebarItem = ({ to, icon: Icon, label }) => {
    return (
        <NavLink
            to={to}
            className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200 group ${isActive
                    ? 'bg-primary-500 text-white shadow-glow'
                    : 'text-slate-500 hover:bg-slate-100'
                }`
            }
        >
            <Icon size={18} className="shrink-0" />
            <span className="font-medium">{label}</span>
        </NavLink>
    );
};

const Sidebar = () => {
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
        <aside className="w-64 bg-white border-r border-slate-200 h-screen sticky top-0 flex flex-col p-6 overflow-y-auto">
            <div className="flex items-center gap-3 mb-10 px-2">
                <div className="w-10 h-10 bg-primary-500 rounded-xl flex items-center justify-center text-white shadow-glow">
                    <FaUserGraduate size={20} />
                </div>
                <span className="text-xl font-display font-bold text-slate-900 tracking-tight">EWS Retention</span>
            </div>

            <nav className="flex flex-col gap-2 flex-grow">
                {navItems.map((item) => (
                    <SidebarItem key={item.to} {...item} />
                ))}
            </nav>

            <div className="mt-10 pt-6 border-t border-slate-100">
                <button className="flex items-center gap-3 px-4 py-3 rounded-xl text-slate-500 hover:bg-rose-50 hover:text-rose-600 transition-all duration-200 w-full">
                    <FaSignOutAlt size={18} />
                    <span className="font-medium">Sign Out</span>
                </button>
            </div>
        </aside>
    );
};

export default Sidebar;
