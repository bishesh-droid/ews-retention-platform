import React, { useState, useEffect } from 'react';

/**
 * Revenue-at-Risk Dashboard Component
 * 
 * BENEFIT: Translate student risk into financial impact
 * EXCLUSIVITY: Business intelligence layer on academic data
 * USER TYPE: Sales / Retention Teams
 * LOCATION: Executive dashboard, business intelligence view
 */

const RevenueAtRisk = ({ studentData, revenueData }) => {
    const [metrics, setMetrics] = useState(null);
    const [breakdown, setBreakdown] = useState([]);
    const [trend, setTrend] = useState(null);

    useEffect(() => {
        if (studentData && revenueData) {
            calculateRevenueMetrics(studentData, revenueData);
        } else {
            // Mock data
            setMetrics({
                totalRevenue: 2450000,
                highRiskRevenue: 245000,
                mediumRiskRevenue: 480000,
                lowRiskRevenue: 125000,
                safeRevenue: 1600000,
                totalAtRisk: 850000
            });

            setBreakdown([
                { category: 'High Risk (>70%)', amount: 245000, studentCount: 18, avgValue: 13611 },
                { category: 'Medium Risk (40-70%)', amount: 480000, studentCount: 42, avgValue: 11429 },
                { category: 'Low Risk (20-40%)', amount: 125000, studentCount: 15, avgValue: 8333 }
            ]);

            setTrend({
                change: -35000,
                changePercent: -3.95,
                period: 'vs last month'
            });
        }
    }, [studentData, revenueData]);

    const calculateRevenueMetrics = (students, revenue) => {
        // Calculate revenue at risk based on student dropout probabilities
        // In production, this would aggregate student LTV * dropout probability
        // Mock implementation for demonstration
    };

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

            {metrics && (
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
                            ${metrics.totalAtRisk.toLocaleString()}
                        </div>

                        {/* Percentage */}
                        <div style={{
                            fontSize: 'var(--font-size-h3)',
                            fontWeight: 'var(--font-weight-semibold)',
                            opacity: 0.95
                        }}>
                            {((metrics.totalAtRisk / metrics.totalRevenue) * 100).toFixed(1)}% of total revenue
                        </div>

                        {/* Trend - Delta with ± symbols */}
                        {trend && (
                            <div style={{
                                marginTop: 'var(--space-md)',
                                fontSize: 'var(--font-size-small)',
                                fontWeight: 'var(--font-weight-semibold)',
                                opacity: 0.9
                            }}>
                                {trend.change < 0 ? '↓' : '↑'} ${Math.abs(trend.change).toLocaleString()} ({trend.changePercent > 0 ? '+' : ''}{trend.changePercent.toFixed(1)}%) {trend.period}
                            </div>
                        )}
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
                            value={`$${metrics.totalRevenue.toLocaleString()}`}
                            color="var(--business-primary)"
                        />
                        <SummaryMetric
                            label="At Risk"
                            value={`$${metrics.totalAtRisk.toLocaleString()}`}
                            color="var(--business-revenue)"
                        />
                        <SummaryMetric
                            label="Safe Revenue"
                            value={`$${metrics.safeRevenue.toLocaleString()}`}
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
        background: 'white',
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
                {category.category}
            </div>
            <div style={{
                fontSize: 'var(--font-size-small)',
                color: 'var(--gray-600)'
            }}>
                {category.studentCount} students • ${category.avgValue.toLocaleString()} avg value
            </div>
        </div>

        <div style={{
            fontSize: 'var(--font-size-h1)',
            fontWeight: 'var(--font-weight-bold)',
            fontFamily: 'var(--font-family-mono)',
            color: 'var(--business-revenue)'
        }}>
            ${category.amount.toLocaleString()}
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
