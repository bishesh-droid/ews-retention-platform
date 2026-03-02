import React, { useState, useEffect } from 'react';

/**
 * CohortChurn Diagnostics Component
 * 
 * BENEFIT: Identify which cohorts have abnormal churn patterns
 * EXCLUSIVITY: Statistical anomaly detection + cohort comparison
 * USER TYPE: Sales / Retention Teams
 * LOCATION: Business intelligence analytics view
 */

const CohortChurnDiagnostics = ({ cohorts }) => {
    const [cohortData, setCohortData] = useState([]);
    const [anomalies, setAnomalies] = useState([]);
    const [avgChurn, setAvgChurn] = useState(0);

    useEffect(() => {
        if (Array.isArray(cohorts) && cohorts.length) {
            processCohortData(cohorts);
        } else {
            setCohortData([]);
            setAvgChurn(0);
            setAnomalies([]);
        }
    }, [cohorts]);

    const processCohortData = (data) => {
        setCohortData(data);
        if (!data.length) {
            setAvgChurn(0);
            setAnomalies([]);
            return;
        }
        const avg = data.reduce((sum, c) => sum + (c.churnRate || 0), 0) / data.length;
        setAvgChurn(avg);
        setAnomalies(data.filter((c) => c.isAnomaly));
    };

    const getChurnColor = (rate, isAnomaly) => {
        if (isAnomaly) return 'var(--business-revenue)';
        if (rate > avgChurn * 1.2) return 'var(--business-warning)';
        return 'var(--business-growth)';
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
                Cohort Churn Diagnostics
            </div>

            <div style={{
                fontSize: 'var(--font-size-small)',
                color: 'var(--gray-600)',
                marginBottom: 'var(--space-xl)',
                lineHeight: 'var(--line-height-relaxed)'
            }}>
                Statistical analysis of cohort retention patterns with anomaly detection
            </div>

            {/* Alert for Anomalies */}
            {anomalies.length > 0 && (
                <div className="alert-calm warning" style={{ marginBottom: 'var(--space-lg)' }}>
                    <strong>⚠️ {anomalies.length} Anomalous Cohort{anomalies.length > 1 ? 's' : ''} Detected</strong>
                    <div style={{ marginTop: 'var(--space-xs)', fontSize: 'var(--font-size-small)' }}>
                        {anomalies.map(a => a.name).join(', ')} show significantly higher churn rates than expected.
                    </div>
                </div>
            )}

            {/* Average Benchmark */}
            <div style={{
                padding: 'var(--space-md)',
                background: 'var(--gray-50)',
                borderRadius: 'var(--radius-md)',
                marginBottom: 'var(--space-lg)',
                textAlign: 'center'
            }}>
                <div style={{
                    fontSize: 'var(--font-size-caption)',
                    color: 'var(--gray-600)',
                    textTransform: 'uppercase',
                    marginBottom: 'var(--space-xs)'
                }}>
                    Average Churn Rate
                </div>
                <div style={{
                    fontSize: 'var(--font-size-h1)',
                    fontWeight: 'var(--font-weight-bold)',
                    fontFamily: 'var(--font-family-mono)',
                    color: 'var(--business-primary)'
                }}>
                    {(avgChurn * 100).toFixed(1)}%
                </div>
            </div>

            {/* Cohort Table */}
            <div>
                {cohortData.length === 0 && (
                    <div className="text-muted small">No cohort churn data available.</div>
                )}
                {cohortData.map((cohort) => (
                    <CohortRow
                        key={cohort.id}
                        cohort={cohort}
                        avgChurn={avgChurn}
                        churnColor={getChurnColor(cohort.churnRate, cohort.isAnomaly)}
                    />
                ))}
            </div>
        </div>
    );
};

const CohortRow = ({ cohort, avgChurn, churnColor }) => {
    const variance = ((cohort.churnRate - avgChurn) / avgChurn) * 100;

    return (
        <div style={{
            padding: 'var(--space-lg)',
            background: cohort.isAnomaly ? 'rgba(220, 38, 38, 0.05)' : 'white',
            border: `var(--border-width-medium) solid ${cohort.isAnomaly ? 'var(--business-revenue)' : 'var(--gray-200)'}`,
            borderRadius: 'var(--radius-md)',
            marginBottom: 'var(--space-md)',
            display: 'grid',
            gridTemplateColumns: '2fr 1fr 1fr 1fr',
            gap: 'var(--space-md)',
            alignItems: 'center'
        }}>
            {/* Cohort Name - H3, semibold */}
            <div>
                <div style={{
                    fontSize: 'var(--font-size-h3)',
                    fontWeight: 'var(--font-weight-semibold)',
                    color: 'var(--gray-900)'
                }}>
                    {cohort.name}
                    {cohort.isAnomaly && (
                        <span style={{
                            marginLeft: 'var(--space-sm)',
                            fontSize: 'var(--font-size-caption)',
                            color: 'var(--business-revenue)',
                            fontWeight: 'var(--font-weight-bold)'
                        }}>
                            🚨 ANOMALY
                        </span>
                    )}
                </div>
                <div style={{
                    fontSize: 'var(--font-size-small)',
                    color: 'var(--gray-600)',
                    marginTop: 'var(--space-xs)'
                }}>
                    {cohort.size} students
                </div>
            </div>

            {/* Churn Rate - H1, bold, alert colors */}
            <div>
                <div style={{
                    fontSize: 'var(--font-size-caption)',
                    color: 'var(--gray-600)',
                    textTransform: 'uppercase',
                    marginBottom: 'var(--space-xs)'
                }}>
                    Churn Rate
                </div>
                <div style={{
                    fontSize: 'var(--font-size-h1)',
                    fontWeight: 'var(--font-weight-bold)',
                    fontFamily: 'var(--font-family-mono)',
                    color: churnColor
                }}>
                    {(cohort.churnRate * 100).toFixed(1)}%
                </div>
            </div>

            {/* Variance from Average */}
            <div>
                <div style={{
                    fontSize: 'var(--font-size-caption)',
                    color: 'var(--gray-600)',
                    textTransform: 'uppercase',
                    marginBottom: 'var(--space-xs)'
                }}>
                    vs Avg
                </div>
                <div style={{
                    fontSize: 'var(--font-size-h2)',
                    fontWeight: 'var(--font-weight-semibold)',
                    fontFamily: 'var(--font-family-mono)',
                    color: variance > 0 ? 'var(--business-revenue)' : 'var(--business-growth)'
                }}>
                    {variance > 0 ? '+' : ''}{variance.toFixed(0)}%
                </div>
            </div>

            {/* Action */}
            <div>
                <button
                    className="btn-premium"
                    style={{
                        background: cohort.isAnomaly ? 'var(--business-revenue)' : 'var(--gray-200)',
                        color: cohort.isAnomaly ? 'white' : 'var(--gray-700)',
                        width: '100%'
                    }}
                >
                    {cohort.isAnomaly ? 'Investigate' : 'View Details'}
                </button>
            </div>
        </div>
    );
};

export default CohortChurnDiagnostics;
