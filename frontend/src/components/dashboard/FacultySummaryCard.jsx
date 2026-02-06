import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { FaCheckCircle, FaExclamationTriangle, FaUserTie, FaArrowRight } from 'react-icons/fa';
import { motion } from 'framer-motion';

/**
 * Faculty Summary Card Component
 *
 * Provides a quick, actionable summary for faculty members.
 * Shows what they need to do TODAY without overwhelming detail.
 */

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

        // Generate concerns based on patterns
        const topConcerns = [];

        if (critical.length > 3) {
            topConcerns.push({
                severity: 'critical',
                message: `${critical.length} students require immediate attention`,
                action: 'Review critical cases'
            });
        }

        // Check for clusters of high-risk students (simulated course analysis)
        const highRiskPercentage = ((critical.length + highRisk.length) / students.length) * 100;
        if (highRiskPercentage > 15) {
            topConcerns.push({
                severity: 'warning',
                message: `${highRiskPercentage.toFixed(0)}% of students are high-risk`,
                action: 'Consider cohort-level intervention'
            });
        }

        // Generate suggested actions
        const suggestedActions = [];

        if (critical.length > 0) {
            suggestedActions.push({
                priority: 1,
                action: `Schedule calls with ${Math.min(critical.length, 5)} critical-risk students`,
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

        if (needsReview.length > 0) {
            suggestedActions.push({
                priority: 3,
                action: `Review ${needsReview.length} borderline cases this week`,
                type: 'moderate'
            });
        }

        return {
            criticalCount: critical.length,
            highRiskCount: highRisk.length,
            needsReviewCount: needsReview.length,
            recentlyImproved: Math.floor(students.length * 0.05),  // Simulated
            topConcerns,
            suggestedActions: suggestedActions.slice(0, 3)
        };
    }, [students]);

    return (
        <motion.div
            className="glass-panel p-4"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
        >
            <div className="d-flex align-items-center gap-2 mb-4">
                <FaUserTie className="text-primary" />
                <h5 className="mb-0 fw-bold">Faculty Action Summary</h5>
            </div>

            {/* Quick Stats */}
            <div className="d-flex gap-3 mb-4">
                <StatBadge
                    count={summary.criticalCount}
                    label="Critical"
                    color="var(--color-error)"
                    bgColor="rgba(239, 68, 68, 0.1)"
                />
                <StatBadge
                    count={summary.highRiskCount}
                    label="High Risk"
                    color="var(--color-warning)"
                    bgColor="rgba(245, 158, 11, 0.1)"
                />
                <StatBadge
                    count={summary.needsReviewCount}
                    label="Review"
                    color="var(--color-info)"
                    bgColor="rgba(59, 130, 246, 0.1)"
                />
                <StatBadge
                    count={summary.recentlyImproved}
                    label="Improved"
                    color="var(--color-success)"
                    bgColor="rgba(16, 185, 129, 0.1)"
                />
            </div>

            {/* Top Concerns */}
            {summary.topConcerns.length > 0 && (
                <div className="mb-4">
                    <div className="small text-muted text-uppercase fw-semibold mb-2" style={{ letterSpacing: '0.05em' }}>
                        Key Concerns
                    </div>
                    {summary.topConcerns.map((concern, idx) => (
                        <div
                            key={idx}
                            className="d-flex align-items-start gap-2 p-2 rounded mb-2"
                            style={{
                                background: concern.severity === 'critical'
                                    ? 'rgba(239, 68, 68, 0.05)'
                                    : 'rgba(245, 158, 11, 0.05)',
                                borderLeft: `3px solid ${concern.severity === 'critical' ? 'var(--color-error)' : 'var(--color-warning)'}`
                            }}
                        >
                            <FaExclamationTriangle
                                size={14}
                                className="mt-1"
                                style={{
                                    color: concern.severity === 'critical' ? 'var(--color-error)' : 'var(--color-warning)'
                                }}
                            />
                            <div>
                                <div className="small fw-medium text-dark">{concern.message}</div>
                                <div className="small text-muted">{concern.action}</div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Suggested Actions */}
            {summary.suggestedActions.length > 0 && (
                <div className="mb-3">
                    <div className="small text-muted text-uppercase fw-semibold mb-2" style={{ letterSpacing: '0.05em' }}>
                        Suggested Actions
                    </div>
                    {summary.suggestedActions.map((item, idx) => (
                        <div
                            key={idx}
                            className="d-flex align-items-center justify-content-between p-2 rounded mb-2"
                            style={{ background: 'var(--gray-50)' }}
                        >
                            <div className="d-flex align-items-center gap-2">
                                <span
                                    className="badge rounded-pill"
                                    style={{
                                        background: item.type === 'urgent'
                                            ? 'var(--color-error)'
                                            : item.type === 'important'
                                                ? 'var(--color-warning)'
                                                : 'var(--gray-500)',
                                        color: 'white',
                                        fontSize: '0.65rem'
                                    }}
                                >
                                    {item.priority}
                                </span>
                                <span className="small">{item.action}</span>
                            </div>
                            <FaCheckCircle
                                size={14}
                                className="text-muted"
                                style={{ cursor: 'pointer', opacity: 0.5 }}
                                title="Mark as done"
                            />
                        </div>
                    ))}
                </div>
            )}

            {/* Action Links */}
            <div className="d-flex gap-3 pt-3 border-top">
                <Link
                    to="/students"
                    className="btn btn-sm btn-outline-primary d-flex align-items-center gap-2"
                >
                    View All Students <FaArrowRight size={12} />
                </Link>
                <Link
                    to="/interventions"
                    className="btn btn-sm btn-primary d-flex align-items-center gap-2"
                >
                    Intervention Queue <FaArrowRight size={12} />
                </Link>
            </div>
        </motion.div>
    );
};

const StatBadge = ({ count, label, color, bgColor }) => (
    <div
        className="text-center px-3 py-2 rounded"
        style={{ background: bgColor, minWidth: '70px' }}
    >
        <div
            className="fw-bold"
            style={{
                fontSize: 'var(--font-size-h2)',
                color,
                fontFamily: 'var(--font-family-mono)'
            }}
        >
            {count}
        </div>
        <div className="small" style={{ color, opacity: 0.8 }}>
            {label}
        </div>
    </div>
);

export default FacultySummaryCard;
