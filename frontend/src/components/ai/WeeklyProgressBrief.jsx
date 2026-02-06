import React, { useState, useEffect } from 'react';

/**
 * Weekly Progress Brief Component
 * 
 * BENEFIT: Scannable weekly summary of achievements and attention areas
 * EXCLUSIVITY: AI-generated personalized messaging based on behavior patterns
 * USER TYPE: Students
 * LOCATION: Student Portal, sent via email
 */

const WeeklyProgressBrief = ({ weekData, studentName }) => {
    const [highlights, setHighlights] = useState([]);
    const [focusAreas, setFocusAreas] = useState([]);
    const [weeklyMetrics, setWeeklyMetrics] = useState(null);

    useEffect(() => {
        if (weekData) {
            // Generate highlights
            const newHighlights = [];
            if (weekData.assignmentsCompleted >= 3) {
                newHighlights.push(`Completed ${weekData.assignmentsCompleted} assignments this week`);
            }
            if (weekData.attendanceRate >= 0.9) {
                newHighlights.push('Perfect attendance this week! 🎉');
            }
            if (weekData.engagementImprovement > 0) {
                newHighlights.push(`Engagement improved by ${weekData.engagementImprovement}%`);
            }
            setHighlights(newHighlights.length > 0 ? newHighlights : ['Stay engaged this week!']);

            // Generate focus areas (calm, not alarming)
            const areas = [];
            if (weekData.missedAssignments > 0) {
                areas.push(`${weekData.missedAssignments} assignment${weekData.missedAssignments > 1 ? 's' : ''} to catch up on`);
            }
            if (weekData.lowEngagementDays >= 3) {
                areas.push('Consider joining more study sessions');
            }
            setFocusAreas(areas);

            setWeeklyMetrics({
                studyTime: weekData.totalStudyTimeMinutes || 0,
                interactions: weekData.facultyInteractions || 0,
                resourcesViewed: weekData.resourcesViewed || 0
            });
        }
    }, [weekData]);

    return (
        <div className="premium-card student-context" style={{ marginBottom: 'var(--space-lg)' }}>
            {/* Brief Title - H2 typography */}
            <div className="card-header" style={{ fontSize: 'var(--font-size-h2)', fontWeight: 'var(--font-weight-semibold)', marginBottom: 'var(--space-md)' }}>
                This Week's Progress
            </div>

            <div style={{ fontSize: 'var(--font-size-small)', color: 'var(--gray-600)', marginBottom: 'var(--space-lg)' }}>
                Week of {new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
            </div>

            {/* Highlights Section */}
            <div style={{ marginBottom: 'var(--space-lg)' }}>
                <div style={{ fontSize: 'var(--font-size-body)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--student-success)', marginBottom: 'var(--space-sm)' }}>
                    ✨ Highlights
                </div>
                <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                    {highlights.map((highlight, idx) => (
                        <li key={idx} style={{ fontSize: 'var(--font-size-body)', fontWeight: 'var(--font-weight-medium)', color: 'var(--gray-700)', padding: 'var(--space-sm) 0', paddingLeft: 'var(--space-md)', borderLeft: '3px solid var(--student-success)', marginBottom: 'var(--space-sm)', lineHeight: 'var(--line-height-relaxed)' }}>
                            {highlight}
                        </li>
                    ))}
                </ul>
            </div>

            {/* Focus Areas (if any) */}
            {focusAreas.length > 0 && (
                <div style={{ marginBottom: 'var(--space-lg)' }}>
                    <div style={{ fontSize: 'var(--font-size-body)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--student-warning)', marginBottom: 'var(--space-sm)' }}>
                        📌 Areas to Focus On
                    </div>
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                        {focusAreas.map((area, idx) => (
                            <li key={idx} style={{ fontSize: 'var(--font-size-body)', fontWeight: 'var(--font-weight-medium)', color: 'var(--gray-700)', padding: 'var(--space-sm) 0', paddingLeft: 'var(--space-md)', borderLeft: '3px solid var(--student-warning)', marginBottom: 'var(--space-sm)', lineHeight: 'var(--line-height-relaxed)' }}>
                                {area}
                            </li>
                        ))}
                    </ul>
                </div>
            )}

            {/* Weekly Metrics - Small typography with monospace numbers */}
            {weeklyMetrics && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 'var(--space-md)', padding: 'var(--space-md)', background: 'var(--gray-50)', borderRadius: 'var(--radius-md)' }}>
                    <MetricItem label="Study Time" value={`${Math.round(weeklyMetrics.studyTime / 60)}h`} />
                    <MetricItem label="Interactions" value={weeklyMetrics.interactions} />
                    <MetricItem label="Resources" value={weeklyMetrics.resourcesViewed} />
                </div>
            )}
        </div>
    );
};

const MetricItem = ({ label, value }) => (
    <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 'var(--font-size-h3)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--student-primary)', fontFamily: 'var(--font-family-mono)' }}>
            {value}
        </div>
        <div style={{ fontSize: 'var(--font-size-caption)', color: 'var(--gray-600)', marginTop: 'var(--space-xs)' }}>
            {label}
        </div>
    </div>
);

export default WeeklyProgressBrief;
