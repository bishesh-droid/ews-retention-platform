import React, { useState, useRef, useEffect } from 'react';
import { FaSearch, FaBell, FaUserCircle, FaExclamationTriangle, FaChartLine, FaUserGraduate } from 'react-icons/fa';
import ThemeToggle from './ThemeToggle';

const notifications = [
    { id: 1, icon: FaExclamationTriangle, title: '3 students entered high risk', time: '5 min ago' },
    { id: 2, icon: FaChartLine, title: 'Cohort risk score increased 4%', time: '1 hr ago' },
    { id: 3, icon: FaUserGraduate, title: 'Retention report is ready', time: '3 hr ago' },
];

const Header = () => {
    const [showNotifications, setShowNotifications] = useState(false);
    const notifRef = useRef(null);

    useEffect(() => {
        const handleClickOutside = (e) => {
            if (notifRef.current && !notifRef.current.contains(e.target)) {
                setShowNotifications(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    return (
        <header
            className="h-16 px-8 flex items-center justify-between sticky top-0 z-10"
            style={{ backgroundColor: 'transparent' }}
        >
            {/* Search */}
            <div className="flex-grow max-w-md">
                <div
                    className="flex items-center gap-3 rounded-xl px-4 py-2.5 transition-all duration-200"
                    style={{
                        backgroundColor: 'var(--surface-color)',
                        border: '1px solid var(--border-color)',
                        transition: 'background-color 0.25s ease, border-color 0.25s ease',
                    }}
                >
                    <FaSearch className="shrink-0" style={{ color: 'var(--text-muted)' }} />
                    <input
                        type="text"
                        placeholder="Search students or analytics..."
                        className="w-full bg-transparent text-sm outline-none"
                        style={{ color: 'var(--text-primary)' }}
                    />
                </div>
            </div>

            <div className="flex items-center gap-3">
                {/* Theme Toggle */}
                <ThemeToggle />

                {/* Notification Bell */}
                <div className="relative" ref={notifRef}>
                    <button
                        onClick={() => setShowNotifications((v) => !v)}
                        className="w-10 h-10 rounded-xl flex items-center justify-center transition-colors relative"
                        style={{ color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer' }}
                        onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'rgba(139,92,246,0.12)'; e.currentTarget.style.color = 'var(--primary-light)'; }}
                        onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}
                    >
                        <FaBell size={18} />
                        <span
                            className="absolute top-2 right-2 w-2 h-2 bg-rose-500 rounded-full"
                            style={{ border: '2px solid var(--bg-color)' }}
                        />
                    </button>

                    {showNotifications && (
                        <div
                            className="absolute right-0 mt-2 w-80 rounded-2xl shadow-xl z-50 overflow-hidden"
                            style={{
                                backgroundColor: 'var(--surface-color)',
                                border: '1px solid var(--border-color)',
                                boxShadow: 'var(--shadow-lg)',
                                transition: 'background-color 0.25s ease',
                            }}
                        >
                            <div
                                className="px-4 py-3 flex items-center justify-between"
                                style={{ borderBottom: '1px solid var(--border-color)' }}
                            >
                                <span className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>Notifications</span>
                                <span className="text-xs cursor-pointer hover:underline" style={{ color: 'var(--primary-color)' }}>Mark all read</span>
                            </div>
                            <ul>
                                {notifications.map(({ id, icon: Icon, title, time }) => (
                                    <li
                                        key={id}
                                        className="flex items-start gap-3 px-4 py-3 transition-colors cursor-pointer"
                                        style={{ borderBottom: '1px solid var(--border-color)' }}
                                        onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--surface-hover)'}
                                        onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                                    >
                                        <div
                                            className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0 mt-0.5"
                                            style={{ backgroundColor: 'rgba(124,58,237,0.12)' }}
                                        >
                                            <Icon size={14} style={{ color: 'var(--primary-color)' }} />
                                        </div>
                                        <div>
                                            <p className="text-sm" style={{ color: 'var(--text-primary)' }}>{title}</p>
                                            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{time}</p>
                                        </div>
                                    </li>
                                ))}
                            </ul>
                            <div className="px-4 py-3 text-center" style={{ borderTop: '1px solid var(--border-color)' }}>
                                <span className="text-xs cursor-pointer" style={{ color: 'var(--text-muted)' }}>View all notifications</span>
                            </div>
                        </div>
                    )}
                </div>

                <div className="h-8 w-px" style={{ backgroundColor: 'var(--border-color)' }} />

                {/* User Info */}
                <div className="flex items-center gap-3">
                    <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                        style={{ backgroundColor: 'rgba(124,58,237,0.12)', color: 'var(--primary-color)' }}
                    >
                        <FaUserCircle size={26} />
                    </div>
                    <div className="hidden sm:flex flex-col leading-tight">
                        <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Admin User</span>
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Institutional Lead</span>
                    </div>
                </div>
            </div>
        </header>
    );
};

export default Header;
