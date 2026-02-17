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
        <span ref={ref} className="text-3xl font-display font-bold text-slate-900 leading-none">
            {displayValue}{isPercent ? '%' : ''}
        </span>
    );
};

const KpiCard = ({ title, value, icon, children, isPercent, suffix }) => (
    <motion.div
        className="bg-white p-6 rounded-2xl border border-slate-100 shadow-soft hover:shadow-glow hover:border-primary-100 transition-all duration-300 flex flex-col justify-between group h-full"
        whileHover={{ y: -4 }}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
    >
        <div className="flex items-start justify-between mb-4">
            <div className="flex flex-col gap-1">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">{title}</span>
                <div className="flex items-baseline gap-2">
                    <AnimatedNumber value={value} isPercent={isPercent} />
                    {suffix && <span className="text-xs font-medium text-slate-400">{suffix}</span>}
                </div>
            </div>
            <div className="w-12 h-12 rounded-xl bg-primary-50 text-primary-500 flex items-center justify-center group-hover:bg-primary-500 group-hover:text-white transition-colors duration-300">
                {React.cloneElement(icon, { size: 22 })}
            </div>
        </div>

        {children && <div className="mt-2">{children}</div>}
    </motion.div>
);

export default KpiCard;
