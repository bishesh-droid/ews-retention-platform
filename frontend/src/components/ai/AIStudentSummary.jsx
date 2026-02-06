import React, { useState } from 'react';
import { Card, Button, Spinner, Badge } from 'react-bootstrap';
import { FaRobot, FaChevronDown, FaChevronUp } from 'react-icons/fa';
import axios from 'axios';

/**
 * AIStudentSummary - One-click AI-generated student summary for faculty
 * Saves time by providing instant insights
 */
function AIStudentSummary({ studentId, riskCategory }) {
    const [summary, setSummary] = useState(null);
    const [loading, setLoading] = useState(false);
    const [showReasoning, setShowReasoning] = useState(false);

    const generateSummary = async () => {
        setLoading(true);

        try {
            const response = await axios.post('http://localhost:8000/api/llm/faculty-summary', {
                student_id: studentId,
                for_role: 'faculty'
            });
            setSummary(response.data);
        } catch (err) {
            console.error('Error generating summary:', err);
            setSummary({ content: 'Unable to generate summary.', confidence: 'low' });
        } finally {
            setLoading(false);
        }
    };

    const getConfidenceBadge = (confidence) => {
        const badges = {
            high: { color: 'success', text: 'High' },
            medium: { color: 'warning', text: 'Medium' },
            low: { color: 'secondary', text: 'Low' }
        };
        const badge = badges[confidence] || badges.medium;
        return (
            <Badge bg={badge.color} className="bg-opacity-25" style={{ color: `var(--bs-${badge.color})` }}>
                {badge.text} Confidence
            </Badge>
        );
    };

    const getRiskBadge = (category) => {
        const colors = {
            critical: 'danger',
            high: 'warning',
            moderate: 'info',
            low: 'success'
        };
        return (
            <Badge bg={colors[category] || 'secondary'} className="bg-opacity-10"
                style={{ color: `var(--bs-${colors[category] || 'secondary'})`, borderWidth: '1px', borderStyle: 'solid' }}>
                {category?.toUpperCase() || 'UNKNOWN'} RISK
            </Badge>
        );
    };

    return (
        <Card className="glass-panel border-0 shadow-sm">
            <Card.Body className="p-3">
                <div className="d-flex align-items-center justify-content-between mb-3">
                    <div className="d-flex align-items-center">
                        <FaRobot className="text-primary me-2" size={18} />
                        <h6 className="mb-0 fw-semibold">AI Summary</h6>
                    </div>
                    {riskCategory && getRiskBadge(riskCategory)}
                </div>

                {!summary && !loading && (
                    <div className="text-center py-3">
                        <Button
                            variant="primary"
                            size="sm"
                            onClick={generateSummary}
                            className="rounded-pill px-3"
                        >
                            <FaRobot className="me-2" />
                            Generate AI Summary
                        </Button>
                        <p className="small text-muted mt-2 mb-0">
                            Get instant insights in 2-3 seconds
                        </p>
                    </div>
                )}

                {loading && (
                    <div className="text-center py-4">
                        <Spinner animation="border" size="sm" variant="primary" />
                        <p className="small text-muted mt-2 mb-0">Analyzing student profile...</p>
                    </div>
                )}

                {summary && summary.content && (
                    <div>
                        {/* AI Summary Content */}
                        <div className="ai-text mb-3 p-3 bg-light rounded-3">
                            <p className="mb-0" style={{ lineHeight: '1.6', fontSize: '0.9rem' }}>
                                {summary.content}
                            </p>
                        </div>

                        {/* Confidence and Sources */}
                        <div className="d-flex align-items-center justify-content-between mb-2">
                            {summary.confidence && getConfidenceBadge(summary.confidence)}
                            {summary.sources && summary.sources.length > 0 && (
                                <small className="text-muted">
                                    📊 {summary.sources.length} source{summary.sources.length > 1 ? 's' : ''}
                                </small>
                            )}
                        </div>

                        {/* Expandable Reasoning */}
                        <Button
                            variant="link"
                            size="sm"
                            onClick={() => setShowReasoning(!showReasoning)}
                            className="text-decoration-none p-0 mb-0"
                            style={{ fontSize: '0.85rem' }}
                        >
                            {showReasoning ? <FaChevronUp className="me-1" /> : <FaChevronDown className="me-1" />}
                            {showReasoning ? 'Hide' : 'Show'} data sources
                        </Button>

                        {showReasoning && summary.sources && (
                            <div className="mt-2 p-2 bg-white rounded border">
                                <small className="d-block mb-1 fw-semibold">Data Sources Used:</small>
                                <ul className="small mb-0 ps-3">
                                    {summary.sources.map((source, idx) => (
                                        <li key={idx}>{source}</li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>
                )}
            </Card.Body>
        </Card>
    );
}

export default AIStudentSummary;
