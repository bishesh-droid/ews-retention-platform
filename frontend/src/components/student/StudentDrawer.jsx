import React, { useRef, useEffect } from 'react';
import { Offcanvas, Badge, Button, ListGroup, Row, Col } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { FaTimes, FaEnvelope, FaClipboardList, FaStickyNote, FaChartLine, FaGraduationCap } from 'react-icons/fa';
import { Line } from 'react-chartjs-2';
import { motion } from 'framer-motion';
import ConfidenceBadge from '../common/ConfidenceBadge';
import { RiskTrendIndicator } from '../common/TrendIndicator';
import RiskBreakdownChart from './RiskBreakdownChart';
import RiskExplanation from '../ai/RiskExplanation';

const StudentDrawer = ({ show, onHide, student }) => {
    const chartRef = useRef(null);
    const navigate = useNavigate();

    // Cleanup chart on unmount
    useEffect(() => {
        return () => {
            if (chartRef.current) {
                chartRef.current.destroy();
            }
        };
    }, []);

    if (!student) return null;

    // Calculate latest GPA from semester 7 quarterly marks
    const getLatestGPA = () => {
        const q1 = student.q1mpa7 || 0;
        const q2 = student.q2mpa7 || 0;
        const q3 = student.q3mpa7 || 0;
        const q4 = student.q4mpa7 || 0;
        return ((q1 + q2 + q3 + q4) / 4).toFixed(2);
    };

    // Get attendance rate (normalized from absrate7)
    const getAttendanceRate = () => {
        const absRate = student.absrate7 || 0;
        return Math.max(0, Math.min(100, Math.round(100 - (absRate * 3))));
    };

    const handleViewFullProfile = () => {
        onHide();
        navigate(`/students/${student.id}`);
    };

    // Mock 30-day risk score trend data
    const trendData = {
        labels: ['30d ago', '25d ago', '20d ago', '15d ago', '10d ago', '5d ago', 'Today'],
        datasets: [
            {
                label: 'Risk Score',
                data: [
                    student.risk_score - 15,
                    student.risk_score - 10,
                    student.risk_score - 5,
                    student.risk_score - 3,
                    student.risk_score + 2,
                    student.risk_score + 5,
                    student.risk_score,
                ],
                borderColor: 'var(--primary-color)',
                backgroundColor: 'rgba(0, 130, 201, 0.1)',
                fill: true,
                tension: 0.4,
            },
        ],
    };

    const chartOptions = {
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
                beginAtZero: true,
                max: 100,
                grid: { color: 'rgba(139,92,246,0.18)' },
                ticks: { color: '#B8AADA' },
            },
            x: {
                grid: { display: false },
                ticks: { color: 'var(--text-muted)' },
            },
        },
    };

    const getRiskLevel = (score) => {
        if (score > 75) return { label: 'Critical', color: 'danger' };
        if (score > 50) return { label: 'High', color: 'warning' };
        if (score > 25) return { label: 'Medium', color: 'info' };
        return { label: 'Low', color: 'success' };
    };

    const riskLevel = getRiskLevel(student.risk_score);

    return (
        <Offcanvas
            show={show}
            onHide={onHide}
            placement="end"
            backdrop={true}
            style={{
                width: '500px',
                backgroundColor: 'var(--surface-color)',
                borderLeft: '1px solid var(--border-color)',
            }}
        >
            <Offcanvas.Header
                className="border-bottom"
                style={{ borderColor: 'var(--border-color)' }}
            >
                <div className="d-flex align-items-center gap-3 flex-grow-1">
                    <div
                        className="rounded-circle bg-primary text-white d-flex align-items-center justify-content-center fw-bold"
                        style={{ width: '50px', height: '50px', fontSize: '1.2rem' }}
                    >
                        {student.id.charAt(0).toUpperCase()}
                    </div>
                    <div>
                        <Offcanvas.Title className="mb-0">Student {student.id}</Offcanvas.Title>
                        <small className="text-muted">ID: {student.id}</small>
                    </div>
                </div>
                <Button
                    variant="link"
                    onClick={onHide}
                    className="text-muted p-0"
                    style={{ fontSize: '1.2rem' }}
                >
                    <FaTimes />
                </Button>
            </Offcanvas.Header>

            <Offcanvas.Body className="p-4">
                {/* Risk Score Badge */}
                <div className="mb-4 text-center">
                    <div className="d-flex justify-content-center align-items-center gap-2 flex-wrap">
                        <Badge
                            bg={riskLevel.color}
                            className="px-4 py-2"
                            style={{ fontSize: '1rem' }}
                        >
                            Risk Score: {student.risk_score} - {riskLevel.label}
                        </Badge>
                        <RiskTrendIndicator student={student} showDelta={true} />
                        <ConfidenceBadge student={student} size="sm" showLabel={false} />
                    </div>
                </div>

                {/* Risk Explanation */}
                <div className="mb-4">
                    <RiskExplanation student={student} variant="compact" />
                </div>

                {/* 30-Day Risk Trend */}
                <div className="mb-4">
                    <h6 className="mb-3 fw-semibold">30-Day Risk Trend</h6>
                    <div style={{ height: '200px' }}>
                        <Line ref={chartRef} data={trendData} options={chartOptions} />
                    </div>
                </div>

                {/* Risk Factors Breakdown */}
                <div className="mb-4">
                    <h6 className="mb-3 fw-semibold">Risk Factors Breakdown</h6>
                    <RiskBreakdownChart student={student} variant="mini" />
                </div>

                {/* Recent Activity Timeline */}
                <div className="mb-4">
                    <h6 className="mb-3 fw-semibold">Recent Activity</h6>
                    <div className="d-flex flex-column gap-3">
                        <div className="d-flex gap-2">
                            <div
                                className="rounded-circle bg-primary"
                                style={{ width: '8px', height: '8px', marginTop: '6px' }}
                            ></div>
                            <div>
                                <small className="text-muted">2 hours ago</small>
                                <p className="mb-0">Logged into LMS</p>
                            </div>
                        </div>
                        <div className="d-flex gap-2">
                            <div
                                className="rounded-circle bg-warning"
                                style={{ width: '8px', height: '8px', marginTop: '6px' }}
                            ></div>
                            <div>
                                <small className="text-muted">1 day ago</small>
                                <p className="mb-0">Missed class: MATH-201</p>
                            </div>
                        </div>
                        <div className="d-flex gap-2">
                            <div
                                className="rounded-circle bg-success"
                                style={{ width: '8px', height: '8px', marginTop: '6px' }}
                            ></div>
                            <div>
                                <small className="text-muted">3 days ago</small>
                                <p className="mb-0">Submitted assignment early</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Key Metrics */}
                <div className="mb-4">
                    <h6 className="mb-3 fw-semibold">Key Metrics (Semester 7)</h6>
                    <Row className="g-2">
                        <Col xs={6}>
                            <div className="p-3 rounded bg-surface-hover text-center">
                                <small className="d-block text-muted mb-1">Latest GPA</small>
                                <span className={`fw-bold fs-5 ${parseFloat(getLatestGPA()) < 2.0 ? 'text-danger' : 'text-success'}`}>
                                    {getLatestGPA()}
                                </span>
                            </div>
                        </Col>
                        <Col xs={6}>
                            <div className="p-3 rounded bg-surface-hover text-center">
                                <small className="d-block text-muted mb-1">Attendance</small>
                                <span className={`fw-bold fs-5 ${getAttendanceRate() < 70 ? 'text-warning' : 'text-success'}`}>
                                    {getAttendanceRate()}%
                                </span>
                            </div>
                        </Col>
                        <Col xs={6}>
                            <div className="p-3 rounded bg-surface-hover text-center">
                                <small className="d-block text-muted mb-1">Engagement</small>
                                <span className="fw-bold fs-5 text-primary">
                                    {Math.round(student.engagement_score || 0)}%
                                </span>
                            </div>
                        </Col>
                        <Col xs={6}>
                            <div className="p-3 rounded bg-surface-hover text-center">
                                <small className="d-block text-muted mb-1">Status</small>
                                <Badge bg={student.nograd === 1 ? 'danger' : 'success'}>
                                    {student.nograd === 1 ? 'At Risk' : 'On Track'}
                                </Badge>
                            </div>
                        </Col>
                    </Row>
                </div>

                {/* Quick Actions */}
                <div className="d-grid gap-2">
                    <Button variant="primary" className="d-flex align-items-center justify-content-center gap-2" onClick={handleViewFullProfile}>
                        <FaChartLine /> View Full Profile
                    </Button>
                    <Button variant="outline-primary" className="d-flex align-items-center justify-content-center gap-2">
                        <FaClipboardList /> Assign Intervention
                    </Button>
                    <Button variant="outline-secondary" className="d-flex align-items-center justify-content-center gap-2">
                        <FaEnvelope /> Send Email
                    </Button>
                    <Button variant="outline-secondary" className="d-flex align-items-center justify-content-center gap-2">
                        <FaStickyNote /> Add Note
                    </Button>
                </div>
            </Offcanvas.Body>
        </Offcanvas>
    );
};

export default StudentDrawer;
