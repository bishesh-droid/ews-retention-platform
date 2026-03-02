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
        <span ref={ref} className="text-3xl font-display font-bold leading-none" style={{ color: '#EDE9FE' }}>
            {displayValue}{isPercent ? '%' : ''}
        </span>
    );
};

const KpiCard = ({ title, value, icon, children, isPercent, suffix }) => (
    <motion.div
        className="p-6 rounded-2xl transition-all duration-300 flex flex-col justify-between group h-full"
        style={{ backgroundColor: '#130D23', border: '1px solid rgba(139,92,246,0.18)' }}
        whileHover={{ y: -6, boxShadow: '0 0 30px rgba(139,92,246,0.25), 0 8px 32px rgba(0,0,0,0.4)', borderColor: 'rgba(139,92,246,0.5)' }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
    >
        <div className="flex items-start justify-between mb-4">
            <div className="flex flex-col gap-1">
                <span className="text-xs font-bold uppercase tracking-wider" style={{ color: '#8B7DB8' }}>{title}</span>
                <div className="flex items-baseline gap-2">
                    <AnimatedNumber value={value} isPercent={isPercent} />
                    {suffix && <span className="text-xs font-medium" style={{ color: '#8B7DB8' }}>{suffix}</span>}
                </div>
            </div>
            <div className="w-12 h-12 rounded-xl flex items-center justify-center transition-all duration-300" style={{ backgroundColor: 'rgba(139,92,246,0.15)', color: '#A78BFA' }}>
                {React.cloneElement(icon, { size: 22 })}
            </div>
        </div>

        {children && <div className="mt-2">{children}</div>}
    </motion.div>
);

export default KpiCard;
