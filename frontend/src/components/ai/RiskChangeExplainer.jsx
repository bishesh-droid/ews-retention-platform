import React, { useState, useEffect } from 'react';
import { Card, Button, Spinner, Alert } from 'react-bootstrap';
import { FaChartLine, FaInfoCircle, FaChevronDown, FaChevronUp } from 'react-icons/fa';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

/**
 * RiskChangeExplainer - Explains why a student's risk score changed
 * Student-facing component with empathetic, non-alarming tone
 */
function RiskChangeExplainer({ studentId }) {
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
}

export default RiskChangeExplainer;
