import React, { useMemo } from 'react';
import { useStudentData } from '../../context/StudentContext';

/**
 * Cost Per Retained Student Component
 *
 * Shows the ROI of retention efforts by calculating cost efficiency.
 * Essential for justifying retention program investments to leadership.
 */

const CostPerRetainedStudent = () => {
    const { students } = useStudentData();

    const metrics = useMemo(() => {
        if (!students || students.length === 0) {
            return null;
        }

        const atRiskCount = students.filter(s => s.risk_score > 40).length;
        const highRiskCount = students.filter(s => s.risk_score > 70).length;

        // Cost assumptions (in production, these would come from config/API)
        const staffTimePerIntervention = 2.5;  // hours
        const hourlyStaffCost = 45;  // dollars
        const automatedToolCost = 5000;  // monthly platform cost
        const incentiveBudget = 25000;  // quarterly incentive pool
        const trainingCost = 3500;  // quarterly training costs

        // Calculate interventions (simplified model)
        const interventionsTriggered = Math.floor(atRiskCount * 0.6);
        const recoveredStudents = Math.floor(interventionsTriggered * 0.35);

        // Calculate costs
        const staffTimeCost = interventionsTriggered * staffTimePerIntervention * hourlyStaffCost;
        const toolingCost = automatedToolCost;
        const incentivesUsed = Math.min(incentiveBudget, recoveredStudents * 150);  // ~$150 per recovered
        const totalCost = staffTimeCost + toolingCost + incentivesUsed + trainingCost;

        // Calculate cost per retained student
        const costPerStudent = recoveredStudents > 0 ? totalCost / recoveredStudents : 0;

        // Revenue preserved (assume $12,500 LTV per student)
        const avgStudentLTV = 12500;
        const revenueSaved = recoveredStudents * avgStudentLTV;

        // ROI calculation
        const roi = totalCost > 0 ? ((revenueSaved - totalCost) / totalCost) * 100 : 0;

        return {
            totalCost,
            studentsRetained: recoveredStudents,
            costPerStudent: Math.round(costPerStudent),
            revenueSaved,
            roi: Math.round(roi * 10) / 10,
            breakdown: [
                { category: 'Staff Time', amount: Math.round(staffTimeCost), percentage: Math.round((staffTimeCost / totalCost) * 100) },
                { category: 'Platform & Tools', amount: toolingCost, percentage: Math.round((toolingCost / totalCost) * 100) },
                { category: 'Student Incentives', amount: Math.round(incentivesUsed), percentage: Math.round((incentivesUsed / totalCost) * 100) },
                { category: 'Training & Development', amount: trainingCost, percentage: Math.round((trainingCost / totalCost) * 100) }
            ],
            efficiency: {
                interventionsPerRecovery: recoveredStudents > 0 ? (interventionsTriggered / recoveredStudents).toFixed(1) : 'N/A',
                revenueMultiple: totalCost > 0 ? (revenueSaved / totalCost).toFixed(1) : 'N/A'
            }
        };
    }, [students]);

    if (!metrics) {
        return (
            <div className="premium-card business-context">
                <div style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--gray-500)' }}>
                    No data available
                </div>
            </div>
        );
    }

    return (
        <div className="premium-card business-context" style={{ marginBottom: 'var(--space-lg)' }}>
            <div style={{
                fontSize: 'var(--font-size-h2)',
                fontWeight: 'var(--font-weight-semibold)',
                color: 'var(--business-primary)',
                marginBottom: 'var(--space-sm)'
            }}>
                Cost per Retained Student
            </div>
            <div style={{
                fontSize: 'var(--font-size-small)',
                color: 'var(--gray-600)',
                marginBottom: 'var(--space-xl)'
            }}>
                Efficiency metrics for retention program investments
            </div>

            {/* Primary Metric */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 'var(--space-lg)',
                marginBottom: 'var(--space-xl)'
            }}>
                <div style={{
                    textAlign: 'center',
                    padding: 'var(--space-lg)',
                    background: 'linear-gradient(135deg, var(--business-primary), #1E1E5F)',
                    borderRadius: 'var(--radius-lg)',
                    color: 'white'
                }}>
                    <div style={{
                        fontSize: 'var(--font-size-caption)',
                        fontWeight: 'var(--font-weight-semibold)',
                        textTransform: 'uppercase',
                        letterSpacing: 'var(--letter-spacing-wider)',
                        opacity: 0.9,
                        marginBottom: 'var(--space-xs)'
                    }}>
                        Cost Per Student
                    </div>
                    <div style={{
                        fontSize: 'var(--font-size-display)',
                        fontWeight: 'var(--font-weight-extrabold)',
                        fontFamily: 'var(--font-family-mono)'
                    }}>
                        ${metrics.costPerStudent.toLocaleString()}
                    </div>
                </div>

                <div style={{
                    textAlign: 'center',
                    padding: 'var(--space-lg)',
                    background: 'linear-gradient(135deg, var(--business-growth), #047857)',
                    borderRadius: 'var(--radius-lg)',
                    color: 'white'
                }}>
                    <div style={{
                        fontSize: 'var(--font-size-caption)',
                        fontWeight: 'var(--font-weight-semibold)',
                        textTransform: 'uppercase',
                        letterSpacing: 'var(--letter-spacing-wider)',
                        opacity: 0.9,
                        marginBottom: 'var(--space-xs)'
                    }}>
                        Students Retained
                    </div>
                    <div style={{
                        fontSize: 'var(--font-size-display)',
                        fontWeight: 'var(--font-weight-extrabold)',
                        fontFamily: 'var(--font-family-mono)'
                    }}>
                        {metrics.studentsRetained}
                    </div>
                </div>

                <div style={{
                    textAlign: 'center',
                    padding: 'var(--space-lg)',
                    background: metrics.roi > 0
                        ? 'linear-gradient(135deg, #10B981, #059669)'
                        : 'linear-gradient(135deg, var(--color-warning), #D97706)',
                    borderRadius: 'var(--radius-lg)',
                    color: 'white'
                }}>
                    <div style={{
                        fontSize: 'var(--font-size-caption)',
                        fontWeight: 'var(--font-weight-semibold)',
                        textTransform: 'uppercase',
                        letterSpacing: 'var(--letter-spacing-wider)',
                        opacity: 0.9,
                        marginBottom: 'var(--space-xs)'
                    }}>
                        ROI
                    </div>
                    <div style={{
                        fontSize: 'var(--font-size-display)',
                        fontWeight: 'var(--font-weight-extrabold)',
                        fontFamily: 'var(--font-family-mono)'
                    }}>
                        {metrics.roi}x
                    </div>
                </div>
            </div>

            {/* Cost Breakdown */}
            <div style={{ marginBottom: 'var(--space-xl)' }}>
                <div style={{
                    fontSize: 'var(--font-size-small)',
                    fontWeight: 'var(--font-weight-semibold)',
                    color: 'var(--gray-700)',
                    marginBottom: 'var(--space-md)',
                    textTransform: 'uppercase',
                    letterSpacing: 'var(--letter-spacing-wide)'
                }}>
                    Cost Breakdown
                </div>
                {metrics.breakdown.map((item, idx) => (
                    <div key={idx} style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: 'var(--space-md)',
                        background: idx % 2 === 0 ? 'var(--gray-50)' : 'white',
                        borderRadius: 'var(--radius-sm)'
                    }}>
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 'var(--space-md)'
                        }}>
                            <div style={{
                                width: '60px',
                                height: '6px',
                                background: 'var(--gray-200)',
                                borderRadius: 'var(--radius-full)',
                                overflow: 'hidden'
                            }}>
                                <div style={{
                                    width: `${item.percentage}%`,
                                    height: '100%',
                                    background: 'var(--business-primary)',
                                    borderRadius: 'var(--radius-full)'
                                }} />
                            </div>
                            <span style={{
                                fontSize: 'var(--font-size-small)',
                                color: 'var(--gray-700)'
                            }}>
                                {item.category}
                            </span>
                        </div>
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 'var(--space-md)'
                        }}>
                            <span style={{
                                fontSize: 'var(--font-size-small)',
                                color: 'var(--gray-500)'
                            }}>
                                {item.percentage}%
                            </span>
                            <span style={{
                                fontSize: 'var(--font-size-body)',
                                fontWeight: 'var(--font-weight-semibold)',
                                fontFamily: 'var(--font-family-mono)',
                                color: 'var(--gray-900)',
                                minWidth: '80px',
                                textAlign: 'right'
                            }}>
                                ${item.amount.toLocaleString()}
                            </span>
                        </div>
                    </div>
                ))}
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    padding: 'var(--space-md)',
                    marginTop: 'var(--space-sm)',
                    borderTop: '2px solid var(--gray-200)',
                    fontWeight: 'var(--font-weight-bold)'
                }}>
                    <span>Total Investment</span>
                    <span style={{ fontFamily: 'var(--font-family-mono)' }}>
                        ${metrics.totalCost.toLocaleString()}
                    </span>
                </div>
            </div>

            {/* Efficiency Metrics */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 'var(--space-md)',
                padding: 'var(--space-lg)',
                background: 'var(--gray-50)',
                borderRadius: 'var(--radius-md)'
            }}>
                <div>
                    <div style={{
                        fontSize: 'var(--font-size-caption)',
                        color: 'var(--gray-600)',
                        marginBottom: 'var(--space-xs)'
                    }}>
                        Interventions per Recovery
                    </div>
                    <div style={{
                        fontSize: 'var(--font-size-h2)',
                        fontWeight: 'var(--font-weight-bold)',
                        fontFamily: 'var(--font-family-mono)',
                        color: 'var(--gray-900)'
                    }}>
                        {metrics.efficiency.interventionsPerRecovery}
                    </div>
                </div>
                <div>
                    <div style={{
                        fontSize: 'var(--font-size-caption)',
                        color: 'var(--gray-600)',
                        marginBottom: 'var(--space-xs)'
                    }}>
                        Revenue Multiple
                    </div>
                    <div style={{
                        fontSize: 'var(--font-size-h2)',
                        fontWeight: 'var(--font-weight-bold)',
                        fontFamily: 'var(--font-family-mono)',
                        color: 'var(--business-growth)'
                    }}>
                        {metrics.efficiency.revenueMultiple}x
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CostPerRetainedStudent;
