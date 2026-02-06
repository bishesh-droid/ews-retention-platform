import React from 'react';
import { motion, animate } from 'framer-motion';
import { useInView } from 'react-intersection-observer';
import { useState, useEffect } from 'react';

const AnimatedNumber = ({ value, isPercent = false }) => {
    const [ref, inView] = useInView({ triggerOnce: true, threshold: 0.1 });
    const [displayValue, setDisplayValue] = useState(0);

    useEffect(() => {
        if (inView) {
            const controls = animate(0, value, {
                duration: 1.5,
                ease: "easeOut",
                onUpdate(latest) {
                    setDisplayValue(Math.round(latest));
                }
            });
            return () => controls.stop();
        }
    }, [inView, value]);

    return (
        <span ref={ref} className="fw-bold text-gradient display-6">
            {displayValue}{isPercent ? '%' : ''}
        </span>
    );
};

const KpiCard = ({ title, value, icon, children, isPercent }) => (
    <motion.div
        className="glass-panel p-4 h-100 d-flex flex-column justify-content-between position-relative overflow-hidden"
        whileHover={{ y: -5, boxShadow: 'var(--shadow-glow)' }}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
    >
        <div className="d-flex align-items-center justify-content-between mb-3">
            <div>
                <h6 className="text-secondary text-uppercase fw-bold mb-1" style={{ fontSize: '0.75rem', letterSpacing: '0.05em' }}>{title}</h6>
                <AnimatedNumber value={value} isPercent={isPercent} />
            </div>
            <div className="p-3 rounded-circle" style={{ background: 'rgba(79, 70, 229, 0.1)', color: 'var(--primary-color)' }}>
                {React.cloneElement(icon, { size: 24 })}
            </div>
        </div>
        {children && <div className="mt-2">{children}</div>}

        {/* Decorative background element */}
        <div style={{
            position: 'absolute',
            top: '-50%',
            right: '-10%',
            width: '150px',
            height: '150px',
            background: 'radial-gradient(circle, rgba(79,70,229,0.1) 0%, rgba(0,0,0,0) 70%)',
            zIndex: 0,
            pointerEvents: 'none'
        }} />
    </motion.div>
);

export default KpiCard;
