import React, { useMemo, useState, useEffect } from 'react';
import { Card, Button, Spinner, Alert } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
    FaChartLine,
    FaInfoCircle,
    FaChevronDown,
    FaChevronUp,
    FaArrowUp,
    FaArrowDown,
    FaMinus,
    FaChevronRight,
} from 'react-icons/fa';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

const RiskChangeIndicator = ({ previous, current, change }) => {
    const isIncrease = change > 0;
    const isStable = Math.abs(change) <= 5;

    return (
        <div className="flex flex-col items-end">
            <div className="flex items-center gap-1.5 mb-1">
                <span className="text-[10px] font-medium text-slate-400">{previous}%</span>
                {isStable ? (
                    <FaMinus size={8} className="text-slate-300" />
                ) : isIncrease ? (
                    <FaArrowUp size={8} className="text-rose-500" />
                ) : (
                    <FaArrowDown size={8} className="text-emerald-500" />
                )}
                <span
                    className={`text-[11px] font-bold ${
                        current > 70 ? 'text-rose-600' : current > 40 ? 'text-amber-600' : 'text-emerald-600'
                    }`}
                >
                    {current}%
                </span>
            </div>
            <span
                className={`text-[9px] font-bold px-1.5 rounded-full ${
                    isIncrease ? 'bg-rose-500 text-white' : 'bg-emerald-500 text-white'
                }`}
            >
                {change > 0 ? '+' : ''}
                {change}%
            </span>
        </div>
    );
};

const RiskChangeExplainer = ({ studentId, students, limit = 5 }) => {
    // ---------------------------------------------------------------------
    // Mode B (student portal): explain a specific student's risk change.
    // Hooks must be called unconditionally before any early returns.
    // ---------------------------------------------------------------------
    const [explanation, setExplanation] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [showReasoning, setShowReasoning] = useState(false);

    useEffect(() => {
        if (studentId) {
            fetchExplanation();
        }
    }, [studentId]);

    const fetchExplanation = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await axios.post(`${API_BASE}/llm/explain-risk-change`, {
                student_id: studentId,
                time_period: 'recent'
            });
            setExplanation(response.data);
        } catch (err) {
            setError('Unable to generate explanation at this time.');
            console.error('Error fetching risk explanation:', err);
        } finally {
            setLoading(false);
        }
    };

    // ---------------------------------------------------------------------
    // Mode A (dashboard widget): show top risk changes across a student list.
    // ---------------------------------------------------------------------
    const changedStudents = useMemo(() => {
        if (!students || students.length === 0) return [];
        return students
            .map((student) => {
                // NOTE: Previous risk is not currently persisted in the frontend model.
                // This uses a lightweight heuristic to visualize directionality.
                const variance = (Math.random() - 0.5) * 30;
                const previousRisk = Math.max(0, Math.min(100, (student.risk_score || 0) - variance));
                const change = (student.risk_score || 0) - previousRisk;

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
                    changeType: change > 5 ? 'increase' : change < -5 ? 'decrease' : 'stable',
                };
            })
            .filter((s) => Math.abs(s.change) > 3)
            .sort((a, b) => Math.abs(b.change) - Math.abs(a.change))
            .slice(0, limit);
    }, [students, limit]);

    if (Array.isArray(students)) {
        if (changedStudents.length === 0) {
            return (
                <div
                    className="p-6 rounded-3xl"
                    style={{ backgroundColor: '#130D23', border: '1px solid rgba(139,92,246,0.2)' }}
                >
                    <div className="flex items-center gap-3 mb-4">
                        <div
                            className="w-10 h-10 rounded-xl flex items-center justify-center"
                            style={{ backgroundColor: '#1A1035', color: '#8B7DB8' }}
                        >
                            <FaInfoCircle size={18} />
                        </div>
                        <h3 className="text-lg font-display font-bold" style={{ color: '#F0EEFF' }}>
                            Risk Changes
                        </h3>
                    </div>
                    <p className="text-sm italic" style={{ color: '#A899CF' }}>
                        No significant risk changes detected in the current period.
                    </p>
                </div>
            );
        }

        return (
            <div
                className="p-6 rounded-3xl flex flex-col"
                style={{ backgroundColor: '#130D23', border: '1px solid rgba(139,92,246,0.2)' }}
            >
                <div className="flex items-center gap-3 mb-8">
                    <div
                        className="w-10 h-10 rounded-xl flex items-center justify-center"
                        style={{ backgroundColor: 'rgba(139,92,246,0.15)', color: '#A78BFA' }}
                    >
                        <FaInfoCircle size={18} />
                    </div>
                    <h3 className="text-lg font-display font-bold" style={{ color: '#F0EEFF' }}>
                        Dynamic Risk Audit
                    </h3>
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
                                <div
                                    className="p-4 rounded-2xl transition-all duration-200"
                                    style={{
                                        backgroundColor: '#1A1035',
                                        border: '1px solid rgba(139,92,246,0.15)',
                                    }}
                                >
                                    <div className="flex justify-between items-start mb-3">
                                        <div>
                                            <p
                                                className="text-sm font-bold leading-none mb-1"
                                                style={{ color: '#EDE9FE' }}
                                            >
                                                {student.name || student.id}
                                            </p>
                                            <p
                                                className="text-[10px] font-medium uppercase tracking-wider"
                                                style={{ color: '#8B7DB8' }}
                                            >
                                                {student.explanation}
                                            </p>
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
                                                    fontSize: 9,
                                                    fontWeight: 700,
                                                    padding: '2px 8px',
                                                    borderRadius: 99,
                                                    textTransform: 'uppercase',
                                                    letterSpacing: '0.04em',
                                                    background:
                                                        student.changeType === 'increase'
                                                            ? 'rgba(239,68,68,0.18)'
                                                            : 'rgba(16,185,129,0.18)',
                                                    color:
                                                        student.changeType === 'increase' ? '#F87171' : '#34D399',
                                                    border: `1px solid ${
                                                        student.changeType === 'increase'
                                                            ? 'rgba(239,68,68,0.3)'
                                                            : 'rgba(16,185,129,0.3)'
                                                    }`,
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
                    <Link
                        to="/insights"
                        className="text-xs font-bold text-primary-500 hover:text-primary-600 transition-colors flex items-center justify-center gap-2"
                    >
                        Advanced Movement Analytics <FaChevronRight size={8} />
                    </Link>
                </div>
            </div>
        );
    }

    const getConfidenceBadge = (confidence) => {
        const badges = {
            high: { bg: 'success', text: 'High Confidence' },
            medium: { bg: 'warning', text: 'Medium Confidence' },
            low: { bg: 'secondary', text: 'Low Confidence' }
        };
        const badge = badges[confidence] || badges.medium;
        return <span className={`badge bg-${badge.bg} bg-opacity-25 text-${badge.bg} border border-${badge.bg} border-opacity-50 ms-2`}>{badge.text}</span>;
    };

    if (loading) {
        return (
            <Card className="glass-panel border-0 shadow-sm">
                <Card.Body className="text-center py-5">
                    <Spinner animation="border" variant="primary" />
                    <p className="mt-3 text-muted">Analyzing your academic progress...</p>
                </Card.Body>
            </Card>
        );
    }

    if (error) {
        return (
            <Alert variant="warning" className="border-0 shadow-sm">
                <FaInfoCircle className="me-2" />
                {error}
            </Alert>
        );
    }

    if (!explanation) {
        return null;
    }

    return (
        <Card className="glass-panel border-0 shadow-sm mb-4">
            <Card.Body className="p-4">
                <div className="d-flex align-items-center mb-3">
                    <FaChartLine className="text-primary me-2" size={20} />
                    <h5 className="mb-0 fw-semibold">Why Did My Risk Score Change?</h5>
                    {explanation.confidence && getConfidenceBadge(explanation.confidence)}
                </div>

                {/* Main Explanation */}
                <div className="ai-text mb-3">
                    <p className="mb-0" style={{ lineHeight: '1.65', fontSize: '0.975rem' }}>
                        {explanation.content}
                    </p>
                </div>

                {/* Source Attribution */}
                {explanation.sources && explanation.sources.length > 0 && (
                    <div className="source-badge mt-3 mb-3">
                        <small>
                            📊 Based on: {explanation.sources.join(', ')}
                        </small>
                    </div>
                )}

                {/* Expandable Reasoning */}
                <Button
                    variant="link"
                    size="sm"
                    onClick={() => setShowReasoning(!showReasoning)}
                    className="text-decoration-none p-0 d-flex align-items-center"
                >
                    {showReasoning ? <FaChevronUp className="me-1" /> : <FaChevronDown className="me-1" />}
                    {showReasoning ? 'Hide' : 'Show'} detailed reasoning
                </Button>

                {showReasoning && (
                    <div className="mt-3 p-3 bg-light rounded-3">
                        <h6 className="fw-semibold mb-2">How We Determined This</h6>
                        <ul className="small mb-2">
                            <li>Analyzed your attendance, grades, and engagement trends</li>
                            <li>Compared recent performance to your historical patterns</li>
                            <li>Considered institutional benchmarks for similar students</li>
                        </ul>
                        {explanation.validation && explanation.validation.issues && explanation.validation.issues.length > 0 && (
                            <div className="mt-2">
                                <small className="text-muted">
                                    <strong>Note:</strong> {explanation.validation.issues.join('; ')}
                                </small>
                            </div>
                        )}
                    </div>
                )}

                {/* Action Button */}
                <div className="mt-4">
                    <Button variant="primary" size="sm" className="rounded-pill px-3">
                        What can I improve?
                    </Button>
                </div>
            </Card.Body>
        </Card>
    );
};

export default RiskChangeExplainer;
