import React, { useState } from 'react';
import { Row, Col, Container, Nav } from 'react-bootstrap';
import { motion } from 'framer-motion';
import { FaChartLine, FaFunnelDollar, FaUsers, FaHandshake, FaDollarSign } from 'react-icons/fa';
import RetentionFunnel from '../components/business/RetentionFunnel';
import RevenueAtRisk from '../components/business/RevenueAtRisk';
import CostPerRetainedStudent from '../components/business/CostPerRetainedStudent';
import SalesAcademicAlignment from '../components/business/SalesAcademicAlignment';
import RevenueRiskTranslator from '../components/business/RevenueRiskTranslator';
import DropoutProbabilityFunnel from '../components/analytics/DropoutProbabilityFunnel';
import { useStudentData } from '../context/StudentContext';
import { variants } from '../utils/motionConfig';

/**
 * Business Analytics Page
 *
 * Comprehensive business intelligence dashboard for non-technical leadership.
 * Shows retention metrics translated into financial impact.
 *
 * Key sections:
 * 1. Executive Summary - High-level KPIs
 * 2. Revenue Impact - Revenue at risk and saved
 * 3. Retention Funnel - Student journey visualization
 * 4. ROI Analysis - Cost per retained student
 * 5. Team Alignment - Sales & Academic coordination
 */

const BusinessAnalytics = () => {
    const { students } = useStudentData();
    const [activeTab, setActiveTab] = useState('overview');

    // Calculate executive summary metrics
    const executiveSummary = React.useMemo(() => {
        if (!students || students.length === 0) {
            return {
                totalEnrolled: 0,
                retentionRate: 0,
                revenueAtRisk: 0,
                interventionROI: 0
            };
        }

        const totalEnrolled = students.length;
        const atRisk = students.filter(s => s.risk_score > 40).length;
        const highRisk = students.filter(s => s.risk_score > 70).length;

        // Calculate metrics
        const avgLTV = 12500;
        const revenueAtRisk = highRisk * avgLTV * 0.25;  // 25% expected dropout rate for high-risk
        const interventionsTriggered = Math.floor(atRisk * 0.6);
        const recovered = Math.floor(interventionsTriggered * 0.35);
        const revenueSaved = recovered * avgLTV;
        const interventionCost = recovered * 350;
        const roi = interventionCost > 0 ? ((revenueSaved - interventionCost) / interventionCost) : 0;

        return {
            totalEnrolled,
            retentionRate: ((totalEnrolled - highRisk * 0.25) / totalEnrolled * 100).toFixed(1),
            revenueAtRisk: Math.round(revenueAtRisk),
            interventionROI: Math.round(roi * 10) / 10,
            atRiskCount: atRisk,
            highRiskCount: highRisk,
            recoveredCount: recovered,
            revenueSaved: Math.round(revenueSaved)
        };
    }, [students]);

    return (
        <motion.div
            initial="hidden"
            animate="visible"
            variants={variants.container}
        >
            <Container fluid className="py-4" style={{ maxWidth: '1600px' }}>
                {/* Page Header */}
                <div className="mb-4">
                    <h1 className="display-5 fw-bold text-gradient mb-2">
                        Business Analytics
                    </h1>
                    <p className="text-secondary fs-5" style={{ maxWidth: '700px' }}>
                        Strategic insights for institutional decision-making. Translate student retention metrics into actionable business intelligence.
                    </p>
                </div>

                {/* Executive Summary Cards */}
                <motion.div variants={variants.item} className="mb-5">
                    <Row className="g-4">
                        <Col md={3}>
                            <ExecutiveKPI
                                icon={<FaUsers />}
                                label="Total Enrolled"
                                value={executiveSummary.totalEnrolled.toLocaleString()}
                                trend={`${executiveSummary.atRiskCount} at risk`}
                                trendColor="var(--color-warning)"
                            />
                        </Col>
                        <Col md={3}>
                            <ExecutiveKPI
                                icon={<FaChartLine />}
                                label="Retention Rate"
                                value={`${executiveSummary.retentionRate}%`}
                                trend="Target: 95%"
                                trendColor={parseFloat(executiveSummary.retentionRate) >= 95 ? 'var(--color-success)' : 'var(--color-warning)'}
                            />
                        </Col>
                        <Col md={3}>
                            <ExecutiveKPI
                                icon={<FaDollarSign />}
                                label="Revenue at Risk"
                                value={`$${executiveSummary.revenueAtRisk.toLocaleString()}`}
                                trend={`${executiveSummary.highRiskCount} high-risk students`}
                                trendColor="var(--color-error)"
                            />
                        </Col>
                        <Col md={3}>
                            <ExecutiveKPI
                                icon={<FaFunnelDollar />}
                                label="Intervention ROI"
                                value={`${executiveSummary.interventionROI}x`}
                                trend={`$${executiveSummary.revenueSaved.toLocaleString()} saved`}
                                trendColor="var(--color-success)"
                            />
                        </Col>
                    </Row>
                </motion.div>

                {/* Tab Navigation */}
                <motion.div variants={variants.item} className="mb-4">
                    <Nav variant="pills" className="gap-2">
                        <Nav.Item>
                            <Nav.Link
                                active={activeTab === 'overview'}
                                onClick={() => setActiveTab('overview')}
                                style={{
                                    background: activeTab === 'overview' ? 'var(--business-primary)' : 'var(--gray-100)',
                                    color: activeTab === 'overview' ? 'white' : 'var(--gray-700)',
                                    border: 'none',
                                    fontWeight: 'var(--font-weight-semibold)'
                                }}
                            >
                                Overview
                            </Nav.Link>
                        </Nav.Item>
                        <Nav.Item>
                            <Nav.Link
                                active={activeTab === 'revenue'}
                                onClick={() => setActiveTab('revenue')}
                                style={{
                                    background: activeTab === 'revenue' ? 'var(--business-primary)' : 'var(--gray-100)',
                                    color: activeTab === 'revenue' ? 'white' : 'var(--gray-700)',
                                    border: 'none',
                                    fontWeight: 'var(--font-weight-semibold)'
                                }}
                            >
                                Revenue Impact
                            </Nav.Link>
                        </Nav.Item>
                        <Nav.Item>
                            <Nav.Link
                                active={activeTab === 'funnel'}
                                onClick={() => setActiveTab('funnel')}
                                style={{
                                    background: activeTab === 'funnel' ? 'var(--business-primary)' : 'var(--gray-100)',
                                    color: activeTab === 'funnel' ? 'white' : 'var(--gray-700)',
                                    border: 'none',
                                    fontWeight: 'var(--font-weight-semibold)'
                                }}
                            >
                                Retention Funnel
                            </Nav.Link>
                        </Nav.Item>
                        <Nav.Item>
                            <Nav.Link
                                active={activeTab === 'roi'}
                                onClick={() => setActiveTab('roi')}
                                style={{
                                    background: activeTab === 'roi' ? 'var(--business-primary)' : 'var(--gray-100)',
                                    color: activeTab === 'roi' ? 'white' : 'var(--gray-700)',
                                    border: 'none',
                                    fontWeight: 'var(--font-weight-semibold)'
                                }}
                            >
                                ROI Analysis
                            </Nav.Link>
                        </Nav.Item>
                        <Nav.Item>
                            <Nav.Link
                                active={activeTab === 'alignment'}
                                onClick={() => setActiveTab('alignment')}
                                style={{
                                    background: activeTab === 'alignment' ? 'var(--business-primary)' : 'var(--gray-100)',
                                    color: activeTab === 'alignment' ? 'white' : 'var(--gray-700)',
                                    border: 'none',
                                    fontWeight: 'var(--font-weight-semibold)'
                                }}
                            >
                                Team Alignment
                            </Nav.Link>
                        </Nav.Item>
                    </Nav>
                </motion.div>

                {/* Tab Content */}
                <motion.div variants={variants.item}>
                    {activeTab === 'overview' && (
                        <Row className="g-4">
                            <Col lg={6}>
                                <RevenueRiskTranslator />
                            </Col>
                            <Col lg={6}>
                                <DropoutProbabilityFunnel />
                            </Col>
                            <Col lg={12}>
                                <RetentionFunnel />
                            </Col>
                        </Row>
                    )}

                    {activeTab === 'revenue' && (
                        <Row className="g-4">
                            <Col lg={12}>
                                <RevenueAtRisk />
                            </Col>
                            <Col lg={6}>
                                <RevenueRiskTranslator />
                            </Col>
                            <Col lg={6}>
                                <CostPerRetainedStudent />
                            </Col>
                        </Row>
                    )}

                    {activeTab === 'funnel' && (
                        <Row className="g-4">
                            <Col lg={8}>
                                <RetentionFunnel />
                            </Col>
                            <Col lg={4}>
                                <DropoutProbabilityFunnel />
                            </Col>
                        </Row>
                    )}

                    {activeTab === 'roi' && (
                        <Row className="g-4">
                            <Col lg={6}>
                                <CostPerRetainedStudent />
                            </Col>
                            <Col lg={6}>
                                <RevenueAtRisk />
                            </Col>
                        </Row>
                    )}

                    {activeTab === 'alignment' && (
                        <Row className="g-4">
                            <Col lg={12}>
                                <SalesAcademicAlignment />
                            </Col>
                        </Row>
                    )}
                </motion.div>

                {/* Footer Note */}
                <div className="mt-5 pt-4 border-top text-center">
                    <small className="text-muted">
                        Data refreshed in real-time from EWS prediction engine. Financial projections based on configured LTV of $12,500 per student.
                    </small>
                </div>
            </Container>
        </motion.div>
    );
};

const ExecutiveKPI = ({ icon, label, value, trend, trendColor }) => (
    <div className="premium-card business-context" style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        textAlign: 'center',
        padding: 'var(--space-xl)'
    }}>
        <div style={{
            fontSize: '24px',
            color: 'var(--business-primary)',
            marginBottom: 'var(--space-sm)'
        }}>
            {icon}
        </div>
        <div style={{
            fontSize: 'var(--font-size-caption)',
            fontWeight: 'var(--font-weight-semibold)',
            textTransform: 'uppercase',
            letterSpacing: 'var(--letter-spacing-wider)',
            color: 'var(--gray-600)',
            marginBottom: 'var(--space-xs)'
        }}>
            {label}
        </div>
        <div style={{
            fontSize: 'var(--font-size-h1)',
            fontWeight: 'var(--font-weight-extrabold)',
            fontFamily: 'var(--font-family-mono)',
            color: 'var(--gray-900)',
            marginBottom: 'var(--space-xs)'
        }}>
            {value}
        </div>
        <div style={{
            fontSize: 'var(--font-size-caption)',
            fontWeight: 'var(--font-weight-medium)',
            color: trendColor
        }}>
            {trend}
        </div>
    </div>
);

export default BusinessAnalytics;
