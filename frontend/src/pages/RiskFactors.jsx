import React, { useState, useRef, useEffect } from 'react';
import { Row, Col, Button, Card, Form, Badge, Modal } from 'react-bootstrap';
import { FaExclamationTriangle, FaInfoCircle } from 'react-icons/fa';
import { motion } from 'framer-motion';
import { Bar } from 'react-chartjs-2';
import { variants } from '../utils/motionConfig';

const RiskFactors = () => {
    const chartRef = useRef(null);
    const [weights, setWeights] = useState({
        academic: 35,
        engagement: 30,
        consistency: 20,
        intent: 15,
    });

    const [showConfirmModal, setShowConfirmModal] = useState(false);
    const [pendingWeights, setPendingWeights] = useState(null);

    const handleWeightChange = (factor, value) => {
        const newValue = parseInt(value);
        const oldValue = weights[factor];
        const diff = newValue - oldValue;

        // Calculate how to distribute the difference among other factors
        const otherFactors = Object.keys(weights).filter(f => f !== factor);
        const adjustment = -diff / otherFactors.length;

        const newWeights = { ...weights, [factor]: newValue };
        otherFactors.forEach(f => {
            newWeights[f] = Math.max(0, Math.round(newWeights[f] + adjustment));
        });

        // Ensure total is 100
        const total = Object.values(newWeights).reduce((sum, val) => sum + val, 0);
        if (total !== 100) {
            const firstOther = otherFactors[0];
            newWeights[firstOther] += (100 - total);
        }

        setWeights(newWeights);
    };

    const handleApplyChanges = () => {
        setPendingWeights(weights);
        setShowConfirmModal(true);
    };

    const confirmApplyChanges = () => {
        // In a real app, this would call an API to update the risk model
        setShowConfirmModal(false);
        setPendingWeights(null);
    };

    const resetToDefault = () => {
        setWeights({
            academic: 35,
            engagement: 30,
            consistency: 20,
            intent: 15,
        });
    };

    const weightData = {
        labels: ['Academic Performance', 'Engagement', 'Consistency', 'Intent & Responsiveness'],
        datasets: [
            {
                label: 'Weight %',
                data: [weights.academic, weights.engagement, weights.consistency, weights.intent],
                backgroundColor: [
                    'rgba(0, 130, 201, 0.6)',
                    'rgba(0, 130, 201, 0.5)',
                    'rgba(0, 130, 201, 0.4)',
                    'rgba(0, 130, 201, 0.3)',
                ],
                borderColor: 'var(--primary-color)',
                borderWidth: 1,
            },
        ],
    };

    const chartOptions = {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: 'var(--surface-color)',
                titleColor: 'var(--text-primary)',
                bodyColor: 'var(--text-secondary)',
                borderColor: 'var(--border-color)',
                borderWidth: 1,
            },
        },
        scales: {
            x: {
                beginAtZero: true,
                max: 100,
                grid: { color: 'var(--border-color)' },
                ticks: { color: 'var(--text-muted)', callback: (value) => value + '%' },
            },
            y: {
                grid: { display: false },
                ticks: { color: 'var(--text-primary)' },
            },
        },
    };

    const factorDescriptions = {
        academic: {
            title: 'Academic Performance Signals',
            metrics: [
                'Quiz scores',
                'Assignment grades',
                'Final exam scores',
                'Improvement over time',
                'Time spent on assessments',
                'Retake count',
                'Practice test accuracy',
                'Difficulty of questions solved',
            ],
            scoring: 'Critical: <40% avg score, High: 40-60%, Medium: 60-75%, Low: >75%',
        },
        engagement: {
            title: 'Engagement Signals',
            metrics: [
                'LMS login frequency',
                'Video watch percentage',
                'Pause / rewind behavior',
                'Live class attendance',
                'Time spent per session',
                'Forum participation',
                'Resource downloads',
                'Notes opened',
            ],
            scoring: 'Critical: No activity 14+ days, High: 1-2x/week, Medium: 3-4x/week, Low: Daily',
        },
        consistency: {
            title: 'Consistency Signals',
            metrics: [
                'Standard deviation of login times',
                'Gaps between sessions',
                'Week-to-week drop in activity',
                'Streaks of activity',
                'Sudden changes in behavior',
            ],
            scoring: 'Critical: No streaks & high variance, High: Declining weekly, Medium: Occasional gaps, Low: Consistent daily activity',
        },
        intent: {
            title: 'Intent & Responsiveness Signals',
            metrics: [
                'Course progress %',
                'New courses browsed',
                'Upsell clicks',
                'Certificates downloaded',
                'Exam registrations',
                'Refund request attempts',
                'Subscription renewal',
                'Email open rate',
                'WhatsApp reply rate',
                'Click-through rate',
                'Time to respond',
                'Ignore count',
            ],
            scoring: 'Critical: Refund requested & no engagement, High: Declining intent signals, Medium: Mixed signals, Low: Active progression & responsive',
        },
    };

    // Cleanup chart on unmount
    useEffect(() => {
        return () => {
            if (chartRef.current) {
                chartRef.current.destroy();
            }
        };
    }, []);

    return (
        <motion.div
            initial="hidden"
            animate="visible"
            variants={variants.container}
            className="pb-5"
        >
            <div className="mb-5">
                <h1 className="display-5 fw-bold text-gradient mb-2">Risk Factors</h1>
                <p className="text-secondary fs-5" style={{ maxWidth: '700px' }}>
                    Configure and fine-tune the weighted risk scoring model. Adjust how different factors contribute to overall student risk assessment.
                </p>
            </div>

            <Row className="g-4 mb-4">
                <Col lg={6}>
                    <motion.div variants={variants.item} className="glass-panel p-4 h-100">
                        <h5 className="mb-4 fw-semibold">Weight Distribution</h5>
                        <div style={{ height: '300px' }}>
                            <Bar ref={chartRef} data={weightData} options={chartOptions} />
                        </div>
                        <div className="mt-3 text-center">
                            <Badge bg="secondary">Total: {Object.values(weights).reduce((sum, val) => sum + val, 0)}%</Badge>
                        </div>
                    </motion.div>
                </Col>

                <Col lg={6}>
                    <motion.div variants={variants.item} className="glass-panel p-4 h-100">
                        <h5 className="mb-4 fw-semibold">Adjust Weights</h5>

                        {Object.entries(weights).map(([factor, weight]) => (
                            <div key={factor} className="mb-4">
                                <div className="d-flex justify-content-between align-items-center mb-2">
                                    <span className="fw-medium text-capitalize">{factorDescriptions[factor].title}</span>
                                    <Badge bg="primary">{weight}%</Badge>
                                </div>
                                <Form.Range
                                    min="0"
                                    max="100"
                                    value={weight}
                                    onChange={(e) => handleWeightChange(factor, e.target.value)}
                                    className="custom-range"
                                />
                            </div>
                        ))}

                        <div className="d-grid gap-2 mt-4">
                            <Button variant="primary" onClick={handleApplyChanges}>
                                Apply Changes
                            </Button>
                            <Button variant="outline-secondary" onClick={resetToDefault}>
                                Reset to Default
                            </Button>
                        </div>

                        <div className="alert alert-info mt-3 d-flex align-items-start gap-2">
                            <FaInfoCircle className="mt-1" />
                            <small>
                                Changing weights will recalculate risk scores for all students. This may affect risk level classifications and intervention priorities.
                            </small>
                        </div>
                    </motion.div>
                </Col>
            </Row>

            <Row className="g-4">
                {Object.entries(factorDescriptions).map(([key, factor]) => (
                    <Col lg={6} key={key}>
                        <motion.div variants={variants.item}>
                            <Card className="glass-panel border-0 h-100">
                                <Card.Body>
                                    <Card.Title className="d-flex align-items-center gap-2 mb-3">
                                        <Badge bg="primary">{weights[key]}%</Badge>
                                        <span className="fw-semibold">{factor.title}</span>
                                    </Card.Title>

                                    <h6 className="text-muted small mb-2">Sub-metrics:</h6>
                                    <ul className="small mb-3">
                                        {factor.metrics.map((metric, idx) => (
                                            <li key={idx}>{metric}</li>
                                        ))}
                                    </ul>

                                    <h6 className="text-muted small mb-2">Scoring Thresholds:</h6>
                                    <p className="small mb-0">{factor.scoring}</p>
                                </Card.Body>
                            </Card>
                        </motion.div>
                    </Col>
                ))}
            </Row>

            {/* Confirmation Modal */}
            <Modal
                show={showConfirmModal}
                onHide={() => setShowConfirmModal(false)}
                centered
                style={{ zIndex: 9999 }}
            >
                <Modal.Header closeButton style={{ borderColor: 'var(--border-color)', backgroundColor: 'var(--surface-color)' }}>
                    <Modal.Title className="d-flex align-items-center gap-2">
                        <FaExclamationTriangle className="text-warning" />
                        Confirm Risk Model Update
                    </Modal.Title>
                </Modal.Header>
                <Modal.Body style={{ backgroundColor: 'var(--surface-color)' }}>
                    <p>This will recalculate risk scores for all students.</p>
                    <p className="mb-0">Changes will affect:</p>
                    <ul>
                        <li>Dashboard metrics</li>
                        <li>Risk level classifications</li>
                        <li>Active intervention priorities</li>
                    </ul>
                    <p className="mb-0 mt-3">Do you want to proceed?</p>
                </Modal.Body>
                <Modal.Footer style={{ borderColor: 'var(--border-color)', backgroundColor: 'var(--surface-color)' }}>
                    <Button variant="outline-secondary" onClick={() => setShowConfirmModal(false)}>
                        Cancel
                    </Button>
                    <Button variant="primary" onClick={confirmApplyChanges}>
                        Yes, Update Risk Model
                    </Button>
                </Modal.Footer>
            </Modal>
        </motion.div>
    );
};

export default RiskFactors;
