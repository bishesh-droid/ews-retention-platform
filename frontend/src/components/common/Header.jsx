import React from 'react';
import { FaSearch, FaBell, FaUserCircle } from 'react-icons/fa';

const Header = () => {
    return (
        <header className="h-20 bg-white/80 backdrop-blur-md border-b border-slate-200 px-8 flex items-center justify-between sticky top-0 z-10">
            <div className="flex-grow max-w-md">
                <div className="relative group">
                    <FaSearch className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-primary-500 transition-colors" />
                    <input
                        type="text"
                        placeholder="Search students or analytics..."
                        className="w-full bg-slate-100 border-transparent focus:bg-white focus:border-primary-500 focus:ring-4 focus:ring-primary-100 rounded-xl py-2.5 pl-11 pr-4 text-sm transition-all duration-200 outline-none"
                    />
                </div>
            </div>

            <div className="flex items-center gap-4">
                <button className="w-10 h-10 rounded-xl hover:bg-slate-100 flex items-center justify-center text-slate-500 transition-colors relative">
                    <FaBell size={18} />
                    <span className="absolute top-2.5 right-2.5 w-2 h-2 bg-rose-500 border-2 border-white rounded-full"></span>
                </button>
                <div className="h-8 w-px bg-slate-200 mx-2"></div>
                <div className="flex items-center gap-3 pl-2">
                    <div className="text-right hidden sm:block">
                        <p className="text-sm font-semibold text-slate-900 leading-none">Admin User</p>
                        <p className="text-xs text-slate-500 mt-1">Institutional Lead</p>
                    </div>
                    <button className="w-10 h-10 rounded-xl bg-slate-100 flex items-center justify-center text-slate-400 hover:text-primary-500 transition-colors">
                        <FaUserCircle size={28} />
                    </button>
                </div>
            </div>
        </header>
    );
};

export default Header;
