import React from 'react';
import {
    Radar,
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    ResponsiveContainer,
    Tooltip,
    Legend
} from 'recharts';

/**
 * SignalRadarChart Component
 * Displays signal breakdown as a radar chart for visual comparison
 */
const SignalRadarChart = ({ signals }) => {
    if (!signals) {
        return <div className="chart-empty">No signal data available</div>;
    }

    // Transform signal breakdown into radar chart format
    const chartData = [
        {
            subject: 'Academic',
            value: Math.round((signals.academic_signal_score || 0) * 100),
            fullMark: 100
        },
        {
            subject: 'Engagement',
            value: Math.round((signals.engagement_signal_score || 0) * 100),
            fullMark: 100
        },
        {
            subject: 'Consistency',
            value: Math.round((signals.consistency_signal_score || 0) * 100),
            fullMark: 100
        },
        {
            subject: 'Intent',
            value: Math.round((signals.intent_signal_score || 0) * 100),
            fullMark: 100
        },
        {
            subject: 'Responsiveness',
            value: Math.round((signals.responsiveness_signal_score || 0) * 100),
            fullMark: 100
        }
    ];

    return (
        <div className="signal-radar-chart">
            <h3 className="chart-title">Signal Analysis</h3>
            <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={chartData}>
                    <PolarGrid stroke="#e5e7eb" />
                    <PolarAngleAxis
                        dataKey="subject"
                        tick={{ fill: '#6b7280', fontSize: 12 }}
                    />
                    <PolarRadiusAxis
                        angle={90}
                        domain={[0, 100]}
                        tick={{ fill: '#9ca3af', fontSize: 10 }}
                    />
                    <Radar
                        name="Risk Score"
                        dataKey="value"
                        stroke="#3b82f6"
                        fill="#3b82f6"
                        fillOpacity={0.6}
                    />
                    <Tooltip
                        contentStyle={{
                            backgroundColor: '#ffffff',
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px',
                            padding: '8px 12px'
                        }}
                        formatter={(value) => [`${value}%`, 'Risk Score']}
                    />
                </RadarChart>
            </ResponsiveContainer>
        </div>
    );
};

export default SignalRadarChart;
