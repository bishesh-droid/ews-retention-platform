import React from 'react';
import { Card, ProgressBar, Badge, Accordion } from 'react-bootstrap';
import { FaCheckCircle, FaExclamationCircle, FaExclamationTriangle } from 'react-icons/fa';
import { calculateDataQuality, getDataQualitySummary } from '../../utils/dataQualityCalculator';

/**
 * DataQualityPanel Component
 * Shows data completeness and quality indicators
 */
const DataQualityPanel = ({ student, variant = 'full' }) => {
    const quality = calculateDataQuality(student);

    const getQualityIcon = () => {
        if (quality.qualityLevel === 'high') return <FaCheckCircle className="text-success" />;
        if (quality.qualityLevel === 'moderate') return <FaExclamationTriangle className="text-warning" />;
        return <FaExclamationCircle className="text-danger" />;
    };

    const getProgressBarVariant = () => {
        if (quality.completenessScore >= 90) return 'success';
        if (quality.completenessScore >= 70) return 'warning';
        return 'danger';
    };

    if (variant === 'compact') {
        return (
            <div className="d-flex align-items-center gap-2">
                {getQualityIcon()}
                <small className="text-muted">
                    Data: {quality.completenessScore}% complete
                </small>
            </div>
        );
    }

    if (variant === 'badge') {
        return (
            <Badge
                bg={quality.qualityLevel === 'high' ? 'success' : quality.qualityLevel === 'moderate' ? 'warning' : 'danger'}
                className="d-flex align-items-center gap-1"
            >
                {quality.qualityIcon} {quality.completenessScore}% Data Quality
            </Badge>
        );
    }

    return (
        <Card className="glass-panel border-0">
            <Card.Body>
                <div className="d-flex align-items-center gap-2 mb-3">
                    <h6 className="mb-0 fw-semibold">Data Quality</h6>
                    {getQualityIcon()}
                </div>

                <div className="mb-3">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                        <small className="text-muted">Completeness</small>
                        <strong>{quality.completenessScore}%</strong>
                    </div>
                    <ProgressBar
                        now={quality.completenessScore}
                        variant={getProgressBarVariant()}
                        style={{ height: '8px' }}
                    />
                    <small className="text-muted mt-1 d-block">
                        {quality.presentCount} of {quality.totalCount} data points available
                    </small>
                </div>

                <div className="mb-3">
                    <div className="d-flex justify-content-between align-items-center mb-2">
                        <small className="text-muted">Quality Level</small>
                        <Badge bg={getProgressBarVariant()}>
                            {quality.qualityLevel.toUpperCase()}
                        </Badge>
                    </div>
                </div>

                {quality.missingFields.length > 0 && (
                    <Accordion className="mt-3">
                        <Accordion.Item eventKey="0" className="bg-transparent border">
                            <Accordion.Header className="bg-transparent">
                                <small className="text-warning">
                                    ⚠️ {quality.missingFields.length} missing data point{quality.missingFields.length !== 1 ? 's' : ''}
                                </small>
                            </Accordion.Header>
                            <Accordion.Body className="bg-transparent">
                                <ul className="mb-0 ps-3">
                                    {quality.missingFields.slice(0, 10).map((field, idx) => (
                                        <li key={idx}>
                                            <small className="text-muted">{field}</small>
                                        </li>
                                    ))}
                                    {quality.missingFields.length > 10 && (
                                        <li>
                                            <small className="text-muted">
                                                ... and {quality.missingFields.length - 10} more
                                            </small>
                                        </li>
                                    )}
                                </ul>
                            </Accordion.Body>
                        </Accordion.Item>
                    </Accordion>
                )}

                {quality.hasSufficientData && (
                    <div className="alert alert-success mt-3 mb-0 py-2">
                        <small className="mb-0">
                            ✓ Sufficient data for reliable risk assessment
                        </small>
                    </div>
                )}

                {!quality.hasSufficientData && (
                    <div className="alert alert-warning mt-3 mb-0 py-2">
                        <small className="mb-0">
                            ⚠️ Limited data may affect risk score accuracy
                        </small>
                    </div>
                )}
            </Card.Body>
        </Card>
    );
};

export default DataQualityPanel;
