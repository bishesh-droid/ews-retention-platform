import React, { useState, useEffect } from 'react';

/**
 * Intervention Effectiveness Ranking Component
 * 
 * BENEFIT: Data-driven ranking of which interventions work best
 * EXCLUSIVITY: Causal inference modeling from historical intervention data
 * USER TYPE: Faculty / Counselors
 * LOCATION: Intervention planning dashboard
 */

const InterventionEffectiveness = ({ historicalData }) => {
    const [rankedInterventions, setRankedInterventions] = useState([]);
    const [filters, setFilters] = useState({
        riskLevel: 'all',
        timeframe: '6months'
    });

    useEffect(() => {
        if (historicalData) {
            processInterventionData(historicalData);
        } else {
            // Mock ranked interventions with effectiveness metrics
            setRankedInterventions([
                {
                    name: 'Weekly One-on-One Check-ins',
                    effectiveness: 82,
                    sampleSize: 45,
                    avgImprovement: 18,
                    confidence: 0.92,
                    timeToImpact: '2 weeks'
                },
                {
                    name: 'Peer Tutoring Program',
                    effectiveness: 76,
                    sampleSize: 38,
                    avgImprovement: 15,
                    confidence: 0.88,
                    timeToImpact: '3 weeks'
                },
                {
                    name: 'Study Skills Workshop',
                    effectiveness: 68,
                    sampleSize: 52,
                    avgImprovement: 12,
                    confidence: 0.85,
                    timeToImpact: '4 weeks'
                },
                {
                    name: 'Extended Assignment Deadlines',
                    effectiveness: 54,
                    sampleSize: 29,
                    avgImprovement: 8,
                    confidence: 0.71,
                    timeToImpact: '1 week'
                },
                {
                    name: 'Academic Advisor Meeting',
                    effectiveness: 48,
                    sampleSize: 67,
                    avgImprovement: 6,
                    confidence: 0.79,
                    timeToImpact: '3 weeks'
                }
            ]);
        }
    }, [historicalData, filters]);

    const processInterventionData = (data) => {
        // Process and rank interventions based on effectiveness
        // In production, this would use causal inference models
        setRankedInterventions(data);
    };

    const getRankColor = (rank) => {
        if (rank === 1) return 'var(--color-success)';
        if (rank === 2) return 'var(--faculty-accent)';
        if (rank === 3) return 'var(--student-primary)';
        return 'var(--gray-500)';
    };

    return (
        <div className="premium-card faculty-context" style={{ marginBottom: 'var(--space-lg)' }}>
            {/* Header - H2, semibold */}
            <div className="section-header" style={{
                fontSize: 'var(--font-size-h2)',
                fontWeight: 'var(--font-weight-semibold)',
                color: 'var(--faculty-primary)',
                marginBottom: 'var(--space-sm)'
            }}>
                Intervention Effectiveness Rankings
            </div>

            <div style={{
                fontSize: 'var(--font-size-small)',
                color: 'var(--gray-600)',
                marginBottom: 'var(--space-lg)',
                lineHeight: 'var(--line-height-relaxed)'
            }}>
                Based on historical outcomes, here are the most effective interventions for improving student retention.
            </div>

            {/* Filters */}
            <div style={{
                display: 'flex',
                gap: 'var(--space-md)',
                marginBottom: 'var(--space-lg)',
                flexWrap: 'wrap'
            }}>
                <select
                    value={filters.riskLevel}
                    onChange={(e) => setFilters({ ...filters, riskLevel: e.target.value })}
                    style={{
                        padding: 'var(--space-sm) var(--space-md)',
                        fontSize: 'var(--font-size-small)',
                        border: 'var(--border-width-thin) solid var(--gray-300)',
                        borderRadius: 'var(--radius-md)',
                        background: 'white',
                        cursor: 'pointer'
                    }}
                >
                    <option value="all">All Risk Levels</option>
                    <option value="high">High Risk Only</option>
                    <option value="medium">Medium Risk Only</option>
                    <option value="low">Low Risk Only</option>
                </select>

                <select
                    value={filters.timeframe}
                    onChange={(e) => setFilters({ ...filters, timeframe: e.target.value })}
                    style={{
                        padding: 'var(--space-sm) var(--space-md)',
                        fontSize: 'var(--font-size-small)',
                        border: 'var(--border-width-thin) solid var(--gray-300)',
                        borderRadius: 'var(--radius-md)',
                        background: 'white',
                        cursor: 'pointer'
                    }}
                >
                    <option value="3months">Last 3 Months</option>
                    <option value="6months">Last 6 Months</option>
                    <option value="1year">Last Year</option>
                    <option value="all">All Time</option>
                </select>
            </div>

            {/* Ranked Interventions */}
            <div>
                {rankedInterventions.map((intervention, idx) => (
                    <InterventionCard
                        key={idx}
                        rank={idx + 1}
                        intervention={intervention}
                        rankColor={getRankColor(idx + 1)}
                    />
                ))}
            </div>
        </div>
    );
};

const InterventionCard = ({ rank, intervention, rankColor }) => (
    <div style={{
        display: 'flex',
        padding: 'var(--space-lg)',
        background: 'white',
        border: 'var(--border-width-thin) solid var(--gray-200)',
        borderRadius: 'var(--radius-md)',
        marginBottom: 'var(--space-md)',
        transition: 'all var(--transition-fast)',
        cursor: 'pointer'
    }}
        onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow = 'var(--shadow-md)';
            e.currentTarget.style.transform = 'translateY(-2px)';
        }}
        onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow = 'none';
            e.currentTarget.style.transform = 'translateY(0)';
        }}
    >
        {/* Ranking Number - H1, bold, distinct color */}
        <div style={{
            marginRight: 'var(--space-lg)',
            minWidth: '60px',
            textAlign: 'center'
        }}>
            <div style={{
                fontSize: 'var(--font-size-display)',
                fontWeight: 'var(--font-weight-extrabold)',
                color: rankColor,
                fontFamily: 'var(--font-family-mono)',
                lineHeight: '1'
            }}>
                {rank}
            </div>
            {rank <= 3 && (
                <div style={{ fontSize: 'var(--font-size-caption)', color: 'var(--gray-500)' }}>
                    {rank === 1 ? '🥇' : rank === 2 ? '🥈' : '🥉'}
                </div>
            )}
        </div>

        {/* Intervention Details */}
        <div style={{ flex: 1 }}>
            {/* Intervention Name - Body, semibold */}
            <div style={{
                fontSize: 'var(--font-size-body)',
                fontWeight: 'var(--font-weight-semibold)',
                color: 'var(--gray-900)',
                marginBottom: 'var(--space-sm)'
            }}>
                {intervention.name}
            </div>

            {/* Metrics Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))',
                gap: 'var(--space-md)',
                marginTop: 'var(--space-md)'
            }}>
                <MetricDisplay
                    label="Effectiveness"
                    value={`${intervention.effectiveness}%`}
                    highlight={true}
                />
                <MetricDisplay
                    label="Avg Improvement"
                    value={`+${intervention.avgImprovement}%`}
                />
                <MetricDisplay
                    label="Sample Size"
                    value={intervention.sampleSize}
                />
                <MetricDisplay
                    label="Confidence"
                    value={`${(intervention.confidence * 100).toFixed(0)}%`}
                />
                <MetricDisplay
                    label="Time to Impact"
                    value={intervention.timeToImpact}
                />
            </div>
        </div>
    </div>
);

const MetricDisplay = ({ label, value, highlight }) => (
    <div>
        <div style={{
            fontSize: 'var(--font-size-caption)',
            color: 'var(--gray-600)',
            textTransform: 'uppercase',
            letterSpacing: 'var(--letter-spacing-wide)',
            marginBottom: 'var(--space-xs)'
        }}>
            {label}
        </div>
        <div style={{
            fontSize: highlight ? 'var(--font-size-h2)' : 'var(--font-size-body)',
            fontWeight: highlight ? 'var(--font-weight-bold)' : 'var(--font-weight-semibold)',
            color: highlight ? 'var(--faculty-accent)' : 'var(--gray-800)',
            fontFamily: 'var(--font-family-mono)'
        }}>
            {value}
        </div>
    </div>
);

export default InterventionEffectiveness;
