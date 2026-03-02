import React from 'react';
import { Row, Col } from 'react-bootstrap';
import {
    RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
    ReferenceLine, ResponsiveContainer,
} from 'recharts';

const SUBJECTS = [
    { name: 'Mathematics',  score: 78, grade: 'B+', trend: +3,  risk: 'medium', credits: 3 },
    { name: 'English Comp', score: 85, grade: 'A',  trend: +5,  risk: 'low',    credits: 3 },
    { name: 'Data Science', score: 62, grade: 'C+', trend: -2,  risk: 'high',   credits: 4 },
    { name: 'World History',score: 91, grade: 'A',  trend: +2,  risk: 'low',    credits: 3 },
    { name: 'Programming',  score: 73, grade: 'B',  trend: +8,  risk: 'medium', credits: 4 },
    { name: 'Statistics',   score: 68, grade: 'B-', trend: -4,  risk: 'medium', credits: 3 },
];

const GPA_HISTORY = [
    { week: 'Wk 1', gpa: 2.90 },
    { week: 'Wk 2', gpa: 3.00 },
    { week: 'Wk 3', gpa: 2.85 },
    { week: 'Wk 4', gpa: 3.10 },
    { week: 'Wk 5', gpa: 3.05 },
    { week: 'Wk 6', gpa: 3.20 },
    { week: 'Wk 7', gpa: 3.30 },
    { week: 'Wk 8', gpa: 3.20 },
];

const radarData = SUBJECTS.map(s => ({
    subject: s.name.split(' ')[0],
    score: s.score,
}));

const tooltipStyle = {
    contentStyle: { background: '#1E1535', border: '1px solid rgba(139,92,246,0.3)', borderRadius: 10 },
    labelStyle: { color: '#EDE9FE', fontWeight: 600 },
    itemStyle: { color: '#C4B5FD' },
};

const riskColor = { low: '#10B981', medium: '#F59E0B', high: '#EF4444' };
const riskBg    = { low: 'rgba(16,185,129,0.12)', medium: 'rgba(245,158,11,0.12)', high: 'rgba(239,68,68,0.12)' };
const riskLabel = { low: 'On Track', medium: 'Attention', high: 'At Risk' };

const AcademicPerformance = () => {
    const avgGpa      = (GPA_HISTORY.reduce((s, d) => s + d.gpa, 0) / GPA_HISTORY.length).toFixed(2);
    const atRiskCount = SUBJECTS.filter(s => s.risk === 'high').length;
    const improving   = SUBJECTS.filter(s => s.trend > 0).length;
    const totalCredits = SUBJECTS.reduce((s, c) => s + c.credits, 0);

    return (
        <div>
            {/* Mini stat cards */}
            <Row className="g-3 mb-4">
                {[
                    { label: 'Current GPA',       value: '3.2',       color: '#8B5CF6', icon: '🎓' },
                    { label: 'Semester Avg GPA',   value: avgGpa,      color: '#10B981', icon: '📈' },
                    { label: 'Subjects At Risk',   value: atRiskCount, color: '#EF4444', icon: '⚠️' },
                    { label: 'Improving Subjects', value: improving,   color: '#F59E0B', icon: '↑' },
                ].map(s => (
                    <Col xs={6} md={3} key={s.label}>
                        <div className="glass-panel p-3 text-center h-100">
                            <div style={{ fontSize: '1.4rem', marginBottom: 4 }}>{s.icon}</div>
                            <div style={{ fontSize: '0.62rem', textTransform: 'uppercase', letterSpacing: '0.08em', color: '#B8AADA', marginBottom: 4 }}>
                                {s.label}
                            </div>
                            <div style={{ fontSize: '1.8rem', fontWeight: 800, fontFamily: 'var(--font-family-mono)', color: s.color }}>
                                {s.value}
                            </div>
                        </div>
                    </Col>
                ))}
            </Row>

            {/* Charts row */}
            <Row className="g-4 mb-4">
                {/* Radar */}
                <Col lg={5}>
                    <div className="glass-panel p-4 h-100">
                        <h6 className="fw-bold mb-1" style={{ color: '#EDE9FE' }}>Subject Performance Radar</h6>
                        <p style={{ fontSize: '0.8rem', color: '#B8AADA', marginBottom: '0.5rem' }}>
                            Scores across all {SUBJECTS.length} enrolled courses
                        </p>
                        <ResponsiveContainer width="100%" height={250}>
                            <RadarChart data={radarData} margin={{ top: 10, right: 20, left: 20, bottom: 10 }}>
                                <PolarGrid stroke="rgba(139,92,246,0.2)" />
                                <PolarAngleAxis dataKey="subject" tick={{ fill: '#B8AADA', fontSize: 11 }} />
                                <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#B8AADA', fontSize: 9 }} />
                                <Radar
                                    name="Score"
                                    dataKey="score"
                                    stroke="#8B5CF6"
                                    fill="#8B5CF6"
                                    fillOpacity={0.3}
                                    strokeWidth={2}
                                />
                                <Tooltip {...tooltipStyle} formatter={v => [`${v}/100`, 'Score']} />
                            </RadarChart>
                        </ResponsiveContainer>
                    </div>
                </Col>

                {/* GPA Trend */}
                <Col lg={7}>
                    <div className="glass-panel p-4 h-100">
                        <h6 className="fw-bold mb-1" style={{ color: '#EDE9FE' }}>GPA Trend — Last 8 Weeks</h6>
                        <p style={{ fontSize: '0.8rem', color: '#B8AADA', marginBottom: '0.5rem' }}>
                            Grade point average trajectory this semester
                        </p>
                        <ResponsiveContainer width="100%" height={250}>
                            <AreaChart data={GPA_HISTORY} margin={{ top: 8, right: 16, left: -16, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="gpaGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%"  stopColor="#8B5CF6" stopOpacity={0.4} />
                                        <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.1)" />
                                <XAxis dataKey="week" tick={{ fill: '#B8AADA', fontSize: 11 }} axisLine={false} tickLine={false} />
                                <YAxis domain={[2.4, 4.0]} tick={{ fill: '#B8AADA', fontSize: 11 }} axisLine={false} tickLine={false} />
                                <Tooltip {...tooltipStyle} formatter={v => [v.toFixed(2), 'GPA']} />
                                <ReferenceLine y={3.0} stroke="#F59E0B" strokeDasharray="5 3"
                                    label={{ value: 'Good Standing (3.0)', fill: '#F59E0B', fontSize: 10, position: 'insideTopRight' }}
                                />
                                <ReferenceLine y={2.0} stroke="#EF4444" strokeDasharray="3 3"
                                    label={{ value: 'Min. Required (2.0)', fill: '#EF4444', fontSize: 10, position: 'insideBottomRight' }}
                                />
                                <Area type="monotone" dataKey="gpa" name="GPA" stroke="#8B5CF6" fill="url(#gpaGrad)"
                                    strokeWidth={2.5} dot={{ fill: '#8B5CF6', r: 3, strokeWidth: 0 }} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                </Col>
            </Row>

            {/* Course breakdown table */}
            <div className="glass-panel p-4">
                <div className="d-flex justify-content-between align-items-center mb-3">
                    <div>
                        <h6 className="fw-bold mb-0" style={{ color: '#EDE9FE' }}>Course Breakdown</h6>
                        <p style={{ fontSize: '0.8rem', color: '#B8AADA', margin: 0 }}>
                            {totalCredits} credit hours · {SUBJECTS.length} active courses
                        </p>
                    </div>
                    <span style={{
                        fontSize: '0.7rem', fontWeight: 700, padding: '4px 12px', borderRadius: 99,
                        background: 'rgba(139,92,246,0.15)', color: '#C4B5FD',
                    }}>
                        Spring 2026
                    </span>
                </div>

                <div className="d-flex flex-column gap-2">
                    {SUBJECTS.map((s, i) => (
                        <div key={i} style={{
                            display: 'flex', alignItems: 'center', gap: '1rem',
                            padding: '0.85rem 1rem',
                            background: 'rgba(139,92,246,0.05)',
                            border: `1px solid ${riskBg[s.risk].replace('0.12', '0.2')}`,
                            borderLeft: `3px solid ${riskColor[s.risk]}`,
                            borderRadius: 10,
                        }}>
                            {/* Score circle */}
                            <div style={{
                                width: 46, height: 46, borderRadius: '50%', flexShrink: 0,
                                background: riskBg[s.risk],
                                border: `2px solid ${riskColor[s.risk]}`,
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                fontWeight: 800, fontSize: '0.85rem', fontFamily: 'var(--font-family-mono)',
                                color: riskColor[s.risk],
                            }}>
                                {s.score}
                            </div>

                            {/* Name & status */}
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ fontWeight: 600, color: '#EDE9FE', fontSize: '0.9rem' }}>{s.name}</div>
                                <div style={{ fontSize: '0.72rem', marginTop: 2 }}>
                                    <span style={{
                                        background: riskBg[s.risk], color: riskColor[s.risk],
                                        padding: '1px 8px', borderRadius: 99,
                                    }}>
                                        {riskLabel[s.risk]}
                                    </span>
                                    <span style={{ color: '#B8AADA', marginLeft: 6 }}>{s.credits} credits</span>
                                </div>
                            </div>

                            {/* Grade */}
                            <div style={{ textAlign: 'center', minWidth: 50 }}>
                                <div style={{ fontSize: '1.3rem', fontWeight: 800, fontFamily: 'var(--font-family-mono)', color: '#EDE9FE' }}>
                                    {s.grade}
                                </div>
                                <div style={{ fontSize: '0.62rem', color: '#B8AADA' }}>Grade</div>
                            </div>

                            {/* Trend delta */}
                            <div style={{ textAlign: 'center', minWidth: 64 }}>
                                <div style={{
                                    fontSize: '0.85rem', fontWeight: 700,
                                    color: s.trend > 0 ? '#10B981' : s.trend < 0 ? '#EF4444' : '#B8AADA',
                                }}>
                                    {s.trend > 0 ? `▲ +${s.trend}` : s.trend < 0 ? `▼ ${s.trend}` : '— 0'}
                                </div>
                                <div style={{ fontSize: '0.62rem', color: '#B8AADA' }}>vs last wk</div>
                            </div>

                            {/* Progress bar */}
                            <div style={{ width: 80, flexShrink: 0 }}>
                                <div style={{ height: 5, background: 'rgba(139,92,246,0.15)', borderRadius: 99, overflow: 'hidden' }}>
                                    <div style={{
                                        width: `${s.score}%`, height: '100%',
                                        background: riskColor[s.risk], borderRadius: 99,
                                        transition: 'width 0.5s ease',
                                    }} />
                                </div>
                                <div style={{ fontSize: '0.62rem', color: '#B8AADA', marginTop: 3, textAlign: 'right' }}>
                                    {s.score}/100
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Advice banner for at-risk courses */}
                <div style={{
                    marginTop: '1rem', padding: '0.75rem 1rem',
                    background: 'rgba(239,68,68,0.07)',
                    border: '1px solid rgba(239,68,68,0.2)',
                    borderRadius: 10, display: 'flex', gap: '0.75rem', alignItems: 'center',
                }}>
                    <span style={{ fontSize: '1.2rem' }}>💡</span>
                    <span style={{ fontSize: '0.82rem', color: '#C4B5FD' }}>
                        <strong style={{ color: '#EF4444' }}>Data Science</strong> is your lowest-scoring course.
                        Visiting the <strong style={{ color: '#EDE9FE' }}>Tutoring</strong> tab to book a session with Dr. Martinez is strongly recommended.
                    </span>
                </div>
            </div>
        </div>
    );
};

export default AcademicPerformance;
