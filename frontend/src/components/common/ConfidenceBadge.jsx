import React from 'react';
import { Badge, OverlayTrigger, Tooltip } from 'react-bootstrap';
import { FaInfoCircle } from 'react-icons/fa';
import { calculateConfidenceScore } from '../../utils/dataQualityCalculator';

/**
 * ConfidenceBadge Component
 * Displays confidence score for risk predictions with tooltip explanation
 */
const ConfidenceBadge = ({ student, size = 'sm', showLabel = true }) => {
    const confidence = calculateConfidenceScore(student);

    const getBadgeVariant = () => {
        if (confidence.confidenceLevel === 'high') return 'success';
        if (confidence.confidenceLevel === 'moderate') return 'warning';
        return 'danger';
    };

    const renderTooltip = (props) => (
        <Tooltip id="confidence-tooltip" {...props}>
            <div className="text-start">
                <strong>Confidence: {confidence.confidenceScore}%</strong>
                <div className="mt-2">
                    <small>
                        Based on {confidence.dataQuality.presentCount}/{confidence.dataQuality.totalCount} data points available.
                    </small>
                </div>
                {confidence.dataQuality.missingFields.length > 0 && (
                    <div className="mt-2">
                        <small className="text-warning">
                            Missing: {confidence.dataQuality.missingFields.slice(0, 3).join(', ')}
                            {confidence.dataQuality.missingFields.length > 3 && ` +${confidence.dataQuality.missingFields.length - 3} more`}
                        </small>
                    </div>
                )}
            </div>
        </Tooltip>
    );

    return (
        <OverlayTrigger
            placement="top"
            overlay={renderTooltip}
            delay={{ show: 250, hide: 400 }}
        >
            <Badge
                bg={getBadgeVariant()}
                className={`d-inline-flex align-items-center gap-1 ${size === 'sm' ? 'px-2 py-1' : 'px-3 py-2'}`}
                style={{ cursor: 'help', fontSize: size === 'sm' ? '0.75rem' : '0.85rem' }}
            >
                {showLabel && <span>{confidence.confidenceBadge}</span>}
                {!showLabel && <span>{confidence.confidenceScore}%</span>}
                <FaInfoCircle size={12} className="opacity-75" />
            </Badge>
        </OverlayTrigger>
    );
};

export default ConfidenceBadge;
