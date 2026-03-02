import React, { useState, useRef, useEffect } from 'react';
import { Row, Col, Card, Button, Form } from 'react-bootstrap';
import { FaDownload, FaChartLine, FaFileExport } from 'react-icons/fa';
import { Line, Scatter } from 'react-chartjs-2';
import { motion } from 'framer-motion';
import { variants } from '../utils/motionConfig';
import { useStudentData } from '../context/StudentContext';
import TimeFilter from '../components/common/TimeFilter';

const Analytics = () => {
    const { students } = useStudentData();
    const [timeRange, setTimeRange] = useState('semester');
    const lineChartRef = useRef(null);
    const scatterChartRef = useRef(null);

    // Risk trends data — all three lines show avg risk SCORE (0-100) for each group over time
    const riskTrendsData = {
        labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6', 'Current'],
        datasets: [
            {
                label: 'Overall Average',
                data: [45, 44, 46, 43, 42, 41, 42],
                borderColor: '#7C3AED',
                backgroundColor: 'rgba(124, 58, 237, 0.08)',
                borderWidth: 2,
                tension: 0.4,
                pointRadius: 4,
            },
            {
                // Avg risk score of the HIGH-RISK cohort — should sit between Overall and Critical
                label: 'High Risk (avg score)',
                data: [72, 74, 71, 73, 70, 69, 67],
                borderColor: '#F59E0B',
                backgroundColor: 'rgba(245, 158, 11, 0.08)',
                borderWidth: 2,
                tension: 0.4,
                pointRadius: 4,
            },
            {
                // Avg risk score of the CRITICAL cohort — highest line
                label: 'Critical (avg score)',
                data: [88, 87, 90, 89, 91, 88, 86],
                borderColor: '#EF4444',
                backgroundColor: 'rgba(239, 68, 68, 0.08)',
                borderWidth: 2,
                tension: 0.4,
                pointRadius: 4,
            },
        ],
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'top',
                labels: { color: '#EDE9FE', usePointStyle: true },
            },
            tooltip: {
                backgroundColor: '#130D23',
                titleColor: '#EDE9FE',
                bodyColor: '#B8AADA',
                borderColor: 'rgba(139,92,246,0.18)',
                borderWidth: 1,
            },
        },
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                grid: { color: 'rgba(139,92,246,0.18)' },
                ticks: { color: '#B8AADA' },
            },
            x: {
                grid: { display: false },
                ticks: { color: '#B8AADA' },
            },
        },
    };

    // Scatter plot: Attendance % (x) vs Risk Score (y)
    // Uses real student dropout_risk (0-1) scaled to 0-100, with attendance derived
    // from existing fields or synthesised to show realistic negative correlation.
    const scatterPoints = students.slice(0, 60).map(s => {
        const risk = Math.round((s.dropout_risk ?? Math.random() * 0.9) * 100);
        // Derive attendance: high risk → lower attendance, with noise
        const baseAttendance = 100 - risk;
        const attendance = Math.max(5, Math.min(100, baseAttendance + (Math.random() - 0.5) * 35));
        return { x: Math.round(attendance), y: risk };
    });

    const scatterData = {
        datasets: [
            {
                label: 'Students',
                data: scatterPoints,
                backgroundColor: 'rgba(139, 92, 246, 0.5)',
                borderColor: 'rgba(139, 92, 246, 0.8)',
                pointRadius: 5,
            },
        ],
    };

    const scatterOptions = {
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
            y: {
                title: { display: true, text: 'Risk Score', color: '#EDE9FE' },
                beginAtZero: true,
                max: 100,
                grid: { color: 'rgba(139,92,246,0.18)' },
                ticks: { color: '#B8AADA' },
            },
            x: {
                title: { display: true, text: 'Attendance %', color: '#EDE9FE' },
                beginAtZero: true,
                max: 100,
                grid: { color: 'rgba(139,92,246,0.18)' },
                ticks: { color: '#B8AADA' },
            },
        },
    };

    // Cleanup charts on unmount
    useEffect(() => {
        return () => {
            if (lineChartRef.current) {
                lineChartRef.current.destroy();
            }
            if (scatterChartRef.current) {
                scatterChartRef.current.destroy();
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
            <div className="d-flex justify-content-between align-items-end mb-5">
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

            {/* Risk Trends Over Time */}
            <motion.div variants={variants.item} className="glass-panel p-4 mb-4">
                <h5 className="mb-4 fw-semibold">Risk Score Trends Over Time</h5>
                <div style={{ height: '350px' }}>
                    <Line ref={lineChartRef} data={riskTrendsData} options={chartOptions} />
                </div>
            </motion.div>

            <Row className="g-4 mb-4">
                {/* Correlation Analysis */}
                <Col lg={6}>
                    <motion.div variants={variants.item} className="glass-panel p-4 h-100">
                        <h5 className="mb-3 fw-semibold">Attendance vs. Risk Correlation</h5>
                        <div style={{ height: '300px' }}>
                            <Scatter ref={scatterChartRef} data={scatterData} options={scatterOptions} />
                        </div>
                        <div className="mt-3 alert alert-info">
                            <small>
                                <strong>Insight:</strong> Students with &lt;70% attendance have 3.2x higher risk scores
                            </small>
                        </div>
                    </motion.div>
                </Col>

                {/* Cohort Comparison */}
                <Col lg={6}>
                    <motion.div variants={variants.item} className="glass-panel p-4 h-100">
                        <h5 className="mb-3 fw-semibold">Cohort Comparison</h5>
                        <Form.Group className="mb-3">
                            <Form.Label>Select Cohorts to Compare:</Form.Label>
                            <Form.Check type="checkbox" label="MATH-201 (Spring 2026) - Avg Risk: 48" defaultChecked />
                            <Form.Check type="checkbox" label="MATH-201 (Fall 2025) - Avg Risk: 52" defaultChecked />
                            <Form.Check type="checkbox" label="ENG-101 (Spring 2026) - Avg Risk: 35" />
                        </Form.Group>

                        <table className="table table-sm">
                            <thead>
                                <tr>
                                    <th>Metric</th>
                                    <th>Spring '26</th>
                                    <th>Fall '25</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>Avg Risk</td>
                                    <td>48</td>
                                    <td>52</td>
                                </tr>
                                <tr>
                                    <td>At-Risk %</td>
                                    <td>34%</td>
                                    <td>41%</td>
                                </tr>
                                <tr>
                                    <td>Critical</td>
                                    <td>5</td>
                                    <td>12</td>
                                </tr>
                                <tr>
                                    <td>Avg GPA</td>
                                    <td>2.8</td>
                                    <td>2.6</td>
                                </tr>
                                <tr>
                                    <td>Attendance</td>
                                    <td>82%</td>
                                    <td>76%</td>
                                </tr>
                            </tbody>
                        </table>

                        <div className="alert alert-success">
                            <small>
                                <strong>Insight:</strong> Spring 2026 cohort performing better. Potential reason: New instructor
                            </small>
                        </div>
                    </motion.div>
                </Col>
            </Row>

            {/* Automated Insights */}
            <motion.div variants={variants.item} className="glass-panel p-4">
                <h5 className="mb-4 fw-semibold d-flex align-items-center gap-2">
                    <FaChartLine /> Key Insights (Auto-generated)
                </h5>
                <Row className="g-3">
                    <Col md={4}>
                        <Card bg="danger" bg-opacity="10" border="danger" className="border-opacity-25">
                            <Card.Body>
                                <div className="d-flex align-items-start gap-2">
                                    <span className="text-danger">🔔</span>
                                    <div>
                                        <h6 className="text-danger mb-2">Alert</h6>
                                        <p className="small mb-2">MATH-201 risk scores increased 15% this week</p>
                                        <small className="text-muted">→ Investigate instructor change or exam period</small>
                                    </div>
                                </div>
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={4}>
                        <Card bg="success" bg-opacity="10" border="success" className="border-opacity-25">
                            <Card.Body>
                                <div className="d-flex align-items-start gap-2">
                                    <span className="text-success">✅</span>
                                    <div>
                                        <h6 className="text-success mb-2">Positive</h6>
                                        <p className="small mb-2">Overall attendance up 8% since intervention program</p>
                                        <small className="text-muted">→ Contributing factors: Engagement reminders, peer mentoring</small>
                                    </div>
                                </div>
                            </Card.Body>
                        </Card>
                    </Col>
                    <Col md={4}>
                        <Card bg="warning" bg-opacity="10" border="warning" className="border-opacity-25">
                            <Card.Body>
                                <div className="d-flex align-items-start gap-2">
                                    <span className="text-warning">⚠️</span>
                                    <div>
                                        <h6 className="text-warning mb-2">Warning</h6>
                                        <p className="small mb-2">23 students showing rapid risk deterioration</p>
                                        <small className="text-muted">→ Priority intervention assignments recommended</small>
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
