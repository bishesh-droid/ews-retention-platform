import React, { useState, useEffect, useMemo } from 'react';
import { Row, Col, Button, Table, Badge, Modal, Form, Card, ListGroup, Alert } from 'react-bootstrap';
import { FaPlus, FaClipboardList, FaUser, FaUsers, FaCalendar } from 'react-icons/fa';
import { motion } from 'framer-motion';
import { variants } from '../utils/motionConfig';
import { useStudentData } from '../context/StudentContext';
import { getAllInterventions, createIntervention, updateIntervention } from '../services/api';

const Interventions = () => {
    const { students } = useStudentData();
    const studentNameById = useMemo(() => {
        const map = new Map();
        students.forEach(s => map.set(s.id, s.name || s.id));
        return map;
    }, [students]);
    const [showModal, setShowModal] = useState(false);
    const [modalStep, setModalStep] = useState(1);
    const [selectedStudents, setSelectedStudents] = useState([]);
    const [selectedIntervention, setSelectedIntervention] = useState(null);
    const [assignedFaculty, setAssignedFaculty] = useState('');
    const [startDate, setStartDate] = useState('');

    // Backend-backed interventions
    const [interventions, setInterventions] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [successMessage, setSuccessMessage] = useState(null);

    // Pagination (client-side over backend list)
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize, setPageSize] = useState(25);

    const loadInterventions = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await getAllInterventions({ limit: 500 });
            if (response.success && response.data) {
                const list = response.data.interventions || [];
                setInterventions(list);
            } else {
                setError(response.message || 'Failed to load interventions.');
                setInterventions([]);
            }
        } catch (err) {
            console.error('Error loading interventions:', err);
            setError('Failed to load interventions.');
            setInterventions([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadInterventions();
    }, []);

    const interventionLibrary = useMemo(() => {
        // Derive a lightweight “library” from real intervention types already used.
        const grouped = {};
        interventions.forEach((i) => {
            const category = i.assigned_team || 'General';
            const key = i.action || i.threshold_category || 'Intervention';
            if (!grouped[category]) grouped[category] = {};
            if (!grouped[category][key]) grouped[category][key] = { count: 0, avgEff: 0, effN: 0 };
            grouped[category][key].count += 1;
            const eff = typeof i.effectiveness_score === 'number' ? i.effectiveness_score : null;
            if (eff !== null) {
                grouped[category][key].avgEff += eff;
                grouped[category][key].effN += 1;
            }
        });
        return Object.entries(grouped).map(([category, itemsMap]) => ({
            category,
            items: Object.entries(itemsMap).map(([name, meta]) => {
                const avg = meta.effN ? meta.avgEff / meta.effN : null;
                const rating = avg !== null ? Math.round(avg * 10) / 2 : null; // 0..1 → 0..5 (0.5 steps)
                return {
                    name,
                    duration: '—',
                    frequency: `${meta.count} assigned`,
                    rating: rating !== null ? Math.min(5, Math.max(0, rating)) : null,
                };
            }),
        }));
    }, [interventions]);

    const facultyOptions = useMemo(() => {
        const set = new Set();
        interventions.forEach((i) => {
            if (i.assigned_faculty) set.add(i.assigned_faculty);
        });
        return [...set].sort();
    }, [interventions]);

    const handleCreateIntervention = () => {
        setModalStep(1);
        setSelectedStudents([]);
        setSelectedIntervention(null);
        setAssignedFaculty('');
        setStartDate('');
        setShowModal(true);
    };

    const nextStep = () => setModalStep(modalStep + 1);
    const prevStep = () => setModalStep(modalStep - 1);

    const handleAssign = async () => {
        setError(null);
        if (!selectedIntervention) {
            setError('Please select an intervention type.');
            return;
        }
        if (selectedStudents.length === 0) {
            setError('Please select at least one student.');
            return;
        }

        setLoading(true);
        const response = await createIntervention({
            student_ids: selectedStudents,
            date: startDate || undefined,
            user: assignedFaculty || 'Unassigned',
            assigned_faculty: assignedFaculty || null,
            action: selectedIntervention,
            status: 'Pending',
        });
        setLoading(false);

        if (!response.success) {
            setError(response.message || 'Failed to create intervention.');
            return;
        }

        setShowModal(false);
        setSuccessMessage('Intervention assigned successfully.');
        await loadInterventions();
        setTimeout(() => setSuccessMessage(null), 3000);
    };

    const handleStatusToggle = async (idx) => {
        setError(null);
        const current = interventions[idx];
        if (!current) return;

        const nextStatus =
            current.status === 'Completed'
                ? 'Pending'
                : current.status === 'In Progress'
                ? 'Completed'
                : 'In Progress';

        setLoading(true);
        const response = await updateIntervention(current.id, { status: nextStatus });
        setLoading(false);

        if (!response.success) {
            setError(response.message || 'Failed to update intervention status.');
            return;
        }

        setSuccessMessage('Intervention status updated.');
        await loadInterventions();
        setTimeout(() => setSuccessMessage(null), 3000);
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
        if (typeof rating !== 'number') return '—';
        const fullStars = Math.floor(rating);
        return '★'.repeat(fullStars) + '☆'.repeat(5 - fullStars);
    };

    const total = interventions.length;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    const paginatedInterventions = useMemo(() => {
        const start = (currentPage - 1) * pageSize;
        return interventions.slice(start, start + pageSize);
    }, [interventions, currentPage, pageSize]);

    const studentRiskById = useMemo(() => {
        const map = new Map();
        (students || []).forEach((s) => {
            map.set(s.id, s.risk_score);
        });
        return map;
    }, [students]);

    const handlePageSizeChange = (newSize) => {
        setPageSize(newSize);
        setCurrentPage(1);
    };

    const handlePageChange = (newPage) => {
        if (newPage >= 1 && newPage <= totalPages) {
            setCurrentPage(newPage);
        }
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

            {successMessage && (
                <Alert variant="success" className="mb-3">
                    {successMessage}
                </Alert>
            )}
            {error && (
                <Alert variant="danger" className="mb-3">
                    {error}
                </Alert>
            )}

            {/* Active Interventions Table */}
            <motion.div variants={variants.item} className="glass-panel p-4 mb-4">
                <h5 className="mb-4 fw-semibold">Active Interventions</h5>
                {loading ? (
                    <div className="text-center py-4 text-muted">Loading interventions…</div>
                ) : paginatedInterventions.length === 0 ? (
                    <div className="text-center py-4 text-muted">No pending interventions found.</div>
                ) : (
                    <>
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
                                    {paginatedInterventions.map((item, idx) => (
                                        <tr key={`${item.student_id}-${idx}`}>
                                            <td>{studentNameById.get(item.student_id) || item.student_id}</td>
                                            <td>{item.action || item.threshold_category || 'Intervention'}</td>
                                            <td>{item.date || '—'}</td>
                                            <td>{getStatusBadge(item.status || 'Pending')}</td>
                                            <td>{item.assigned_faculty || item.assigned_team || 'Unassigned'}</td>
                                            <td>
                                                {(() => {
                                                    const currentRisk = studentRiskById.get(item.student_id);
                                                    const baseRisk = typeof item.risk_score_at_trigger === 'number' ? item.risk_score_at_trigger : null;
                                                    if (typeof currentRisk !== 'number' || baseRisk === null) return '—';
                                                    const delta = Math.round((currentRisk - baseRisk) * 10) / 10;
                                                    const color = delta <= -5 ? 'text-success' : delta >= 5 ? 'text-danger' : 'text-muted';
                                                    const sign = delta > 0 ? '+' : '';
                                                    return <span className={color}>{sign}{delta} pts</span>;
                                                })()}
                                            </td>
                                            <td>
                                                <Button
                                                    variant="link"
                                                    size="sm"
                                                    className="p-0"
                                                    onClick={() => handleStatusToggle((currentPage - 1) * pageSize + idx)}
                                                >
                                                    •••
                                                </Button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </Table>
                        </div>

                        {/* Pagination Controls */}
                        <div className="d-flex justify-content-between align-items-center mt-3 pt-2 border-top" style={{ borderColor: 'var(--border-color)' }}>
                            <div className="d-flex align-items-center gap-3">
                                <small className="text-muted">
                                    Showing {(currentPage - 1) * pageSize + 1}-
                                    {(currentPage - 1) * pageSize + paginatedInterventions.length} of {total} interventions
                                </small>
                                <div className="d-flex align-items-center gap-2">
                                    <small className="text-muted">Per page:</small>
                                    <Form.Select
                                        size="sm"
                                        value={pageSize}
                                        onChange={(e) => handlePageSizeChange(parseInt(e.target.value, 10))}
                                        style={{ width: 'auto' }}
                                    >
                                        <option value="10">10</option>
                                        <option value="25">25</option>
                                        <option value="50">50</option>
                                    </Form.Select>
                                </div>
                            </div>
                            <div className="d-flex gap-2">
                                <Button
                                    variant="outline-secondary"
                                    size="sm"
                                    onClick={() => handlePageChange(currentPage - 1)}
                                    disabled={currentPage === 1}
                                >
                                    ← Previous
                                </Button>
                                <Button variant="primary" size="sm" disabled>
                                    {currentPage}
                                </Button>
                                <Button
                                    variant="outline-secondary"
                                    size="sm"
                                    onClick={() => handlePageChange(currentPage + 1)}
                                    disabled={currentPage === totalPages}
                                >
                                    Next →
                                </Button>
                            </div>
                        </div>
                    </>
                )}
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
                                                        <small className="text-muted d-block">{typeof item.rating === 'number' ? `${item.rating}/5` : '—'}</small>
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
                            {(() => {
                                const byType = {};
                                interventions.forEach((i) => {
                                    const key = i.action || i.threshold_category || 'Intervention';
                                    if (!byType[key]) byType[key] = { type: key, count: 0, success: 0, deltaSum: 0, deltaN: 0 };
                                    byType[key].count += 1;

                                    const eff = typeof i.effectiveness_score === 'number' ? i.effectiveness_score : null;
                                    if (eff !== null && eff >= 0.2) byType[key].success += 1;

                                    const currentRisk = studentRiskById.get(i.student_id);
                                    const baseRisk = typeof i.risk_score_at_trigger === 'number' ? i.risk_score_at_trigger : null;
                                    if (typeof currentRisk === 'number' && baseRisk !== null) {
                                        byType[key].deltaSum += (baseRisk - currentRisk);
                                        byType[key].deltaN += 1;
                                    }
                                });

                                const rows = Object.values(byType).sort((a, b) => b.count - a.count).slice(0, 8);
                                if (!rows.length) {
                                    return (
                                        <tr>
                                            <td colSpan="4" className="text-center text-muted py-4">No intervention data available.</td>
                                        </tr>
                                    );
                                }

                                return rows.map((r) => {
                                    const successRate = r.count ? Math.round((r.success / r.count) * 100) : 0;
                                    const avgImprove = r.deltaN ? Math.round((r.deltaSum / r.deltaN) * 10) / 10 : null;
                                    const badgeVariant = successRate >= 80 ? 'success' : successRate >= 60 ? 'warning' : 'secondary';
                                    return (
                                        <tr key={r.type}>
                                            <td>{r.type}</td>
                                            <td>{r.count}</td>
                                            <td><Badge bg={badgeVariant}>{successRate}%</Badge></td>
                                            <td className={avgImprove !== null && avgImprove > 0 ? 'text-success' : 'text-muted'}>
                                                {avgImprove !== null ? `+${avgImprove} pts` : '—'}
                                            </td>
                                        </tr>
                                    );
                                });
                            })()}
                        </tbody>
                    </Table>
                </div>
                <small className="text-muted">Success = Effectiveness score ≥ 0.2 or measurable risk improvement where available.</small>
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
                                {students.slice(0, 25).map(student => (
                                    <Form.Check
                                        key={student.id}
                                        type="checkbox"
                                        label={`${student.name || student.id} (Risk: ${student.risk_score})`}
                                        className="ms-4"
                                        checked={selectedStudents.includes(student.id)}
                                        onChange={(e) => {
                                            setSelectedStudents((prev) =>
                                                e.target.checked ? [...prev, student.id] : prev.filter((id) => id !== student.id),
                                            );
                                        }}
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
                                <Form.Select value={assignedFaculty} onChange={(e) => setAssignedFaculty(e.target.value)}>
                                    <option value="">Unassigned</option>
                                    {facultyOptions.map((f) => (
                                        <option key={f} value={f}>{f}</option>
                                    ))}
                                </Form.Select>
                            </Form.Group>

                            <Row>
                                <Col md={6}>
                                    <Form.Group className="mb-3">
                                        <Form.Label>Start Date:</Form.Label>
                                        <Form.Control type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
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
