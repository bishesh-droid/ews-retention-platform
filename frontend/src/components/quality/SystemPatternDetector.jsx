import React, { useState, useEffect } from 'react';
import { Card, ListGroup, Badge, Button, Spinner } from 'react-bootstrap';
import { FaLightbulb, FaExclamationTriangle, FaChartBar } from 'react-icons/fa';
import axios from 'axios';
import { motion } from 'framer-motion';

/**
 * SystemPatternDetector - Displays LLM-discovered institutional insights
 * Admin-facing blind spot detection
 */
function SystemPatternDetector() {
    const [insights, setInsights] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchInsights();
    }, []);

    const fetchInsights = async () => {
        setLoading(true);

        try {
            const response = await axios.get('http://localhost:8000/api/llm/institutional-insights');
            const allInsights = [
                ...(response.data.systemic_issues || []),
                ...(response.data.blind_spots || [])
            ];
            setInsights(allInsights);
        } catch (err) {
            console.error('Error fetching insights:', err);
        } finally {
            setLoading(false);
        }
    };

    const getInsightIcon = (type) => {
        const icons = {
            attendance_policy_impact: FaChartBar,
            gpa_trend_impact: FaChartBar,
            intervention_gap: FaExclamationTriangle,
            risk_clustering: FaExclamationTriangle,
            performance_timing: FaLightbulb,
            suspension_correlation: FaChartBar
        };
        return icons[type] || FaLightbulb;
    };

    const getInsightColor = (type) => {
        const colors = {
            attendance_policy_impact: 'primary',
            gpa_trend_impact: 'info',
            intervention_gap: 'danger',
            risk_clustering: 'warning',
            performance_timing: 'info',
            suspension_correlation: 'warning'
        };
        return colors[type] || 'secondary';
    };

    const getConfidenceBadge = (confidence) => {
        const badges = {
            high: { color: 'success', text: 'High Confidence' },
            medium: { color: 'warning', text: 'Medium Confidence' },
            low: { color: 'secondary', text: 'Low Confidence' }
        };
        const badge = badges[confidence] || badges.medium;
        return (
            <Badge bg={badge.color} className="bg-opacity-25" style={{ fontSize: '0.7rem' }}>
                {badge.text}
            </Badge>
        );
    };

    if (loading) {
        return (
            <Card className="glass-panel border-0 shadow-sm h-100">
                <Card.Body className="text-center py-5">
                    <Spinner animation="border" variant="primary" />
                    <p className="mt-3 text-muted small">Discovering patterns...</p>
                </Card.Body>
            </Card>
        );
    }

    return (
        <Card className="glass-panel border-0 shadow-sm h-100">
            <Card.Body className="p-4">
                <div className="d-flex align-items-center justify-content-between mb-4">
                    <div className="d-flex align-items-center">
                        <FaLightbulb className="text-warning me-2" size={24} />
                        <h4 className="mb-0 fw-bold">Pattern Detection</h4>
                    </div>
                    <Badge bg="warning" className="bg-opacity-25 text-warning">
                        {insights.length} Insight{insights.length !== 1 ? 's' : ''}
                    </Badge>
                </div>

                <p className="text-muted mb-4">
                    AI-discovered institutional patterns and systemic issues that may affect retention.
                </p>

                {insights.length === 0 ? (
                    <div className="text-center text-muted py-5">
                        <FaLightbulb size={48} className="mb-3 opacity-25" />
                        <p className="mb-2">No significant patterns detected yet.</p>
                        <p className="small">System requires more data for pattern discovery.</p>
                    </div>
                ) : (
                    <ListGroup variant="flush" className="bg-transparent">
                        {insights.map((insight, index) => {
                            const Icon = getInsightIcon(insight.type);
                            const color = getInsightColor(insight.type);

                            return (
                                <motion.div
                                    key={index}
                                    initial={{ opacity: 0, x: -20 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ delay: index * 0.1 }}
                                >
                                    <ListGroup.Item className="bg-transparent border-0 px-0 py-3 mb-3">
                                        <Card className={`border-start border-${color} border-4 shadow-sm`}>
                                            <Card.Body className="p-3">
                                                <div className="d-flex align-items-start mb-2">
                                                    <div className={`p-2 bg-${color} bg-opacity-10 rounded me-3`}>
                                                        <Icon className={`text-${color}`} size={20} />
                                                    </div>
                                                    <div className="flex-grow-1">
                                                        <div className="d-flex align-items-center justify-content-between mb-2">
                                                            <h6 className="mb-0 fw-semibold">{insight.title}</h6>
                                                            {insight.confidence && getConfidenceBadge(insight.confidence)}
                                                        </div>
                                                        <p className="mb-2 small" style={{ lineHeight: '1.5' }}>
                                                            {insight.description}
                                                        </p>

                                                        {/* Evidence */}
                                                        {insight.evidence && (
                                                            <div className="mb-2 p-2 bg-light rounded">
                                                                <small className="fw-semibold d-block mb-1">📊 Evidence:</small>
                                                                <ul className="small mb-0 ps-3">
                                                                    {Object.entries(insight.evidence).slice(0, 3).map(([key, value]) => (
                                                                        <li key={key}>
                                                                            {key.replace(/_/g, ' ')}: <strong>{typeof value === 'number' ? value.toFixed(1) : value}</strong>
                                                                        </li>
                                                                    ))}
                                                                </ul>
                                                            </div>
                                                        )}

                                                        {/* Suggested Action */}
                                                        {(insight.suggested_action || insight.insight) && (
                                                            <div className={`p-2 bg-${color} bg-opacity-5 rounded border border-${color} border-opacity-25`}>
                                                                <small className="fw-semibold d-block mb-1">💡 Recommendation:</small>
                                                                <small className="d-block">
                                                                    {insight.suggested_action || insight.insight}
                                                                </small>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            </Card.Body>
                                        </Card>
                                    </ListGroup.Item>
                                </motion.div>
                            );
                        })}
                    </ListGroup>
                )}

                <div className="mt-4 pt-3 border-top text-center">
                    <Button
                        variant="outline-primary"
                        size="sm"
                        onClick={fetchInsights}
                        className="rounded-pill px-4"
                    >
                        Refresh Patterns
                    </Button>
                </div>
            </Card.Body>
        </Card>
    );
}

export default SystemPatternDetector;
