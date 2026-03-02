import React, { useMemo } from 'react';
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid,
    Tooltip, ReferenceLine, Legend, ResponsiveContainer,
} from 'recharts';

const tooltipStyle = {
    contentStyle: { background: '#1E1535', border: '1px solid rgba(139,92,246,0.3)', borderRadius: 10 },
    labelStyle: { color: '#EDE9FE', fontWeight: 600 },
    itemStyle: { color: '#C4B5FD' },
};

const RetentionTrendChart = ({ forecast, targetRetentionRatePct = 95 }) => {
    const data = useMemo(() => {
        const points = forecast?.points;
        if (!Array.isArray(points) || points.length === 0) return [];
        return points.map((p) => {
            const retentionPct = Number.isFinite(p.baseline_retention_rate) ? p.baseline_retention_rate * 100 : 0;
            return {
                month: p.period,
                retention: Number(retentionPct.toFixed(1)),
                atRisk: Number((100 - retentionPct).toFixed(1)),
            };
        });
    }, [forecast]);

    return (
        <div className="glass-panel p-4 h-100">
            <h5 className="fw-semibold mb-1" style={{ color: '#EDE9FE' }}>Monthly Retention Trend</h5>
            <p style={{ fontSize: '0.85rem', color: '#B8AADA', marginBottom: '1.5rem' }}>
                Retention vs at-risk rate with target threshold
            </p>

            {data.length === 0 ? (
                <div className="text-muted" style={{ fontSize: '0.9rem' }}>
                    No retention trend data available.
                </div>
            ) : (
            <ResponsiveContainer width="100%" height={255}>
                <AreaChart data={data} margin={{ top: 8, right: 16, left: -10, bottom: 0 }}>
                    <defs>
                        <linearGradient id="retGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%"  stopColor="#8B5CF6" stopOpacity={0.35} />
                            <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="riskGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%"  stopColor="#EF4444" stopOpacity={0.28} />
                            <stop offset="95%" stopColor="#EF4444" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.1)" />
                    <XAxis dataKey="month" tick={{ fill: '#B8AADA', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis domain={[0, 100]} tick={{ fill: '#B8AADA', fontSize: 11 }} axisLine={false} tickLine={false} unit="%" />
                    <Tooltip {...tooltipStyle} formatter={(v, n) => [`${v}%`, n]} />
                    <ReferenceLine
                        y={targetRetentionRatePct}
                        stroke="#F59E0B"
                        strokeDasharray="5 3"
                        label={{ value: `Target ${targetRetentionRatePct}%`, fill: '#F59E0B', fontSize: 10, position: 'insideTopRight' }}
                    />
                    <Area type="monotone" dataKey="retention" name="Retention Rate" stroke="#8B5CF6" fill="url(#retGrad)" strokeWidth={2.5} dot={false} />
                    <Area type="monotone" dataKey="atRisk"    name="At-Risk Rate"   stroke="#EF4444" fill="url(#riskGrad)"  strokeWidth={2}   dot={false} />
                    <Legend wrapperStyle={{ color: '#B8AADA', fontSize: 12, paddingTop: 12 }} />
                </AreaChart>
            </ResponsiveContainer>
            )}
        </div>
    );
};

export default RetentionTrendChart;
