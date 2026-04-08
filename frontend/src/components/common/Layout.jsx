import React from 'react';
import { useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { variants } from '../../utils/motionConfig';
import Sidebar from './Sidebar';
import Header from './Header';

const GlobalBackground = () => (
    <div style={{ position: 'fixed', inset: 0, overflow: 'hidden', pointerEvents: 'none', zIndex: 0 }}>
        {/* Base gradient — driven by CSS variable, switches with theme */}
        <div style={{
            position: 'absolute', inset: 0,
            background: `
                radial-gradient(ellipse 70% 55% at 15% 10%, var(--bg-orb-primary) 0%, transparent 60%),
                radial-gradient(ellipse 55% 45% at 85% 85%, var(--bg-orb-secondary) 0%, transparent 55%),
                radial-gradient(ellipse 40% 35% at 70% 5%, var(--bg-orb-gold) 0%, transparent 50%),
                var(--bg-gradient)
            `,
            transition: 'background 0.25s ease',
        }} />
        {/* Orbs */}
        <div style={{ position: 'absolute', top: '8%', left: '20%', width: 500, height: 500, borderRadius: '50%', background: 'radial-gradient(circle, var(--bg-orb-primary) 0%, transparent 70%)', filter: 'blur(50px)', transition: 'background 0.25s ease' }} />
        <div style={{ position: 'absolute', bottom: '10%', right: '8%', width: 420, height: 420, borderRadius: '50%', background: 'radial-gradient(circle, var(--bg-orb-secondary) 0%, transparent 70%)', filter: 'blur(45px)', transition: 'background 0.25s ease' }} />
        <div style={{ position: 'absolute', top: '45%', right: '30%', width: 250, height: 250, borderRadius: '50%', background: 'radial-gradient(circle, var(--bg-orb-gold) 0%, transparent 70%)', filter: 'blur(35px)', transition: 'background 0.25s ease' }} />
        {/* Dot grid */}
        <div style={{
            position: 'absolute', inset: 0,
            backgroundImage: 'radial-gradient(circle, var(--bg-dot-color) 1px, transparent 1px)',
            backgroundSize: '36px 36px',
            transition: 'opacity 0.25s ease',
        }} />
    </div>
);

const Layout = ({ children }) => {
    const location = useLocation();

    return (
        <div
            className="flex h-screen overflow-hidden"
            style={{ backgroundColor: 'var(--bg-color)', position: 'relative', transition: 'background-color 0.25s ease' }}
        >
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
