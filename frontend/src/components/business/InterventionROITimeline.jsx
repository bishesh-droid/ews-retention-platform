import React from 'react';
import { Alert } from 'react-bootstrap';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer, Cell,
} from 'recharts';

const QUARTERS = ['Q1', 'Q2', 'Q3', 'Q4'];

const tooltipStyle = {
    contentStyle: { background: '#1E1535', border: '1px solid rgba(139,92,246,0.3)', borderRadius: 10 },
    labelStyle: { color: '#EDE9FE', fontWeight: 600 },
    itemStyle: { color: '#C4B5FD' },
};

const StatBadge = ({ label, value, color }) => (
    <div style={{
        flex: 1,
        padding: '0.75rem 1rem',
        background: 'rgba(139,92,246,0.07)',
        border: '1px solid rgba(139,92,246,0.15)',
        borderRadius: 10,
        textAlign: 'center',
    }}>
        <div style={{ fontSize: '0.68rem', textTransform: 'uppercase', letterSpacing: '0.07em', color: '#B8AADA', marginBottom: '0.35rem' }}>
            {label}
        </div>
        <div style={{ fontSize: '1.25rem', fontWeight: 800, fontFamily: 'var(--font-family-mono)', color }}>
            {value}
        </div>
    </div>
);

const InterventionROITimeline = () => {
    return (
        <div className="glass-panel p-4 h-100">
            <h5 className="fw-semibold mb-1" style={{ color: '#EDE9FE' }}>Quarterly ROI Breakdown</h5>
            <p style={{ fontSize: '0.85rem', color: '#B8AADA', marginBottom: '1.25rem' }}>
                Quarterly breakdown is not yet available from the backend.
            </p>
            <Alert variant="secondary" className="mb-0" style={{ background: 'rgba(139,92,246,0.07)', borderColor: 'rgba(139,92,246,0.15)', color: '#C4B5FD' }}>
                This panel previously displayed simulated data. Add a backend time-series endpoint to enable a real quarterly ROI chart.
            </Alert>
        </div>
    );
};

export default InterventionROITimeline;
