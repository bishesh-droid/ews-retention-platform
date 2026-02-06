import React from 'react';
import { Row, Col, Container } from 'react-bootstrap';
import { motion } from 'framer-motion';
import CourseRiskAnalysis from '../components/analytics/CourseRiskAnalysis';
import BiasIndicators from '../components/quality/BiasIndicators';
import SystemPatternDetector from '../components/quality/SystemPatternDetector';

/**
 * Institutional Insights Page - Enhanced with AI Pattern Discovery
 * 
 * Administrator dashboard for systemic analysis with AI-powered blind spot detection
 * NEW: Pattern discovery engine surfaces insights humans wouldn't query manually
 */

const InstitutionalInsights = () => {
    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
        >
            <Container fluid className="py-4" style={{ maxWidth: '1600px' }}>
                {/* Page Header */}
                <div className="mb-4">
                    <h1 className="display-5 fw-bold text-gradient mb-2">
                        Institutional Insights & Governance
                    </h1>
                    <p className="text-secondary fs-5">
                        AI-powered system-level analysis, fairness metrics, and structural pattern recognition to guide institutional policy.
                    </p>
                </div>

                <Row className="g-4">
                    {/* Left Column - 2/3 */}
                    <Col lg={8}>
                        <div className="d-flex flex-column gap-4">
                            {/* Course Risk Analysis */}
                            <CourseRiskAnalysis />

                            {/* Bias Indicators */}
                            <BiasIndicators />
                        </div>
                    </Col>

                    {/* Right Column - 1/3 */}
                    <Col lg={4}>
                        {/* NEW: AI Pattern Discovery */}
                        <SystemPatternDetector />
                    </Col>
                </Row>

                {/* AI Attribution */}
                <div className="mt-5 pt-4 border-top text-center">
                    <small className="text-muted">
                        🔍 AI pattern discovery reveals systemic issues you wouldn't think to query manually
                    </small>
                </div>
            </Container>
        </motion.div>
    );
};

export default InstitutionalInsights;

