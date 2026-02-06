import React from 'react';
import './SignalBreakdown.css';

/**
 * SignalBreakdown Component
 * Displays the 5 signal categories as visual bars with scores
 */
const SignalBreakdown = ({ signals, showLabels = true }) => {
    const signalConfig = {
        academic_signal_score: {
            label: 'Academic Performance',
            color: '#3b82f6', // blue
            icon: '📚'
        },
        engagement_signal_score: {
            label: 'Engagement',
            color: '#10b981', // green
            icon: '🎯'
        },
        consistency_signal_score: {
            label: 'Consistency',
            color: '#f59e0b', // amber
            icon: '📊'
        },
        intent_signal_score: {
            label: 'Intent',
            color: '#8b5cf6', // purple
            icon: '💡'
        },
        responsiveness_signal_score: {
            label: 'Responsiveness',
            color: '#ec4899', // pink
            icon: '💬'
        }
    };

    if (!signals) {
        return <div className="signal-breakdown-empty">No signal data available</div>;
    }

    const getRiskLevel = (score) => {
        if (score < 0.3) return 'low';
        if (score < 0.6) return 'medium';
        return 'high';
    };

    return (
        <div className="signal-breakdown">
            {showLabels && <h3 className="signal-breakdown-title">Signal Breakdown</h3>}

            <div className="signal-bars">
                {Object.entries(signalConfig).map(([key, config]) => {
                    const score = signals[key] || 0;
                    const percentage = Math.round(score * 100);
                    const riskLevel = getRiskLevel(score);

                    return (
                        <div key={key} className="signal-item">
                            <div className="signal-header">
                                <span className="signal-icon">{config.icon}</span>
                                <span className="signal-label">{config.label}</span>
                                <span className={`signal-score signal-score-${riskLevel}`}>
                                    {percentage}%
                                </span>
                            </div>

                            <div className="signal-bar-container">
                                <div
                                    className={`signal-bar signal-bar-${riskLevel}`}
                                    style={{
                                        width: `${percentage}%`,
                                        backgroundColor: config.color
                                    }}
                                />
                            </div>
                        </div>
                    );
                })}
            </div>

            <div className="signal-legend">
                <div className="legend-item">
                    <span className="legend-dot legend-low"></span>
                    <span>Low Risk (&lt;30%)</span>
                </div>
                <div className="legend-item">
                    <span className="legend-dot legend-medium"></span>
                    <span>Medium Risk (30-60%)</span>
                </div>
                <div className="legend-item">
                    <span className="legend-dot legend-high"></span>
                    <span>High Risk (&gt;60%)</span>
                </div>
            </div>
        </div>
    );
};

export default SignalBreakdown;
