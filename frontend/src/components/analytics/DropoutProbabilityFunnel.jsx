import React, { useState, useEffect } from 'react';

const DropoutProbabilityFunnel = ({ cohortData }) => {
    const [funnelStages, setFunnelStages] = useState([]);
    const [totalRevenue, setTotalRevenue] = useState(0);

    useEffect(() => {
        if (cohortData) {
            setFunnelStages(cohortData.stages);
            setTotalRevenue(cohortData.totalRevenue);
        } else {
            const mockStages = [
                { stage: 'Enrolled',     count: 500, dropoutRisk: 0.05, avgRevenue: 5000 },
                { stage: 'First Month',  count: 475, dropoutRisk: 0.12, avgRevenue: 4750 },
                { stage: 'Second Month', count: 420, dropoutRisk: 0.18, avgRevenue: 4200 },
                { stage: 'Mid-Term',     count: 380, dropoutRisk: 0.22, avgRevenue: 3800 },
                { stage: 'Final Term',   count: 345, dropoutRisk: 0.15, avgRevenue: 3450 },
                { stage: 'Completed',    count: 315, dropoutRisk: 0.02, avgRevenue: 3150 },
            ];
            setFunnelStages(mockStages);
            setTotalRevenue(mockStages[0].count * mockStages[0].avgRevenue);
        }
    }, [cohortData]);

    const getRiskColor = (risk) => {
        if (risk >= 0.20) return '#EF4444';
        if (risk >= 0.10) return '#F59E0B';
        return '#10B981';
    };

    const maxCount = funnelStages.length > 0 ? funnelStages[0].count : 1;

    return (
        <div className="glass-panel p-4 h-100">
            {/* Header */}
            <h5 className="fw-semibold mb-1" style={{ color: '#EDE9FE' }}>Dropout Probability Funnel</h5>
            <p style={{ fontSize: '0.85rem', color: '#B8AADA', marginBottom: '1.25rem' }}>
                Stage-wise cohort progression with risk indicators
            </p>

            {/* Total cohort value banner */}
            <div style={{
                padding: '0.75rem 1.25rem',
                background: 'rgba(139,92,246,0.18)',
                borderRadius: 10,
                border: '1px solid rgba(139,92,246,0.3)',
                marginBottom: '1.25rem',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
            }}>
                <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#C4B5FD', fontWeight: 600 }}>
                    Total Cohort Value
                </span>
                <span style={{ fontSize: '1.3rem', fontWeight: 800, fontFamily: 'var(--font-family-mono)', color: '#EDE9FE' }}>
                    ${totalRevenue.toLocaleString()}
                </span>
            </div>

            {/* Funnel stages */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {funnelStages.map((stage, idx) => {
                    const widthPct  = Math.max(30, (stage.count / maxCount) * 100);
                    const riskColor = getRiskColor(stage.dropoutRisk);
                    const isLast    = idx === funnelStages.length - 1;

                    return (
                        <div key={idx}>
                            <div style={{
                                width: `${widthPct}%`,
                                margin: '0 auto',
                                padding: '10px 14px',
                                background: `${riskColor}10`,
                                border: `1px solid ${riskColor}40`,
                                borderRadius: 8,
                                transition: 'all 0.2s',
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    {/* Stage name + count */}
                                    <div>
                                        <div style={{ fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: riskColor, marginBottom: 2 }}>
                                            {stage.stage}
                                        </div>
                                        <div style={{ fontSize: '1.15rem', fontWeight: 800, fontFamily: 'var(--font-family-mono)', color: '#EDE9FE', lineHeight: 1 }}>
                                            {stage.count}
                                            <span style={{ fontSize: '0.7rem', color: '#B8AADA', fontWeight: 500, marginLeft: 4 }}>students</span>
                                        </div>
                                    </div>
                                    {/* Risk */}
                                    <div style={{ textAlign: 'center' }}>
                                        <div style={{ fontSize: '0.6rem', color: '#B8AADA', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 2 }}>Risk</div>
                                        <div style={{ fontSize: '1.15rem', fontWeight: 800, fontFamily: 'var(--font-family-mono)', color: riskColor, lineHeight: 1 }}>
                                            {(stage.dropoutRisk * 100).toFixed(0)}%
                                        </div>
                                    </div>
                                    {/* Value */}
                                    <div style={{ textAlign: 'right' }}>
                                        <div style={{ fontSize: '0.6rem', color: '#B8AADA', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 2 }}>Value</div>
                                        <div style={{ fontSize: '0.9rem', fontWeight: 700, fontFamily: 'var(--font-family-mono)', color: '#EDE9FE', lineHeight: 1 }}>
                                            ${(stage.count * stage.avgRevenue).toLocaleString()}
                                        </div>
                                    </div>
                                </div>
                            </div>
                            {!isLast && (
                                <div style={{ textAlign: 'center', color: '#4B3B7A', fontSize: '0.75rem', lineHeight: '14px' }}>↓</div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default DropoutProbabilityFunnel;
