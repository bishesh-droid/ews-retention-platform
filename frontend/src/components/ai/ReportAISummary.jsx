import React, { useState, useEffect } from 'react';
import { Card, Badge, Spinner, Alert } from 'react-bootstrap';
import { FaLightbulb, FaChartLine, FaExclamationTriangle } from 'react-icons/fa';
import { motion } from 'framer-motion';
import ConfidenceBadge from './ConfidenceBadge';
import CollapsiblePanel from './CollapsiblePanel';

/**
 * ReportAISummary Component
 * Generates and displays AI-powered executive summaries for reports
 * with chart explanations, key findings, and suggested actions.
 */
const ReportAISummary = ({ reportType, reportData }) => {
    const [loading, setLoading] = useState(false);
    const [summary, setSummary] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (reportData) {
            generateSummary();
        }
    }, [reportData]);

    const generateSummary = async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch('/api/llm/generate-report-narrative', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    report_type: reportType,
                    data: reportData
                })
            });

            if (!response.ok) throw new Error('Failed to generate summary');

            const data = await response.json();
            setSummary(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <Card className="glass-panel border-0 mb-4">
                <Card.Body className="text-center py-5">
                    <Spinner animation="border" variant="primary" className="mb-3" />
                    <p className="text-muted mb-0">Generating AI executive summary...</p>
                </Card.Body>
            </Card>
        );
    }

    if (error) {
        return (
            <Alert variant="warning" className="mb-4">
                <FaExclamationTriangle className="me-2" />
                Unable to generate AI summary: {error}
            </Alert>
        );
    }

    if (!summary) return null;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="mb-4"
        >
            <Card className="glass-panel border-0 ai-summary-card">
                <Card.Body>
                    {/* Header */}
                    <div className="d-flex justify-content-between align-items-start mb-3">
                        <div className="d-flex align-items-center gap-2">
                            <FaLightbulb className="text-primary" size={20} />
                            <h5 className="mb-0 ai-heading">AI Executive Summary</h5>
                        </div>
                        <div className="d-flex gap-2 align-items-center">
                            <Badge bg="info" className="ai-badge">AI-Generated</Badge>
                            <ConfidenceBadge confidence={summary.confidence} />
                        </div>
                    </div>

                    {/* Main Summary Content */}
                    <div className="ai-text mb-4">
                        {summary.content}
                    </div>

                    {/* Key Findings */}
                    {summary.key_findings && summary.key_findings.length > 0 && (
                        <div className="mb-4">
                            <h6 className="fw-semibold mb-3 d-flex align-items-center gap-2">
                                <FaChartLine className="text-success" />
                                Key Findings
                            </h6>
                            <ul className="ai-findings-list">
                                {summary.key_findings.map((finding, index) => (
                                    <li key={index} className="mb-2">
                                        <span className="finding-highlight">{finding.title}:</span>{' '}
                                        <span className="ai-text">{finding.description}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Anomalies / Concerns */}
                    {summary.anomalies && summary.anomalies.length > 0 && (
                        <div className="mb-4">
                            <h6 className="fw-semibold mb-3 d-flex align-items-center gap-2">
                                <FaExclamationTriangle className="text-warning" />
                                Notable Anomalies
                            </h6>
                            <div className="anomalies-container">
                                {summary.anomalies.map((anomaly, index) => (
                                    <Alert key={index} variant="warning" className="mb-2 py-2">
                                        <small className="ai-text">{anomaly}</small>
                                    </Alert>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Suggested Actions */}
                    {summary.suggested_actions && summary.suggested_actions.length > 0 && (
                        <div className="mb-3">
                            <h6 className="fw-semibold mb-3">Recommended Next Steps</h6>
                            <ol className="ai-actions-list">
                                {summary.suggested_actions.map((action, index) => (
                                    <li key={index} className="mb-2 ai-text">{action}</li>
                                ))}
                            </ol>
                        </div>
                    )}

                    {/* Collapsible Reasoning */}
                    <CollapsiblePanel
                        title="How was this generated?"
                        defaultExpanded={false}
                        variant="light"
                    >
                        <div className="source-attribution-section">
                            <h6 className="small fw-semibold mb-2">Data Sources Used:</h6>
                            <ul className="source-list">
                                {summary.sources && summary.sources.map((source, index) => (
                                    <li key={index} className="source-badge mb-1">
                                        {source}
                                    </li>
                                ))}
                            </ul>

                            <h6 className="small fw-semibold mt-3 mb-2">Methodology:</h6>
                            <p className="small text-muted mb-0">
                                This summary was generated using institutional data analysis combined
                                with pattern detection algorithms. The LLM reviewed {' '}
                                {reportData?.student_count || 'multiple'} student records, {' '}
                                {reportData?.intervention_count || 'intervention'} data points, and
                                historical trends to identify significant insights.
                            </p>

                            {summary.confidence === 'low' && (
                                <Alert variant="info" className="mt-3 mb-0">
                                    <small>
                                        <strong>Note:</strong> This summary has lower confidence due to
                                        limited data availability or high uncertainty in patterns.
                                        Please validate findings with additional research.
                                    </small>
                                </Alert>
                            )}
                        </div>
                    </CollapsiblePanel>
                </Card.Body>
            </Card>
        </motion.div>
    );
};

export default ReportAISummary;
