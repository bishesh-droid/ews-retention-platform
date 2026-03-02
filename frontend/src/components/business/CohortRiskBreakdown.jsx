import React, { useMemo } from 'react';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

const RISK_TIERS = [
    { key: 'Low',      color: '#10B981', label: 'Low Risk (≤40)'       },
    { key: 'Medium',   color: '#F59E0B', label: 'Medium Risk (41–70)'  },
    { key: 'High',     color: '#EF4444', label: 'High Risk (71–85)'    },
    { key: 'Critical', color: '#DC2626', label: 'Critical Risk (>85)'  },
];

const tooltipStyle = {
    contentStyle: { background: '#1E1535', border: '1px solid rgba(139,92,246,0.3)', borderRadius: 10 },
    labelStyle: { color: '#EDE9FE', fontWeight: 600 },
    itemStyle: { color: '#C4B5FD' },
};

const CohortRiskBreakdown = ({ heatmap }) => {
    const data = useMemo(() => {
        if (!Array.isArray(heatmap) || heatmap.length === 0) return [];
        return heatmap.map((r) => ({
            cohort: r.cohort,
            Low: r.Low,
            Medium: r.Medium,
            High: r.High,
            Critical: r.Critical,
        }));
    }, [heatmap]);

    /* Summary: worst and best cohort by high+critical share */
    const summary = useMemo(() => {
        if (!data.length) return null;
        const withRisk = data.map(d => ({ ...d, riskPct: d.High + d.Critical }));
        const worst = withRisk.reduce((a, b) => b.riskPct > a.riskPct ? b : a);
        const best  = withRisk.reduce((a, b) => b.riskPct < a.riskPct ? b : a);
        return { worst, best };
    }, [data]);

    return (
        <div className="glass-panel p-4 h-100">
            <h5 className="fw-semibold mb-1" style={{ color: '#EDE9FE' }}>Cohort Risk Breakdown</h5>
            <p style={{ fontSize: '0.85rem', color: '#B8AADA', marginBottom: '1.25rem' }}>
                Risk tier distribution by enrollment cohort (% of students per cohort)
            </p>

            {data.length === 0 ? (
                <div className="text-muted" style={{ fontSize: '0.9rem' }}>
                    No cohort heatmap data available.
                </div>
            ) : (
            <>
            {summary && (
                <div className="d-flex gap-3 mb-4">
                    <div style={{
                        flex: 1, padding: '0.65rem 0.9rem',
                        background: 'rgba(239,68,68,0.08)',
                        border: '1px solid rgba(239,68,68,0.2)',
                        borderRadius: 9,
                    }}>
                        <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.07em', color: '#EF4444', marginBottom: 3 }}>
                            Highest Risk Cohort
                        </div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 800, fontFamily: 'var(--font-family-mono)', color: '#EDE9FE' }}>
                            {summary.worst.cohort}
                        </div>
                        <div style={{ fontSize: '0.72rem', color: '#B8AADA' }}>
                            {summary.worst.riskPct}% high + critical
                        </div>
                    </div>
                    <div style={{
                        flex: 1, padding: '0.65rem 0.9rem',
                        background: 'rgba(16,185,129,0.08)',
                        border: '1px solid rgba(16,185,129,0.2)',
                        borderRadius: 9,
                    }}>
                        <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.07em', color: '#10B981', marginBottom: 3 }}>
                            Healthiest Cohort
                        </div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 800, fontFamily: 'var(--font-family-mono)', color: '#EDE9FE' }}>
                            {summary.best.cohort}
                        </div>
                        <div style={{ fontSize: '0.72rem', color: '#B8AADA' }}>
                            {summary.best.riskPct}% high + critical
                        </div>
                    </div>
                </div>
            )}

            <ResponsiveContainer width="100%" height={240}>
                <BarChart data={data} margin={{ top: 5, right: 16, left: -10, bottom: 0 }} barSize={38}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.1)" vertical={false} />
                    <XAxis dataKey="cohort" tick={{ fill: '#B8AADA', fontSize: 12 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: '#B8AADA', fontSize: 12 }} axisLine={false} tickLine={false} unit="%" />
                    <Tooltip {...tooltipStyle} formatter={(v, n) => [`${v}%`, n]} />
                    <Legend wrapperStyle={{ color: '#B8AADA', fontSize: 12, paddingTop: 10 }} />
                    <Bar dataKey="Low"      name="Low Risk"      stackId="a" fill="#10B981" fillOpacity={0.85} />
                    <Bar dataKey="Medium"   name="Medium Risk"   stackId="a" fill="#F59E0B" fillOpacity={0.85} />
                    <Bar dataKey="High"     name="High Risk"     stackId="a" fill="#EF4444" fillOpacity={0.85} />
                    <Bar dataKey="Critical" name="Critical Risk"  stackId="a" fill="#DC2626" fillOpacity={0.9} radius={[4, 4, 0, 0]} />
                </BarChart>
            </ResponsiveContainer>
            </>
            )}
        </div>
    );
};

export default CohortRiskBreakdown;
