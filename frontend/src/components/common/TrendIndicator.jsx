import React from 'react';
import { OverlayTrigger, Tooltip } from 'react-bootstrap';
import { calculateRiskTrend, calculateAttendanceTrend, formatDelta, formatDeltaPercent, getPreviousRiskScore, getPreviousAttendance } from '../../utils/trendCalculator';

/**
 * TrendIndicator Component
 * Shows trend arrows and delta values for metrics
 */
const TrendIndicator = ({
    current,
    previous,
    metricType = 'general',
    unit = 'pts',
    size = 'md',
    showDelta = true,
    showPercent = false
}) => {
    if (previous === null || previous === undefined) {
        return null;
    }

    let trend;
    if (metricType === 'risk') {
        trend = calculateRiskTrend(current, previous);
    } else if (metricType === 'attendance') {
        trend = calculateAttendanceTrend(current, previous);
    } else {
        trend = { direction: 'stable', delta: 0, color: '#9E9E9E', arrow: '→' };
    }

    if (trend.direction === 'stable') {
        return (
            <span className="text-muted ms-1" style={{ fontSize: size === 'sm' ? '0.75rem' : '0.85rem' }}>
                {trend.arrow}
            </span>
        );
    }

    const renderTooltip = (props) => (
        <Tooltip id="trend-tooltip" {...props}>
            <div className="text-start">
                <strong>{trend.message}</strong>
                <div className="mt-1">
                    <small>
                        Changed from {previous.toFixed(1)} to {current.toFixed(1)}
                    </small>
                </div>
                <div>
                    <small>
                        {formatDelta(trend.deltaRaw, true, 1)} {unit} ({formatDeltaPercent(trend.deltaPercent, false)})
                    </small>
                </div>
            </div>
        </Tooltip>
    );

    return (
        <OverlayTrigger
            placement="top"
            overlay={renderTooltip}
            delay={{ show: 250, hide: 400 }}
        >
            <span
                className="ms-1 d-inline-flex align-items-center gap-1"
                style={{
                    color: trend.color,
                    fontSize: size === 'sm' ? '0.75rem' : '0.85rem',
                    cursor: 'help',
                    fontWeight: 500
                }}
            >
                <span>{trend.arrow}</span>
                {showDelta && (
                    <span>
                        {formatDelta(trend.deltaRaw, true, 1)}
                        {showPercent && ` (${formatDeltaPercent(trend.deltaPercent, false)})`}
                    </span>
                )}
            </span>
        </OverlayTrigger>
    );
};

/**
 * RiskTrendIndicator - Convenience wrapper for risk scores
 */
export const RiskTrendIndicator = ({ student, showDelta = true }) => {
    const current = student.risk_score;
    const previous = getPreviousRiskScore(student);

    return (
        <TrendIndicator
            current={current}
            previous={previous}
            metricType="risk"
            unit="pts"
            showDelta={showDelta}
            showPercent={false}
        />
    );
};

/**
 * AttendanceTrendIndicator - Convenience wrapper for attendance
 */
export const AttendanceTrendIndicator = ({ student, showDelta = true }) => {
    const current = student.attendance || 75;
    const previous = getPreviousAttendance(student);

    return (
        <TrendIndicator
            current={current}
            previous={previous}
            metricType="attendance"
            unit="%"
            showDelta={showDelta}
            showPercent={false}
        />
    );
};

export default TrendIndicator;
