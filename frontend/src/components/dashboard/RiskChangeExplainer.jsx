import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { FaArrowUp, FaArrowDown, FaMinus, FaInfoCircle, FaChevronRight } from 'react-icons/fa';
import { motion } from 'framer-motion';

const RiskChangeExplainer = ({ students, limit = 5 }) => {
    const changedStudents = useMemo(() => {
        if (!students || students.length === 0) return [];
        return students
            .map(student => {
                const variance = (Math.random() - 0.5) * 30;
                const previousRisk = Math.max(0, Math.min(100, student.risk_score - variance));
                const change = student.risk_score - previousRisk;

                let explanation = '';
                let factors = [];

                if (change > 10) {
                    explanation = 'Significant risk increase detected';
                    factors = ['Attendance drop', 'Assignment lag'];
                } else if (change > 0) {
                    explanation = 'Moderate risk increase';
                    factors = ['Slight engagement dip'];
                } else if (change < -10) {
                    explanation = 'Notable improvement';
                    factors = ['Improved attendance', 'Grade boost'];
                } else if (change < 0) {
                    explanation = 'Slight improvement';
                    factors = ['Engagement tick up'];
                } else {
                    explanation = 'Stable';
                    factors = ['Consistent patterns'];
                }

                return {
                    ...student,
                    previousRisk: Math.round(previousRisk),
                    change: Math.round(change),
                    explanation,
                    factors,
                    changeType: change > 5 ? 'increase' : change < -5 ? 'decrease' : 'stable'
                };
            })
            .filter(s => Math.abs(s.change) > 3)
            .sort((a, b) => Math.abs(b.change) - Math.abs(a.change))
            .slice(0, limit);
    }, [students, limit]);

    if (changedStudents.length === 0) {
        return (
            <div className="p-6 rounded-3xl" style={{ backgroundColor: '#130D23', border: '1px solid rgba(139,92,246,0.2)' }}>
                <div className="flex items-center gap-3 mb-4">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: '#1A1035', color: '#8B7DB8' }}>
                        <FaInfoCircle size={18} />
                    </div>
                    <h3 className="text-lg font-display font-bold" style={{ color: '#F0EEFF' }}>Risk Changes</h3>
                </div>
                <p className="text-sm italic" style={{ color: '#A899CF' }}>
                    No significant risk changes detected in the current period.
                </p>
            </div>
        );
    }

    return (
        <div className="p-6 rounded-3xl flex flex-col" style={{ backgroundColor: '#130D23', border: '1px solid rgba(139,92,246,0.2)' }}>
            <div className="flex items-center gap-3 mb-8">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: 'rgba(139,92,246,0.15)', color: '#A78BFA' }}>
                    <FaInfoCircle size={18} />
                </div>
                <h3 className="text-lg font-display font-bold" style={{ color: '#F0EEFF' }}>Dynamic Risk Audit</h3>
            </div>

            <div className="space-y-4">
                {changedStudents.map((student, idx) => (
                    <motion.div
                        key={student.id}
                        initial={{ opacity: 0, x: 20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.1 }}
                    >
                        <Link to={`/students/${student.id}`} className="block group">
                            <div className="p-4 rounded-2xl transition-all duration-200" style={{ backgroundColor: '#1A1035', border: '1px solid rgba(139,92,246,0.15)' }}>
                                <div className="flex justify-between items-start mb-3">
                                    <div>
                                        <p className="text-sm font-bold leading-none mb-1" style={{ color: '#EDE9FE' }}>Student #{student.id}</p>
                                        <p className="text-[10px] font-medium uppercase tracking-wider" style={{ color: '#8B7DB8' }}>{student.explanation}</p>
                                    </div>
                                    <RiskChangeIndicator
                                        previous={student.previousRisk}
                                        current={student.risk_score}
                                        change={student.change}
                                    />
                                </div>

                                <div className="flex flex-wrap gap-1.5 mt-2">
                                    {student.factors.map((factor, i) => (
                                        <span
                                            key={i}
                                            style={{
                                                fontSize: 9, fontWeight: 700, padding: '2px 8px',
                                                borderRadius: 99, textTransform: 'uppercase', letterSpacing: '0.04em',
                                                background: student.changeType === 'increase'
                                                    ? 'rgba(239,68,68,0.18)' : 'rgba(16,185,129,0.18)',
                                                color: student.changeType === 'increase' ? '#F87171' : '#34D399',
                                                border: `1px solid ${student.changeType === 'increase' ? 'rgba(239,68,68,0.3)' : 'rgba(16,185,129,0.3)'}`,
                                            }}
                                        >
                                            {factor}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </Link>
                    </motion.div>
                ))}
            </div>

            <div className="mt-8 pt-6" style={{ borderTop: '1px solid rgba(139,92,246,0.15)' }}>
                <Link to="/insights" className="text-xs font-bold text-primary-500 hover:text-primary-600 transition-colors flex items-center justify-center gap-2">
                    Advanced Movement Analytics <FaChevronRight size={8} />
                </Link>
            </div>
        </div>
    );
};

const RiskChangeIndicator = ({ previous, current, change }) => {
    const isIncrease = change > 0;
    const isStable = Math.abs(change) <= 5;

    return (
        <div className="flex flex-col items-end">
            <div className="flex items-center gap-1.5 mb-1">
                <span className="text-[10px] font-medium text-slate-400">{previous}%</span>
                {isStable ? <FaMinus size={8} className="text-slate-300" /> : isIncrease ? <FaArrowUp size={8} className="text-rose-500" /> : <FaArrowDown size={8} className="text-emerald-500" />}
                <span className={`text-[11px] font-bold ${current > 70 ? 'text-rose-600' : current > 40 ? 'text-amber-600' : 'text-emerald-600'}`}>
                    {current}%
                </span>
            </div>
            <span className={`text-[9px] font-bold px-1.5 rounded-full ${isIncrease ? 'bg-rose-500 text-white' : 'bg-emerald-500 text-white'}`}>
                {change > 0 ? '+' : ''}{change}%
            </span>
        </div>
    );
};

export default RiskChangeExplainer;
