import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Badge, Spinner } from 'react-bootstrap';
import { FaDollarSign, FaExclamationCircle } from 'react-icons/fa';
import axios from 'axios';
import { motion } from 'framer-motion';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

/**
 * RevenueRiskTranslator - Converts academic risk to business impact
 * Sales/retention team view
 */
function RevenueRiskTranslator() {
    const [revenueData, setRevenueData] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchRevenueRisk();
    }, []);

    const fetchRevenueRisk = async () => {
        setLoading(true);

        try {
            const response = await axios.get(`${API_BASE}/llm/revenue-risk-translation`);
            setRevenueData(response.data);
        } catch (err) {
            console.error('Error fetching revenue risk:', err);
        } finally {
            setLoading(false);
        }
    };

    const formatCurrency = (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }).format(amount);
    };

    if (loading) {
        return (
            <Card className="glass-panel border-0 shadow-sm h-100">
                <Card.Body className="text-center py-5">
                    <Spinner animation="border" variant="danger" />
                    <p className="mt-3 text-muted small">Calculating revenue at risk...</p>
                </Card.Body>
            </Card>
        );
    }

    if (!revenueData || revenueData.error || !revenueData.revenue_impact) {
        return (
            <Card className="glass-panel border-0 shadow-sm h-100">
                <Card.Body className="p-4">
                    <div className="text-center text-muted py-4">
                        <FaExclamationCircle size={32} className="mb-3 opacity-50" />
                        <p>Unable to calculate revenue risk</p>
                    </div>
                </Card.Body>
            </Card>
        );
    }

    const { cohort_size, average_risk_score, churn_estimates, revenue_impact } = revenueData;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
        >
            <Card className="glass-panel border-0 shadow-lg border-start border-danger border-4">
                <Card.Body className="p-4">
                    <div className="d-flex align-items-center mb-4">
                        <div className="p-3 bg-danger bg-opacity-10 rounded-3 me-3">
                            <FaDollarSign className="text-danger" size={28} />
                        </div>
                        <div>
                            <h4 className="mb-0 fw-bold">Revenue at Risk</h4>
                            <p className="text-muted small mb-0">Academic risk translated to business impact</p>
                        </div>
                    </div>

                    {/* Total Revenue at Risk */}
                    <div className="mb-4 p-4 bg-danger bg-opacity-5 rounded-3 border border-danger border-opacity-25">
                        <div className="text-center">
                            <small className="text-muted d-block mb-2">Total Revenue at Risk</small>
                            <h1 className="display-4 fw-bold text-danger mb-0">
                                {formatCurrency(revenue_impact.total_revenue_at_risk)}
                            </h1>
                            <Badge bg="danger" className="bg-opacity-25 text-danger mt-2">
                                Estimated Churn Impact
                            </Badge>
                        </div>
                    </div>

                    {/* Cohort Metrics */}
                    <Row className="g-3 mb-4">
                        <Col md={6}>
                            <div className="text-center p-3 bg-light rounded-3">
                                <small className="text-muted d-block mb-1">Cohort Size</small>
                                <h3 className="mb-0 fw-bold">{cohort_size}</h3>
                                <small className="text-muted">Students</small>
                            </div>
                        </Col>
                        <Col md={6}>
                            <div className="text-center p-3 bg-warning bg-opacity-10 rounded-3">
                                <small className="text-muted d-block mb-1">Avg Risk Score</small>
                                <h3 className="mb-0 fw-bold text-warning">{average_risk_score}%</h3>
                                <small className="text-muted">Cohort Average</small>
                            </div>
                        </Col>
                    </Row>

                    {/* Risk Breakdown */}
                    <div className="mb-4">
                        <h6 className="fw-semibold mb-3">Churn Risk Breakdown</h6>
                        <div className="d-flex flex-column gap-2">
                            <div className="d-flex align-items-center justify-content-between p-2 bg-danger bg-opacity-10 rounded">
                                <span className="small">
                                    <Badge bg="danger" className="me-2">High</Badge>
                                    {churn_estimates.high_risk_students} students
                                </span>
                                <span className="small fw-bold text-danger">
                                    {formatCurrency(revenue_impact.high_risk_revenue)}
                                </span>
                            </div>
                            <div className="d-flex align-items-center justify-content-between p-2 bg-warning bg-opacity-10 rounded">
                                <span className="small">
                                    <Badge bg="warning" className="me-2">Medium</Badge>
                                    {churn_estimates.medium_risk_students} students
                                </span>
                                <span className="small fw-bold text-warning">
                                    {formatCurrency(revenue_impact.medium_risk_revenue)}
                                </span>
                            </div>
                            <div className="d-flex align-items-center justify-content-between p-2 bg-success bg-opacity-10 rounded">
                                <span className="small">
                                    <Badge bg="success" className="me-2">Low</Badge>
                                    {churn_estimates.low_risk_students} students
                                </span>
                                <span className="small text-success">On Track</span>
                            </div>
                        </div>
                    </div>

                    {/* Estimated Churn */}
                    <div className="p-3 bg-light rounded-3">
                        <h6 className="small fw-semibold mb-2">Estimated Churn Rates</h6>
                        <div className="d-flex justify-content-around">
                            <div className="text-center">
                                <div className="fw-bold text-danger">{churn_estimates.estimated_high_churn_pct}%</div>
                                <small className="text-muted">High Risk</small>
                            </div>
                            <div className="text-center">
                                <div className="fw-bold text-warning">{churn_estimates.estimated_medium_churn_pct}%</div>
                                <small className="text-muted">Medium Risk</small>
                            </div>
                        </div>
                    </div>

                    {/* Confidence */}
                    <div className="mt-3 text-center">
                        <Badge bg="secondary" className="bg-opacity-25">
                            {revenueData.confidence} confidence
                        </Badge>
                    </div>
                </Card.Body>
            </Card>
        </motion.div>
    );
}

export default RevenueRiskTranslator;
