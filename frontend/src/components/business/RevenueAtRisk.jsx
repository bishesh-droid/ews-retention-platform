import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Spinner } from 'react-bootstrap';
import { getRevenueAtRiskMetrics } from '../../services/api';

/**
 * Revenue-at-Risk Dashboard Component
 * 
 * BENEFIT: Translate student risk into financial impact
 * EXCLUSIVITY: Business intelligence layer on academic data
 * USER TYPE: Sales / Retention Teams
 * LOCATION: Executive dashboard, business intelligence view
 */

const RevenueAtRisk = () => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [payload, setPayload] = useState(null);

    const fmtCurrency = useMemo(
        () => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }),
        []
    );

    useEffect(() => {
        let isMounted = true;
        const load = async () => {
            setLoading(true);
            setError(null);
            const resp = await getRevenueAtRiskMetrics();
            if (!isMounted) return;

            if (!resp.success) {
                setError(resp.message || 'Failed to load revenue-at-risk metrics.');
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
        const totalRevenue = payload.total_enrolled_revenue ?? 0;
        const totalAtRisk = payload.revenue_at_risk ?? 0;
        const safeRevenue = Math.max(0, totalRevenue - totalAtRisk);
        return { totalRevenue, totalAtRisk, safeRevenue };
    }, [payload]);

    const breakdown = useMemo(() => {
        const raw = payload?.risk_breakdown;
        if (!Array.isArray(raw)) return [];
        return raw.map((r) => ({
            category: String(r.category || '').toLowerCase(),
            amount: Number(r.revenue_at_risk || 0),
            studentCount: Number(r.student_count || 0),
            avgValue: Number(r.avg_value_per_student || 0),
        }));
    }, [payload]);

    return (
        <div className="premium-card business-context" style={{ marginBottom: 'var(--space-lg)' }}>
            {/* Header */}
            <div style={{
                fontSize: 'var(--font-size-h2)',
                fontWeight: 'var(--font-weight-semibold)',
                color: 'var(--business-primary)',
                marginBottom: 'var(--space-sm)'
            }}>
                Revenue at Risk
            </div>

            <div style={{
                fontSize: 'var(--font-size-small)',
                color: 'var(--gray-600)',
                marginBottom: 'var(--space-xl)'
            }}>
                Financial impact of student dropout risk
            </div>

            {loading && (
                <div className="text-center py-5 text-muted">
                    <Spinner animation="border" size="sm" />
                    <div className="mt-2">Loading revenue risk…</div>
                </div>
            )}

            {error && (
                <Alert variant="danger" className="mb-0">
                    {error}
                </Alert>
            )}

            {!loading && !error && metrics && (
                <>
                    {/* Primary Metric - Revenue at Risk */}
                    <div style={{
                        padding: 'var(--space-xl)',
                        background: 'linear-gradient(135deg, var(--business-revenue), #B91C1C)',
                        color: 'white',
                        borderRadius: 'var(--radius-lg)',
                        marginBottom: 'var(--space-xl)',
                        textAlign: 'center'
                    }}>
                        <div className="metric-label" style={{
                            fontSize: 'var(--font-size-caption)',
                            fontWeight: 'var(--font-weight-semibold)',
                            textTransform: 'uppercase',
                            letterSpacing: 'var(--letter-spacing-wider)',
                            marginBottom: 'var(--space-sm)',
                            opacity: 0.9
                        }}>
                            Total Revenue at Risk
                        </div>

                        {/* Revenue Figures - Display, extrabold, financial */}
                        <div className="revenue-number" style={{
                            fontSize: 'var(--font-size-display)',
                            fontWeight: 'var(--font-weight-extrabold)',
                            fontFamily: 'var(--font-family-mono)',
                            marginBottom: 'var(--space-md)'
                        }}>
                            {fmtCurrency.format(metrics.totalAtRisk)}
                        </div>

                        {/* Percentage */}
                        <div style={{
                            fontSize: 'var(--font-size-h3)',
                            fontWeight: 'var(--font-weight-semibold)',
                            opacity: 0.95
                        }}>
                            {metrics.totalRevenue > 0 ? `${((metrics.totalAtRisk / metrics.totalRevenue) * 100).toFixed(1)}%` : '0.0%'} of total revenue
                        </div>
                    </div>

                    {/* Breakdown by Risk Level */}
                    <div style={{ marginBottom: 'var(--space-xl)' }}>
                        <div style={{
                            fontSize: 'var(--font-size-small)',
                            fontWeight: 'var(--font-weight-semibold)',
                            color: 'var(--gray-700)',
                            marginBottom: 'var(--space-md)',
                            textTransform: 'uppercase',
                            letterSpacing: 'var(--letter-spacing-wide)'
                        }}>
                            Breakdown by Risk Level
                        </div>

                        {breakdown.map((item, idx) => (
                            <RiskCategoryCard key={idx} category={item} />
                        ))}
                    </div>

                    {/* Total Revenue Summary */}
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: 'var(--space-md)',
                        padding: 'var(--space-lg)',
                        background: 'var(--gray-50)',
                        borderRadius: 'var(--radius-md)'
                    }}>
                        <SummaryMetric
                            label="Total Revenue"
                            value={fmtCurrency.format(metrics.totalRevenue)}
                            color="var(--business-primary)"
                        />
                        <SummaryMetric
                            label="At Risk"
                            value={fmtCurrency.format(metrics.totalAtRisk)}
                            color="var(--business-revenue)"
                        />
                        <SummaryMetric
                            label="Safe Revenue"
                            value={fmtCurrency.format(metrics.safeRevenue)}
                            color="var(--business-growth)"
                        />
                    </div>
                </>
            )}
        </div>
    );
};

const RiskCategoryCard = ({ category }) => (
    <div style={{
        padding: 'var(--space-lg)',
        background: 'var(--surface-color)',
        border: 'var(--border-width-thin) solid var(--gray-200)',
        borderRadius: 'var(--radius-md)',
        marginBottom: 'var(--space-md)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
    }}>
        <div>
            <div style={{
                fontSize: 'var(--font-size-body)',
                fontWeight: 'var(--font-weight-semibold)',
                color: 'var(--gray-900)',
                marginBottom: 'var(--space-xs)'
            }}>
                {category.category || 'Risk segment'}
            </div>
            <div style={{
                fontSize: 'var(--font-size-small)',
                color: 'var(--gray-600)'
            }}>
                {Number(category.studentCount || 0).toLocaleString()} students • ${Number(category.avgValue || 0).toLocaleString()} avg value
            </div>
        </div>

        <div style={{
            fontSize: 'var(--font-size-h1)',
            fontWeight: 'var(--font-weight-bold)',
            fontFamily: 'var(--font-family-mono)',
            color: 'var(--business-revenue)'
        }}>
            ${Number(category.amount || 0).toLocaleString()}
        </div>
    </div>
);

const SummaryMetric = ({ label, value, color }) => (
    <div style={{ textAlign: 'center' }}>
        <div style={{
            fontSize: 'var(--font-size-caption)',
            color: 'var(--gray-600)',
            textTransform: 'uppercase',
            letterSpacing: 'var(--letter-spacing-wider)',
            marginBottom: 'var(--space-xs)'
        }}>
            {label}
        </div>
        <div style={{
            fontSize: 'var(--font-size-h2)',
            fontWeight: 'var(--font-weight-bold)',
            color: color,
            fontFamily: 'var(--font-family-mono)'
        }}>
            {value}
        </div>
    </div>
);

export default RevenueAtRisk;
