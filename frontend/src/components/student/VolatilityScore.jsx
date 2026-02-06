import React, { useState, useEffect } from 'react';

/**
 * Behavioral Volatility Score Component
 * 
 * BENEFIT: Detect erratic behavior patterns (high variance in engagement)
 * EXCLUSIVITY: Time-series variance analysis
 * USER TYPE: Faculty / Counselors
 * LOCATION: Student detail view, early warning alerts
 */

const VolatilityScore = ({ studentId, engagementHistory }) => {
    const [volatilityScore, setVolatilityScore] = useState(0);
    const [pattern, setPattern] = useState('');
    const [recentSpikes, setRecentSpikes] = useState([]);

    useEffect(() => {
        if (engagementHistory && engagementHistory.length > 0) {
            calculateVolatility(engagementHistory);
        } else {
            // Mock data
            setVolatilityScore(68);
            setPattern('High Variance');
            setRecentSpikes([
                { date: '2024-01-28', type: 'Drop', magnitude: -35 },
                { date: '2024-01-25', type: 'Spike', magnitude: +42 },
                { date: '2024-01-20', type: 'Drop', magnitude: -28 }
            ]);
        }
    }, [engagementHistory]);

    const calculateVolatility = (history) => {
        // Calculate standard deviation of engagement levels
        const values = history.map(h => h.engagementLevel);
        const mean = values.reduce((sum, v) => sum + v, 0) / values.length;
        const variance = values.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / values.length;
        const stdDev = Math.sqrt(variance);

        // Normalize to 0-100 score
        const volatility = Math.min(100, (stdDev / mean) * 100);
        setVolatilityScore(Math.round(volatility));

        // Determine pattern
        if (volatility > 60) setPattern('High Variance');
        else if (volatility > 30) setPattern('Moderate Fluctuation');
        else setPattern('Stable');
    };

    const getVolatilityColor = () => {
        if (volatilityScore >= 60) return 'var(--student-warning)'; // Subtle orange, not alarming
        if (volatilityScore >= 30) return 'var(--student-primary)';
        return 'var(--student-success)';
    };

    return (
        <div className="premium-card faculty-context" style={{ marginBottom: 'var(--space-lg)' }}>
            {/* Header */}
            <div className="section-header" style={{
                fontSize: 'var(--font-size-h3)',
                fontWeight: 'var(--font-weight-semibold)',
                color: 'var(--faculty-primary)',
                marginBottom: 'var(--space-md)'
            }}>
                Engagement Volatility
            </div>

            {/* Volatility Indicator - H2, bold, subtle orange (not alarming) */}
            <div style={{
                textAlign: 'center',
                padding: 'var(--space-xl)',
                background: `${getVolatilityColor()}10`,
                borderRadius: 'var(--radius-lg)',
                marginBottom: 'var(--space-lg)'
            }}>
                <div style={{
                    fontSize: 'var(--font-size-h2)',
                    fontWeight: 'var(--font-weight-bold)',
                    color: getVolatilityColor(),
                    fontFamily: 'var(--font-family-mono)',
                    marginBottom: 'var(--space-sm)'
                }}>
                    {volatilityScore}
                    <span style={{ fontSize: 'var(--font-size-body)', fontWeight: 'var(--font-weight-medium)' }}>/100</span>
                </div>

                {/* Description - Body, regular, increased letter-spacing for emphasis */}
                <div style={{
                    fontSize: 'var(--font-size-body)',
                    fontWeight: 'var(--font-weight-regular)',
                    color: 'var(--gray-700)',
                    letterSpacing: 'var(--letter-spacing-wide)'
                }}>
                    {pattern}
                </div>
            </div>

            {/* Explanation */}
            <div style={{
                fontSize: 'var(--font-size-small)',
                color: 'var(--gray-600)',
                marginBottom: 'var(--space-md)',
                lineHeight: 'var(--line-height-relaxed)',
                fontStyle: 'italic'
            }}>
                Volatility measures inconsistency in engagement patterns. High volatility may indicate external stressors or unstable routines.
            </div>

            {/* Recent Spikes/Drops */}
            {recentSpikes.length > 0 && (
                <div>
                    <div className="data-label" style={{
                        fontSize: 'var(--font-size-small)',
                        fontWeight: 'var(--font-weight-semibold)',
                        color: 'var(--gray-600)',
                        textTransform: 'uppercase',
                        marginBottom: 'var(--space-sm)'
                    }}>
                        Recent Fluctuations
                    </div>

                    {recentSpikes.map((spike, idx) => (
                        <div key={idx} style={{
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            padding: 'var(--space-sm) var(--space-md)',
                            background: 'white',
                            border: 'var(--border-width-thin) solid var(--gray-200)',
                            borderRadius: 'var(--radius-sm)',
                            marginBottom: 'var(--space-xs)'
                        }}>
                            <span style={{
                                fontSize: 'var(--font-size-small)',
                                color: 'var(--gray-700)'
                            }}>
                                {new Date(spike.date).toLocaleDateString()}
                            </span>
                            <span style={{
                                fontSize: 'var(--font-size-small)',
                                fontWeight: 'var(--font-weight-semibold)',
                                color: spike.type === 'Spike' ? 'var(--color-success)' : 'var(--student-warning)'
                            }}>
                                {spike.type} {spike.magnitude > 0 ? '+' : ''}{spike.magnitude}%
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default VolatilityScore;
