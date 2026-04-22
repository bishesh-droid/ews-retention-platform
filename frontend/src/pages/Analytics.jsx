import React, { useState, useEffect, useMemo } from 'react';
import { Row, Col, Card, Button, Form, Spinner, Alert } from 'react-bootstrap';
import { FaDownload, FaChartLine, FaUsers, FaExclamationTriangle, FaShieldAlt, FaUserCheck } from 'react-icons/fa';
import { Line, Scatter, Doughnut, Bar } from 'react-chartjs-2';
import {
    BarChart, Bar as ReBar, XAxis, YAxis, CartesianGrid,
    Tooltip as ReTooltip, Legend as ReLegend, ResponsiveContainer,
    RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from 'recharts';
import { motion } from 'framer-motion';
import { variants } from '../utils/motionConfig';
import TimeFilter from '../components/common/TimeFilter';
import {
    getRiskDistribution,
    getStudentList,
    getCohortRiskTrends,
    getCohortEngagementTrends,
    getCohortPerformanceTrends,
    getInterventionEffectivenessSummary,
} from '../services/api';

const PALETTE = {
    critical: '#EF4444',
    high:     '#F59E0B',
    medium:   '#EAB308',
    low:      '#10B981',
    purple:   '#7C3AED',
    blue:     '#3B82F6',
    pink:     '#EC4899',
};

// Shared recharts tooltip style
const reTooltipProps = {
    contentStyle: {
        background: '#1E1535',
        border: '1px solid rgba(139,92,246,0.3)',
        borderRadius: 10,
        color: '#EDE9FE',
    },
    itemStyle: { color: '#EDE9FE' },
    labelStyle: { color: '#B8AADA', fontWeight: 600 },
};

const Analytics = () => {
    const [timeRange, setTimeRange] = useState('semester');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [sampleStudents, setSampleStudents] = useState([]);
    const [riskDistribution, setRiskDistribution] = useState(null);
    const [cohortRiskTrends, setCohortRiskTrends] = useState(null);
    const [cohortEngagementTrends, setCohortEngagementTrends] = useState(null);
    const [cohortPerformanceTrends, setCohortPerformanceTrends] = useState(null);
    const [interventionEffectiveness, setInterventionEffectiveness] = useState(null);

    const weeksForRange = useMemo(() => {
        if (timeRange === 'month') return 4;
        if (timeRange === 'quarter') return 13;
        if (timeRange === 'year') return 52;
        return 16; // semester-ish default
    }, [timeRange]);

    useEffect(() => {
        let isMounted = true;
        const load = async () => {
            setLoading(true);
            setError(null);

            const [distResp, studentsResp, riskTrendResp, engagementResp, performanceResp, interventionResp] = await Promise.all([
                getRiskDistribution(),
                getStudentList(1, 500),
                getCohortRiskTrends(weeksForRange),
                getCohortEngagementTrends(weeksForRange),
                getCohortPerformanceTrends(weeksForRange),
                getInterventionEffectivenessSummary(weeksForRange),
            ]);

            if (!isMounted) return;

            if (!distResp.success) {
                setError(distResp.message || 'Failed to load analytics data.');
                setLoading(false);
                return;
            }

            setRiskDistribution(distResp.data || null);
            setSampleStudents(studentsResp.success ? (studentsResp.data?.students || []) : []);
            setCohortRiskTrends(riskTrendResp.success ? riskTrendResp.data : null);
            setCohortEngagementTrends(engagementResp.success ? engagementResp.data : null);
            setCohortPerformanceTrends(performanceResp.success ? performanceResp.data : null);
            setInterventionEffectiveness(interventionResp.success ? interventionResp.data : null);

            setLoading(false);
        };

        load();
        return () => {
            isMounted = false;
        };
    }, [weeksForRange]);

    /* ── KPI stats derived from real student data ─────────────────────── */
    const stats = useMemo(() => {
        if (!sampleStudents.length) return { total: 0, atRisk: 0, critical: 0, atRiskPct: 0, avgAttendance: null };
        const total    = sampleStudents.length;
        const atRisk   = sampleStudents.filter(s => (s.risk_score ?? 0) >= 60).length;
        const critical = sampleStudents.filter(s => (s.risk_score ?? 0) >= 80).length;
        const atRiskPct = total > 0 ? Math.round((atRisk / total) * 100) : 0;
        const avgAttendance = total > 0
            ? Math.round(sampleStudents.reduce((a, s) => a + (s.exam_attendance_rate ?? 0), 0) / total)
            : null;
        return { total, atRisk, critical, atRiskPct, avgAttendance };
    }, [sampleStudents]);

    /* ── Risk distribution counts for Doughnut ────────────────────────── */
    const riskCounts = useMemo(() => {
        const hist = riskDistribution?.histogram;
        if (Array.isArray(hist) && hist.length > 0) {
            const bucketToStart = (range) => {
                const m = String(range).match(/^(\d+)\s*-\s*(\d+)/);
                return m ? parseInt(m[1], 10) : null;
            };
            const sumRange = (min, max) =>
                hist
                    .filter((b) => {
                        const start = bucketToStart(b.range);
                        return start !== null && start >= min && start < max;
                    })
                    .reduce((a, b) => a + (b.count ?? 0), 0);
            return [
                sumRange(0, 40),
                sumRange(40, 60),
                sumRange(60, 80),
                sumRange(80, 101),
            ];
        }
        if (sampleStudents.length) {
            return [
                sampleStudents.filter(s => (s.risk_score ?? 0) <  40).length,
                sampleStudents.filter(s => (s.risk_score ?? 0) >= 40 && (s.risk_score ?? 0) < 60).length,
                sampleStudents.filter(s => (s.risk_score ?? 0) >= 60 && (s.risk_score ?? 0) < 80).length,
                sampleStudents.filter(s => (s.risk_score ?? 0) >= 80).length,
            ];
        }
        return [0, 0, 0, 0];
    }, [riskDistribution, sampleStudents]);

    /* ── Risk Score Trends (existing) ──────────────────────────────────── */
    const riskTrendsData = useMemo(() => {
        const labels = cohortRiskTrends?.labels || [];
        const series = cohortRiskTrends?.series || {};
        return {
            labels,
            datasets: [
                {
                    label: 'Overall Average',
                    data: series.overall || [],
                    borderColor: PALETTE.purple,
                    backgroundColor: 'rgba(124,58,237,0.08)',
                    borderWidth: 2, tension: 0.4, pointRadius: 3,
                },
                {
                    label: 'High Risk (avg score)',
                    data: series.high || [],
                    borderColor: PALETTE.high,
                    backgroundColor: 'rgba(245,158,11,0.08)',
                    borderWidth: 2, tension: 0.4, pointRadius: 3,
                },
                {
                    label: 'Critical (avg score)',
                    data: series.critical || [],
                    borderColor: PALETTE.critical,
                    backgroundColor: 'rgba(239,68,68,0.08)',
                    borderWidth: 2, tension: 0.4, pointRadius: 3,
                },
            ],
        };
    }, [cohortRiskTrends]);

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: true, position: 'top', labels: { color: '#EDE9FE', usePointStyle: true } },
            tooltip: { backgroundColor: '#130D23', titleColor: '#EDE9FE', bodyColor: '#B8AADA', borderColor: 'rgba(139,92,246,0.18)', borderWidth: 1 },
        },
        scales: {
            y: { beginAtZero: true, max: 100, grid: { color: 'rgba(139,92,246,0.18)' }, ticks: { color: '#B8AADA' } },
            x: { grid: { display: false }, ticks: { color: '#B8AADA' } },
        },
    };

    /* ── Attendance vs Risk Scatter (existing) ─────────────────────────── */
    const scatterPoints = useMemo(
        () =>
            sampleStudents
                .slice(0, 300)
                .map(s => {
                    const attendance = Number.isFinite(s.exam_attendance_rate) ? s.exam_attendance_rate : 0;
                    const risk = Number.isFinite(s.risk_score) ? s.risk_score : 0;
                    return { x: Math.round(attendance), y: Math.round(risk) };
                })
                .filter(p => Number.isFinite(p.x) && Number.isFinite(p.y)),
        [sampleStudents],
    );

    const scatterData = {
        datasets: [{
            label: 'Students',
            data: scatterPoints,
            backgroundColor: 'rgba(139,92,246,0.5)',
            borderColor: 'rgba(139,92,246,0.8)',
            pointRadius: 5,
        }],
    };

    const scatterOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: { backgroundColor: '#130D23', titleColor: '#EDE9FE', bodyColor: '#B8AADA', borderColor: 'rgba(139,92,246,0.18)', borderWidth: 1 },
        },
        scales: {
            y: { title: { display: true, text: 'Risk Score', color: '#EDE9FE' }, beginAtZero: true, max: 100, grid: { color: 'rgba(139,92,246,0.18)' }, ticks: { color: '#B8AADA' } },
            x: { title: { display: true, text: 'Attendance %', color: '#EDE9FE' }, beginAtZero: true, max: 100, grid: { color: 'rgba(139,92,246,0.18)' }, ticks: { color: '#B8AADA' } },
        },
    };

    /* ── Doughnut – Risk Distribution ──────────────────────────────────── */
    const doughnutData = {
        labels: ['Low Risk', 'Medium Risk', 'High Risk', 'Critical'],
        datasets: [{
            data: riskCounts,
            backgroundColor: [PALETTE.low, PALETTE.medium, PALETTE.high, PALETTE.critical],
            borderColor: ['rgba(16,185,129,0.3)', 'rgba(234,179,8,0.3)', 'rgba(245,158,11,0.3)', 'rgba(239,68,68,0.3)'],
            borderWidth: 2,
            hoverOffset: 10,
        }],
    };

    const doughnutOptions = {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '62%',
        plugins: {
            legend: {
                position: 'bottom',
                labels: { color: '#EDE9FE', usePointStyle: true, padding: 14, font: { size: 12 } },
            },
            tooltip: {
                backgroundColor: '#130D23',
                titleColor: '#EDE9FE',
                bodyColor: '#B8AADA',
                borderColor: 'rgba(139,92,246,0.18)',
                borderWidth: 1,
                callbacks: {
                    label: ctx => {
                        const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                        const pct   = total > 0 ? Math.round((ctx.parsed / total) * 100) : 0;
                        return ` ${ctx.label}: ${ctx.parsed} students (${pct}%)`;
                    },
                },
            },
        },
    };

    /* ── Horizontal Bar – Top Risk Factors ─────────────────────────────── */
    const riskFactorData = useMemo(() => {
        const agg = {};
        sampleStudents.forEach((s) => {
            const rb = s.risk_breakdown;
            if (!rb || typeof rb !== 'object') return;
            Object.entries(rb).forEach(([k, v]) => {
                if (!k.endsWith('_risk')) return;
                const num = typeof v === 'number' ? v : 0;
                if (!agg[k]) agg[k] = { sum: 0, n: 0 };
                agg[k].sum += num;
                agg[k].n += 1;
            });
        });
        const top = Object.entries(agg)
            .map(([k, meta]) => ({
                key: k,
                label: k.replace(/_risk$/, '').replace(/_/g, ' '),
                value: meta.n ? meta.sum / meta.n : 0,
            }))
            .sort((a, b) => b.value - a.value)
            .slice(0, 5);

        return {
            labels: top.map((t) => t.label),
            datasets: [{
                label: 'Avg Risk Contribution (0–100)',
                data: top.map((t) => Math.round(t.value)),
                backgroundColor: [
                    'rgba(239,68,68,0.8)',
                    'rgba(245,158,11,0.8)',
                    'rgba(234,179,8,0.8)',
                    'rgba(124,58,237,0.8)',
                    'rgba(59,130,246,0.8)',
                ].slice(0, top.length),
                borderRadius: 6,
                borderSkipped: false,
            }],
        };
    }, [sampleStudents]);

    const riskFactorOptions = {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: '#130D23',
                titleColor: '#EDE9FE',
                bodyColor: '#B8AADA',
                borderColor: 'rgba(139,92,246,0.18)',
                borderWidth: 1,
            },
        },
        scales: {
            x: {
                beginAtZero: true, max: 100,
                grid: { color: 'rgba(139,92,246,0.12)' },
                ticks: { color: '#B8AADA', callback: v => v + '%' },
            },
            y: { grid: { display: false }, ticks: { color: '#EDE9FE', font: { size: 12 } } },
        },
    };

    /* ── Recharts – Cohort Comparison bar ──────────────────────────────── */
    const cohortChartData = useMemo(() => {
        // Use engagement + performance trend values as the two series where possible.
        const labels = cohortEngagementTrends?.labels || [];
        const lastEng = Array.isArray(cohortEngagementTrends?.values) ? cohortEngagementTrends.values.at(-1) : null;
        const lastPerf = Array.isArray(cohortPerformanceTrends?.values) ? cohortPerformanceTrends.values.at(-1) : null;
        if (lastEng === null && lastPerf === null) return [];
        return [
            { metric: 'Engagement', current: lastEng ?? 0, previous: 0 },
            { metric: 'Performance', current: lastPerf ?? 0, previous: 0 },
        ];
    }, [cohortEngagementTrends, cohortPerformanceTrends]);

    /* ── Recharts – Intervention Effectiveness ─────────────────────────── */
    const interventionData = useMemo(() => {
        const risk = interventionEffectiveness?.risk;
        if (!risk || risk.before_avg == null || risk.after_avg == null) return [];
        return [
            { metric: 'Risk Score', before: risk.before_avg, after: risk.after_avg },
        ];
    }, [interventionEffectiveness]);

    /* ── Recharts – Risk Radar (multi-factor profile) ───────────────────── */
    const radarData = useMemo(() => {
        const groups = {
            critical: sampleStudents.filter(s => (s.risk_score ?? 0) >= 80),
            high: sampleStudents.filter(s => (s.risk_score ?? 0) >= 60 && (s.risk_score ?? 0) < 80),
            low: sampleStudents.filter(s => (s.risk_score ?? 0) < 40),
        };
        const avg = (arr, key) => {
            if (!arr.length) return 0;
            return Math.round(arr.reduce((a, s) => a + (s[key] ?? 0), 0) / arr.length);
        };
        return [
            { factor: 'Attendance', critical: avg(groups.critical, 'exam_attendance_rate'), high: avg(groups.high, 'exam_attendance_rate'), low: avg(groups.low, 'exam_attendance_rate') },
            { factor: 'Quiz', critical: avg(groups.critical, 'graded_quiz_score'), high: avg(groups.high, 'graded_quiz_score'), low: avg(groups.low, 'graded_quiz_score') },
            { factor: 'Assignments', critical: avg(groups.critical, 'graded_assignment_score'), high: avg(groups.high, 'graded_assignment_score'), low: avg(groups.low, 'graded_assignment_score') },
            { factor: 'Engagement', critical: avg(groups.critical, 'content_completion_score'), high: avg(groups.high, 'content_completion_score'), low: avg(groups.low, 'content_completion_score') },
            { factor: 'Discussion', critical: avg(groups.critical, 'discussion_engagement_score'), high: avg(groups.high, 'discussion_engagement_score'), low: avg(groups.low, 'discussion_engagement_score') },
            { factor: 'Exam', critical: avg(groups.critical, 'exam_score'), high: avg(groups.high, 'exam_score'), low: avg(groups.low, 'exam_score') },
        ];
    }, [sampleStudents]);

    /* ═══════════════════════════════════════════════════════════════════ */
    return (
        <motion.div initial="hidden" animate="visible" variants={variants.container} className="pb-5">

            {/* ── Header ─────────────────────────────────────────────── */}
            <div className="d-flex justify-content-between align-items-end mb-4">
                <div>
                    <h1 className="display-5 fw-bold text-gradient mb-2">Analytics</h1>
                    <p className="text-secondary fs-5" style={{ maxWidth: '700px' }}>
                        Deep-dive data visualization and trend analysis for institutional insights and reporting.
                    </p>
                </div>
                <div className="d-flex gap-2">
                    <TimeFilter selectedRange={timeRange} onRangeChange={setTimeRange} />
                    <Button variant="outline-primary" className="d-flex align-items-center gap-2">
                        <FaDownload /> Export Data
                    </Button>
                </div>
            </div>

            {loading && (
                <div className="mb-4 d-flex align-items-center gap-2">
                    <Spinner animation="border" variant="primary" size="sm" />
                    <span className="text-secondary">Loading analytics…</span>
                </div>
            )}
            {!loading && error && (
                <Alert variant="danger" className="mb-4">
                    {error}
                </Alert>
            )}
            {!loading && !error && riskCounts.reduce((a, b) => a + b, 0) === 0 && (
                <Alert variant="info" className="mb-4">
                    No analytics data available yet.
                </Alert>
            )}

            {/* ── KPI Summary Cards ───────────────────────────────────── */}
            <motion.div variants={variants.item} className="mb-4">
                <Row className="g-3">
                    {[
                        {
                            icon: <FaUsers size={22} />,
                            value: stats.total || '—',
                            label: 'Total Students',
                            sub: 'Enrolled this semester',
                            color: PALETTE.purple,
                            bg: 'rgba(124,58,237,0.12)',
                        },
                        {
                            icon: <FaExclamationTriangle size={22} />,
                            value: `${stats.atRisk}`,
                            label: 'At-Risk Students',
                            sub: `${stats.atRiskPct}% of total enrollment`,
                            color: PALETTE.high,
                            bg: 'rgba(245,158,11,0.12)',
                        },
                        {
                            icon: <FaShieldAlt size={22} />,
                            value: stats.critical,
                            label: 'Critical Cases',
                            sub: 'Need immediate attention',
                            color: PALETTE.critical,
                            bg: 'rgba(239,68,68,0.12)',
                        },
                        {
                            icon: <FaUserCheck size={22} />,
                            value: stats.avgAttendance !== null ? `${stats.avgAttendance}%` : '—',
                            label: 'Avg Attendance',
                            sub: 'Across loaded cohort sample',
                            color: PALETTE.low,
                            bg: 'rgba(16,185,129,0.12)',
                        },
                    ].map((kpi, i) => (
                        <Col md={3} key={i}>
                            <motion.div
                                variants={variants.item}
                                className="glass-panel p-3 h-100"
                                style={{ borderLeft: `3px solid ${kpi.color}` }}
                            >
                                <div className="d-flex align-items-center gap-3">
                                    <div
                                        className="rounded-3 d-flex align-items-center justify-content-center"
                                        style={{ width: 48, height: 48, background: kpi.bg, color: kpi.color, flexShrink: 0 }}
                                    >
                                        {kpi.icon}
                                    </div>
                                    <div>
                                        <div className="fw-bold fs-4" style={{ color: kpi.color, lineHeight: 1.1 }}>{kpi.value}</div>
                                        <div className="fw-semibold text-light small">{kpi.label}</div>
                                        <div className="text-secondary" style={{ fontSize: '0.72rem' }}>{kpi.sub}</div>
                                    </div>
                                </div>
                            </motion.div>
                        </Col>
                    ))}
                </Row>
            </motion.div>

            {/* ── Risk Score Trends Over Time ─────────────────────────── */}
            <motion.div variants={variants.item} className="glass-panel p-4 mb-4">
                <h5 className="mb-4 fw-semibold">Risk Score Trends Over Time</h5>
                <div style={{ height: '320px' }}>
                    {riskTrendsData.labels.length > 0 ? (
                        <Line data={riskTrendsData} options={chartOptions} />
                    ) : (
                        <div className="text-center py-5 text-muted">No cohort risk trend data available.</div>
                    )}
                </div>
            </motion.div>

            {/* ── NEW: Risk Distribution + Top Risk Factors ──────────── */}
            <Row className="g-4 mb-4">
                {/* Doughnut – who is at risk? */}
                <Col lg={5}>
                    <motion.div variants={variants.item} className="glass-panel p-4 h-100">
                        <h5 className="mb-1 fw-semibold">Student Risk Distribution</h5>
                        <p className="text-secondary small mb-3">Snapshot of where every student stands right now</p>
                        <div style={{ height: '280px' }}>
                            <Doughnut data={doughnutData} options={doughnutOptions} />
                        </div>
                        <div className="mt-3 d-flex flex-wrap gap-2 justify-content-center">
                            {['Low Risk', 'Medium Risk', 'High Risk', 'Critical'].map((label, i) => {
                                const colors = [PALETTE.low, PALETTE.medium, PALETTE.high, PALETTE.critical];
                                const total  = riskCounts.reduce((a, b) => a + b, 0);
                                const pct    = total > 0 ? Math.round((riskCounts[i] / total) * 100) : 0;
                                return (
                                    <span key={label} className="badge rounded-pill px-3 py-2" style={{ background: colors[i] + '22', color: colors[i], border: `1px solid ${colors[i]}55`, fontSize: '0.75rem' }}>
                                        {label}: {pct}%
                                    </span>
                                );
                            })}
                        </div>
                    </motion.div>
                </Col>

                {/* Horizontal Bar – what drives risk? */}
                <Col lg={7}>
                    <motion.div variants={variants.item} className="glass-panel p-4 h-100">
                        <h5 className="mb-1 fw-semibold">Top Risk Factors</h5>
                        <p className="text-secondary small mb-3">How much each factor contributes to student dropout risk</p>
                        <div style={{ height: '280px' }}>
                            {riskFactorData.labels.length > 0 ? (
                                <Bar data={riskFactorData} options={riskFactorOptions} />
                            ) : (
                                <div className="text-center py-5 text-muted">No risk factor breakdown available.</div>
                            )}
                        </div>
                        {riskFactorData.labels.length > 0 && (
                            <div className="mt-3 alert alert-info py-2 mb-0">
                                <small><strong>Takeaway:</strong> Top drivers are computed from backend risk breakdowns (averaged across the cohort sample).</small>
                            </div>
                        )}
                    </motion.div>
                </Col>
            </Row>

            {/* ── Attendance vs Risk + Cohort Comparison ─────────────── */}
            <Row className="g-4 mb-4">
                {/* Scatter (existing) */}
                <Col lg={6}>
                    <motion.div variants={variants.item} className="glass-panel p-4 h-100">
                        <h5 className="mb-3 fw-semibold">Attendance vs. Risk Correlation</h5>
                        <div style={{ height: '280px' }}>
                            {scatterPoints.length > 0 ? (
                                <Scatter data={scatterData} options={scatterOptions} />
                            ) : (
                                <div className="text-center py-5 text-muted">No student metrics available for correlation plot.</div>
                            )}
                        </div>
                        {scatterPoints.length > 0 && (
                            <div className="mt-3 alert alert-info mb-0">
                                <small><strong>Insight:</strong> Each point is a student from the backend cohort sample.</small>
                            </div>
                        )}
                    </motion.div>
                </Col>

                {/* Cohort Comparison – bar chart instead of plain table */}
                <Col lg={6}>
                    <motion.div variants={variants.item} className="glass-panel p-4 h-100">
                        <h5 className="mb-1 fw-semibold">Cohort Comparison</h5>
                        <p className="text-secondary small mb-3">Engagement & performance snapshots from backend trends</p>
                        <div style={{ height: '280px' }}>
                            {cohortChartData.length > 0 ? (
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={cohortChartData} margin={{ top: 4, right: 8, left: -10, bottom: 0 }}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.15)" />
                                        <XAxis dataKey="metric" tick={{ fill: '#B8AADA', fontSize: 11 }} />
                                        <YAxis tick={{ fill: '#B8AADA', fontSize: 11 }} />
                                        <ReTooltip {...reTooltipProps} />
                                        <ReLegend wrapperStyle={{ color: '#EDE9FE', fontSize: 12 }} />
                                        <ReBar dataKey="current" name="Current" fill={PALETTE.purple} radius={[4,4,0,0]} />
                                        <ReBar dataKey="previous" name="Previous" fill={PALETTE.blue} radius={[4,4,0,0]} />
                                    </BarChart>
                                </ResponsiveContainer>
                            ) : (
                                <div className="text-center py-5 text-muted">No engagement/performance trend data available.</div>
                            )}
                        </div>
                        {cohortChartData.length > 0 && (
                            <div className="alert alert-success mt-3 mb-0">
                                <small><strong>Insight:</strong> Trend snapshots are computed from backend trend feeds.</small>
                            </div>
                        )}
                    </motion.div>
                </Col>
            </Row>

            {/* ── NEW: Intervention Effectiveness ─────────────────────── */}
            <motion.div variants={variants.item} className="glass-panel p-4 mb-4">
                <h5 className="mb-1 fw-semibold">Intervention Effectiveness</h5>
                <p className="text-secondary small mb-3">
                    Before vs. After the intervention programme — higher is better, except for Risk Score (lower = safer)
                </p>
                <div style={{ height: '280px' }}>
                    {interventionData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={interventionData} margin={{ top: 4, right: 20, left: -10, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.15)" />
                                <XAxis dataKey="metric" tick={{ fill: '#B8AADA', fontSize: 12 }} />
                                <YAxis domain={[0, 100]} tick={{ fill: '#B8AADA', fontSize: 12 }} tickFormatter={v => v} />
                                <ReTooltip {...reTooltipProps} />
                                <ReLegend wrapperStyle={{ color: '#EDE9FE', fontSize: 12 }} />
                                <ReBar dataKey="before" name="Before" fill="rgba(239,68,68,0.75)"  radius={[4,4,0,0]} />
                                <ReBar dataKey="after"  name="After"  fill="rgba(16,185,129,0.8)" radius={[4,4,0,0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    ) : (
                        <div className="text-center py-5 text-muted">No intervention effectiveness data available.</div>
                    )}
                </div>
                <Row className="g-3 mt-1">
                    {(interventionEffectiveness?.risk?.improvement_avg != null ? ([
                        { label: 'Avg risk improvement', value: `${interventionEffectiveness.risk.improvement_avg > 0 ? '+' : ''}${interventionEffectiveness.risk.improvement_avg} pts`, color: PALETTE.low },
                        { label: 'Interventions counted', value: `${interventionEffectiveness.risk.n}`, color: PALETTE.low },
                        { label: 'Window', value: `${interventionEffectiveness.window_weeks} wks`, color: PALETTE.low },
                        { label: 'Total interventions', value: `${interventionEffectiveness.total_interventions}`, color: PALETTE.low },
                    ]) : ([])).map((m, i) => (
                        <Col key={i} md={3}>
                            <div className="text-center p-2 rounded-3" style={{ background: 'rgba(16,185,129,0.08)', border: '1px solid rgba(16,185,129,0.2)' }}>
                                <div className="fw-bold fs-5" style={{ color: PALETTE.low }}>{m.value}</div>
                                <small className="text-secondary">{m.label}</small>
                            </div>
                        </Col>
                    ))}
                </Row>
            </motion.div>

            {/* ── NEW: Risk Profile Radar ─────────────────────────────── */}
            <motion.div variants={variants.item} className="glass-panel p-4 mb-4">
                <h5 className="mb-1 fw-semibold">Risk Profile Radar</h5>
                <p className="text-secondary small mb-3">
                    Multi-factor risk profile across student groups — larger area = higher risk in that dimension
                </p>
                <div style={{ height: '320px' }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <RadarChart data={radarData}>
                            <PolarGrid stroke="rgba(139,92,246,0.25)" />
                            <PolarAngleAxis dataKey="factor" tick={{ fill: '#EDE9FE', fontSize: 12 }} />
                            <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#B8AADA', fontSize: 10 }} />
                            <Radar name="Critical" dataKey="critical" stroke={PALETTE.critical} fill={PALETTE.critical} fillOpacity={0.25} strokeWidth={2} />
                            <Radar name="High Risk" dataKey="high"     stroke={PALETTE.high}     fill={PALETTE.high}     fillOpacity={0.2}  strokeWidth={2} />
                            <Radar name="Low Risk"  dataKey="low"      stroke={PALETTE.low}      fill={PALETTE.low}      fillOpacity={0.15} strokeWidth={2} />
                            <ReLegend wrapperStyle={{ color: '#EDE9FE', fontSize: 12 }} />
                            <ReTooltip {...reTooltipProps} />
                        </RadarChart>
                    </ResponsiveContainer>
                </div>
                <div className="mt-2 alert alert-info mb-0">
                    <small><strong>How to read:</strong> Each axis represents a risk dimension. A larger shaded area means that group scores higher on that risk factor. Critical students (red) consistently spike across all dimensions.</small>
                </div>
            </motion.div>

            {/* ── Key Insights (Auto-generated) ───────────────────────── */}
            <motion.div variants={variants.item} className="glass-panel p-4">
                <h5 className="mb-4 fw-semibold d-flex align-items-center gap-2">
                    <FaChartLine /> Key Insights (Auto-generated)
                </h5>
                <Row className="g-3">
                    <Col md={4}>
                        <Card bg="danger" bg-opacity="10" border="danger" className="border-opacity-25 h-100">
                            <Card.Body>
                                <div className="d-flex align-items-start gap-2">
                                    <span className="text-danger">🔔</span>
                                    <div>
                                        <h6 className="text-danger mb-2">Alert</h6>
                                        <p className="small mb-2">
                                            {riskFactorData.labels.length ? `Top risk driver: ${riskFactorData.labels[0]}` : 'No alert insight available yet.'}
                                        </p>
                                        <small className="text-muted">→ Based on current cohort risk breakdown and trend feeds</small>
                                    </div>
                                </div>
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={4}>
                        <Card bg="success" bg-opacity="10" border="success" className="border-opacity-25 h-100">
                            <Card.Body>
                                <div className="d-flex align-items-start gap-2">
                                    <span className="text-success">✅</span>
                                    <div>
                                        <h6 className="text-success mb-2">Positive</h6>
                                        <p className="small mb-2">
                                            {interventionEffectiveness?.risk?.improvement_avg != null
                                                ? `Avg risk improved by ${interventionEffectiveness.risk.improvement_avg} pts in the last ${interventionEffectiveness.window_weeks} weeks`
                                                : 'No intervention impact insight available yet.'}
                                        </p>
                                        <small className="text-muted">→ Computed from interventions with recorded trigger risk</small>
                                    </div>
                                </div>
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={4}>
                        <Card bg="warning" bg-opacity="10" border="warning" className="border-opacity-25 h-100">
                            <Card.Body>
                                <div className="d-flex align-items-start gap-2">
                                    <span className="text-warning">⚠️</span>
                                    <div>
                                        <h6 className="text-warning mb-2">Warning</h6>
                                        <p className="small mb-2">
                                            {stats.critical ? `${stats.critical} critical cases in loaded cohort sample` : 'No warning insight available yet.'}
                                        </p>
                                        <small className="text-muted">→ Prioritize outreach and verify attendance / assessment signals</small>
                                    </div>
                                </div>
                            </Card.Body>
                        </Card>
                    </Col>
                </Row>
            </motion.div>

        </motion.div>
    );
};

export default Analytics;
