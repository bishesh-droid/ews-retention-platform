import React, { useState, useEffect } from 'react';

/**
 * Course Risk Analysis Component
 * 
 * BENEFIT: Identify courses that consistently correlate with dropout
 * EXCLUSIVITY: Multi-cohort impact analysis
 * USER TYPE: Institution Administrators
 * LOCATION: Institutional insights dashboard
 */

const CourseRiskAnalysis = ({ courseData }) => {
    const [courses, setCourses] = useState([]);
    const [sortBy, setSortBy] = useState('riskCorrelation');

    useEffect(() => {
        if (courseData) {
            processCourseData(courseData);
        } else {
            // Mock data
            const mockCourses = [
                {
                    id: 'CS301',
                    name: 'Advanced Algorithms',
                    riskCorrelation: 0.68,
                    studentCount: 85,
                    avgDropoutRate: 0.34,
                    difficulty: 'High',
                    insights: 'High failure rate in midterm exam correlates with dropout'
                },
                {
                    id: 'MATH205',
                    name: 'Calculus II',
                    riskCorrelation: 0.54,
                    studentCount: 120,
                    avgDropoutRate: 0.28,
                    difficulty: 'High',
                    insights: 'Prerequisites gap leads to struggling'
                },
                {
                    id: 'PHY101',
                    name: 'Physics Fundamentals',
                    riskCorrelation: 0.42,
                    studentCount: 95,
                    avgDropoutRate: 0.22,
                    difficulty: 'Medium',
                    insights: 'Lab attendance issues correlate with risk'
                },
                {
                    id: 'ENG102',
                    name: 'Technical Writing',
                    riskCorrelation: 0.18,
                    studentCount: 110,
                    avgDropoutRate: 0.08,
                    difficulty: 'Low',
                    insights: 'Low risk factor, well-supported course'
                }
            ];

            setCourses(mockCourses.sort((a, b) => b.riskCorrelation - a.riskCorrelation));
        }
    }, [courseData, sortBy]);

    const processCourseData = (data) => {
        setCourses(data.sort((a, b) => b[sortBy] - a[sortBy]));
    };

    const getRiskLevel = (correlation) => {
        if (correlation >= 0.6) return { label: 'HIGH', color: 'var(--business-revenue)' };
        if (correlation >= 0.4) return { label: 'MEDIUM', color: 'var(--business-warning)' };
        return { label: 'LOW', color: 'var(--business-growth)' };
    };

    return (
        <div className="premium-card institutional-context" style={{ marginBottom: 'var(--space-lg)' }}>
            {/* Authority Header - Institutional style */}
            <div className="authority-header" style={{
                fontSize: 'var(--font-size-h1)',
                fontWeight: 'var(--font-weight-bold)',
                color: 'var(--institutional-primary)',
                borderTop: '3px solid var(--institutional-accent)',
                paddingTop: 'var(--space-lg)',
                marginTop: 0,
                marginBottom: 'var(--space-md)'
            }}>
                Course-Level Risk Analysis
            </div>

            <div style={{
                fontSize: 'var(--font-size-small)',
                color: 'var(--gray-600)',
                marginBottom: 'var(--space-xl)',
                lineHeight: 'var(--line-height-relaxed)'
            }}>
                Multi-cohort analysis identifying courses with elevated dropout correlation
            </div>

            {/* Sort Controls */}
            <div style={{
                display: 'flex',
                gap: 'var(--space-md)',
                marginBottom: 'var(--space-lg)'
            }}>
                <button
                    className="btn-premium"
                    style={{
                        background: sortBy === 'riskCorrelation' ? 'var(--institutional-accent)' : 'var(--gray-200)',
                        color: sortBy === 'riskCorrelation' ? 'white' : 'var(--gray-700)'
                    }}
                    onClick={() => setSortBy('riskCorrelation')}
                >
                    By Risk Correlation
                </button>
                <button
                    className="btn-premium"
                    style={{
                        background: sortBy === 'avgDropoutRate' ? 'var(--institutional-accent)' : 'var(--gray-200)',
                        color: sortBy === 'avgDropoutRate' ? 'white' : 'var(--gray-700)'
                    }}
                    onClick={() => setSortBy('avgDropoutRate')}
                >
                    By Dropout Rate
                </button>
            </div>

            {/* Course Cards */}
            <div>
                {courses.map((course, idx) => {
                    const riskLevel = getRiskLevel(course.riskCorrelation);
                    return (
                        <div
                            key={course.id}
                            style={{
                                padding: 'var(--space-lg)',
                                background: 'var(--surface-color)',
                                border: `var(--border-width-medium) solid ${riskLevel.color}`,
                                borderLeft: `6px solid ${riskLevel.color}`,
                                borderRadius: 'var(--radius-md)',
                                marginBottom: 'var(--space-md)'
                            }}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-md)' }}>
                                {/* Course Name - Body, semibold */}
                                <div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                                        <span style={{
                                            fontSize: 'var(--font-size-small)',
                                            fontWeight: 'var(--font-weight-bold)',
                                            color: 'var(--gray-600)',
                                            fontFamily: 'var(--font-family-mono)'
                                        }}>
                                            {course.id}
                                        </span>
                                        <span style={{
                                            fontSize: 'var(--font-size-body)',
                                            fontWeight: 'var(--font-weight-semibold)',
                                            color: 'var(--gray-900)'
                                        }}>
                                            {course.name}
                                        </span>
                                    </div>
                                    <div style={{
                                        fontSize: 'var(--font-size-small)',
                                        color: 'var(--gray-600)',
                                        marginTop: 'var(--space-xs)'
                                    }}>
                                        {course.studentCount} students enrolled • {course.difficulty} difficulty
                                    </div>
                                </div>

                                {/* Risk Badge */}
                                <div style={{
                                    padding: '4px 12px',
                                    background: `${riskLevel.color}15`,
                                    color: riskLevel.color,
                                    fontSize: 'var(--font-size-caption)',
                                    fontWeight: 'var(--font-weight-bold)',
                                    borderRadius: 'var(--radius-sm)',
                                    textTransform: 'uppercase',
                                    letterSpacing: 'var(--letter-spacing-wide)'
                                }}>
                                    {riskLevel.label} RISK
                                </div>
                            </div>

                            {/* Metrics */}
                            <div style={{
                                display: 'grid',
                                gridTemplateColumns: 'repeat(2, 1fr)',
                                gap: 'var(--space-md)',
                                marginBottom: 'var(--space-md)'
                            }}>
                                <div>
                                    <div style={{
                                        fontSize: 'var(--font-size-caption)',
                                        color: 'var(--gray-600)',
                                        textTransform: 'uppercase',
                                        marginBottom: 'var(--space-xs)'
                                    }}>
                                        Risk Correlation
                                    </div>
                                    <div style={{
                                        fontSize: 'var(--font-size-h2)',
                                        fontWeight: 'var(--font-weight-bold)',
                                        color: riskLevel.color,
                                        fontFamily: 'var(--font-family-mono)'
                                    }}>
                                        {(course.riskCorrelation * 100).toFixed(0)}%
                                    </div>
                                </div>

                                <div>
                                    <div style={{
                                        fontSize: 'var(--font-size-caption)',
                                        color: 'var(--gray-600)',
                                        textTransform: 'uppercase',
                                        marginBottom: 'var(--space-xs)'
                                    }}>
                                        Avg Dropout Rate
                                    </div>
                                    <div style={{
                                        fontSize: 'var(--font-size-h2)',
                                        fontWeight: 'var(--font-weight-bold)',
                                        color: riskLevel.color,
                                        fontFamily: 'var(--font-family-mono)'
                                    }}>
                                        {(course.avgDropoutRate * 100).toFixed(0)}%
                                    </div>
                                </div>
                            </div>

                            {/* Insight Summary - Small, regular, background highlight */}
                            <div style={{
                                padding: 'var(--space-md)',
                                background: 'var(--gray-50)',
                                borderRadius: 'var(--radius-sm)',
                                fontSize: 'var(--font-size-small)',
                                fontWeight: 'var(--font-weight-regular)',
                                color: 'var(--gray-700)',
                                lineHeight: 'var(--line-height-relaxed)'
                            }}>
                                <strong>Insight:</strong> {course.insights}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default CourseRiskAnalysis;
