import React, { useEffect, useState } from 'react';
import { Alert, Row, Col, Card, Form, Button, Table, Badge, Spinner } from 'react-bootstrap';
import { FaCog, FaBell, FaUsers, FaDatabase, FaPalette, FaInfoCircle, FaUserCircle } from 'react-icons/fa';
import { motion } from 'framer-motion';
import { variants } from '../utils/motionConfig';
import { getCurrentProfile, updateCurrentProfile } from '../services/api';

const Settings = () => {
    const [thresholds, setThresholds] = useState({
        critical: { min: 0, max: 25 },
        high: { min: 26, max: 50 },
        medium: { min: 51, max: 75 },
        low: { min: 76, max: 100 },
    });

    const [profile, setProfile] = useState(null);
    const [preferences, setPreferences] = useState({
        dashboardLayout: 'comfortable',
        highContrast: false,
        reduceAnimations: false,
        notifications: {
            criticalRisk: true,
            riskDrop: true,
            lowAttendance: true,
            interventionCompleted: false,
            aiHighConfidence: true,
        },
    });
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);
    const [success, setSuccess] = useState(null);

    useEffect(() => {
        let isMounted = true;
        const load = async () => {
            setLoading(true);
            setError(null);
            const resp = await getCurrentProfile();
            if (!isMounted) return;
            if (!resp.success) {
                setError(resp.message || 'Failed to load settings.');
                setLoading(false);
                return;
            }
            const data = resp.data || {};
            setProfile({
                id: data.id,
                username: data.username || '',
                email: data.email || '',
                role: data.role || '',
                is_active: data.is_active,
            });
            const prefs = data.preferences || {};
            setPreferences((prev) => ({
                ...prev,
                ...prefs,
                notifications: {
                    ...prev.notifications,
                    ...(prefs.notifications || {}),
                },
            }));
            const riskPrefs = prefs.risk_thresholds;
            if (riskPrefs && typeof riskPrefs === 'object') {
                setThresholds((prev) => ({
                    critical: riskPrefs.critical || prev.critical,
                    high: riskPrefs.high || prev.high,
                    medium: riskPrefs.medium || prev.medium,
                    low: riskPrefs.low || prev.low,
                }));
            }
            setLoading(false);
        };
        load();
        return () => { isMounted = false; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleSave = async () => {
        if (!profile) return;
        setSaving(true);
        setError(null);
        setSuccess(null);
        const payload = {
            username: profile.username,
            email: profile.email,
            role: profile.role,
            is_active: profile.is_active,
            preferences: {
                ...preferences,
                risk_thresholds: thresholds,
            },
        };
        const resp = await updateCurrentProfile(payload);
        setSaving(false);
        if (!resp.success) {
            setError(resp.message || 'Failed to save settings.');
            return;
        }
        setSuccess('Settings saved successfully.');
        setTimeout(() => setSuccess(null), 3000);
    };

    return (
        <motion.div
            initial="hidden"
            animate="visible"
            variants={variants.container}
            className="pb-5"
        >
            <div className="mb-5">
                <h1 className="display-5 fw-bold text-gradient mb-2">Settings</h1>
                <p className="text-secondary fs-5" style={{ maxWidth: '700px' }}>
                    Platform configuration, user management, and system preferences.
                </p>
            </div>

            {loading && (
                <div className="mb-4 d-flex align-items-center gap-2 text-muted">
                    <Spinner animation="border" size="sm" />
                    <span>Loading your profile and preferences…</span>
                </div>
            )}
            {error && (
                <Alert variant="danger" className="mb-4">
                    {error}
                </Alert>
            )}
            {success && (
                <Alert variant="success" className="mb-4">
                    {success}
                </Alert>
            )}

            <Row className="g-4">
                {/* My Profile */}
                <Col lg={6}>
                    <motion.div variants={variants.item}>
                        <Card className="glass-panel border-0 h-100">
                            <Card.Body>
                                <h5 className="mb-4 fw-semibold d-flex align-items-center gap-2">
                                    <FaUserCircle /> My Profile
                                </h5>
                                {profile ? (
                                    <>
                                        <Form.Group className="mb-3">
                                            <Form.Label>Username</Form.Label>
                                            <Form.Control
                                                type="text"
                                                value={profile.username}
                                                onChange={(e) => setProfile({ ...profile, username: e.target.value })}
                                            />
                                        </Form.Group>
                                        <Form.Group className="mb-3">
                                            <Form.Label>Email</Form.Label>
                                            <Form.Control
                                                type="email"
                                                value={profile.email}
                                                onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                                            />
                                        </Form.Group>
                                        <Form.Group className="mb-3">
                                            <Form.Label>Role</Form.Label>
                                            <Form.Control
                                                type="text"
                                                value={profile.role}
                                                disabled
                                            />
                                        </Form.Group>
                                    </>
                                ) : (
                                    <div className="text-muted small">Profile not available.</div>
                                )}
                            </Card.Body>
                        </Card>
                    </motion.div>
                </Col>

                {/* Risk Score Thresholds */}
                <Col lg={6}>
                    <motion.div variants={variants.item}>
                        <Card className="glass-panel border-0 h-100">
                            <Card.Body>
                                <h5 className="mb-4 fw-semibold d-flex align-items-center gap-2">
                                    <FaCog /> Risk Score Thresholds
                                </h5>

                                {Object.entries(thresholds).map(([level, range]) => (
                                    <div className="mb-3" key={level}>
                                        <div className="d-flex justify-content-between align-items-center mb-2">
                                            <span className="text-capitalize fw-medium">{level} Risk:</span>
                                            <Badge bg={level === 'critical' ? 'danger' : level === 'high' ? 'warning' : level === 'medium' ? 'info' : 'success'}>
                                                {range.min} - {range.max}
                                            </Badge>
                                        </div>
                                        <div className="d-flex gap-2">
                                            <Form.Control
                                                type="number"
                                                value={range.min}
                                                onChange={(e) => setThresholds({
                                                    ...thresholds,
                                                    [level]: { ...range, min: parseInt(e.target.value) }
                                                })}
                                                size="sm"
                                            />
                                            <span className="align-self-center">to</span>
                                            <Form.Control
                                                type="number"
                                                value={range.max}
                                                onChange={(e) => setThresholds({
                                                    ...thresholds,
                                                    [level]: { ...range, max: parseInt(e.target.value) }
                                                })}
                                                size="sm"
                                            />
                                        </div>
                                    </div>
                                ))}

                                <div className="alert alert-warning mt-3 d-flex align-items-start gap-2">
                                    <span>⚠️</span>
                                    <small>Changing these values will reclassify students and may trigger notifications.</small>
                                </div>

                                <div className="d-grid gap-2">
                                    <Button variant="outline-secondary" disabled={saving}>Reset to Default</Button>
                                </div>
                            </Card.Body>
                        </Card>
                    </motion.div>
                </Col>

                {/* Notification Rules */}
                <Col lg={6}>
                    <motion.div variants={variants.item}>
                        <Card className="glass-panel border-0 h-100">
                            <Card.Body>
                                <h5 className="mb-4 fw-semibold d-flex align-items-center gap-2">
                                    <FaBell /> Notification Rules
                                </h5>

                                <Form.Check
                                    type="checkbox"
                                    label="Student enters Critical risk level"
                                    className="mb-3"
                                    checked={preferences.notifications.criticalRisk}
                                    onChange={(e) =>
                                        setPreferences((prev) => ({
                                            ...prev,
                                            notifications: { ...prev.notifications, criticalRisk: e.target.checked },
                                        }))
                                    }
                                />
                                <div className="ms-4 mb-3">
                                    <small className="text-muted d-block">Recipients: Assigned counselor</small>
                                    <small className="text-muted">Frequency: Immediate</small>
                                </div>

                                <Form.Check
                                    type="checkbox"
                                    label="Risk score drops 20+ points in 7 days"
                                    className="mb-3"
                                    checked={preferences.notifications.riskDrop}
                                    onChange={(e) =>
                                        setPreferences((prev) => ({
                                            ...prev,
                                            notifications: { ...prev.notifications, riskDrop: e.target.checked },
                                        }))
                                    }
                                />
                                <div className="ms-4 mb-3">
                                    <small className="text-muted d-block">Recipients: Academic advisor</small>
                                    <small className="text-muted">Frequency: Daily digest</small>
                                </div>

                                <Form.Check
                                    type="checkbox"
                                    label="Attendance falls below 60%"
                                    className="mb-3"
                                    checked={preferences.notifications.lowAttendance}
                                    onChange={(e) =>
                                        setPreferences((prev) => ({
                                            ...prev,
                                            notifications: { ...prev.notifications, lowAttendance: e.target.checked },
                                        }))
                                    }
                                />
                                <div className="ms-4 mb-3">
                                    <small className="text-muted d-block">Recipients: Student, Counselor</small>
                                    <small className="text-muted">Frequency: Weekly</small>
                                </div>

                                <Form.Check
                                    type="checkbox"
                                    label="Intervention completed"
                                    className="mb-3"
                                    checked={preferences.notifications.interventionCompleted}
                                    onChange={(e) =>
                                        setPreferences((prev) => ({
                                            ...prev,
                                            notifications: { ...prev.notifications, interventionCompleted: e.target.checked },
                                        }))
                                    }
                                />
                                <div className="ms-4 mb-3">
                                    <small className="text-muted d-block">Recipients: Coach, System admin</small>
                                    <small className="text-muted">Frequency: Immediate</small>
                                </div>

                                <Form.Check
                                    type="checkbox"
                                    label="AI suggestion has 90%+ confidence"
                                    className="mb-3"
                                    checked={preferences.notifications.aiHighConfidence}
                                    onChange={(e) =>
                                        setPreferences((prev) => ({
                                            ...prev,
                                            notifications: { ...prev.notifications, aiHighConfidence: e.target.checked },
                                        }))
                                    }
                                />
                                <div className="ms-4 mb-3">
                                    <small className="text-muted d-block">Recipients: Dashboard only</small>
                                </div>

                                <Button variant="primary" className="w-100 mt-3" disabled={saving} onClick={handleSave}>
                                    {saving ? 'Saving…' : 'Save Settings'}
                                </Button>
                            </Card.Body>
                        </Card>
                    </motion.div>
                </Col>

                {/* User Roles & Permissions */}
                <Col lg={12}>
                    <motion.div variants={variants.item}>
                        <Card className="glass-panel border-0">
                            <Card.Body>
                                <div className="d-flex justify-content-between align-items-center mb-4">
                                    <h5 className="mb-0 fw-semibold d-flex align-items-center gap-2">
                                        <FaUsers /> User Roles & Permissions
                                    </h5>
                                    <Button variant="outline-secondary" size="sm" disabled>Manage in Admin console</Button>
                                </div>

                                <div className="table-responsive">
                                    <Table className="modern-table">
                                        <thead>
                                            <tr>
                                                <th>Name</th>
                                                <th>Email</th>
                                                <th>Role</th>
                                                <th>Last Login</th>
                                                <th>Status</th>
                                                <th>Actions</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr>
                                                <td colSpan={6} className="text-muted small">
                                                    User management is handled via the Admin APIs. This section is read-only in the current build.
                                                </td>
                                            </tr>
                                        </tbody>
                                    </Table>
                                </div>
                            </Card.Body>
                        </Card>
                    </motion.div>
                </Col>

                {/* Data Integration Settings */}
                <Col lg={12}>
                    <motion.div variants={variants.item}>
                        <Card className="glass-panel border-0">
                            <Card.Body>
                                <h5 className="mb-4 fw-semibold d-flex align-items-center gap-2">
                                    <FaDatabase /> Data Sources
                                </h5>

                                <div className="border-bottom pb-3 mb-3" style={{ borderColor: 'var(--border-color)' }}>
                                        <div className="d-flex justify-content-between align-items-start">
                                            <div>
                                                <h6 className="mb-2">Data source configuration</h6>
                                                <small className="text-muted d-block mb-1">
                                                    SIS / LMS connectors are configured server-side. UI configuration for data sources is not enabled in this environment.
                                                </small>
                                            </div>
                                        </div>
                                    </div>

                                <div className="alert alert-info d-flex align-items-center gap-2">
                                    <FaInfoCircle />
                                    <small>⚠️ Sync errors: 0 | Last error: None</small>
                                </div>
                            </Card.Body>
                        </Card>
                    </motion.div>
                </Col>

                {/* Appearance & Preferences */}
                <Col lg={6}>
                    <motion.div variants={variants.item}>
                        <Card className="glass-panel border-0">
                            <Card.Body>
                                <h5 className="mb-4 fw-semibold d-flex align-items-center gap-2">
                                    <FaPalette /> Display Preferences
                                </h5>

                                <Form.Group className="mb-3">
                                    <Form.Label>Dashboard Layout:</Form.Label>
                                    <Form.Select>
                                        <option
                                            value="compact"
                                            selected={preferences.dashboardLayout === 'compact'}
                                            onChange={() => {}}
                                        >
                                            Compact
                                        </option>
                                        <option
                                            value="comfortable"
                                            selected={preferences.dashboardLayout === 'comfortable'}
                                            onChange={() => {}}
                                        >
                                            Comfortable (default)
                                        </option>
                                        <option
                                            value="spacious"
                                            selected={preferences.dashboardLayout === 'spacious'}
                                            onChange={() => {}}
                                        >
                                            Spacious
                                        </option>
                                    </Form.Select>
                                </Form.Group>

                                <Form.Group className="mb-3">
                                    <Form.Label>Accessibility:</Form.Label>
                                    <Form.Check
                                        type="checkbox"
                                        label="High contrast mode"
                                        checked={preferences.highContrast}
                                        onChange={(e) => setPreferences((prev) => ({ ...prev, highContrast: e.target.checked }))}
                                    />
                                    <Form.Check
                                        type="checkbox"
                                        label="Reduce animations"
                                        checked={preferences.reduceAnimations}
                                        onChange={(e) => setPreferences((prev) => ({ ...prev, reduceAnimations: e.target.checked }))}
                                    />
                                </Form.Group>

                                <Button variant="primary" className="w-100" disabled={saving} onClick={handleSave}>
                                    {saving ? 'Saving…' : 'Save Preferences'}
                                </Button>
                            </Card.Body>
                        </Card>
                    </motion.div>
                </Col>

                {/* System Information */}
                <Col lg={6}>
                    <motion.div variants={variants.item}>
                        <Card className="glass-panel border-0">
                            <Card.Body>
                                <h5 className="mb-4 fw-semibold d-flex align-items-center gap-2">
                                    <FaInfoCircle /> System Information
                                </h5>

                                <div className="mb-2">
                                    <small className="text-muted">Platform Version:</small>
                                    <p className="mb-0 fw-medium">v2.4.1</p>
                                </div>

                                <div className="mb-2">
                                    <small className="text-muted">Last Updated:</small>
                                    <p className="mb-0 fw-medium">Jan 28, 2026</p>
                                </div>

                                <div className="mb-2">
                                    <small className="text-muted">Database:</small>
                                    <p className="mb-0 fw-medium">PostgreSQL 14.2</p>
                                </div>

                                <div className="mb-2">
                                    <small className="text-muted">Uptime:</small>
                                    <p className="mb-0 fw-medium">45 days</p>
                                </div>

                                <div className="mb-2">
                                    <small className="text-muted">Storage Used:</small>
                                    <p className="mb-0 fw-medium">2.3 GB / 50 GB</p>
                                </div>

                                <div className="mb-2">
                                    <small className="text-muted">Active Sessions:</small>
                                    <p className="mb-0 fw-medium">23</p>
                                </div>

                                <div className="d-grid gap-2 mt-4">
                                    <Button variant="outline-secondary">View System Logs</Button>
                                    <Button variant="outline-secondary">Download Diagnostics</Button>
                                    <Button variant="outline-primary">Contact Support</Button>
                                </div>
                            </Card.Body>
                        </Card>
                    </motion.div>
                </Col>
            </Row>
        </motion.div>
    );
};

export default Settings;
