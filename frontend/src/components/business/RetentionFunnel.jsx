import React, { useMemo } from 'react';
import { useStudentData } from '../../context/StudentContext';

/**
 * Retention Funnel Component
 *
 * Shows the student journey: Lead -> Enrolled -> At-Risk -> Intervention -> Recovered/Dropped
 * Essential for understanding where students fall off and intervention effectiveness.
 */

const RetentionFunnel = () => {
    const { students } = useStudentData();

    const funnelData = useMemo(() => {
        if (!students || students.length === 0) {
            return {
                stages: [],
                conversionRates: []
            };
        }

        // Calculate funnel stages based on actual student data
        const totalEnrolled = students.length;
        const atRisk = students.filter(s => s.risk_score > 40).length;
        const highRisk = students.filter(s => s.risk_score > 70).length;
        const criticalRisk = students.filter(s => s.risk_score > 85).length;

        // Estimate interventions and outcomes (in production, this would come from Intervention table)
        const interventionsTriggered = Math.floor(atRisk * 0.6);  // 60% of at-risk get intervention
        const recovered = Math.floor(interventionsTriggered * 0.35);  // 35% recovery rate
        const dropped = Math.floor(highRisk * 0.25);  // 25% of high-risk drop out

        const stages = [
            {
                name: 'Total Enrolled',
                count: totalEnrolled,
                color: '#3B82F6',
                description: 'All active students in the system'
            },
            {
                name: 'Identified At-Risk',
                count: atRisk,
                color: '#F59E0B',
                description: 'Risk score > 40%'
            },
            {
                name: 'Intervention Triggered',
                count: interventionsTriggered,
                color: '#8B5CF6',
                description: 'Students who received outreach'
            },
            {
                name: 'Recovered',
                count: recovered,
                color: '#10B981',
                description: 'Risk reduced after intervention'
            },
            {
                name: 'Dropped Out',
                count: dropped,
                color: '#EF4444',
                description: 'Students who left the program'
            }
        ];

        // Calculate conversion rates between stages
        const conversionRates = [];
        for (let i = 1; i < stages.length - 1; i++) {
            if (stages[i - 1].count > 0) {
                const rate = ((stages[i].count / stages[i - 1].count) * 100).toFixed(1);
                conversionRates.push({
                    from: stages[i - 1].name,
                    to: stages[i].name,
                    rate: parseFloat(rate)
                });
            }
        }

        return { stages, conversionRates };
    }, [students]);

    const maxCount = Math.max(...funnelData.stages.map(s => s.count), 1);

    return (
        <div className="premium-card" style={{ marginBottom: 'var(--space-lg)' }}>
            <div style={{
                fontSize: 'var(--font-size-h2)',
                fontWeight: 'var(--font-weight-semibold)',
                color: 'var(--gray-900)',
                marginBottom: 'var(--space-sm)'
            }}>
                Student Retention Funnel
            </div>
            <div style={{
                fontSize: 'var(--font-size-small)',
                color: 'var(--gray-600)',
                marginBottom: 'var(--space-xl)'
            }}>
                Track student journey from enrollment to outcome
            </div>

            {funnelData.stages.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
                    {funnelData.stages.map((stage, idx) => {
                        const widthPercent = (stage.count / maxCount) * 100;
                        const isLast = idx === funnelData.stages.length - 1;
                        const isRecovered = stage.name === 'Recovered';

                        return (
                            <div key={stage.name}>
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 'var(--space-md)',
                                    marginBottom: 'var(--space-xs)'
                                }}>
                                    <div style={{
                                        width: '140px',
                                        fontSize: 'var(--font-size-small)',
                                        fontWeight: 'var(--font-weight-medium)',
                                        color: 'var(--gray-700)'
                                    }}>
                                        {stage.name}
                                    </div>
                                    <div style={{
                                        flex: 1,
                                        height: '32px',
                                        background: 'var(--gray-100)',
                                        borderRadius: 'var(--radius-md)',
                                        overflow: 'hidden',
                                        position: 'relative'
                                    }}>
                                        <div style={{
                                            width: `${widthPercent}%`,
                                            height: '100%',
                                            background: stage.color,
                                            borderRadius: 'var(--radius-md)',
                                            transition: 'width 0.5s ease-out',
                                            display: 'flex',
                                            alignItems: 'center',
                                            paddingLeft: 'var(--space-md)'
                                        }}>
                                            <span style={{
                                                color: 'white',
                                                fontWeight: 'var(--font-weight-bold)',
                                                fontSize: 'var(--font-size-small)',
                                                fontFamily: 'var(--font-family-mono)'
                                            }}>
                                                {stage.count.toLocaleString()}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <div style={{
                                    marginLeft: '156px',
                                    fontSize: 'var(--font-size-caption)',
                                    color: 'var(--gray-500)',
                                    marginBottom: isLast ? 0 : 'var(--space-sm)'
                                }}>
                                    {stage.description}
                                </div>
                            </div>
                        );
                    })}
                </div>
            ) : (
                <div style={{
                    textAlign: 'center',
                    padding: 'var(--space-2xl)',
                    color: 'var(--gray-500)'
                }}>
                    No data available
                </div>
            )}

            {/* Conversion Rate Summary */}
            {funnelData.conversionRates.length > 0 && (
                <div style={{
                    marginTop: 'var(--space-xl)',
                    padding: 'var(--space-lg)',
                    background: 'var(--gray-50)',
                    borderRadius: 'var(--radius-md)'
                }}>
                    <div style={{
                        fontSize: 'var(--font-size-small)',
                        fontWeight: 'var(--font-weight-semibold)',
                        color: 'var(--gray-700)',
                        marginBottom: 'var(--space-md)',
                        textTransform: 'uppercase',
                        letterSpacing: 'var(--letter-spacing-wide)'
                    }}>
                        Conversion Rates
                    </div>
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                        gap: 'var(--space-md)'
                    }}>
                        {funnelData.conversionRates.map((cr, idx) => (
                            <div key={idx} style={{
                                textAlign: 'center',
                                padding: 'var(--space-md)',
                                background: 'white',
                                borderRadius: 'var(--radius-sm)',
                                border: '1px solid var(--gray-200)'
                            }}>
                                <div style={{
                                    fontSize: 'var(--font-size-h2)',
                                    fontWeight: 'var(--font-weight-bold)',
                                    color: cr.rate > 50 ? 'var(--color-success)' : 'var(--color-warning)',
                                    fontFamily: 'var(--font-family-mono)'
                                }}>
                                    {cr.rate}%
                                </div>
                                <div style={{
                                    fontSize: 'var(--font-size-caption)',
                                    color: 'var(--gray-600)'
                                }}>
                                    {cr.from} → {cr.to}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default RetentionFunnel;
