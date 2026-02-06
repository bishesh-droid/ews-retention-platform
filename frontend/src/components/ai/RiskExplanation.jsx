import React from 'react';
import { Card, Badge } from 'react-bootstrap';
import { generateRiskNarrative, getSeverityInfo, getFactorExplanation } from '../../utils/riskNarrativeGenerator';
import { getPrimaryRiskFactor } from '../../utils/studentUtils';

/**
 * RiskExplanation Component
 * Displays AI-generated natural language explanation of risk score
 */
const RiskExplanation = ({ student, variant = 'full' }) => {
    const narrative = generateRiskNarrative(student);
    const severityInfo = getSeverityInfo(student.risk_score);
    const primaryFactor = getPrimaryRiskFactor(student);
    const factorExplanation = getFactorExplanation(primaryFactor, student);

    if (variant === 'compact') {
        return (
            <div className="p-3 rounded-3 bg-surface-hover">
                <div className="d-flex align-items-start gap-2 mb-2">
                    <span style={{ fontSize: '1.25rem' }}>{severityInfo.icon}</span>
                    <div className="flex-grow-1">
                        <div className="d-flex justify-content-between align-items-start mb-1">
                            <strong style={{ color: severityInfo.color }}>{severityInfo.label}</strong>
                            <Badge bg="secondary" className="ms-2">{student.risk_score}</Badge>
                        </div>
                        <p className="mb-0 small text-muted">{narrative}</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <Card
            className="border-0 shadow-sm"
            style={{ borderLeft: `4px solid ${severityInfo.color}` }}
        >
            <Card.Body>
                <div className="d-flex align-items-center gap-2 mb-3">
                    <span style={{ fontSize: '2rem' }}>{severityInfo.icon}</span>
                    <div className="flex-grow-1">
                        <div className="d-flex justify-content-between align-items-center">
                            <h5 className="mb-0" style={{ color: severityInfo.color }}>
                                {severityInfo.label}
                            </h5>
                            <Badge
                                bg="light"
                                text="dark"
                                className="fs-6 px-3 py-2"
                            >
                                Risk Score: {student.risk_score}
                            </Badge>
                        </div>
                        <p className="mb-0 text-muted small">{severityInfo.description}</p>
                    </div>
                </div>

                <div className="mb-3">
                    <h6 className="fw-semibold mb-2">Analysis</h6>
                    <p className="mb-0">{narrative}</p>
                </div>

                <div className="mb-3">
                    <h6 className="fw-semibold mb-2">Primary Factor: {primaryFactor}</h6>
                    <p className="mb-0 small text-muted">{factorExplanation}</p>
                </div>

                <div className="alert alert-info mb-0 d-flex align-items-start gap-2">
                    <span className="mt-1">💡</span>
                    <div>
                        <strong className="d-block mb-1">Recommended Action</strong>
                        <small>{severityInfo.action}</small>
                    </div>
                </div>
            </Card.Body>
        </Card>
    );
};

export default RiskExplanation;
