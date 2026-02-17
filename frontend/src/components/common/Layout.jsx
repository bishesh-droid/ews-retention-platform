import React from 'react';
import { useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { variants } from '../../utils/motionConfig';
import Sidebar from './Sidebar';
import Header from './Header';

const Layout = ({ children }) => {
    const location = useLocation();

    return (
        <div className="flex h-screen bg-slate-50 overflow-hidden">
            {/* New Sidebar */}
            <Sidebar />

            {/* Main Content Area */}
            <div className="flex-grow flex flex-col min-w-0 overflow-hidden">
                {/* New Header */}
                <Header />

                <main className="flex-grow overflow-y-auto p-8">
                    <div className="max-w-7xl mx-auto">
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={location.pathname}
                                initial="hidden"
                                animate="visible"
                                exit="exit"
                                variants={variants.fadeIn}
                                className="h-full"
                            >
                                {children}
                            </motion.div>
                        </AnimatePresence>
                    </div>
                </main>
            </div>
        </div>
    );
};

export default Layout;
