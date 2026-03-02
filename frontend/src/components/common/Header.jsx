import React, { useState, useRef, useEffect } from 'react';
import { FaSearch, FaBell, FaUserCircle, FaExclamationTriangle, FaChartLine, FaUserGraduate } from 'react-icons/fa';

const notifications = [
    { id: 1, icon: FaExclamationTriangle, color: 'text-rose-500 bg-rose-50', title: '3 students entered high risk', time: '5 min ago' },
    { id: 2, icon: FaChartLine, color: 'text-amber-500 bg-amber-50', title: 'Cohort risk score increased 4%', time: '1 hr ago' },
    { id: 3, icon: FaUserGraduate, color: 'text-primary-500 bg-primary-50', title: 'Retention report is ready', time: '3 hr ago' },
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
            <div className="flex-grow max-w-md">
                <div
                    className="flex items-center gap-3 rounded-xl px-4 py-2.5 transition-all duration-200 group"
                    style={{ backgroundColor: '#1A1035', border: '1px solid rgba(139,92,246,0.2)' }}
                >
                    <FaSearch className="shrink-0 transition-colors" style={{ color: '#6B5E8E' }} />
                    <input
                        type="text"
                        placeholder="Search students or analytics..."
                        className="w-full bg-transparent text-sm outline-none"
                        style={{ color: '#EDE9FE' }}
                    />
                </div>
            </div>

            <div className="flex items-center gap-4">
                {/* Notification Bell */}
                <div className="relative" ref={notifRef}>
                    <button
                        onClick={() => setShowNotifications((v) => !v)}
                        className="w-10 h-10 rounded-xl flex items-center justify-center transition-colors relative"
                        style={{ color: '#8B7DB8' }}
                        onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'rgba(139,92,246,0.12)'; e.currentTarget.style.color = '#C4B5FD'; }}
                        onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'transparent'; e.currentTarget.style.color = '#8B7DB8'; }}
                    >
                        <FaBell size={18} />
                        <span className="absolute top-2 right-2 w-2 h-2 bg-rose-500 rounded-full" style={{ border: '2px solid #0F0A1E' }}></span>
                    </button>

                    {showNotifications && (
                        <div
                            className="absolute right-0 mt-2 w-80 rounded-2xl shadow-xl z-50 overflow-hidden"
                            style={{ backgroundColor: '#130D23', border: '1px solid rgba(139,92,246,0.25)', boxShadow: '0 20px 40px rgba(0,0,0,0.5)' }}
                        >
                            <div className="px-4 py-3 flex items-center justify-between" style={{ borderBottom: '1px solid rgba(139,92,246,0.15)' }}>
                                <span className="font-semibold text-sm" style={{ color: '#EDE9FE' }}>Notifications</span>
                                <span className="text-xs cursor-pointer hover:underline" style={{ color: '#8B5CF6' }}>Mark all read</span>
                            </div>
                            <ul>
                                {notifications.map(({ id, icon: Icon, title, time }) => (
                                    <li
                                        key={id}
                                        className="flex items-start gap-3 px-4 py-3 transition-colors cursor-pointer"
                                        style={{ borderBottom: '1px solid rgba(139,92,246,0.08)' }}
                                        onMouseEnter={e => e.currentTarget.style.backgroundColor = 'rgba(139,92,246,0.08)'}
                                        onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                                    >
                                        <div className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0 mt-0.5" style={{ backgroundColor: 'rgba(139,92,246,0.15)' }}>
                                            <Icon size={14} style={{ color: '#A78BFA' }} />
                                        </div>
                                        <div>
                                            <p className="text-sm" style={{ color: '#DDD6FE' }}>{title}</p>
                                            <p className="text-xs mt-0.5" style={{ color: '#6B5E8E' }}>{time}</p>
                                        </div>
                                    </li>
                                ))}
                            </ul>
                            <div className="px-4 py-3 text-center" style={{ borderTop: '1px solid rgba(139,92,246,0.15)' }}>
                                <span className="text-xs cursor-pointer transition-colors" style={{ color: '#6B5E8E' }}>View all notifications</span>
                            </div>
                        </div>
                    )}
                </div>

                <div className="h-8 w-px" style={{ backgroundColor: 'rgba(139,92,246,0.2)' }}></div>

                {/* User Info */}
                <div className="flex items-center gap-3">
                    <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                        style={{ backgroundColor: 'rgba(139,92,246,0.15)', color: '#A78BFA' }}
                    >
                        <FaUserCircle size={26} />
                    </div>
                    <div className="hidden sm:flex flex-col leading-tight">
                        <span className="text-sm font-semibold" style={{ color: '#EDE9FE' }}>Admin User</span>
                        <span className="text-xs" style={{ color: '#8B7DB8' }}>Institutional Lead</span>
                    </div>
                </div>
            </div>
        </header>
    );
};

export default Header;
