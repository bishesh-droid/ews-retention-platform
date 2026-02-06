import React, { useState, useEffect } from 'react';

/**
 * What-If Simulator Component
 * 
 * BENEFIT: Students can model impact of behavior changes ("What if I attend 2 more classes?")
 * EXCLUSIVITY: Real-time ML model prediction, empowering interface
 * USER TYPE: Students
 * LOCATION: Student Portal tools section
 */

const WhatIfSimulator = ({ currentState, onRunSimulation }) => {
    const [scenarios, setScenarios] = useState({
        attendanceIncrease: 0,
        assignmentCompletion: 0,
        studyTimeIncrease: 0
    });

    const [predictedOutcome, setPredictedOutcome] = useState(null);
    const [currentScore, setCurrentScore] = useState(null);

    useEffect(() => {
        if (currentState) {
            const healthScore = Math.round((1 - currentState.dropout_risk) * 100);
            setCurrentScore(healthScore);
        }
    }, [currentState]);

    const handleRunSimulation = async () => {
        if (onRunSimulation) {
            const result = await onRunSimulation(scenarios);
            setPredictedOutcome(result);
        } else {
            // Mock prediction for demonstration
            const improvement =
                (scenarios.attendanceIncrease * 2) +
                (scenarios.assignmentCompletion * 1.5) +
                (scenarios.studyTimeIncrease * 1);
            const newScore = Math.min(100, currentScore + improvement);
            setPredictedOutcome({
                newScore: Math.round(newScore),
                delta: Math.round(newScore - currentScore),
                confidence: 0.85
            });
        }
    };

    const handleReset = () => {
        setScenarios({
            attendanceIncrease: 0,
            assignmentCompletion: 0,
            studyTimeIncrease: 0
        });
        setPredictedOutcome(null);
    };

    return (
        <div className="premium-card student-context" style={{ marginBottom: 'var(--space-lg)' }}>
            <div className="card-header" style={{ fontSize: 'var(--font-size-h2)', fontWeight: 'var(--font-weight-semibold)' }}>
                What-If Simulator
            </div>

            <div style={{ fontSize: 'var(--font-size-small)', color: 'var(--gray-600)', marginBottom: 'var(--space-lg)', lineHeight: 'var(--line-height-relaxed)' }}>
                See how different choices could impact your learning health score.
            </div>

            {/* Current Score */}
            <div style={{ padding: 'var(--space-md)', background: 'var(--gray-50)', borderRadius: 'var(--radius-md)', marginBottom: 'var(--space-lg)' }}>
                <div style={{ fontSize: 'var(--font-size-small)', color: 'var(--gray-600)', marginBottom: 'var(--space-xs)' }}>
                    Current Health Score
                </div>
                <div style={{ fontSize: 'var(--font-size-h1)', fontWeight: 'var(--font-weight-bold)', color: 'var(--student-primary)', fontFamily: 'var(--font-family-mono)' }}>
                    {currentScore}
                </div>
            </div>

            {/* Scenario Inputs - Body typography, medium weight */}
            <div style={{ marginBottom: 'var(--space-lg)' }}>
                <ScenarioControl
                    label="Attend additional classes per week"
                    value={scenarios.attendanceIncrease}
                    onChange={(val) => setScenarios({ ...scenarios, attendanceIncrease: val })}
                    max={5}
                />
                <ScenarioControl
                    label="Complete additional assignments per week"
                    value={scenarios.assignmentCompletion}
                    onChange={(val) => setScenarios({ ...scenarios, assignmentCompletion: val })}
                    max={5}
                />
                <ScenarioControl
                    label="Increase study time (hours per week)"
                    value={scenarios.studyTimeIncrease}
                    onChange={(val) => setScenarios({ ...scenarios, studyTimeIncrease: val })}
                    max={10}
                />
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
                <button
                    onClick={handleRunSimulation}
                    className="btn-premium primary"
                    style={{ flex: 1 }}
                >
                    Run Simulation
                </button>
                <button
                    onClick={handleReset}
                    className="btn-premium"
                    style={{ background: 'var(--gray-200)', color: 'var(--gray-700)' }}
                >
                    Reset
                </button>
            </div>

            {/* Predicted Outcome - H2 typography, bold weight, highlighted */}
            {predictedOutcome && (
                <div style={{ padding: 'var(--space-lg)', background: 'linear-gradient(135deg, var(--student-primary), var(--student-success))', borderRadius: 'var(--radius-lg)', color: 'white', textAlign: 'center' }}>
                    <div style={{ fontSize: 'var(--font-size-small)', fontWeight: 'var(--font-weight-medium)', marginBottom: 'var(--space-sm)', opacity: 0.9 }}>
                        Predicted New Score
                    </div>
                    <div style={{ fontSize: 'var(--font-size-display)', fontWeight: 'var(--font-weight-extrabold)', fontFamily: 'var(--font-family-mono)' }}>
                        {predictedOutcome.newScore}
                    </div>

                    {/* Delta - Small size, semibold weight, with arrows */}
                    <div style={{ fontSize: 'var(--font-size-h3)', fontWeight: 'var(--font-weight-semibold)', marginTop: 'var(--space-md)' }}>
                        {predictedOutcome.delta >= 0 ? '↑' : '↓'} {Math.abs(predictedOutcome.delta)} points
                    </div>

                    <div style={{ fontSize: 'var(--font-size-caption)', marginTop: 'var(--space-sm)', opacity: 0.8 }}>
                        {(predictedOutcome.confidence * 100).toFixed(0)}% confidence
                    </div>
                </div>
            )}
        </div>
    );
};

const ScenarioControl = ({ label, value, onChange, max }) => (
    <div style={{ marginBottom: 'var(--space-md)' }}>
        <label style={{ fontSize: 'var(--font-size-body)', fontWeight: 'var(--font-weight-medium)', color: 'var(--gray-700)', display: 'block', marginBottom: 'var(--space-sm)' }}>
            {label}
        </label>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
            <input
                type="range"
                min="0"
                max={max}
                value={value}
                onChange={(e) => onChange(Number(e.target.value))}
                style={{ flex: 1, accentColor: 'var(--student-primary)' }}
            />
            <div style={{ fontSize: 'var(--font-size-h2)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--student-primary)', fontFamily: 'var(--font-family-mono)', minWidth: '40px', textAlign: 'right' }}>
                {value}
            </div>
        </div>
    </div>
);

export default WhatIfSimulator;
