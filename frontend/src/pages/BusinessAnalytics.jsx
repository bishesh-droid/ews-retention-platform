import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Row, Col, Container, Button, Spinner } from 'react-bootstrap';
import { motion } from 'framer-motion';
import { FaChartLine, FaFunnelDollar, FaUsers, FaDollarSign, FaDownload } from 'react-icons/fa';
import RetentionFunnel from '../components/business/RetentionFunnel';
import RevenueAtRisk from '../components/business/RevenueAtRisk';
import CostPerRetainedStudent from '../components/business/CostPerRetainedStudent';
import SalesAcademicAlignment from '../components/business/SalesAcademicAlignment';
import DropoutProbabilityFunnel from '../components/analytics/DropoutProbabilityFunnel';
import RetentionTrendChart from '../components/business/RetentionTrendChart';
import InterventionROITimeline from '../components/business/InterventionROITimeline';
import RevenueForecast from '../components/business/RevenueForecast';
import CohortRiskBreakdown from '../components/business/CohortRiskBreakdown';
import { variants } from '../utils/motionConfig';
import {
    getCohortHeatmap,
    getDepartmentComparison,
    getInterventionRoiMetrics,
    getRetentionForecast,
    getRetentionMetrics,
    getRevenueAtRiskMetrics,
} from '../services/api';

const TABS = [
    { id: 'overview',     label: 'Overview' },
    { id: 'revenue',      label: 'Revenue Impact' },
    { id: 'funnel',       label: 'Retention Funnel' },
    { id: 'roi',          label: 'ROI Analysis' },
    { id: 'forecasting',  label: 'Forecasting' },
    { id: 'alignment',    label: 'Team Alignment' },
];

const BusinessAnalytics = () => {
    const [activeTab, setActiveTab] = useState('overview');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const [retentionMetrics, setRetentionMetrics] = useState(null);
    const [revenueAtRiskMetrics, setRevenueAtRiskMetrics] = useState(null);
    const [interventionRoiMetrics, setInterventionRoiMetrics] = useState(null);
    const [departmentComparison, setDepartmentComparison] = useState([]);
    const [retentionForecast, setRetentionForecast] = useState(null);
    const [cohortHeatmap, setCohortHeatmap] = useState([]);

    useEffect(() => {
        let isMounted = true;
        const load = async () => {
            setLoading(true);
            setError(null);

            const [
                retentionResp,
                revenueResp,
                roiResp,
                deptResp,
                forecastResp,
                heatmapResp,
            ] = await Promise.all([
                getRetentionMetrics(),
                getRevenueAtRiskMetrics(),
                getInterventionRoiMetrics(),
                getDepartmentComparison(),
                getRetentionForecast(6),
                getCohortHeatmap(),
            ]);

            if (!isMounted) return;

            if (!retentionResp.success) {
                setError(retentionResp.message || 'Failed to load business analytics.');
                setLoading(false);
                return;
            }

            setRetentionMetrics(retentionResp.data || null);
            setRevenueAtRiskMetrics(revenueResp.success ? (revenueResp.data || null) : null);
            setInterventionRoiMetrics(roiResp.success ? (roiResp.data || null) : null);
            setDepartmentComparison(deptResp.success && Array.isArray(deptResp.data) ? deptResp.data : []);
            setRetentionForecast(forecastResp.success ? (forecastResp.data || null) : null);
            setCohortHeatmap(heatmapResp.success && Array.isArray(heatmapResp.data) ? heatmapResp.data : []);

            setLoading(false);
        };

        load();
        return () => {
            isMounted = false;
        };
    }, []);

    const fmtNumber = useMemo(() => new Intl.NumberFormat('en-US'), []);
    const fmtCurrency = useMemo(
        () => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }),
        []
    );
    const fmtPercent1 = useMemo(
        () => new Intl.NumberFormat('en-US', { style: 'percent', minimumFractionDigits: 1, maximumFractionDigits: 1 }),
        []
    );

    const summary = useMemo(() => {
        const totalEnrolled = retentionMetrics?.total_enrolled ?? 0;
        const retentionRate = retentionMetrics?.retention_rate ?? 0; // 0..1
        const atRiskCount = retentionMetrics?.at_risk_count ?? 0;
        const highRiskCount = retentionMetrics?.high_risk_count ?? 0;

        const revenueAtRisk = revenueAtRiskMetrics?.revenue_at_risk ?? 0;
        const revenueSaved = interventionRoiMetrics?.revenue_saved ?? 0;
        const interventionROI = interventionRoiMetrics?.roi_multiple ?? 0;
        const averageStudentLtv =
            revenueAtRiskMetrics?.average_student_ltv ??
            retentionForecast?.base?.average_student_ltv ??
            0;

        return {
            totalEnrolled,
            retentionRate,
            atRiskCount,
            highRiskCount,
            revenueAtRisk,
            revenueSaved,
            interventionROI,
            targetRetentionRate: retentionMetrics?.target_retention_rate ?? 0.95,
            averageStudentLtv,
        };
    }, [retentionMetrics, revenueAtRiskMetrics, interventionRoiMetrics, retentionForecast]);

    return (
        <motion.div initial="hidden" animate="visible" variants={variants.container}>
            <Container fluid className="py-4" style={{ maxWidth: '1600px' }}>

                {/* Header */}
                <div className="d-flex justify-content-between align-items-end mb-5">
                    <div>
                        <h1 className="display-5 fw-bold text-gradient mb-2">Business Analytics</h1>
                        <p className="text-secondary fs-5" style={{ maxWidth: '600px' }}>
                            Strategic insights for institutional decision-making.
                        </p>
                    </div>
                    <Button variant="outline-primary" className="d-flex align-items-center gap-2 px-4">
                        <FaDownload size={13} /> Export Report
                    </Button>
                </div>

                {/* KPI Cards */}
                <motion.div variants={variants.item} className="mb-5">
                    {error && (
                        <Alert variant="danger" className="mb-4">
                            {error}
                        </Alert>
                    )}
                    <Row className="g-4">
                        <Col md={3}>
                            <ExecutiveKPI
                                icon={<FaUsers />}
                                label="Total Enrolled"
                                value={fmtNumber.format(summary.totalEnrolled)}
                                sub={`${fmtNumber.format(summary.atRiskCount)} at risk`}
                                subColor="#F59E0B"
                            />
                        </Col>
                        <Col md={3}>
                            <ExecutiveKPI
                                icon={<FaChartLine />}
                                label="Retention Rate"
                                value={fmtPercent1.format(summary.retentionRate)}
                                sub={`Target: ${Math.round((summary.targetRetentionRate || 0) * 100)}%`}
                                subColor={(summary.retentionRate || 0) * 100 >= (summary.targetRetentionRate || 0) * 100 ? '#10B981' : '#F59E0B'}
                            />
                        </Col>
                        <Col md={3}>
                            <ExecutiveKPI
                                icon={<FaDollarSign />}
                                label="Revenue at Risk"
                                value={fmtCurrency.format(summary.revenueAtRisk)}
                                sub={`${fmtNumber.format(summary.highRiskCount)} high-risk students`}
                                subColor="#EF4444"
                            />
                        </Col>
                        <Col md={3}>
                            <ExecutiveKPI
                                icon={<FaFunnelDollar />}
                                label="Intervention ROI"
                                value={`${Number(summary.interventionROI || 0).toFixed(2)}x`}
                                sub={`${fmtCurrency.format(summary.revenueSaved)} saved`}
                                subColor="#10B981"
                            />
                        </Col>
                    </Row>
                </motion.div>

                {/* Tab Bar */}
                <motion.div variants={variants.item} className="mb-4">
                    <div
                        className="d-flex gap-1 p-1 rounded-3"
                        style={{ background: 'rgba(139,92,246,0.07)', border: '1px solid rgba(139,92,246,0.15)', width: 'fit-content' }}
                    >
                        {TABS.map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                style={{
                                    padding: '8px 22px',
                                    borderRadius: '8px',
                                    border: 'none',
                                    cursor: 'pointer',
                                    fontWeight: 600,
                                    fontSize: '0.875rem',
                                    transition: 'all 0.2s',
                                    background: activeTab === tab.id ? '#8B5CF6' : 'transparent',
                                    color:      activeTab === tab.id ? '#fff'    : '#C4B5FD',
                                    boxShadow:  activeTab === tab.id ? '0 2px 8px rgba(139,92,246,0.35)' : 'none',
                                }}
                            >
                                {tab.label}
                            </button>
                        ))}
                    </div>
                </motion.div>

                {/* Tab Content */}
                <motion.div variants={variants.item}>
                    {loading && (
                        <div className="d-flex align-items-center gap-2 text-muted mb-4">
                            <Spinner animation="border" size="sm" />
                            <span>Loading business intelligence data…</span>
                        </div>
                    )}
                    {activeTab === 'overview' && (
                        <Row className="g-4">
                            <Col lg={5}>
                                <RevenueBreakdown summary={summary} />
                            </Col>
                            <Col lg={7}>
                                <DropoutProbabilityFunnel />
                            </Col>
                            <Col lg={12}>
                                <RetentionTrendChart
                                    forecast={retentionForecast}
                                    targetRetentionRatePct={Math.round((summary.targetRetentionRate || 0.95) * 100)}
                                />
                            </Col>
                            <Col lg={12}>
                                <RetentionFunnel />
                            </Col>
                            <Col lg={12}>
                                <DepartmentComparison departments={departmentComparison} />
                            </Col>
                        </Row>
                    )}
                    {activeTab === 'revenue' && (
                        <Row className="g-4">
                            <Col lg={12}><RevenueAtRisk /></Col>
                            <Col lg={6}><RevenueBreakdown summary={summary} /></Col>
                            <Col lg={6}><CostPerRetainedStudent /></Col>
                        </Row>
                    )}
                    {activeTab === 'funnel' && (
                        <Row className="g-4">
                            <Col lg={8}><RetentionFunnel /></Col>
                            <Col lg={4}><DropoutProbabilityFunnel /></Col>
                            <Col lg={12}><CohortRiskBreakdown heatmap={cohortHeatmap} /></Col>
                        </Row>
                    )}
                    {activeTab === 'roi' && (
                        <Row className="g-4">
                            <Col lg={6}><CostPerRetainedStudent /></Col>
                            <Col lg={6}><RevenueAtRisk /></Col>
                            <Col lg={12}><InterventionROITimeline /></Col>
                        </Row>
                    )}
                    {activeTab === 'forecasting' && (
                        <Row className="g-4">
                            <Col lg={12}><RevenueForecast forecast={retentionForecast} /></Col>
                            <Col lg={7}>
                                <RetentionTrendChart
                                    forecast={retentionForecast}
                                    targetRetentionRatePct={Math.round((summary.targetRetentionRate || 0.95) * 100)}
                                />
                            </Col>
                            <Col lg={5}><CohortRiskBreakdown heatmap={cohortHeatmap} /></Col>
                        </Row>
                    )}
                    {activeTab === 'alignment' && (
                        <Row className="g-4">
                            <Col lg={12}><SalesAcademicAlignment /></Col>
                        </Row>
                    )}
                </motion.div>

                {/* Footer */}
                <div className="mt-5 pt-4 border-top text-center">
                    <small className="text-muted">
                        Data refreshed in real-time from Meridian prediction engine. Financial projections based on configured LTV from the backend configuration.
                    </small>
                </div>
            </Container>
        </motion.div>
    );
};

/* ── Shared sub-components ─────────────────────────────────── */

const ExecutiveKPI = ({ icon, label, value, sub, subColor }) => (
    <div className="glass-panel p-4 h-100">
        <div className="d-flex align-items-center gap-3 mb-3">
            <div style={{
                width: 38, height: 38, borderRadius: 10,
                background: 'rgba(139,92,246,0.15)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#8B5CF6', fontSize: 16, flexShrink: 0,
            }}>
                {icon}
            </div>
            <span style={{ fontSize: '0.68rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#B8AADA' }}>
                {label}
            </span>
        </div>
        <div style={{ fontSize: '1.85rem', fontWeight: 800, fontFamily: 'var(--font-family-mono)', color: '#EDE9FE', lineHeight: 1.1, marginBottom: '0.45rem' }}>
            {value}
        </div>
        <div style={{ fontSize: '0.8rem', fontWeight: 500, color: subColor }}>
            {sub}
        </div>
    </div>
);

const RevenueBreakdown = ({ summary }) => {
    const totalEnrolled = summary?.totalEnrolled ?? 0;
    const ltv = summary?.averageStudentLtv ?? 0;
    const totalRevenue = totalEnrolled * (ltv || 0);
    const safe = Math.max(0, totalRevenue - (summary?.revenueAtRisk ?? 0) - (summary?.revenueSaved ?? 0));
    const saved = summary?.revenueSaved ?? 0;
    const at_risk = summary?.revenueAtRisk ?? 0;

    const fmtCurrency = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });

    const segments = [
        { label: 'Safe Revenue',            amount: safe,    color: '#10B981', pct: totalRevenue > 0 ? Math.round(safe    / totalRevenue * 100) : 0 },
        { label: 'Saved by Intervention',   amount: saved,   color: '#8B5CF6', pct: totalRevenue > 0 ? Math.round(saved   / totalRevenue * 100) : 0 },
        { label: 'Still at Risk',           amount: at_risk, color: '#EF4444', pct: totalRevenue > 0 ? Math.round(at_risk / totalRevenue * 100) : 0 },
    ];

    return (
        <div className="glass-panel p-4 h-100">
            <h5 className="fw-semibold mb-1" style={{ color: '#EDE9FE' }}>Revenue Overview</h5>
            <p style={{ fontSize: '0.85rem', color: '#B8AADA', marginBottom: '1.5rem' }}>
                Financial exposure breakdown by cohort
            </p>

            {/* Total portfolio value */}
            <div style={{
                padding: '1rem 1.25rem',
                background: 'rgba(139,92,246,0.1)',
                borderRadius: 10,
                border: '1px solid rgba(139,92,246,0.25)',
                marginBottom: '1.5rem',
                textAlign: 'center',
            }}>
                <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#B8AADA', marginBottom: '0.35rem' }}>
                    Total Portfolio Value
                </div>
                <div style={{ fontSize: '2rem', fontWeight: 800, fontFamily: 'var(--font-family-mono)', color: '#EDE9FE' }}>
                    {fmtCurrency.format(totalRevenue)}
                </div>
            </div>

            {/* Stacked bar */}
            <div style={{ display: 'flex', height: 7, borderRadius: 99, overflow: 'hidden', marginBottom: '1.25rem', gap: 2 }}>
                {segments.map(s => (
                    <div key={s.label} style={{ width: `${s.pct}%`, background: s.color, borderRadius: 99 }} />
                ))}
            </div>

            {/* Segment rows */}
            <div className="d-flex flex-column gap-3 mb-4">
                {segments.map(s => (
                    <div key={s.label} className="d-flex justify-content-between align-items-center">
                        <div className="d-flex align-items-center gap-2">
                            <div style={{ width: 10, height: 10, borderRadius: 3, background: s.color, flexShrink: 0 }} />
                            <span style={{ fontSize: '0.875rem', color: '#C4B5FD' }}>{s.label}</span>
                        </div>
                        <div>
                            <span style={{ fontSize: '0.95rem', fontWeight: 700, fontFamily: 'var(--font-family-mono)', color: '#EDE9FE' }}>
                                {fmtCurrency.format(s.amount)}
                            </span>
                            <span style={{ fontSize: '0.75rem', color: '#B8AADA', marginLeft: '0.4rem' }}>
                                {s.pct}%
                            </span>
                        </div>
                    </div>
                ))}
            </div>

            {/* ROI callout */}
            <div style={{
                padding: '0.75rem 1rem',
                background: 'rgba(16,185,129,0.08)',
                borderRadius: 8,
                border: '1px solid rgba(16,185,129,0.2)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
            }}>
                <span style={{ fontSize: '0.8rem', color: '#10B981' }}>Intervention ROI</span>
                <span style={{ fontSize: '1.1rem', fontWeight: 800, fontFamily: 'var(--font-family-mono)', color: '#10B981' }}>
                    {summary.interventionROI}x return
                </span>
            </div>
        </div>
    );
};

const DepartmentComparison = ({ departments }) => {
    const rows = Array.isArray(departments) ? departments : [];
    const fmt = new Intl.NumberFormat('en-US');

    return (
        <div className="glass-panel p-4 h-100">
            <h5 className="fw-semibold mb-1" style={{ color: '#EDE9FE' }}>Department Comparison</h5>
            <p style={{ fontSize: '0.85rem', color: '#B8AADA', marginBottom: '1.25rem' }}>
                Cohort size and average risk by department
            </p>

            {rows.length === 0 ? (
                <div className="text-muted" style={{ fontSize: '0.9rem' }}>No department data available.</div>
            ) : (
                <div className="d-flex flex-column gap-2">
                    {rows.slice(0, 10).map((d) => (
                        <div
                            key={d.department}
                            className="d-flex justify-content-between align-items-center"
                            style={{
                                padding: '0.75rem 0.9rem',
                                borderRadius: 10,
                                background: 'rgba(139,92,246,0.07)',
                                border: '1px solid rgba(139,92,246,0.13)',
                            }}
                        >
                            <div>
                                <div style={{ fontWeight: 700, color: '#EDE9FE' }}>{d.department}</div>
                                <div style={{ fontSize: '0.8rem', color: '#B8AADA' }}>{fmt.format(d.student_count)} students</div>
                            </div>
                            <div style={{ textAlign: 'right' }}>
                                <div style={{ fontFamily: 'var(--font-family-mono)', fontWeight: 800, color: '#C4B5FD' }}>
                                    {Number(d.avg_risk_score || 0).toFixed(1)}%
                                </div>
                                <div style={{ fontSize: '0.75rem', color: '#B8AADA' }}>avg risk</div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default BusinessAnalytics;
