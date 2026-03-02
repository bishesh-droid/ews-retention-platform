import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { FaCheckCircle, FaExclamationTriangle, FaUserTie, FaArrowRight } from 'react-icons/fa';
import { motion } from 'framer-motion';

const FacultySummaryCard = ({ students }) => {
    const summary = useMemo(() => {
        if (!students || students.length === 0) {
            return {
                criticalCount: 0,
                highRiskCount: 0,
                needsReviewCount: 0,
                recentlyImproved: 0,
                topConcerns: [],
                suggestedActions: []
            };
        }

        const critical = students.filter(s => s.risk_score > 85);
        const highRisk = students.filter(s => s.risk_score > 70 && s.risk_score <= 85);
        const needsReview = students.filter(s => s.risk_score > 60 && s.risk_score <= 70);

        const topConcerns = [];
        if (critical.length > 3) {
            topConcerns.push({
                severity: 'critical',
                message: `${critical.length} students require immediate attention`,
                action: 'Review critical cases'
            });
        }

        const highRiskPercentage = ((critical.length + highRisk.length) / students.length) * 100;
        if (highRiskPercentage > 15) {
            topConcerns.push({
                severity: 'warning',
                message: `${highRiskPercentage.toFixed(0)}% of students are high-risk`,
                action: 'Consider cohort-level intervention'
            });
        }

        const suggestedActions = [];
        if (critical.length > 0) {
            suggestedActions.push({
                priority: 1,
                action: `Schedule calls with ${Math.min(critical.length, 5)} critical cases`,
                type: 'urgent'
            });
        }
        if (highRisk.length > 0) {
            suggestedActions.push({
                priority: 2,
                action: `Send check-in emails to ${highRisk.length} high-risk students`,
                type: 'important'
            });
        }

        return {
            criticalCount: critical.length,
            highRiskCount: highRisk.length,
            needsReviewCount: needsReview.length,
            recentlyImproved: Math.floor(students.length * 0.05),
            topConcerns,
            suggestedActions: suggestedActions.slice(0, 3)
        };
    }, [students]);

    return (
        <motion.div
            className="bg-slate-900 text-white p-8 rounded-3xl shadow-xl overflow-hidden relative"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.2 }}
        >
            {/* Decorative background circle */}
            <div className="absolute -right-20 -top-20 w-64 h-64 bg-primary-500/10 rounded-full blur-3xl"></div>

            <div className="relative z-10">
                <div className="flex items-center gap-3 mb-8">
                    <div className="w-12 h-12 rounded-2xl bg-white/10 flex items-center justify-center text-primary-400">
                        <FaUserTie size={24} />
                    </div>
                    <div>
                        <h2 className="text-2xl font-display font-bold tracking-tight">Faculty Action Brief</h2>
                        <p className="text-slate-400 text-sm">Prioritized interventions for today</p>
                    </div>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10">
                    <StatBadge count={summary.criticalCount} label="Critical" color="text-rose-400" />
                    <StatBadge count={summary.highRiskCount} label="High Risk" color="text-amber-400" />
                    <StatBadge count={summary.needsReviewCount} label="Review" color="text-blue-400" />
                    <StatBadge count={summary.recentlyImproved} label="Improved" color="text-emerald-400" />
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <div>
                        <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">Key Concerns</h4>
                        <div className="space-y-3">
                            {summary.topConcerns.map((concern, idx) => (
                                <div key={idx} className="flex gap-4 p-4 rounded-2xl bg-white/5 border border-white/10">
                                    <FaExclamationTriangle className={concern.severity === 'critical' ? 'text-rose-400' : 'text-amber-400'} />
                                    <div>
                                        <p className="text-sm font-bold leading-none mb-1">{concern.message}</p>
                                        <p className="text-xs text-slate-400">{concern.action}</p>
                                    </div>
                                </div>
                            ))}
                            {summary.topConcerns.length === 0 && <p className="text-sm text-slate-500 italic">No major cohort concerns.</p>}
                        </div>
                    </div>

                    <div>
                        <h4 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-4">Suggested Actions</h4>
                        <div className="space-y-3">
                            {summary.suggestedActions.map((item, idx) => (
                                <div key={idx} className="flex items-center justify-between p-4 rounded-2xl bg-white/5 border border-white/10 hover:bg-white/[0.08] transition-colors group">
                                    <div className="flex items-center gap-4">
                                        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${item.type === 'urgent' ? 'bg-rose-500' : 'bg-primary-500'}`}>
                                            {item.priority}
                                        </span>
                                        <span className="text-sm font-medium">{item.action}</span>
                                    </div>
                                    <FaCheckCircle className="text-slate-600 group-hover:text-emerald-400 transition-colors cursor-pointer" />
                                </div>
                            ))}
                        </div>
                    </div>
                </div>

                <div className="mt-10 pt-8 border-t border-white/10 flex flex-wrap gap-4">
                    <Link to="/students" className="px-6 py-2.5 rounded-xl font-bold text-sm transition-all flex items-center gap-2" style={{ border: '1px solid rgba(139,92,246,0.35)', color: '#C4B5FD', textDecoration: 'none' }}>
                        View All Students <FaArrowRight size={10} />
                    </Link>
                    <Link to="/interventions" className="px-6 py-2.5 rounded-xl font-bold text-sm transition-all flex items-center gap-2" style={{ backgroundColor: '#7C3AED', color: '#fff', textDecoration: 'none' }}>
                        Intervention Queue <FaArrowRight size={10} />
                    </Link>
                </div>
            </div>
        </motion.div>
    );
};

const StatBadge = ({ count, label, color }) => (
    <div className="bg-white/5 p-4 rounded-2xl border border-white/10 text-center">
        <p className={`text-3xl font-display font-bold mb-1 ${color}`}>{count}</p>
        <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{label}</p>
    </div>
);

export default FacultySummaryCard;
