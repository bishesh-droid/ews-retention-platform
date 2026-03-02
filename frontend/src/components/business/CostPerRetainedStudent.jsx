import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Spinner } from 'react-bootstrap';
import { getInterventionRoiMetrics } from '../../services/api';

/**
 * Cost Per Retained Student Component
 *
 * Shows the ROI of retention efforts by calculating cost efficiency.
 * Essential for justifying retention program investments to leadership.
 */

const CostPerRetainedStudent = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [payload, setPayload] = useState(null);

    useEffect(() => {
        let isMounted = true;
        const load = async () => {
            setLoading(true);
            setError(null);
            const resp = await getInterventionRoiMetrics('quarterly');
            if (!isMounted) return;

            if (!resp.success) {
                setError(resp.message || 'Failed to load intervention ROI metrics.');
                setPayload(null);
                setLoading(false);
                return;
            }

            setPayload(resp.data || null);
            setLoading(false);
        };

        load();
        return () => {
            isMounted = false;
        };
    }, []);

    const metrics = useMemo(() => {
        if (!payload) return null;
        const totalCost = Number(payload.total_intervention_cost || 0);
        const studentsRetained = Number(payload.estimated_recovered || 0);
        const costPerStudent = Number(payload.cost_per_retained_student || 0);
        const revenueSaved = Number(payload.revenue_saved || 0);
        const roiMultiple = Number(payload.roi_multiple || 0);

        const breakdownObj = payload.breakdown && typeof payload.breakdown === 'object' ? payload.breakdown : {};
        const breakdown = [
            { category: 'Staff Time', amount: Number(breakdownObj.staff_time || 0) },
            { category: 'Platform & Tools', amount: Number(breakdownObj.platform_tools || 0) },
            { category: 'Student Incentives', amount: Number(breakdownObj.student_incentives || 0) },
            { category: 'Training & Development', amount: Number(breakdownObj.training || 0) },
        ];
        const total = breakdown.reduce((a, b) => a + (b.amount || 0), 0) || 1;

        return {
            totalCost,
            studentsRetained,
            costPerStudent: Math.round(costPerStudent),
            revenueSaved,
            roiMultiple,
            breakdown: breakdown.map((b) => ({
                ...b,
                amount: Math.round(b.amount || 0),
                percentage: Math.round(((b.amount || 0) / total) * 100),
            })),
            efficiency: {
                revenueMultiple: totalCost > 0 ? (revenueSaved / totalCost).toFixed(1) : 'N/A',
            },
        };
    }, [payload]);

    if (loading) {
        return (
            <div className="premium-card business-context">
                <div style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--gray-500)' }}>
                    <Spinner animation="border" size="sm" />
                    <div className="mt-2">Loading ROI metrics…</div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="premium-card business-context">
                <Alert variant="danger" className="mb-0">
                    {error}
                </Alert>
            </div>
        );
    }

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
                        ROI Multiple
                    </div>
                    <div style={{
                        fontSize: 'var(--font-size-display)',
                        fontWeight: 'var(--font-weight-extrabold)',
                        fontFamily: 'var(--font-family-mono)'
                    }}>
                        {Number(metrics.roiMultiple || 0).toFixed(2)}x
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
                        background: idx % 2 === 0 ? 'var(--gray-50)' : 'transparent',
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
