import React from 'react';
import './InterventionCard.css';

/**
 * InterventionCard Component
 * Displays recommended intervention based on risk threshold
 */
const InterventionCard = ({ recommendation, riskScore }) => {
    if (!recommendation) {
        return null;
    }

    const getThresholdColor = (category) => {
        const colors = {
            'low_risk': '#10b981',
            'gentle_reminder': '#f59e0b',
            'mentor_outreach': '#f97316',
            'urgent_intervention': '#ef4444'
        };
        return colors[category] || '#6b7280';
    };

    const getUrgencyIcon = (urgency) => {
        const icons = {
            'none': '✅',
            'low': '📬',
            'medium': '⚠️',
            'high': '🚨'
        };
        return icons[urgency] || '📋';
    };

    const getPriorityBadge = (priority) => {
        const badges = {
            'critical': { text: 'CRITICAL', class: 'priority-critical' },
            'high': { text: 'HIGH', class: 'priority-high' },
            'medium': { text: 'MEDIUM', class: 'priority-medium' },
            'low': { text: 'LOW', class: 'priority-low' }
        };
        return badges[priority] || badges['low'];
    };

    const thresholdColor = getThresholdColor(recommendation.threshold_category);
    const urgencyIcon = getUrgencyIcon(recommendation.urgency);
    const priorityBadge = getPriorityBadge(recommendation.priority);

    return (
        <div className="intervention-card" style={{ borderLeftColor: thresholdColor }}>
            <div className="intervention-header">
                <div className="intervention-title">
                    <span className="intervention-icon">{urgencyIcon}</span>
                    <h3>Recommended Intervention</h3>
                </div>
                {recommendation.priority && (
                    <span className={`priority-badge ${priorityBadge.class}`}>
                        {priorityBadge.text}
                    </span>
                )}
            </div>

            <div className="intervention-body">
                <div className="intervention-row">
                    <span className="intervention-label">Action Type:</span>
                    <span className="intervention-value">{recommendation.action_type.replace(/_/g, ' ').toUpperCase()}</span>
                </div>

                <div className="intervention-row">
                    <span className="intervention-label">Risk Threshold:</span>
                    <span className="intervention-value">{recommendation.threshold_category.replace(/_/g, ' ')}</span>
                </div>

                <div className="intervention-row">
                    <span className="intervention-label">Assigned Team:</span>
                    <span className="intervention-value team-badge">{recommendation.assigned_team}</span>
                </div>

                {recommendation.channels && recommendation.channels.length > 0 && (
                    <div className="intervention-row">
                        <span className="intervention-label">Communication Channels:</span>
                        <div className="channels-list">
                            {recommendation.channels.map((channel, idx) => (
                                <span key={idx} className="channel-badge">
                                    {channel.replace(/_/g, ' ')}
                                </span>
                            ))}
                        </div>
                    </div>
                )}

                <div className="intervention-description">
                    <p>{recommendation.description}</p>
                </div>
            </div>

            <div className="intervention-footer">
                <div className="risk-indicator">
                    <span className="risk-label">Current Risk Score:</span>
                    <span className="risk-value" style={{ color: thresholdColor }}>
                        {Math.round(riskScore)}%
                    </span>
                </div>
            </div>
        </div>
    );
};

export default InterventionCard;
