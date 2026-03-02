import React, { useState, useEffect } from 'react';

/**
 * Bias Indicators Component
 * 
 * BENEFIT: Show if model predictions vary unfairly by demographics
 * EXCLUSIVITY: Fairness metrics (demographic parity, equal opportunity)
 * USER TYPE: Institution Administrators / Compliance
 * LOCATION: Ethics & transparency dashboard
 */

const BiasIndicators = ({ fairnessMetrics }) => {
    const [metrics, setMetrics] = useState(null);
    const [alerts, setAlerts] = useState([]);

    useEffect(() => {
        if (fairnessMetrics) {
            processFairnessMetrics(fairnessMetrics);
        } else {
            // Mock fairness metrics
            setMetrics({
                demographicParity: 0.92,
                equalOpportunity: 0.88,
                calibration: 0.94,
                groups: [
                    { name: 'Gender', parity: 0.95, concern: false },
                    { name: 'Ethnicity', parity: 0.87, concern: true },
                    { name: 'Age', parity: 0.93, concern: false },
                    { name: 'First-Gen Status', parity: 0.82, concern: true }
                ]
            });

            setAlerts([
                'Slight disparity detected in predictions for ethnicity groups',
                'First-generation students may receive disproportionate high-risk classifications'
            ]);
        }
    }, [fairnessMetrics]);

    const processFairnessMetrics = (data) => {
        setMetrics(data);

        // Generate alerts for concerning disparities
        const concerningGroups = data.groups.filter(g => g.concern);
        setAlerts(concerningGroups.map(g => `Disparity detected: ${g.name}`));
    };

    const getParityColor = (score) => {
        if (score >= 0.90) return 'var(--color-success)';
        if (score >= 0.80) return 'var(--color-warning)';
        return 'var(--color-error)';
    };

    return (
        <div className="premium-card institutional-context" style={{ marginBottom: 'var(--space-lg)' }}>
            {/* Header */}
            <div style={{
                fontSize: 'var(--font-size-h3)',
                fontWeight: 'var(--font-weight-semibold)',
                color: 'var(--institutional-primary)',
                marginBottom: 'var(--space-md)'
            }}>
                Bias & Fairness Indicators
            </div>

            {/* Disclaimer - Small, regular, lighter gray, max-width */}
            <div className="disclaimer" style={{ marginBottom: 'var(--space-lg)' }}>
                These metrics assess whether the predictive model treats different demographic groups fairly. Lower scores indicate potential bias that should be investigated.
            </div>

            {/* Alerts */}
            {alerts.length > 0 && (
                <div className="alert-calm warning" style={{ marginBottom: 'var(--space-lg)' }}>
                    <strong>⚠️ Fairness Concerns Detected</strong>
                    <ul style={{ margin: 'var(--space-sm) 0 0 0', paddingLeft: 'var(--space-lg)' }}>
                        {alerts.map((alert, idx) => (
                            <li key={idx} style={{ marginBottom: 'var(--space-xs)' }}>{alert}</li>
                        ))}
                    </ul>
                </div>
            )}

            {metrics && (
                <>
                    {/* Overall Fairness Metrics */}
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                        gap: 'var(--space-md)',
                        marginBottom: 'var(--space-xl)'
                    }}>
                        <FairnessMetricCard
                            label="Demographic Parity"
                            score={metrics.demographicParity}
                            description="Equal prediction rates across groups"
                        />
                        <FairnessMetricCard
                            label="Equal Opportunity"
                            score={metrics.equalOpportunity}
                            description="Equal true positive rates"
                        />
                        <FairnessMetricCard
                            label="Calibration"
                            score={metrics.calibration}
                            description="Prediction accuracy consistency"
                        />
                    </div>

                    {/* Group-Level Analysis */}
                    <div>
                        <div className="data-label" style={{
                            fontSize: 'var(--font-size-small)',
                            fontWeight: 'var(--font-weight-semibold)',
                            color: 'var(--gray-600)',
                            textTransform: 'uppercase',
                            marginBottom: 'var(--space-md)'
                        }}>
                            Demographic Group Analysis
                        </div>

                        {metrics.groups.map((group, idx) => (
                            <div key={idx} style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                                padding: 'var(--space-md)',
                                background: group.concern ? 'rgba(245, 158, 11, 0.05)' : 'white',
                                border: `var(--border-width-thin) solid ${group.concern ? 'var(--color-warning)' : 'var(--gray-200)'}`,
                                borderRadius: 'var(--radius-sm)',
                                marginBottom: 'var(--space-sm)'
                            }}>
                                <div>
                                    <div style={{
                                        fontSize: 'var(--font-size-body)',
                                        fontWeight: 'var(--font-weight-semibold)',
                                        color: 'var(--gray-900)'
                                    }}>
                                        {group.name}
                                    </div>
                                    {group.concern && (
                                        <div style={{
                                            fontSize: 'var(--font-size-caption)',
                                            color: 'var(--color-warning)',
                                            marginTop: 'var(--space-xs)'
                                        }}>
                                            ⚠️ Below threshold
                                        </div>
                                    )}
                                </div>

                                {/* Bias Metrics - H3, semibold */}
                                <div style={{
                                    fontSize: 'var(--font-size-h3)',
                                    fontWeight: 'var(--font-weight-semibold)',
                                    color: getParityColor(group.parity),
                                    fontFamily: 'var(--font-family-mono)'
                                }}>
                                    {(group.parity * 100).toFixed(0)}%
                                </div>
                            </div>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
};

const FairnessMetricCard = ({ label, score, description }) => {
    const getColor = (s) => {
        if (s >= 0.90) return 'var(--color-success)';
        if (s >= 0.80) return 'var(--color-warning)';
        return 'var(--color-error)';
    };

    return (
        <div style={{
            padding: 'var(--space-md)',
            background: 'var(--surface-color)',
            border: 'var(--border-width-thin) solid var(--gray-200)',
            borderRadius: 'var(--radius-md)',
            textAlign: 'center'
        }}>
            <div style={{
                fontSize: 'var(--font-size-caption)',
                color: 'var(--gray-600)',
                textTransform: 'uppercase',
                marginBottom: 'var(--space-sm)'
            }}>
                {label}
            </div>
            <div style={{
                fontSize: 'var(--font-size-display)',
                fontWeight: 'var(--font-weight-bold)',
                color: getColor(score),
                fontFamily: 'var(--font-family-mono)',
                marginBottom: 'var(--space-sm)'
            }}>
                {(score * 100).toFixed(0)}%
            </div>
            <div className="disclaimer" style={{ fontSize: 'var(--font-size-caption)' }}>
                {description}
            </div>
        </div>
    );
};

export default BiasIndicators;
