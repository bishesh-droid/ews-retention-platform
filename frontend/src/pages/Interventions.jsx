import React, { useState } from 'react';
import { Row, Col, Button, Table, Badge, Modal, Form, Card, ListGroup } from 'react-bootstrap';
import { FaPlus, FaClipboardList, FaUser, FaUsers, FaCalendar } from 'react-icons/fa';
import { motion } from 'framer-motion';
import { variants } from '../utils/motionConfig';
import { useStudentData } from '../context/StudentContext';

const Interventions = () => {
    const { students } = useStudentData();
    const [showModal, setShowModal] = useState(false);
    const [modalStep, setModalStep] = useState(1);
    const [selectedStudents, setSelectedStudents] = useState([]);
    const [selectedIntervention, setSelectedIntervention] = useState(null);

    // Mock active interventions data
    const [activeInterventions] = useState([
        {
            id: 1,
            studentId: students[0]?.id || '2024-001',
            intervention: 'One-on-One Tutoring',
            assignedDate: 'Jan 15, 2026',
            status: 'In Progress',
            owner: 'Dr. Kim',
            riskBefore: 18,
            riskAfter: 32,
        },
        {
            id: 2,
            studentId: students[1]?.id || '2024-002',
            intervention: 'Academic Coaching',
            assignedDate: 'Jan 10, 2026',
            status: 'Completed',
            owner: 'Prof. Lee',
            riskBefore: 22,
            riskAfter: 58,
        },
    ]);

    const interventionLibrary = [
        {
            category: 'Academic Support',
            items: [
                { name: 'One-on-One Tutoring', duration: '4-8 weeks', frequency: '2x/week', rating: 4.2 },
                { name: 'Study Skills Workshop', duration: '3 sessions', frequency: 'Weekly', rating: 3.9 },
                { name: 'Academic Coaching', duration: 'Ongoing', frequency: 'Weekly', rating: 4.0 },
            ],
        },
        {
            category: 'Attendance',
            items: [
                { name: 'Attendance Warning Letter', duration: '1 week follow-up', frequency: 'One-time', rating: 3.2 },
                { name: 'Attendance Contract', duration: '4 weeks', frequency: 'Daily check-ins', rating: 3.8 },
            ],
        },
        {
            category: 'Engagement',
            items: [
                { name: 'Professor Office Hours', duration: '1 semester', frequency: 'Bi-weekly', rating: 4.1 },
                { name: 'Peer Mentoring', duration: '1 semester', frequency: 'Weekly', rating: 4.7 },
            ],
        },
        {
            category: 'Support Services',
            items: [
                { name: 'Counseling Referral', duration: 'As needed', frequency: 'Varies', rating: 4.3 },
                { name: 'Financial Aid Review', duration: '2 weeks', frequency: 'One-time', rating: 3.6 },
                { name: 'Parent/Guardian Outreach', duration: '1 session', frequency: 'As needed', rating: 3.5 },
            ],
        },
    ];

    const handleCreateIntervention = () => {
        setModalStep(1);
        setSelectedStudents([]);
        setSelectedIntervention(null);
        setShowModal(true);
    };

    const nextStep = () => setModalStep(modalStep + 1);
    const prevStep = () => setModalStep(modalStep - 1);

    const handleAssign = () => {
        console.log('Assigning intervention:', {
            students: selectedStudents,
            intervention: selectedIntervention,
        });
        setShowModal(false);
    };

    const getStatusBadge = (status) => {
        const variants = {
            'Pending': 'primary',
            'In Progress': 'warning',
            'Completed': 'success',
            'Cancelled': 'danger',
        };
        return <Badge bg={variants[status] || 'secondary'}>{status}</Badge>;
    };

    const renderStars = (rating) => {
        const fullStars = Math.floor(rating);
        return '★'.repeat(fullStars) + '☆'.repeat(5 - fullStars);
    };

    return (
        <motion.div
            initial="hidden"
            animate="visible"
            variants={variants.container}
            className="pb-5"
        >
            <div className="d-flex justify-content-between align-items-end mb-5">
                <div>
                    <h1 className="display-5 fw-bold text-gradient mb-2">Interventions</h1>
                    <p className="text-secondary fs-5" style={{ maxWidth: '700px' }}>
                        Manage intervention strategies, assign them to students, track progress, and measure effectiveness.
                    </p>
                </div>
                <Button
                    variant="primary"
                    onClick={handleCreateIntervention}
                    className="d-flex align-items-center gap-2 px-4 py-2"
                >
                    <FaPlus /> New Intervention
                </Button>
            </div>

            {/* Active Interventions Table */}
            <motion.div variants={variants.item} className="glass-panel p-4 mb-4">
                <h5 className="mb-4 fw-semibold">Active Interventions</h5>
                <div className="table-responsive">
                    <Table hover className="modern-table">
                        <thead>
                            <tr>
                                <th>Student ID</th>
                                <th>Intervention</th>
                                <th>Assigned Date</th>
                                <th>Status</th>
                                <th>Owner</th>
                                <th>Risk Change</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {activeInterventions.map((intervention) => (
                                <tr key={intervention.id}>
                                    <td>{intervention.studentId}</td>
                                    <td>{intervention.intervention}</td>
                                    <td>{intervention.assignedDate}</td>
                                    <td>{getStatusBadge(intervention.status)}</td>
                                    <td>{intervention.owner}</td>
                                    <td>
                                        <span className={intervention.riskAfter > intervention.riskBefore ? 'text-success' : 'text-danger'}>
                                            {intervention.riskBefore}→{intervention.riskAfter}{' '}
                                            {intervention.riskAfter > intervention.riskBefore ? '↑' : '↓'}
                                        </span>
                                    </td>
                                    <td>
                                        <Button variant="link" size="sm" className="p-0">
                                            •••
                                        </Button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </Table>
                </div>
            </motion.div>

            {/* Intervention Library */}
            <Row className="g-4 mb-4">
                {interventionLibrary.map((category, idx) => (
                    <Col lg={6} key={idx}>
                        <motion.div variants={variants.item}>
                            <Card className="glass-panel border-0 h-100">
                                <Card.Body>
                                    <Card.Title className="mb-3 fw-semibold">{category.category}</Card.Title>
                                    <ListGroup variant="flush">
                                        {category.items.map((item, itemIdx) => (
                                            <ListGroup.Item
                                                key={itemIdx}
                                                className="bg-transparent border-bottom px-0"
                                                style={{ borderColor: 'var(--border-color)' }}
                                            >
                                                <div className="d-flex justify-content-between align-items-start">
                                                    <div>
                                                        <h6 className="mb-1">{item.name}</h6>
                                                        <small className="text-muted d-block">Duration: {item.duration}</small>
                                                        <small className="text-muted">Frequency: {item.frequency}</small>
                                                    </div>
                                                    <div className="text-end">
                                                        <span className="text-warning">{renderStars(item.rating)}</span>
                                                        <small className="text-muted d-block">{item.rating}/5</small>
                                                    </div>
                                                </div>
                                            </ListGroup.Item>
                                        ))}
                                    </ListGroup>
                                </Card.Body>
                            </Card>
                        </motion.div>
                    </Col>
                ))}
            </Row>

            {/* Effectiveness Analytics */}
            <motion.div variants={variants.item} className="glass-panel p-4">
                <h5 className="mb-4 fw-semibold">Intervention Effectiveness Report</h5>
                <div className="table-responsive">
                    <Table className="modern-table">
                        <thead>
                            <tr>
                                <th>Intervention Type</th>
                                <th>Count</th>
                                <th>Success Rate</th>
                                <th>Avg Improvement</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>One-on-One Tutoring</td>
                                <td>45</td>
                                <td><Badge bg="success">84%</Badge></td>
                                <td className="text-success">+28 pts</td>
                            </tr>
                            <tr>
                                <td>Peer Mentoring</td>
                                <td>23</td>
                                <td><Badge bg="success">91%</Badge></td>
                                <td className="text-success">+31 pts</td>
                            </tr>
                            <tr>
                                <td>Academic Coaching</td>
                                <td>31</td>
                                <td><Badge bg="success">77%</Badge></td>
                                <td className="text-success">+22 pts</td>
                            </tr>
                            <tr>
                                <td>Attendance Contract</td>
                                <td>18</td>
                                <td><Badge bg="warning">61%</Badge></td>
                                <td className="text-success">+15 pts</td>
                            </tr>
                        </tbody>
                    </Table>
                </div>
                <small className="text-muted">Success = Risk score improvement of 20+ points</small>
            </motion.div>

            {/* Create Intervention Modal */}
            <Modal
                show={showModal}
                onHide={() => setShowModal(false)}
                size="lg"
                centered
                style={{ zIndex: 9999 }}
            >
                <Modal.Header closeButton style={{ borderColor: 'var(--border-color)', backgroundColor: 'var(--surface-color)' }}>
                    <Modal.Title>Assign Intervention - Step {modalStep} of 3</Modal.Title>
                </Modal.Header>
                <Modal.Body style={{ backgroundColor: 'var(--surface-color)' }}>
                    {modalStep === 1 && (
                        <div>
                            <h6 className="mb-3">Select Students:</h6>
                            <Form.Check
                                type="radio"
                                label="Individual Student"
                                name="studentSelection"
                                id="individual"
                                className="mb-2"
                            />
                            <Form.Control type="text" placeholder="Search by name or ID..." className="mb-3" />

                            <Form.Check
                                type="radio"
                                label="Multiple Students"
                                name="studentSelection"
                                id="multiple"
                                className="mb-2"
                                defaultChecked
                            />
                            <div style={{ maxHeight: '200px', overflowY: 'auto' }}>
                                {students.slice(0, 5).map(student => (
                                    <Form.Check
                                        key={student.id}
                                        type="checkbox"
                                        label={`${student.id} (Risk: ${student.risk_score})`}
                                        className="ms-4"
                                    />
                                ))}
                            </div>

                            <Form.Check
                                type="radio"
                                label="Bulk Import (CSV upload)"
                                name="studentSelection"
                                id="bulk"
                                className="mt-3"
                            />
                        </div>
                    )}

                    {modalStep === 2 && (
                        <div>
                            <h6 className="mb-3">Select Intervention Type:</h6>
                            {interventionLibrary.map((category, idx) => (
                                <div key={idx} className="mb-3">
                                    <h6 className="text-muted small mb-2">{category.category}</h6>
                                    {category.items.map((item, itemIdx) => (
                                        <Form.Check
                                            key={itemIdx}
                                            type="radio"
                                            name="intervention"
                                            label={`${item.name} ${renderStars(item.rating)} (${item.rating}/5)`}
                                            className="mb-2"
                                            onChange={() => setSelectedIntervention(item.name)}
                                        />
                                    ))}
                                </div>
                            ))}
                        </div>
                    )}

                    {modalStep === 3 && (
                        <div>
                            <h6 className="mb-3">Configure Details:</h6>
                            <Form.Group className="mb-3">
                                <Form.Label>Assign To (Coach/Tutor):</Form.Label>
                                <Form.Select>
                                    <option>Dr. Sarah Kim</option>
                                    <option>Prof. Michael Lee</option>
                                    <option>Dr. Johnson</option>
                                </Form.Select>
                            </Form.Group>

                            <Row>
                                <Col md={6}>
                                    <Form.Group className="mb-3">
                                        <Form.Label>Start Date:</Form.Label>
                                        <Form.Control type="date" />
                                    </Form.Group>
                                </Col>
                                <Col md={6}>
                                    <Form.Group className="mb-3">
                                        <Form.Label>Duration:</Form.Label>
                                        <Form.Select>
                                            <option>4 weeks</option>
                                            <option>8 weeks</option>
                                            <option>1 semester</option>
                                        </Form.Select>
                                    </Form.Group>
                                </Col>
                            </Row>

                            <Form.Group className="mb-3">
                                <Form.Label>Success Criteria:</Form.Label>
                                <Form.Check type="checkbox" label="Risk score improves by 20+ points" defaultChecked />
                                <Form.Check type="checkbox" label="Attendance reaches 85%+" defaultChecked />
                                <Form.Check type="checkbox" label="GPA increases by 0.5+" />
                            </Form.Group>

                            <Form.Group className="mb-3">
                                <Form.Label>Notes:</Form.Label>
                                <Form.Control as="textarea" rows={3} placeholder="Additional context..." />
                            </Form.Group>

                            <Form.Group>
                                <Form.Label>Notifications:</Form.Label>
                                <Form.Check type="checkbox" label="Email student(s)" defaultChecked />
                                <Form.Check type="checkbox" label="Email assigned coach" defaultChecked />
                                <Form.Check type="checkbox" label="Add to student dashboard" defaultChecked />
                            </Form.Group>
                        </div>
                    )}
                </Modal.Body>
                <Modal.Footer style={{ borderColor: 'var(--border-color)', backgroundColor: 'var(--surface-color)' }}>
                    {modalStep > 1 && (
                        <Button variant="outline-secondary" onClick={prevStep}>
                            ← Back
                        </Button>
                    )}
                    {modalStep < 3 ? (
                        <Button variant="primary" onClick={nextStep}>
                            Next Step →
                        </Button>
                    ) : (
                        <Button variant="primary" onClick={handleAssign}>
                            Assign Intervention
                        </Button>
                    )}
                </Modal.Footer>
            </Modal>
        </motion.div>
    );
};

export default Interventions;
