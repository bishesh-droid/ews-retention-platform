import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { FaArrowUp, FaArrowDown, FaMinus, FaInfoCircle } from 'react-icons/fa';
import { motion } from 'framer-motion';

/**
 * Risk Change Explainer Component
 *
 * Explains WHY risk scores changed for students.
 * Helps faculty understand trends without diving into detailed analytics.
 */

const RiskChangeExplainer = ({ students, limit = 5 }) => {
    const changedStudents = useMemo(() => {
        if (!students || students.length === 0) return [];

        // Simulate risk changes (in production, this would come from historical data)
        // For now, we'll create mock changes based on current risk scores
        return students
            .map(student => {
                // Simulate previous risk score (random variance for demo)
                const variance = (Math.random() - 0.5) * 30;
                const previousRisk = Math.max(0, Math.min(100, student.risk_score - variance));
                const change = student.risk_score - previousRisk;

                // Generate explanation based on the change direction
                let explanation = '';
                let factors = [];

                if (change > 10) {
                    explanation = 'Significant risk increase detected';
                    factors = ['Attendance dropped', 'Assignment completion declined'];
                } else if (change > 0) {
                    explanation = 'Moderate risk increase';
                    factors = ['Slight engagement decrease'];
                } else if (change < -10) {
                    explanation = 'Notable improvement';
                    factors = ['Improved attendance', 'Better assignment completion'];
                } else if (change < 0) {
                    explanation = 'Slight improvement';
                    factors = ['Minor engagement increase'];
                } else {
                    explanation = 'Stable';
                    factors = ['No significant changes'];
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
            .filter(s => Math.abs(s.change) > 3)  // Only show meaningful changes
            .sort((a, b) => Math.abs(b.change) - Math.abs(a.change))
            .slice(0, limit);
    }, [students, limit]);

    if (changedStudents.length === 0) {
        return (
            <div className="glass-panel p-4">
                <div className="d-flex align-items-center gap-2 mb-3">
                    <FaInfoCircle className="text-info" />
                    <h5 className="mb-0 fw-bold">Risk Changes</h5>
                </div>
                <p className="text-muted small mb-0">
                    No significant risk changes detected in the current period.
                </p>
            </div>
        );
    }

    return (
        <div className="glass-panel p-4">
            <div className="d-flex align-items-center gap-2 mb-4">
                <FaInfoCircle className="text-info" />
                <h5 className="mb-0 fw-bold">Why Risk Changed</h5>
            </div>

            <div className="d-flex flex-column gap-3">
                {changedStudents.map((student, idx) => (
                    <motion.div
                        key={student.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: idx * 0.1 }}
                    >
                        <Link
                            to={`/students/${student.id}`}
                            className="text-decoration-none"
                        >
                            <div
                                className="p-3 rounded-3 border"
                                style={{
                                    borderLeft: `4px solid ${student.changeType === 'increase'
                                        ? 'var(--color-error)'
                                        : student.changeType === 'decrease'
                                            ? 'var(--color-success)'
                                            : 'var(--gray-400)'
                                        }`,
                                    background: 'var(--gray-50)',
                                    transition: 'all 0.2s ease'
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.background = 'white';
                                    e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.background = 'var(--gray-50)';
                                    e.currentTarget.style.boxShadow = 'none';
                                }}
                            >
                                <div className="d-flex justify-content-between align-items-start mb-2">
                                    <div>
                                        <span className="fw-semibold text-dark">
                                            Student #{student.id}
                                        </span>
                                        <div className="small text-muted">
                                            {student.explanation}
                                        </div>
                                    </div>
                                    <div className="d-flex align-items-center gap-2">
                                        <RiskChangeIndicator
                                            previousRisk={student.previousRisk}
                                            currentRisk={student.risk_score}
                                            change={student.change}
                                        />
                                    </div>
                                </div>

                                <div className="d-flex flex-wrap gap-2">
                                    {student.factors.map((factor, i) => (
                                        <span
                                            key={i}
                                            className="badge"
                                            style={{
                                                background: student.changeType === 'increase'
                                                    ? 'rgba(239, 68, 68, 0.1)'
                                                    : 'rgba(16, 185, 129, 0.1)',
                                                color: student.changeType === 'increase'
                                                    ? '#DC2626'
                                                    : '#059669',
                                                fontSize: '0.75rem'
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

            <div className="mt-3 pt-3 border-top">
                <Link
                    to="/insights"
                    className="small text-primary text-decoration-none"
                >
                    View detailed analytics →
                </Link>
            </div>
        </div>
    );
};

const RiskChangeIndicator = ({ previousRisk, currentRisk, change }) => {
    const Icon = change > 0 ? FaArrowUp : change < 0 ? FaArrowDown : FaMinus;
    const color = change > 0 ? 'var(--color-error)' : change < 0 ? 'var(--color-success)' : 'var(--gray-500)';

    return (
        <div className="d-flex align-items-center gap-2">
            <span className="small text-muted" style={{ fontFamily: 'var(--font-family-mono)' }}>
                {previousRisk}%
            </span>
            <Icon size={12} style={{ color }} />
            <span
                className="fw-bold"
                style={{
                    fontFamily: 'var(--font-family-mono)',
                    color: currentRisk > 70 ? 'var(--color-error)' : currentRisk > 40 ? 'var(--color-warning)' : 'var(--color-success)'
                }}
            >
                {currentRisk}%
            </span>
            <span
                className="badge rounded-pill"
                style={{
                    background: color,
                    color: 'white',
                    fontSize: '0.65rem',
                    padding: '2px 6px'
                }}
            >
                {change > 0 ? '+' : ''}{change}%
            </span>
        </div>
    );
};

export default RiskChangeExplainer;
