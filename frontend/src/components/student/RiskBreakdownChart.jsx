import React from 'react';
import { Card } from 'react-bootstrap';
import { Pie } from 'react-chartjs-2';
import { getPrimaryRiskFactor } from '../../utils/studentUtils';

/**
 * RiskBreakdownChart Component
 * Visual breakdown of risk score by contributing factors
 */
const RiskBreakdownChart = ({ student, variant = 'full' }) => {
    // Default weights from RiskFactors page
    const weights = {
        attendance: 35,
        academic: 30,
        engagement: 20,
        behavioral: 15
    };

    // Calculate actual contributions
    const riskScore = student.risk_score;
    const contributions = {
        attendance: Math.round((riskScore * weights.attendance) / 100),
        academic: Math.round((riskScore * weights.academic) / 100),
        engagement: Math.round((riskScore * weights.engagement) / 100),
        behavioral: Math.round((riskScore * weights.behavioral) / 100)
    };

    const chartData = {
        labels: ['Attendance (35%)', 'Academic (30%)', 'Engagement (20%)', 'Behavioral (15%)'],
        datasets: [
            {
                data: [
                    contributions.attendance,
                    contributions.academic,
                    contributions.engagement,
                    contributions.behavioral
                ],
                backgroundColor: [
                    'rgba(233, 102, 102, 0.8)',
                    'rgba(235, 168, 75, 0.8)',
                    'rgba(129, 199, 132, 0.8)',
                    'rgba(100, 181, 246, 0.8)'
                ],
                borderColor: [
                    'rgba(233, 102, 102, 1)',
                    'rgba(235, 168, 75, 1)',
                    'rgba(129, 199, 132, 1)',
                    'rgba(100, 181, 246, 1)'
                ],
                borderWidth: 2
            }
        ]
    };

    const chartOptions = {
        responsive: true,
        maintainAspectRatio: variant === 'mini' ? true : false,
        plugins: {
            legend: {
                display: variant === 'full',
                position: 'bottom',
                labels: {
                    color: '#EDE9FE',
                    padding: 10,
                    font: { size: 11 }
                }
            },
            tooltip: {
                backgroundColor: 'var(--surface-color)',
                titleColor: 'var(--text-primary)',
                bodyColor: 'var(--text-secondary)',
                borderColor: 'var(--border-color)',
                borderWidth: 1,
                padding: 12,
                callbacks: {
                    label: function (context) {
                        const label = context.label || '';
                        const value = context.parsed || 0;
                        return `${label}: ${value} pts contribution`;
                    }
                }
            }
        }
    };

    const primaryFactor = getPrimaryRiskFactor(student);

    if (variant === 'mini') {
        return (
            <div style={{ width: '120px', height: '120px' }}>
                <Pie data={chartData} options={chartOptions} />
            </div>
        );
    }

    return (
        <Card className="glass-panel border-0 h-100">
            <Card.Body>
                <div className="d-flex justify-content-between align-items-center mb-3">
                    <h6 className="mb-0 fw-semibold">Risk Factor Breakdown</h6>
                    <span className="badge bg-primary">{riskScore} pts</span>
                </div>

                <div style={{ height: '200px' }} className="mb-3">
                    <Pie data={chartData} options={chartOptions} />
                </div>

                <div className="mt-3 pt-3 border-top" style={{ borderColor: 'var(--border-color)' }}>
                    <small className="text-muted">Primary Factor: </small>
                    <strong className="text-primary">{primaryFactor}</strong>

                    <div className="mt-2">
                        {Object.entries(contributions).map(([factor, contribution]) => (
                            <div key={factor} className="d-flex justify-content-between align-items-center mb-1">
                                <small className="text-muted text-capitalize">{factor}:</small>
                                <small className="fw-medium">
                                    {contribution} pts ({weights[factor]}% weight)
                                </small>
                            </div>
                        ))}
                    </div>
                </div>
            </Card.Body>
        </Card>
    );
};

export default RiskBreakdownChart;
