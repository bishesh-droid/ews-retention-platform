import React from 'react';
import { useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { variants } from '../../utils/motionConfig';
import Sidebar from './Sidebar';
import Header from './Header';

const GlobalBackground = () => (
    <div style={{ position: 'fixed', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
        {/* Base gradient */}
        <div style={{
            position: 'absolute', inset: 0,
            background: `
                radial-gradient(ellipse 70% 55% at 15% 10%, rgba(124,58,237,0.16) 0%, transparent 60%),
                radial-gradient(ellipse 55% 45% at 85% 85%, rgba(109,40,217,0.13) 0%, transparent 55%),
                radial-gradient(ellipse 40% 35% at 70% 5%, rgba(245,158,11,0.05) 0%, transparent 50%),
                linear-gradient(160deg, #100920 0%, #0B0714 45%, #0E0B1F 100%)
            `
        }} />
        {/* Orbs */}
        <div style={{ position: 'absolute', top: '8%', left: '20%', width: 500, height: 500, borderRadius: '50%', background: 'radial-gradient(circle, rgba(124,58,237,0.1) 0%, transparent 70%)', filter: 'blur(50px)' }} />
        <div style={{ position: 'absolute', bottom: '10%', right: '8%', width: 420, height: 420, borderRadius: '50%', background: 'radial-gradient(circle, rgba(139,92,246,0.09) 0%, transparent 70%)', filter: 'blur(45px)' }} />
        <div style={{ position: 'absolute', top: '45%', right: '30%', width: 250, height: 250, borderRadius: '50%', background: 'radial-gradient(circle, rgba(245,158,11,0.05) 0%, transparent 70%)', filter: 'blur(35px)' }} />
        {/* Dot grid */}
        <div style={{
            position: 'absolute', inset: 0,
            backgroundImage: 'radial-gradient(circle, rgba(139,92,246,0.1) 1px, transparent 1px)',
            backgroundSize: '36px 36px',
        }} />
    </div>
);

const Layout = ({ children }) => {
    const location = useLocation();

    return (
        <div className="flex h-screen overflow-hidden" style={{ backgroundColor: '#0B0714', position: 'relative' }}>
            <GlobalBackground />

            {/* Sidebar */}
            <div style={{ position: 'relative', zIndex: 10 }}>
                <Sidebar />
            </div>

            {/* Main Content Area */}
            <div className="flex-grow flex flex-col min-w-0 overflow-hidden" style={{ position: 'relative', zIndex: 10 }}>
                <Header />

                <main className="flex-grow overflow-y-auto">
                    <div style={{ padding: '3rem 2.5rem 2rem 2.5rem' }}>
                        <AnimatePresence mode="wait">
                            <motion.div
                                key={location.pathname}
                                initial="hidden"
                                animate="visible"
                                exit="exit"
                                variants={variants.fadeIn}
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
