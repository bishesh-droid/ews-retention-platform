import React, { useState, useEffect } from 'react';

/**
 * Explainable Risk Narrative Component
 * 
 * BENEFIT: Plain English explanations of why a student is at risk
 * EXCLUSIVITY: LLM-powered narrative generation from feature importance
 * USER TYPE: Faculty / Counselors
 * LOCATION: Student detail view, intervention planning
 */

const ExplainableRiskNarrative = ({ studentData, riskFactors }) => {
    const [narrative, setNarrative] = useState('');
    const [keyFactors, setKeyFactors] = useState([]);
    const [recommendations, setRecommendations] = useState([]);

    useEffect(() => {
        if (studentData && riskFactors) {
            // Sort factors by importance
            const sortedFactors = [...riskFactors].sort((a, b) => b.importance - a.importance);
            setKeyFactors(sortedFactors.slice(0, 5));

            // Generate narrative
            const narrativeText = generateNarrative(studentData, sortedFactors);
            setNarrative(narrativeText);

            // Generate recommendations
            const recs = generateRecommendations(sortedFactors);
            setRecommendations(recs);
        }
    }, [studentData, riskFactors]);

    const generateNarrative = (student, factors) => {
        const primaryFactor = factors[0];
        const secondaryFactor = factors[1];

        let text = `${student.name} is showing signs of disengagement. `;

        if (primaryFactor.factor === 'attendance') {
            text += `Attendance has been the primary concern, with ${primaryFactor.value}% attendance rate over the past month. `;
        } else if (primaryFactor.factor === 'assignment_completion') {
            text += `Assignment completion rate of ${primaryFactor.value}% indicates difficulty keeping pace with coursework. `;
        } else if (primaryFactor.factor === 'engagement_decline') {
            text += `Engagement has declined by ${primaryFactor.value}% compared to the cohort average. `;
        }

        if (secondaryFactor) {
            text += `Additionally, ${secondaryFactor.factor.replace('_', ' ')} (${secondaryFactor.value}) is contributing to the overall risk profile.`;
        }

        return text;
    };

    const generateRecommendations = (factors) => {
        const recs = [];
        factors.slice(0, 3).forEach(factor => {
            if (factor.factor === 'attendance') {
                recs.push('Schedule a one-on-one check-in to understand attendance barriers');
            } else if (factor.factor === 'assignment_completion') {
                recs.push('Offer extended office hours or tutoring support');
            } else if (factor.factor === 'engagement_decline') {
                recs.push('Connect student with peer study groups');
            }
        });
        return recs;
    };

    return (
        <div className="premium-card faculty-context" style={{ marginBottom: 'var(--space-lg)' }}>
            {/* Section Header - H3, semibold, dark gray */}
            <div className="section-header" style={{
                fontSize: 'var(--font-size-h3)',
                fontWeight: 'var(--font-weight-semibold)',
                color: 'var(--faculty-primary)',
                marginBottom: 'var(--space-md)'
            }}>
                Risk Explanation
            </div>

            {/* Narrative Text - Body, regular weight, generous line-height */}
            <div style={{
                fontSize: 'var(--font-size-body)',
                fontWeight: 'var(--font-weight-regular)',
                lineHeight: 'var(--line-height-relaxed)',
                color: 'var(--gray-700)',
                marginBottom: 'var(--space-lg)',
                padding: 'var(--space-lg)',
                background: 'var(--gray-50)',
                borderRadius: 'var(--radius-md)'
            }}>
                {narrative}
            </div>

            {/* Key Factors - Small, semibold, bulleted */}
            <div style={{ marginBottom: 'var(--space-lg)' }}>
                <div className="data-label" style={{
                    fontSize: 'var(--font-size-small)',
                    fontWeight: 'var(--font-weight-semibold)',
                    color: 'var(--gray-600)',
                    textTransform: 'uppercase',
                    letterSpacing: 'var(--letter-spacing-wide)',
                    marginBottom: 'var(--space-sm)'
                }}>
                    Top Risk Factors
                </div>
                <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                    {keyFactors.map((factor, idx) => (
                        <li key={idx} style={{
                            padding: 'var(--space-sm) var(--space-md)',
                            marginBottom: 'var(--space-xs)',
                            background: 'white',
                            border: 'var(--border-width-thin) solid var(--gray-200)',
                            borderRadius: 'var(--radius-sm)',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center'
                        }}>
                            <span style={{
                                fontSize: 'var(--font-size-small)',
                                fontWeight: 'var(--font-weight-medium)',
                                color: 'var(--gray-800)'
                            }}>
                                {factor.factor.replace('_', ' ').charAt(0).toUpperCase() + factor.factor.replace('_', ' ').slice(1)}
                            </span>
                            <span style={{
                                fontSize: 'var(--font-size-small)',
                                fontWeight: 'var(--font-weight-bold)',
                                color: 'var(--faculty-accent)',
                                fontFamily: 'var(--font-family-mono)'
                            }}>
                                {(factor.importance * 100).toFixed(0)}%
                            </span>
                        </li>
                    ))}
                </ul>
            </div>

            {/* Recommendations */}
            {recommendations.length > 0 && (
                <div>
                    <div className="data-label" style={{
                        fontSize: 'var(--font-size-small)',
                        fontWeight: 'var(--font-weight-semibold)',
                        color: 'var(--gray-600)',
                        textTransform: 'uppercase',
                        letterSpacing: 'var(--letter-spacing-wide)',
                        marginBottom: 'var(--space-sm)'
                    }}>
                        Recommended Interventions
                    </div>
                    <ul style={{ listStyle: 'disc', paddingLeft: 'var(--space-lg)', margin: 0 }}>
                        {recommendations.map((rec, idx) => (
                            <li key={idx} style={{
                                fontSize: 'var(--font-size-small)',
                                fontWeight: 'var(--font-weight-regular)',
                                color: 'var(--gray-700)',
                                marginBottom: 'var(--space-sm)',
                                lineHeight: 'var(--line-height-relaxed)'
                            }}>
                                {rec}
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
};

export default ExplainableRiskNarrative;
