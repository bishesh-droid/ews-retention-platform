import React, { useMemo } from 'react';
import { useStudentData } from '../../context/StudentContext';

/**
 * Sales & Academic Alignment Component
 *
 * Shows how well sales and academic teams coordinate on retention efforts.
 * Key for organizations where both teams share responsibility.
 */

const SalesAcademicAlignment = () => {
    const { students } = useStudentData();

    const alignmentData = useMemo(() => {
        if (!students || students.length === 0) {
            return null;
        }

        const highRiskStudents = students.filter(s => s.risk_score > 70);
        const criticalStudents = students.filter(s => s.risk_score > 85);

        // Simulated alignment metrics (in production, from intervention/activity logs)
        const totalCases = highRiskStudents.length;
        const salesHandled = Math.floor(totalCases * 0.45);
        const facultyHandled = Math.floor(totalCases * 0.35);
        const jointHandled = Math.floor(totalCases * 0.15);
        const unassigned = totalCases - salesHandled - facultyHandled - jointHandled;

        return {
            overallScore: 84,  // 0-100 alignment score
            trend: '+3.2',  // vs last period
            metrics: {
                avgResponseTime: '2.4 hours',
                avgResponseTrend: '-15min',
                escalationsToFaculty: 45,
                escalationTrend: -8,
                sharedCasesResolved: 38,
                resolutionTrend: +5,
                communicationScore: 91,
                communicationTrend: '+2'
            },
            caseDistribution: {
                salesOwned: salesHandled,
                facultyOwned: facultyHandled,
                jointOwnership: jointHandled,
                unassigned: unassigned,
                total: totalCases
            },
            teamPerformance: [
                {
                    team: 'Sales Team',
                    casesHandled: salesHandled,
                    avgResolutionDays: 3.2,
                    successRate: 72,
                    satisfaction: 4.1
                },
                {
                    team: 'Faculty Advisors',
                    casesHandled: facultyHandled,
                    avgResolutionDays: 5.1,
                    successRate: 68,
                    satisfaction: 4.4
                },
                {
                    team: 'Joint Team',
                    casesHandled: jointHandled,
                    avgResolutionDays: 4.5,
                    successRate: 85,
                    satisfaction: 4.6
                }
            ],
            bottlenecks: [
                { issue: 'Handoff delays between teams', severity: 'medium', count: 12 },
                { issue: 'Missing student contact info', severity: 'low', count: 8 },
                { issue: 'Unclear escalation criteria', severity: 'high', count: 5 }
            ]
        };
    }, [students]);

    if (!alignmentData) {
        return (
            <div className="premium-card business-context">
                <div style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--gray-500)' }}>
                    No data available
                </div>
            </div>
        );
    }

    const getSeverityColor = (severity) => {
        switch (severity) {
            case 'high': return 'var(--color-error)';
            case 'medium': return 'var(--color-warning)';
            case 'low': return 'var(--color-info)';
            default: return 'var(--gray-500)';
        }
    };

    return (
        <div className="premium-card business-context" style={{ marginBottom: 'var(--space-lg)' }}>
            <div style={{
                fontSize: 'var(--font-size-h2)',
                fontWeight: 'var(--font-weight-semibold)',
                color: 'var(--business-primary)',
                marginBottom: 'var(--space-sm)'
            }}>
                Sales & Academic Alignment
            </div>
            <div style={{
                fontSize: 'var(--font-size-small)',
                color: 'var(--gray-600)',
                marginBottom: 'var(--space-xl)'
            }}>
                Coordination metrics between retention teams
            </div>

            {/* Alignment Score Banner */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: 'var(--space-xl)',
                background: alignmentData.overallScore >= 80
                    ? 'linear-gradient(135deg, #10B981, #059669)'
                    : alignmentData.overallScore >= 60
                        ? 'linear-gradient(135deg, #F59E0B, #D97706)'
                        : 'linear-gradient(135deg, #EF4444, #DC2626)',
                borderRadius: 'var(--radius-lg)',
                color: 'white',
                marginBottom: 'var(--space-xl)'
            }}>
                <div>
                    <div style={{
                        fontSize: 'var(--font-size-caption)',
                        fontWeight: 'var(--font-weight-semibold)',
                        textTransform: 'uppercase',
                        letterSpacing: 'var(--letter-spacing-wider)',
                        opacity: 0.9,
                        marginBottom: 'var(--space-xs)'
                    }}>
                        Overall Alignment Score
                    </div>
                    <div style={{
                        fontSize: 'var(--font-size-display)',
                        fontWeight: 'var(--font-weight-extrabold)',
                        fontFamily: 'var(--font-family-mono)'
                    }}>
                        {alignmentData.overallScore}/100
                    </div>
                </div>
                <div style={{
                    textAlign: 'right'
                }}>
                    <div style={{
                        fontSize: 'var(--font-size-h2)',
                        fontWeight: 'var(--font-weight-bold)'
                    }}>
                        {alignmentData.trend.startsWith('+') ? '↑' : '↓'} {alignmentData.trend}
                    </div>
                    <div style={{
                        fontSize: 'var(--font-size-small)',
                        opacity: 0.9
                    }}>
                        vs last quarter
                    </div>
                </div>
            </div>

            {/* Key Metrics Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(4, 1fr)',
                gap: 'var(--space-md)',
                marginBottom: 'var(--space-xl)'
            }}>
                <MetricCard
                    label="Avg Response Time"
                    value={alignmentData.metrics.avgResponseTime}
                    trend={alignmentData.metrics.avgResponseTrend}
                    isGoodTrend={true}
                />
                <MetricCard
                    label="Escalations to Faculty"
                    value={alignmentData.metrics.escalationsToFaculty}
                    trend={`${alignmentData.metrics.escalationTrend}`}
                    isGoodTrend={alignmentData.metrics.escalationTrend < 0}
                />
                <MetricCard
                    label="Shared Cases Resolved"
                    value={alignmentData.metrics.sharedCasesResolved}
                    trend={`+${alignmentData.metrics.resolutionTrend}`}
                    isGoodTrend={true}
                />
                <MetricCard
                    label="Communication Score"
                    value={`${alignmentData.metrics.communicationScore}%`}
                    trend={alignmentData.metrics.communicationTrend}
                    isGoodTrend={true}
                />
            </div>

            {/* Case Distribution */}
            <div style={{ marginBottom: 'var(--space-xl)' }}>
                <div style={{
                    fontSize: 'var(--font-size-small)',
                    fontWeight: 'var(--font-weight-semibold)',
                    color: 'var(--gray-700)',
                    marginBottom: 'var(--space-md)',
                    textTransform: 'uppercase',
                    letterSpacing: 'var(--letter-spacing-wide)'
                }}>
                    Case Distribution ({alignmentData.caseDistribution.total} total)
                </div>
                <div style={{
                    display: 'flex',
                    height: '24px',
                    borderRadius: 'var(--radius-full)',
                    overflow: 'hidden',
                    marginBottom: 'var(--space-sm)'
                }}>
                    <div style={{
                        width: `${(alignmentData.caseDistribution.salesOwned / alignmentData.caseDistribution.total) * 100}%`,
                        background: '#3B82F6',
                        transition: 'width 0.3s ease'
                    }} />
                    <div style={{
                        width: `${(alignmentData.caseDistribution.facultyOwned / alignmentData.caseDistribution.total) * 100}%`,
                        background: '#8B5CF6',
                        transition: 'width 0.3s ease'
                    }} />
                    <div style={{
                        width: `${(alignmentData.caseDistribution.jointOwnership / alignmentData.caseDistribution.total) * 100}%`,
                        background: '#10B981',
                        transition: 'width 0.3s ease'
                    }} />
                    <div style={{
                        width: `${(alignmentData.caseDistribution.unassigned / alignmentData.caseDistribution.total) * 100}%`,
                        background: '#EF4444',
                        transition: 'width 0.3s ease'
                    }} />
                </div>
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    fontSize: 'var(--font-size-caption)',
                    color: 'var(--gray-600)'
                }}>
                    <span><span style={{ color: '#3B82F6' }}>●</span> Sales ({alignmentData.caseDistribution.salesOwned})</span>
                    <span><span style={{ color: '#8B5CF6' }}>●</span> Faculty ({alignmentData.caseDistribution.facultyOwned})</span>
                    <span><span style={{ color: '#10B981' }}>●</span> Joint ({alignmentData.caseDistribution.jointOwnership})</span>
                    <span><span style={{ color: '#EF4444' }}>●</span> Unassigned ({alignmentData.caseDistribution.unassigned})</span>
                </div>
            </div>

            {/* Team Performance Table */}
            <div style={{ marginBottom: 'var(--space-xl)' }}>
                <div style={{
                    fontSize: 'var(--font-size-small)',
                    fontWeight: 'var(--font-weight-semibold)',
                    color: 'var(--gray-700)',
                    marginBottom: 'var(--space-md)',
                    textTransform: 'uppercase',
                    letterSpacing: 'var(--letter-spacing-wide)'
                }}>
                    Team Performance Comparison
                </div>
                <table className="data-table" style={{ width: '100%' }}>
                    <thead>
                        <tr>
                            <th>Team</th>
                            <th>Cases</th>
                            <th>Avg Resolution</th>
                            <th>Success Rate</th>
                            <th>Satisfaction</th>
                        </tr>
                    </thead>
                    <tbody>
                        {alignmentData.teamPerformance.map((team, idx) => (
                            <tr key={idx}>
                                <td style={{ fontWeight: 'var(--font-weight-medium)' }}>{team.team}</td>
                                <td style={{ fontFamily: 'var(--font-family-mono)' }}>{team.casesHandled}</td>
                                <td style={{ fontFamily: 'var(--font-family-mono)' }}>{team.avgResolutionDays} days</td>
                                <td>
                                    <span style={{
                                        padding: '2px 8px',
                                        borderRadius: 'var(--radius-full)',
                                        background: team.successRate >= 80 ? '#D1FAE5' : team.successRate >= 60 ? '#FEF3C7' : '#FEE2E2',
                                        color: team.successRate >= 80 ? '#065F46' : team.successRate >= 60 ? '#92400E' : '#991B1B',
                                        fontWeight: 'var(--font-weight-semibold)',
                                        fontSize: 'var(--font-size-small)'
                                    }}>
                                        {team.successRate}%
                                    </span>
                                </td>
                                <td style={{ fontFamily: 'var(--font-family-mono)' }}>{team.satisfaction}/5.0</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Bottlenecks */}
            <div>
                <div style={{
                    fontSize: 'var(--font-size-small)',
                    fontWeight: 'var(--font-weight-semibold)',
                    color: 'var(--gray-700)',
                    marginBottom: 'var(--space-md)',
                    textTransform: 'uppercase',
                    letterSpacing: 'var(--letter-spacing-wide)'
                }}>
                    Identified Bottlenecks
                </div>
                {alignmentData.bottlenecks.map((item, idx) => (
                    <div key={idx} style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: 'var(--space-md)',
                        background: idx % 2 === 0 ? 'var(--gray-50)' : 'white',
                        borderRadius: 'var(--radius-sm)',
                        borderLeft: `3px solid ${getSeverityColor(item.severity)}`
                    }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
                            <span style={{
                                padding: '2px 8px',
                                borderRadius: 'var(--radius-sm)',
                                background: getSeverityColor(item.severity),
                                color: 'white',
                                fontSize: 'var(--font-size-caption)',
                                fontWeight: 'var(--font-weight-semibold)',
                                textTransform: 'uppercase'
                            }}>
                                {item.severity}
                            </span>
                            <span style={{ fontSize: 'var(--font-size-small)', color: 'var(--gray-700)' }}>
                                {item.issue}
                            </span>
                        </div>
                        <span style={{
                            fontSize: 'var(--font-size-body)',
                            fontWeight: 'var(--font-weight-semibold)',
                            fontFamily: 'var(--font-family-mono)',
                            color: 'var(--gray-900)'
                        }}>
                            {item.count} cases
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
};

const MetricCard = ({ label, value, trend, isGoodTrend }) => (
    <div style={{
        padding: 'var(--space-md)',
        background: 'var(--gray-50)',
        borderRadius: 'var(--radius-md)',
        textAlign: 'center'
    }}>
        <div style={{
            fontSize: 'var(--font-size-caption)',
            color: 'var(--gray-600)',
            marginBottom: 'var(--space-xs)',
            textTransform: 'uppercase',
            letterSpacing: 'var(--letter-spacing-wide)'
        }}>
            {label}
        </div>
        <div style={{
            fontSize: 'var(--font-size-h2)',
            fontWeight: 'var(--font-weight-bold)',
            fontFamily: 'var(--font-family-mono)',
            color: 'var(--gray-900)',
            marginBottom: 'var(--space-xs)'
        }}>
            {value}
        </div>
        <div style={{
            fontSize: 'var(--font-size-caption)',
            fontWeight: 'var(--font-weight-semibold)',
            color: isGoodTrend ? 'var(--color-success)' : 'var(--color-error)'
        }}>
            {trend}
        </div>
    </div>
);

export default SalesAcademicAlignment;
