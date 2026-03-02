import React from 'react';
import { Row, Col, Container } from 'react-bootstrap';
import { motion } from 'framer-motion';
import DropoutProbabilityFunnel from '../components/analytics/DropoutProbabilityFunnel';
import RevenueAtRisk from '../components/business/RevenueAtRisk';
import CohortChurnDiagnostics from '../components/analytics/CohortChurnDiagnostics';
import RevenueRiskTranslator from '../components/business/RevenueRiskTranslator';

/**
 * Business Intelligence Page - Enhanced with AI Revenue Insights
 * 
 * Sales and retention team dashboard with AI-powered financial metrics
 * NEW: Revenue risk translator converts academic risk to business impact
 */

const BusinessIntelligence = () => {
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
                        Business Intelligence Dashboard
                    </h1>
                    <p className="text-secondary fs-5">
                        AI-powered revenue insights, cohort analytics, and retention funnel diagnostics for strategic decision-making.
                    </p>
                </div>

                {/* Key Metrics */}
                <Row className="g-4 mb-4">
                    {/* NEW: AI Revenue Risk Translator */}
                    <Col lg={6}>
                        <RevenueRiskTranslator />
                    </Col>
                    <Col lg={6}>
                        <DropoutProbabilityFunnel />
                    </Col>
                </Row>

                {/* Traditional Metrics */}
                <Row className="g- 4 mb-4">
                    <Col lg={12}>
                        <RevenueAtRisk />
                    </Col>
                </Row>

                {/* Cohort Diagnostics */}
                <Row className="g-4">
                    <Col>
                        <CohortChurnDiagnostics />
                    </Col>
                </Row>

            </Container>
        </motion.div>
    );
};

export default BusinessIntelligence;

