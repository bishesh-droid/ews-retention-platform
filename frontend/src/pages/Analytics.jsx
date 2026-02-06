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

    // Risk trends data
    const riskTrendsData = {
        labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6', 'Current'],
        datasets: [
            {
                label: 'Overall Average',
                data: [45, 44, 46, 43, 42, 41, 42],
                borderColor: 'var(--primary-color)',
                backgroundColor: 'rgba(43, 43, 136, 0.1)',
                borderWidth: 3,
                tension: 0.4,
            },
            {
                label: 'Critical Students',
                data: [15, 17, 16, 18, 19, 20, 23],
                borderColor: '#CF2027',
                backgroundColor: 'rgba(207, 32, 39, 0.1)',
                borderWidth: 2,
                tension: 0.4,
            },
            {
                label: 'High Risk',
                data: [72, 75, 73, 70, 68, 65, 62],
                borderColor: '#B78A2D',
                backgroundColor: 'rgba(183, 138, 45, 0.1)',
                borderWidth: 2,
                tension: 0.4,
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
                labels: { color: 'var(--text-primary)', usePointStyle: true },
            },
            tooltip: {
                backgroundColor: 'var(--surface-color)',
                titleColor: 'var(--text-primary)',
                bodyColor: 'var(--text-secondary)',
                borderColor: 'var(--border-color)',
                borderWidth: 1,
            },
        },
        scales: {
            y: {
                beginAtZero: true,
                max: 100,
                grid: { color: 'var(--border-color)' },
                ticks: { color: 'var(--text-muted)' },
            },
            x: {
                grid: { display: false },
                ticks: { color: 'var(--text-muted)' },
            },
        },
    };

    // Scatter plot data (Attendance vs Risk)
    const scatterData = {
        datasets: [
            {
                label: 'Students',
                data: students.slice(0, 50).map(s => ({
                    x: s.attendance || Math.random() * 100,
                    y: s.risk_score,
                })),
                backgroundColor: 'rgba(0, 130, 201, 0.6)',
                borderColor: 'var(--primary-color)',
            },
        ],
    };

    const scatterOptions = {
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
            y: {
                title: { display: true, text: 'Risk Score', color: 'var(--text-primary)' },
                beginAtZero: true,
                max: 100,
                grid: { color: 'var(--border-color)' },
                ticks: { color: 'var(--text-muted)' },
            },
            x: {
                title: { display: true, text: 'Attendance %', color: 'var(--text-primary)' },
                beginAtZero: true,
                max: 100,
                grid: { color: 'var(--border-color)' },
                ticks: { color: 'var(--text-muted)' },
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
