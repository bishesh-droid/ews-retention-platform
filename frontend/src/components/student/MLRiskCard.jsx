import React from 'react';
import { motion } from 'framer-motion';
import { FaRobot, FaCheckCircle, FaExclamationTriangle } from 'react-icons/fa';

const MLRiskCard = ({ mlPrediction, ruleRiskScore }) => {
    if (!mlPrediction || mlPrediction.error) return null;

    const rawProb = typeof mlPrediction.dropout_probability === 'number' ? mlPrediction.dropout_probability : 0;
    const mlPercent = rawProb * 100;
    const mlScore = Number.isFinite(mlPercent) ? parseFloat(mlPercent.toFixed(2)) : 0;
    const riskLevel = mlPrediction.risk_level || 'Low';
    const factors = mlPrediction.top_risk_factors || [];
    const featureEntries = mlPrediction.features && typeof mlPrediction.features === 'object'
        ? Object.entries(mlPrediction.features)
        : [];

    // Determine color based on ML score
    const getColor = (score) => {
        if (score > 75) return 'var(--danger-color, #ef4444)'; // Critical
        if (score > 50) return 'var(--warning-color, #f59e0b)'; // High
        if (score > 25) return 'var(--info-color, #3b82f6)';    // Medium
        return 'var(--success-color, #10b981)';                // Low
    };

    const mlColor = getColor(mlScore);
    const ruleColor = getColor(ruleRiskScore);

    return (
        <div className="glass-panel p-4 mb-4" style={{ borderLeft: `4px solid ${mlColor}` }}>
            <div className="d-flex align-items-center gap-2 mb-3">
                <FaRobot size={20} style={{ color: mlColor }} />
                <h5 className="mb-0 fw-bold">ML Risk Assessment</h5>
                <span className="badge bg-light text-dark border ms-auto">AI Model v2.0</span>
            </div>

            <div className="row align-items-center">
                {/* Score Comparison */}
                <div className="col-md-5 text-center border-end">
                    <div className="mb-3">
                        <span className="display-6 fw-bold" style={{ color: mlColor }}>{mlScore.toFixed(2)}%</span>
                        <p className="text-muted small text-uppercase fw-bold">ML Dropout Probability</p>
                    </div>
                    <div>
                        <small className="text-muted">vs Rule-Based Score: <span style={{ color: ruleColor, fontWeight: 'bold' }}>{Math.round(ruleRiskScore)}%</span></small>
                    </div>
                </div>

                {/* Top Factors */}
                <div className="col-md-7 ps-md-4">
                    <h6 className="fw-bold mb-2">Top Drivers (SHAP)</h6>
                    {factors.length > 0 ? (
                        <ul className="list-unstyled mb-0">
                            {factors.map((factor, idx) => (
                                <li key={idx} className="mb-2 d-flex align-items-start gap-2">
                                    <FaExclamationTriangle className="text-warning mt-1" size={12} />
                                    <span className="small">{factor}</span>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <p className="small text-muted mb-0"><FaCheckCircle className="text-success me-1" /> No significant risk factors detected.</p>
                    )}

                    {/* Top contributing features (raw model inputs) */}
                    {featureEntries.length > 0 && (
                        <div className="mt-3">
                            <h6 className="fw-bold mb-2">Top Contributing Features</h6>
                            <div className="row g-2">
                                {featureEntries.slice(0, 8).map(([k, v]) => {
                                    const num = typeof v === 'number' ? v : null;
                                    const display = num !== null
                                        ? (Number.isFinite(num) ? num.toFixed(2) : String(v))
                                        : String(v);
                                    return (
                                        <div className="col-12 col-sm-6" key={k}>
                                            <div className="d-flex justify-content-between small">
                                                <span className="text-muted text-truncate" style={{ maxWidth: '70%' }}>{k}</span>
                                                <span className="fw-semibold">{display}</span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}

                    <div className="mt-3">
                        <div className="progress" style={{ height: '6px' }}>
                            <div
                                className="progress-bar"
                                role="progressbar"
                                style={{ width: `${mlScore}%`, backgroundColor: mlColor }}
                                aria-valuenow={mlScore}
                                aria-valuemin="0"
                                aria-valuemax="100"
                            ></div>
                        </div>
                        <div className="d-flex justify-content-between mt-1">
                            <small className="text-muted" style={{ fontSize: '0.7rem' }}>Safe</small>
                            <small className="text-muted" style={{ fontSize: '0.7rem' }}>Critical</small>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default MLRiskCard;
