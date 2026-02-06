import React from 'react';
import { Card, Badge, ProgressBar } from 'react-bootstrap';
import { FaCheckCircle, FaTimesCircle, FaExclamationCircle } from 'react-icons/fa';

/**
 * InterventionHistoryCard Component
 * Displays intervention history with before/after metrics and effectiveness
 */
const InterventionHistoryCard = ({ intervention }) => {
    // Calculate improvement
    const riskImprovement = intervention.riskAfter - intervention.riskBefore;
    const attendanceImprovement = (intervention.attendanceAfter || 0) - (intervention.attendanceBefore || 0);
    const gpaImprovement = (intervention.gpaAfter || 0) - (intervention.gpaBefore || 0);

    // Determine effectiveness
    const getEffectiveness = () => {
        let goalsMetCount = 0;
        let totalGoals = 0;

        if (riskImprovement !== undefined) {
            totalGoals++;
            if (riskImprovement >= 20) goalsMetCount++; // Goal: +20 pts
        }
        if (attendanceImprovement !== undefined) {
            totalGoals++;
            if (intervention.attendanceAfter >= 85) goalsMetCount++; // Goal: 85%+
        }
        if (gpaImprovement !== undefined) {
            totalGoals++;
            if (gpaImprovement >= 0.5) goalsMetCount++; // Goal: +0.5
        }

        const percentage = totalGoals > 0 ? (goalsMetCount / totalGoals) * 100 : 0;

        if (percentage === 100) return { level: 'highly-effective', label: 'Highly Effective', icon: <FaCheckCircle className="text-success" />, color: 'success' };
        if (percentage >= 66) return { level: 'effective', label: 'Effective', icon: <FaCheckCircle className="text-success" />, color: 'success' };
        if (percentage >= 33) return { level: 'partially-effective', label: 'Partially Effective', icon: <FaExclamationCircle className="text-warning" />, color: 'warning' };
        return { level: 'ineffective', label: 'Ineffective', icon: <FaTimesCircle className="text-danger" />, color: 'danger' };
    };

    const effectiveness = getEffectiveness();

    const getStatusBadge = (status) => {
        const variants = {
            'Pending': 'secondary',
            'In Progress': 'primary',
            'Completed': 'success',
            'Cancelled': 'danger',
        };
        return <Badge bg={variants[status] || 'secondary'}>{status}</Badge>;
    };

    return (
        <Card className="mb-3 border-0 shadow-sm">
            <Card.Body>
                <div className="d-flex justify-content-between align-items-start mb-3">
                    <div>
                        <h6 className="mb-1 fw-semibold">{intervention.intervention}</h6>
                        <small className="text-muted">
                            {intervention.assignedDate} • Assigned by {intervention.owner}
                        </small>
                    </div>
                    <div className="d-flex flex-column align-items-end gap-1">
                        {getStatusBadge(intervention.status)}
                        <span className="d-flex align-items-center gap-1">
                            {effectiveness.icon}
                            <small className="fw-medium">{effectiveness.label}</small>
                        </span>
                    </div>
                </div>

                {intervention.status === 'Completed' && (
                    <>
                        <div className="mb-3">
                            <h6 className="small text-muted mb-2">Outcome Metrics</h6>
                            <div className="bg-surface-hover p-3 rounded-3">
                                {/* Risk Score Change */}
                                <div className="mb-2">
                                    <div className="d-flex justify-content-between align-items-center mb-1">
                                        <small className="text-muted">Risk Score</small>
                                        <span className={riskImprovement > 0 ? 'text-success fw-medium' : 'text-danger fw-medium'}>
                                            {intervention.riskBefore} → {intervention.riskAfter}
                                            {riskImprovement > 0 ? ' ↓' : ' ↑'}
                                            ({Math.abs(riskImprovement)} pts)
                                        </span>
                                    </div>
                                    <ProgressBar
                                        now={riskImprovement >= 20 ? 100 : (riskImprovement / 20) * 100}
                                        variant={riskImprovement >= 20 ? 'success' : 'warning'}
                                        style={{ height: '4px' }}
                                    />
                                    <small className="text-muted">
                                        Goal: 20+ pts {riskImprovement >= 20 ? '✓' : '✗'}
                                    </small>
                                </div>

                                {/* Attendance Change */}
                                {intervention.attendanceBefore !== undefined && (
                                    <div className="mb-2">
                                        <div className="d-flex justify-content-between align-items-center mb-1">
                                            <small className="text-muted">Attendance</small>
                                            <span className={attendanceImprovement > 0 ? 'text-success fw-medium' : 'text-danger fw-medium'}>
                                                {intervention.attendanceBefore}% → {intervention.attendanceAfter}%
                                                {attendanceImprovement > 0 ? ' ↑' : ' ↓'}
                                                ({Math.abs(attendanceImprovement)}%)
                                            </span>
                                        </div>
                                        <ProgressBar
                                            now={(intervention.attendanceAfter / 85) * 100}
                                            variant={intervention.attendanceAfter >= 85 ? 'success' : 'warning'}
                                            style={{ height: '4px' }}
                                        />
                                        <small className="text-muted">
                                            Goal: 85%+ {intervention.attendanceAfter >= 85 ? '✓' : '✗'}
                                        </small>
                                    </div>
                                )}

                                {/* GPA Change */}
                                {intervention.gpaBefore !== undefined && (
                                    <div>
                                        <div className="d-flex justify-content-between align-items-center mb-1">
                                            <small className="text-muted">GPA</small>
                                            <span className={gpaImprovement > 0 ? 'text-success fw-medium' : 'text-danger fw-medium'}>
                                                {intervention.gpaBefore.toFixed(2)} → {intervention.gpaAfter.toFixed(2)}
                                                {gpaImprovement > 0 ? ' ↑' : ' ↓'}
                                                ({Math.abs(gpaImprovement).toFixed(2)})
                                            </span>
                                        </div>
                                        <ProgressBar
                                            now={gpaImprovement >= 0.5 ? 100 : (gpaImprovement / 0.5) * 100}
                                            variant={gpaImprovement >= 0.5 ? 'success' : 'warning'}
                                            style={{ height: '4px' }}
                                        />
                                        <small className="text-muted">
                                            Goal: +0.5 {gpaImprovement >= 0.5 ? '✓' : '✗'}
                                        </small>
                                    </div>
                                )}
                            </div>
                        </div>

                        {intervention.notes && (
                            <div className="alert alert-info mb-0 py-2">
                                <small><strong>Notes:</strong> {intervention.notes}</small>
                            </div>
                        )}
                    </>
                )}

                {intervention.status === 'In Progress' && (
                    <div className="alert alert-primary mb-0 py-2">
                        <small>📊 Intervention is ongoing. Metrics will be available upon completion.</small>
                    </div>
                )}
            </Card.Body>
        </Card>
    );
};

export default InterventionHistoryCard;
