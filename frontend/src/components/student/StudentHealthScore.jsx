import React, { useState, useEffect } from 'react';

/**
 * PersonalizedStudent Health Score Component
 * 
 * BENEFIT: Translates raw risk scores into empowering, human-readable guidance
 * EXCLUSIVITY: Plain language narratives powered by contextual interpretation
 * USER TYPE: Students
 * LOCATION: Student Portal dashboard
 */

const StudentHealthScore = ({ studentData }) => {
    const [score, setScore] = useState(0);
    const [status, setStatus] = useState('');
    const [narrative, setNarrative] = useState('');
    const [trend, setTrend] = useState(null);

    useEffect(() => {
        if (studentData) {
            // Convert risk to health score (inverse relationship)
            const healthScore = Math.round((1 - studentData.dropout_risk) * 100);
            setScore(healthScore);

            // Determine status and narrative (calm, encouraging language)
            if (healthScore >= 80) {
                setStatus('Thriving');
                setNarrative('You\'re doing great! Your engagement and performance are strong. Keep up the excellent work.');
            } else if (healthScore >= 60) {
                setStatus('On Track');
                setNarrative('You\'re making steady progress. A few small adjustments could help you reach your full potential.');
            } else if (healthScore >= 40) {
                setStatus('Needs Attention');
                setNarrative('We\'ve noticed some areas where extra support could help. Let\'s work together to get you back on track.');
            } else {
                setStatus('Support Available');
                setNarrative('We\'re here to help you succeed. Reach out to your advisor to create a personalized success plan.');
            }

            // Calculate trend if historical data available
            if (studentData.historical_scores && studentData.historical_scores.length > 1) {
                const currentScore = healthScore;
                const previousScore = studentData.historical_scores[studentData.historical_scores.length - 2];
                setTrend(currentScore - previousScore);
            }
        }
    }, [studentData]);

    const getScoreColor = () => {
        if (score >= 80) return 'var(--student-success)';
        if (score >= 60) return 'var(--student-primary)';
        if (score >= 40) return 'var(--student-warning)';
        return 'var(--student-warning)'; // Never use alarming red for students
    };

    return (
        <div className="premium-card student-context" style={{ marginBottom: 'var(--space-lg)' }}>
            <div className="card-header">Your Learning Health Score</div>

            <div style={{ textAlign: 'center', padding: 'var(--space-xl) 0' }}>
                {/* Score Number - Display typography */}
                <div className="score-number" style={{ color: getScoreColor(), fontSize: 'var(--font-size-display)', fontWeight: 'var(--font-weight-extrabold)', lineHeight: '1', fontFamily: 'var(--font-family-mono)' }}>
                    {score}
                    <span style={{ fontSize: 'var(--font-size-h2)', color: 'var(--gray-500)' }}>/100</span>
                </div>

                {/* Status Label - H3 typography */}
                <div style={{ fontSize: 'var(--font-size-h3)', fontWeight: 'var(--font-weight-semibold)', color: getScoreColor(), marginTop: 'var(--space-sm)', letterSpacing: 'var(--letter-spacing-wide)' }}>
                    {status}
                </div>

                {/* Trend Indicator */}
                {trend !== null && (
                    <div style={{ fontSize: 'var(--font-size-small)', fontWeight: 'var(--font-weight-medium)', marginTop: 'var(--space-xs)', color: trend >= 0 ? 'var(--student-success)' : 'var(--student-warning)' }}>
                        {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)} points from last week
                    </div>
                )}
            </div>

            {/* Narrative - Body typography with relaxed line height */}
            <div style={{ fontSize: 'var(--font-size-body)', fontWeight: 'var(--font-weight-regular)', lineHeight: 'var(--line-height-relaxed)', color: 'var(--gray-700)', padding: 'var(--space-lg)', background: 'var(--gray-50)', borderRadius: 'var(--radius-md)', marginTop: 'var(--space-md)' }}>
                {narrative}
            </div>

            {/* Breakdown */}
            <div style={{ marginTop: 'var(--space-lg)', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 'var(--space-md)' }}>
                <ScoreDimension label="Engagement" value={studentData?.engagement_score || 75} />
                <ScoreDimension label="Performance" value={studentData?.performance_score || 82} />
                <ScoreDimension label="Attendance" value={studentData?.attendance_score || 90} />
            </div>
        </div>
    );
};

const ScoreDimension = ({ label, value }) => (
    <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 'var(--font-size-h2)', fontWeight: 'var(--font-weight-bold)', color: 'var(--student-primary)', fontFamily: 'var(--font-family-mono)' }}>
            {value}
        </div>
        <div style={{ fontSize: 'var(--font-size-caption)', fontWeight: 'var(--font-weight-medium)', color: 'var(--gray-600)', textTransform: 'uppercase', letterSpacing: 'var(--letter-spacing-wider)', marginTop: 'var(--space-xs)' }}>
            {label}
        </div>
    </div>
);

export default StudentHealthScore;
