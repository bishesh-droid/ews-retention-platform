import React, { useState, useEffect } from 'react';

/**
 * Dropout Probability Funnel Component
 * 
 * BENEFIT: Visual funnel showing cohort progression and dropout risk at each stage
 * EXCLUSIVITY: Stage-wise churn prediction (rare in academic analytics)
 * USER TYPE: Sales / Retention Teams
 * LOCATION: Business Intelligence dashboard
 */

const DropoutProbabilityFunnel = ({ cohortData }) => {
    const [funnelStages, setFunnelStages] = useState([]);
    const [totalRevenue, setTotalRevenue] = useState(0);

    useEffect(() => {
        if (cohortData) {
            processFunnelData(cohortData);
        } else {
            // Mock funnel data
            const mockStages = [
                { stage: 'ENROLLED', count: 500, dropoutRisk: 0.05, avgRevenue: 5000 },
                { stage: 'FIRST MONTH', count: 475, dropoutRisk: 0.12, avgRevenue: 4750 },
                { stage: 'SECOND MONTH', count: 420, dropoutRisk: 0.18, avgRevenue: 4200 },
                { stage: 'MID-TERM', count: 380, dropoutRisk: 0.22, avgRevenue: 3800 },
                { stage: 'FINAL TERM', count: 345, dropoutRisk: 0.15, avgRevenue: 3450 },
                { stage: 'COMPLETED', count: 315, dropoutRisk: 0.02, avgRevenue: 3150 }
            ];
            setFunnelStages(mockStages);
            setTotalRevenue(mockStages[0].count * mockStages[0].avgRevenue);
        }
    }, [cohortData]);

    const processFunnelData = (data) => {
        // Process cohort data into funnel stages
        setFunnelStages(data.stages);
        setTotalRevenue(data.totalRevenue);
    };

    const getStageWidth = (count) => {
        if (funnelStages.length === 0) return 100;
        const maxCount = funnelStages[0].count;
        return (count / maxCount) * 100;
    };

    const getRiskColor = (risk) => {
        if (risk >= 0.20) return 'var(--business-revenue)';
        if (risk >= 0.10) return 'var(--business-warning)';
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
                Dropout Probability Funnel
            </div>

            <div style={{
                fontSize: 'var(--font-size-small)',
                color: 'var(--gray-600)',
                marginBottom: 'var(--space-xl)'
            }}>
                Stage-wise cohort progression with risk indicators
            </div>

            {/* Total Revenue Header */}
            <div style={{
                padding: 'var(--space-lg)',
                background: 'var(--business-primary)',
                color: 'white',
                borderRadius: 'var(--radius-lg)',
                marginBottom: 'var(--space-xl)',
                textAlign: 'center'
            }}>
                <div style={{
                    fontSize: 'var(--font-size-caption)',
                    fontWeight: 'var(--font-weight-semibold)',
                    textTransform: 'uppercase',
                    letterSpacing: 'var(--letter-spacing-wider)',
                    marginBottom: 'var(--space-sm)',
                    opacity: 0.9
                }}>
                    Total Cohort Value
                </div>
                <div className="revenue-number" style={{
                    fontSize: 'var(--font-size-display)',
                    fontWeight: 'var(--font-weight-extrabold)',
                    fontFamily: 'var(--font-family-mono)'
                }}>
                    ${totalRevenue.toLocaleString()}
                </div>
            </div>

            {/* Funnel Visualization */}
            <div style={{ padding: 'var(--space-lg) 0' }}>
                {funnelStages.map((stage, idx) => (
                    <FunnelStage
                        key={idx}
                        stage={stage}
                        width={getStageWidth(stage.count)}
                        riskColor={getRiskColor(stage.dropoutRisk)}
                        isLast={idx === funnelStages.length - 1}
                    />
                ))}
            </div>
        </div>
    );
};

const FunnelStage = ({ stage, width, riskColor, isLast }) => (
    <div style={{ marginBottom: 'var(--space-md)' }}>
        {/* Stage Bar */}
        <div style={{
            width: `${width}%`,
            margin: '0 auto',
            padding: 'var(--space-lg)',
            background: `linear-gradient(135deg, ${riskColor}15, ${riskColor}05)`,
            border: `var(--border-width-medium) solid ${riskColor}`,
            borderRadius: 'var(--radius-md)',
            position: 'relative',
            transition: 'all var(--transition-normal)'
        }}>
            {/* Stage Name - H3, semibold, uppercase */}
            <div style={{
                fontSize: 'var(--font-size-h3)',
                fontWeight: 'var(--font-weight-semibold)',
                color: 'var(--business-primary)',
                textTransform: 'uppercase',
                letterSpacing: 'var(--letter-spacing-wide)',
                marginBottom: 'var(--space-sm)'
            }}>
                {stage.stage}
            </div>

            {/* Metrics Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: 'var(--space-md)'
            }}>
                {/* Count - Display, extrabold, monospace */}
                <div>
                    <div style={{
                        fontSize: 'var(--font-size-caption)',
                        color: 'var(--gray-600)',
                        textTransform: 'uppercase',
                        letterSpacing: 'var(--letter-spacing-wide)',
                        marginBottom: 'var(--space-xs)'
                    }}>
                        Students
                    </div>
                    <div style={{
                        fontSize: 'var(--font-size-display)',
                        fontWeight: 'var(--font-weight-extrabold)',
                        fontFamily: 'var(--font-family-mono)',
                        color: 'var(--business-primary)'
                    }}>
                        {stage.count}
                    </div>
                </div>

                {/* Dropout Risk - Display, bold, color-coded */}
                <div>
                    <div style={{
                        fontSize: 'var(--font-size-caption)',
                        color: 'var(--gray-600)',
                        textTransform: 'uppercase',
                        letterSpacing: 'var(--letter-spacing-wide)',
                        marginBottom: 'var(--space-xs)'
                    }}>
                        Risk
                    </div>
                    <div style={{
                        fontSize: 'var(--font-size-display)',
                        fontWeight: 'var(--font-weight-bold)',
                        fontFamily: 'var(--font-family-mono)',
                        color: riskColor
                    }}>
                        {(stage.dropoutRisk * 100).toFixed(0)}%
                    </div>
                </div>

                {/* Revenue Impact */}
                <div>
                    <div style={{
                        fontSize: 'var(--font-size-caption)',
                        color: 'var(--gray-600)',
                        textTransform: 'uppercase',
                        letterSpacing: 'var(--letter-spacing-wide)',
                        marginBottom: 'var(--space-xs)'
                    }}>
                        Value
                    </div>
                    <div style={{
                        fontSize: 'var(--font-size-h1)',
                        fontWeight: 'var(--font-weight-bold)',
                        fontFamily: 'var(--font-family-mono)',
                        color: 'var(--business-primary)'
                    }}>
                        ${(stage.count * stage.avgRevenue).toLocaleString()}
                    </div>
                </div>
            </div>
        </div>

        {/* Connector Arrow */}
        {!isLast && (
            <div style={{
                textAlign: 'center',
                fontSize: 'var(--font-size-h1)',
                color: 'var(--gray-400)',
                margin: 'var(--space-xs) 0'
            }}>
                ↓
            </div>
        )}
    </div>
);

export default DropoutProbabilityFunnel;
