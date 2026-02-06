import React, { useState } from 'react';
import { Row, Col, Card, Button, Modal, Form, ListGroup, Badge, Spinner, Alert } from 'react-bootstrap';
import { FaFilePdf, FaFileExcel, FaDownload, FaCalendarAlt, FaClock, FaCheckCircle, FaExclamationCircle } from 'react-icons/fa';
import { motion } from 'framer-motion';
import { variants } from '../utils/motionConfig';
import { generateReportNarrative } from '../api';
import AiInsight from '../components/ai/AiInsight';

const Reports = () => {
    const [showWizard, setShowWizard] = useState(false);
    const [wizardStep, setWizardStep] = useState(1);
    const [selectedReport, setSelectedReport] = useState(null);

    const reportTemplates = [
        {
            id: 1,
            name: 'Monthly Risk Summary',
            description: 'Executive-level overview with KPIs, trend charts, and top 10 at-risk students',
            pages: '4-6 pages',
            format: 'PDF',
            icon: '📊',
        },
        {
            id: 2,
            name: 'High-Risk Students List',
            description: 'Detailed table with risk breakdowns, interventions, and contact information',
            pages: 'Varies',
            format: 'PDF/Excel',
            icon: '⚠️',
        },
        {
            id: 3,
            name: 'Intervention Impact Report',
            description: 'Comprehensive intervention analytics with before/after scores and ROI',
            pages: '8-10 pages',
            format: 'PDF',
            icon: '📈',
        },
        {
            id: 4,
            name: 'Department Performance Report',
            description: 'Metrics by academic department with course-level analysis',
            pages: '6-8 pages',
            format: 'PDF',
            icon: '🏫',
        },
        {
            id: 5,
            name: 'Semester-End Summary',
            description: 'Full semester analytics with year-over-year comparison',
            pages: '15-20 pages',
            format: 'PDF',
            icon: '📅',
        },
    ];

    const scheduledReports = [
        {
            id: 1,
            name: 'Monthly Risk Summary',
            frequency: '1st of each month at 8:00 AM',
            recipients: 'dean@university.edu (+2)',
            lastSent: 'Jan 1, 2026',
        },
        {
            id: 2,
            name: 'Weekly High-Risk Alert',
            frequency: 'Every Monday at 9:00 AM',
            recipients: 'counselors@university.edu',
            lastSent: 'Jan 29, 2026',
        },
    ];

    const reportArchive = [
        {
            id: 1,
            name: 'Intervention Impact - Feb 2026',
            type: 'Impact',
            generated: 'Feb 4, 2026',
            size: '2.4 MB',
        },
        {
            id: 2,
            name: 'Monthly Summary - Jan 2026',
            type: 'Monthly',
            generated: 'Jan 31, 2026',
            size: '1.1 MB',
        },
        {
            id: 3,
            name: 'High-Risk List - Jan 2026',
            type: 'Risk List',
            generated: 'Jan 25, 2026',
            size: '450 KB',
        },
    ];

    const [generating, setGenerating] = useState(false);
    const [generationError, setGenerationError] = useState(null);
    const [generatedNarrative, setGeneratedNarrative] = useState(null);

    const handleGenerateReport = (report) => {
        setSelectedReport(report);
        setWizardStep(1);
        setShowWizard(true);
        setGenerationError(null);
        setGeneratedNarrative(null);
    };

    const executeGeneration = async () => {
        setWizardStep(2);
        setGenerating(true);
        setGenerationError(null);

        try {
            // 1. Fetch data based on report type (SIMULATED DATA FETCH for demo)
            // In a real app, this would be a specific data endpoint
            const reportData = {
                period: "February 2026",
                total_students: 1250,
                high_risk_count: 45,
                risk_trend: "decreasing",
                top_risk_factors: ["Attendance", "Assignment Delays"]
            };

            // 2. Generate Narrative via API
            const data = await generateReportNarrative(selectedReport.name, reportData);

            setGeneratedNarrative(data);
            setWizardStep(3);
        } catch (err) {
            console.error("Report generation failed:", err);
            setGenerationError("Failed to generate report. Please try again.");
            setWizardStep(1); // Go back or show error state
        } finally {
            setGenerating(false);
        }
    };

    return (
        <motion.div
            initial="hidden"
            animate="visible"
            variants={variants.container}
            className="pb-5"
        >
            <div className="mb-5">
                <h1 className="display-5 fw-bold text-gradient mb-2">Reports</h1>
                <p className="text-secondary fs-5" style={{ maxWidth: '700px' }}>
                    Generate, schedule, and manage standardized reports for stakeholders.
                </p>
            </div>

            {/* Report Templates */}
            <h5 className="mb-3 fw-semibold">Pre-built Report Templates</h5>
            <Row className="g-4 mb-5">
                {reportTemplates.map((report) => (
                    <Col lg={6} key={report.id}>
                        <motion.div variants={variants.item}>
                            <Card className="glass-panel border-0 h-100">
                                <Card.Body>
                                    <div className="d-flex align-items-start gap-3">
                                        <div style={{ fontSize: '2rem' }}>{report.icon}</div>
                                        <div className="flex-grow-1">
                                            <Card.Title className="mb-2">{report.name}</Card.Title>
                                            <p className="text-muted small mb-2">{report.description}</p>
                                            <div className="d-flex gap-3 mb-3">
                                                <Badge bg="secondary">{report.pages}</Badge>
                                                <Badge bg="secondary">{report.format}</Badge>
                                            </div>
                                            <Button
                                                variant="primary"
                                                size="sm"
                                                onClick={() => handleGenerateReport(report)}
                                                className="d-flex align-items-center gap-2"
                                            >
                                                <FaFilePdf /> Generate Report
                                            </Button>
                                        </div>
                                    </div>
                                </Card.Body>
                            </Card>
                        </motion.div>
                    </Col>
                ))}
            </Row>

            {/* Scheduled Reports */}
            <h5 className="mb-3 fw-semibold">Scheduled Reports</h5>
            <motion.div variants={variants.item} className="glass-panel p-4 mb-5">
                <ListGroup variant="flush">
                    {scheduledReports.map((report) => (
                        <ListGroup.Item
                            key={report.id}
                            className="bg-transparent border-bottom px-0"
                            style={{ borderColor: 'var(--border-color)' }}
                        >
                            <div className="d-flex justify-content-between align-items-start">
                                <div>
                                    <h6 className="mb-2 d-flex align-items-center gap-2">
                                        <FaCalendarAlt className="text-primary" /> {report.name}
                                    </h6>
                                    <small className="text-muted d-block">Frequency: {report.frequency}</small>
                                    <small className="text-muted d-block">Recipients: {report.recipients}</small>
                                    <small className="text-muted d-block">Last sent: {report.lastSent}</small>
                                </div>
                                <div className="d-flex gap-2">
                                    <Button variant="outline-secondary" size="sm">Edit</Button>
                                    <Button variant="outline-secondary" size="sm">Pause</Button>
                                    <Button variant="outline-danger" size="sm">Delete</Button>
                                </div>
                            </div>
                        </ListGroup.Item>
                    ))}
                </ListGroup>
                <Button variant="primary" className="mt-3">+ Schedule New Report</Button>
            </motion.div>

            {/* Report Archive */}
            <h5 className="mb-3 fw-semibold">Report Archive</h5>
            <motion.div variants={variants.item} className="glass-panel p-4">
                <div className="table-responsive">
                    <table className="table modern-table">
                        <thead>
                            <tr>
                                <th>Report Name</th>
                                <th>Type</th>
                                <th>Generated</th>
                                <th>Size</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {reportArchive.map((report) => (
                                <tr key={report.id}>
                                    <td>{report.name}</td>
                                    <td><Badge bg="secondary">{report.type}</Badge></td>
                                    <td>{report.generated}</td>
                                    <td>{report.size}</td>
                                    <td>
                                        <div className="d-flex gap-2">
                                            <Button variant="link" size="sm" className="p-0">
                                                <FaDownload /> Download
                                            </Button>
                                            <Button variant="link" size="sm" className="p-0 text-danger">
                                                Delete
                                            </Button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </motion.div>

            {/* Report Generation Wizard */}
            <Modal
                show={showWizard}
                onHide={() => setShowWizard(false)}
                size="lg"
                centered
                style={{ zIndex: 9999 }}
            >
                <Modal.Header closeButton style={{ borderColor: 'var(--border-color)', backgroundColor: 'var(--surface-color)' }}>
                    <Modal.Title>Generate Report: {selectedReport?.name}</Modal.Title>
                </Modal.Header>
                <Modal.Body style={{ backgroundColor: 'var(--surface-color)' }}>
                    {wizardStep === 1 && (
                        <div>
                            <h6 className="mb-3">Configure Report:</h6>

                            <Form.Group className="mb-3">
                                <Form.Label>Date Range:</Form.Label>
                                <div className="d-flex gap-2 mb-2">
                                    <Form.Control type="date" placeholder="From" />
                                    <Form.Control type="date" placeholder="To" />
                                </div>
                                <div className="d-flex gap-2">
                                    <Form.Check type="radio" label="This Month" name="dateRange" id="thisMonth" />
                                    <Form.Check type="radio" label="Last Month" name="dateRange" id="lastMonth" />
                                    <Form.Check type="radio" label="Custom" name="dateRange" id="custom" defaultChecked />
                                </div>
                            </Form.Group>

                            <Form.Group className="mb-3">
                                <Form.Label>Include:</Form.Label>
                                <Form.Check type="checkbox" label="Executive Summary" defaultChecked />
                                <Form.Check type="checkbox" label="Risk Score Charts" defaultChecked />
                                <Form.Check type="checkbox" label="Student Progress Tables" defaultChecked />
                                <Form.Check type="checkbox" label="Individual Student Names (requires auth)" />
                                <Form.Check type="checkbox" label="Aggregated Metrics Only" defaultChecked />
                            </Form.Group>

                            <Form.Group className="mb-3">
                                <Form.Label>Format:</Form.Label>
                                <div className="d-flex gap-2">
                                    <Form.Check type="radio" label="PDF (Recommended)" name="format" defaultChecked />
                                    <Form.Check type="radio" label="Excel" name="format" />
                                    <Form.Check type="radio" label="PowerPoint" name="format" />
                                </div>
                            </Form.Group>

                            <Form.Group>
                                <Form.Label>Branding:</Form.Label>
                                <Form.Check type="checkbox" label="Include institution logo" defaultChecked />
                                <Form.Check type="checkbox" label="Add confidentiality footer" defaultChecked />
                            </Form.Group>
                        </div>
                    )}

                    {wizardStep === 2 && (
                        <div className="text-center py-5">
                            <Spinner animation="border" variant="primary" className="mb-3" />
                            <h5>Generating Report...</h5>
                            <p className="text-muted">Analyzing student data and generating executive narrative...</p>
                        </div>
                    )}

                    {wizardStep === 3 && (
                        <div className="py-4">
                            <div className="text-center mb-4">
                                <FaCheckCircle size={48} className="text-success mb-2" />
                                <h5 className="text-success">Report Generated Successfully</h5>
                                <p className="text-muted">
                                    {selectedReport?.name}_Feb2026.pdf • 2.4 MB
                                </p>
                            </div>

                            {generatedNarrative && (
                                <div className="mb-4">
                                    <h6 className="fw-bold mb-3">Executive Summary (AI Generated)</h6>
                                    <AiInsight
                                        title="Executive Summary"
                                        content={generatedNarrative.content}
                                        confidence={generatedNarrative.confidence}
                                        type="summary"
                                    />
                                </div>
                            )}

                            <div className="d-grid gap-2">
                                <Button variant="primary" className="d-flex align-items-center justify-content-center gap-2">
                                    <FaDownload /> Download PDF
                                </Button>
                                <Button variant="outline-secondary">Email to Stakeholders</Button>
                            </div>
                        </div>
                    )}
                </Modal.Body>
                <Modal.Footer style={{ borderColor: 'var(--border-color)', backgroundColor: 'var(--surface-color)' }}>
                    {wizardStep === 1 && (
                        <>
                            {generationError && <Alert variant="danger">{generationError}</Alert>}
                            <Button variant="primary" onClick={executeGeneration} disabled={generating}>
                                {generating ? 'Processing...' : 'Generate Report →'}
                            </Button>
                        </>
                    )}
                    {wizardStep === 3 && (
                        <Button variant="secondary" onClick={() => setShowWizard(false)}>
                            Close
                        </Button>
                    )}
                </Modal.Footer>
            </Modal>
        </motion.div>
    );
};

export default Reports;
