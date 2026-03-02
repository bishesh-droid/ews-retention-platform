import React, { useMemo } from 'react';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

const LABELS = ['+1 Mo', '+2 Mo', '+3 Mo', '+4 Mo', '+5 Mo', '+6 Mo'];

const tooltipStyle = {
    contentStyle: { background: '#1E1535', border: '1px solid rgba(139,92,246,0.3)', borderRadius: 10 },
    labelStyle: { color: '#EDE9FE', fontWeight: 600 },
    itemStyle: { color: '#C4B5FD' },
};

const fmt = (v) => {
    const n = typeof v === 'number' ? v : 0;
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n);
};

const ScenarioPill = ({ color, label, desc }) => (
    <div style={{
        flex: 1,
        padding: '0.65rem 0.9rem',
        background: 'rgba(139,92,246,0.07)',
        border: '1px solid rgba(139,92,246,0.13)',
        borderRadius: 9,
        display: 'flex',
        alignItems: 'flex-start',
        gap: '0.5rem',
    }}>
        <div style={{ width: 10, height: 10, borderRadius: 3, background: color, flexShrink: 0, marginTop: 3 }} />
        <div>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#EDE9FE' }}>{label}</div>
            <div style={{ fontSize: '0.68rem', color: '#B8AADA', marginTop: 1 }}>{desc}</div>
        </div>
    </div>
);

const RevenueForecast = ({ forecast }) => {
    const data = useMemo(() => {
        const points = forecast?.points;
        if (!Array.isArray(points) || points.length === 0) return [];
        return points.map((p) => ({
            month: p.period,
            Optimistic: p.optimistic_retained_revenue,
            Baseline: p.baseline_retained_revenue,
            Pessimistic: p.pessimistic_retained_revenue,
        }));
    }, [forecast]);

    const scenarios = [
        { color: '#10B981', label: 'Optimistic',  desc: '97.5% retention via full program' },
        { color: '#8B5CF6', label: 'Baseline',    desc: 'Current trajectory maintained'    },
        { color: '#EF4444', label: 'Pessimistic', desc: 'Minimal intervention effort'      },
    ];

    return (
        <div className="glass-panel p-4 h-100">
            <h5 className="fw-semibold mb-1" style={{ color: '#EDE9FE' }}>6-Month Revenue Forecast</h5>
            <p style={{ fontSize: '0.85rem', color: '#B8AADA', marginBottom: '1.25rem' }}>
                Projected retained revenue across three intervention scenarios
            </p>

            {data.length === 0 ? (
                <div className="text-muted" style={{ fontSize: '0.9rem' }}>
                    No forecast data available.
                </div>
            ) : (
            <div className="d-flex gap-3 mb-4">
                {scenarios.map(s => <ScenarioPill key={s.label} {...s} />)}
            </div>
            )}

            {data.length > 0 && (
                <ResponsiveContainer width="100%" height={230}>
                    <LineChart data={data} margin={{ top: 5, right: 16, left: -10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.1)" />
                        <XAxis dataKey="month" tick={{ fill: '#B8AADA', fontSize: 11 }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fill: '#B8AADA', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={(v) => fmt(v)} />
                        <Tooltip {...tooltipStyle} formatter={(v, n) => [fmt(v), n]} />
                        <Legend wrapperStyle={{ color: '#B8AADA', fontSize: 12, paddingTop: 10 }} />
                        <Line type="monotone" dataKey="Optimistic"  stroke="#10B981" strokeWidth={2.5} dot={false} />
                        <Line type="monotone" dataKey="Baseline"    stroke="#8B5CF6" strokeWidth={2.5} strokeDasharray="6 3" dot={false} />
                        <Line type="monotone" dataKey="Pessimistic" stroke="#EF4444" strokeWidth={2}   strokeDasharray="3 3" dot={false} />
                    </LineChart>
                </ResponsiveContainer>
            )}
        </div>
    );
};

export default RevenueForecast;
