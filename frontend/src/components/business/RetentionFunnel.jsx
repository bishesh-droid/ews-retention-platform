import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Spinner } from 'react-bootstrap';
import { getRetentionFunnel } from '../../services/api';

/**
 * Retention Funnel Component
 *
 * Shows the student journey: Lead -> Enrolled -> At-Risk -> Intervention -> Recovered/Dropped
 * Essential for understanding where students fall off and intervention effectiveness.
 */

const RetentionFunnel = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [payload, setPayload] = useState(null);

    useEffect(() => {
        let isMounted = true;
        const load = async () => {
            setLoading(true);
            setError(null);
            const resp = await getRetentionFunnel('current_semester');
            if (!isMounted) return;

            if (!resp.success) {
                setError(resp.message || 'Failed to load retention funnel.');
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

    const funnelData = useMemo(() => {
        if (!payload) {
            return {
                stages: [],
                conversionRates: []
            };
        }

        const stagesRaw = Array.isArray(payload.stages) ? payload.stages : [];
        const conversionRaw = Array.isArray(payload.conversion_rates) ? payload.conversion_rates : [];

        const stages = stagesRaw.map((s) => ({
            name: s.name,
            count: Number(s.count || 0),
            color: s.color || '#8B5CF6',
            description: s.description,
        }));

        const conversionRates = conversionRaw.map((c) => ({
            from: c.from,
            to: c.to,
            rate: Number(c.rate || 0),
        }));

        return { stages, conversionRates };
    }, [payload]);

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

            {loading && (
                <div style={{ textAlign: 'center', padding: 'var(--space-2xl)', color: 'var(--gray-500)' }}>
                    <Spinner animation="border" size="sm" />
                    <div className="mt-2">Loading funnel…</div>
                </div>
            )}

            {error && (
                <Alert variant="danger" className="mb-0">
                    {error}
                </Alert>
            )}

            {!loading && !error && funnelData.stages.length > 0 ? (
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
                                    {stage.description || ''}
                                </div>
                            </div>
                        );
                    })}
                </div>
            ) : (
                !loading && !error ? (
                    <div style={{
                        textAlign: 'center',
                        padding: 'var(--space-2xl)',
                        color: 'var(--gray-500)'
                    }}>
                        No data available
                    </div>
                ) : null
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
                                background: 'var(--surface-color)',
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
