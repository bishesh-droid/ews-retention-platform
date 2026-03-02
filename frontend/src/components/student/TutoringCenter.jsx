import React, { useState } from 'react';
import { Row, Col } from 'react-bootstrap';
import { FaUsers, FaBookOpen, FaLightbulb, FaStar, FaVideo, FaFileAlt, FaChalkboardTeacher } from 'react-icons/fa';

const IMPROVEMENT_TIPS = [
    {
        subject: 'Data Science',
        icon: '📊',
        score: 62,
        risk: 'high',
        action: 'Book Tutoring',
        tips: [
            'Review pandas & NumPy fundamentals — complete 2 short exercises daily to build muscle memory',
            'Rewatch recorded lectures from Weeks 3–4 on feature engineering (available in course portal)',
            'Schedule a session with Dr. Martinez before Thursday\'s quiz — she specialises in exactly this topic',
        ],
    },
    {
        subject: 'Statistics',
        icon: '📈',
        score: 68,
        risk: 'medium',
        action: 'Join Study Group',
        tips: [
            'Practise hypothesis testing problems using the Coursera Statistics module (free with your student ID)',
            'Join the "Stats Problem Solving Circle" study group — avg members score 12% higher on exams',
            'Use Khan Academy\'s free statistics course to reinforce the fundamentals before the next assignment',
        ],
    },
    {
        subject: 'Mathematics',
        icon: '✏️',
        score: 78,
        risk: 'medium',
        action: 'View Resources',
        tips: [
            'You\'re very close to an A — focus on integration problems from Chapter 7 in the textbook',
            'Use WolframAlpha to self-check homework solutions and understand step-by-step breakdowns',
        ],
    },
];

const TUTORS = [
    {
        name: 'Dr. Sarah Martinez',
        subject: 'Data Science & Machine Learning',
        rating: 4.9, reviews: 142,
        available: 'Today, 3:00 PM',
        avatar: 'SM', color: '#8B5CF6',
        tag: 'Most Recommended',
        specialties: ['Pandas', 'ML Models', 'Feature Eng.'],
    },
    {
        name: 'Prof. James Chen',
        subject: 'Mathematics & Statistics',
        rating: 4.8, reviews: 98,
        available: 'Tomorrow, 10:00 AM',
        avatar: 'JC', color: '#10B981',
        tag: 'Student Favourite',
        specialties: ['Calculus', 'Hypothesis Testing', 'Regression'],
    },
    {
        name: 'Ms. Priya Kapoor',
        subject: 'Programming & Computer Science',
        rating: 4.7, reviews: 76,
        available: 'Wed, 2:00 PM',
        avatar: 'PK', color: '#F59E0B',
        tag: 'Quick Responder',
        specialties: ['Python', 'Algorithms', 'OOP'],
    },
    {
        name: 'Dr. Tom Williams',
        subject: 'English & Academic Writing',
        rating: 4.6, reviews: 55,
        available: 'Thu, 11:00 AM',
        avatar: 'TW', color: '#3B82F6',
        tag: '',
        specialties: ['Essay Structure', 'Research Writing', 'Citations'],
    },
];

const STUDY_GROUPS = [
    { name: 'Data Science Study Squad',      members: 6, max: 8, next: 'Today, 5:00 PM',    topic: 'Pandas & EDA',          joined: false },
    { name: 'Stats Problem Solving Circle',  members: 4, max: 6, next: 'Tomorrow, 7:00 PM', topic: 'Hypothesis Testing',    joined: true  },
    { name: 'Math Calculus Crew',            members: 5, max: 8, next: 'Wed, 4:00 PM',      topic: 'Integration Methods',  joined: false },
    { name: 'Python Programming Workshop',   members: 7, max: 10,next: 'Thu, 6:00 PM',      topic: 'Recursion & Trees',    joined: false },
];

const RESOURCES = [
    {
        category: 'Video Lectures',
        icon: <FaVideo size={13} color="#8B5CF6" />,
        items: [
            'Data Science: Pandas Deep Dive (42 min)',
            'Statistics: Regression Analysis (38 min)',
            'Math: Calculus Integration Techniques (51 min)',
            'Programming: Recursive Algorithms (29 min)',
        ],
    },
    {
        category: 'Practice Sets',
        icon: <FaFileAlt size={13} color="#10B981" />,
        items: [
            'Stats Chapters 5–7 Problem Bank',
            'Python Coding Challenges (Beginner Level)',
            'Math Integration Worksheet — 20 Problems',
            'Data Science Quiz Practice Set',
        ],
    },
    {
        category: 'Quick Reference',
        icon: <FaBookOpen size={13} color="#F59E0B" />,
        items: [
            'Statistics Formula Cheat Sheet (PDF)',
            'Python Syntax Quick Guide',
            'GPA Calculator Tool',
            'APA / MLA Citation Generator',
        ],
    },
];

const riskColor = { high: '#EF4444', medium: '#F59E0B', low: '#10B981' };
const riskBg    = { high: 'rgba(239,68,68,0.08)', medium: 'rgba(245,158,11,0.08)', low: 'rgba(16,185,129,0.08)' };
const riskBorder = { high: 'rgba(239,68,68,0.22)', medium: 'rgba(245,158,11,0.22)', low: 'rgba(16,185,129,0.22)' };

const TutoringCenter = () => {
    const [booked,  setBooked]  = useState({});
    const [joined,  setJoined]  = useState(
        STUDY_GROUPS.reduce((acc, g, i) => ({ ...acc, [i]: g.joined }), {})
    );

    return (
        <div>
            {/* ── Personalised Improvement Plan ────────────────────── */}
            <div className="glass-panel p-4 mb-4">
                <div className="d-flex align-items-center gap-2 mb-1">
                    <FaLightbulb color="#F59E0B" size={15} />
                    <h6 className="fw-bold m-0" style={{ color: '#EDE9FE' }}>Personalised Improvement Plan</h6>
                </div>
                <p style={{ fontSize: '0.82rem', color: '#B8AADA', marginBottom: '1.25rem' }}>
                    AI-curated action steps based on your current performance and subject risk levels
                </p>

                <div className="d-flex flex-column gap-3">
                    {IMPROVEMENT_TIPS.map((tip, i) => (
                        <div key={i} style={{
                            padding: '1rem 1.25rem',
                            background: riskBg[tip.risk],
                            border: `1px solid ${riskBorder[tip.risk]}`,
                            borderLeft: `4px solid ${riskColor[tip.risk]}`,
                            borderRadius: 12,
                        }}>
                            <div className="d-flex justify-content-between align-items-start mb-2">
                                <div className="d-flex align-items-center gap-2">
                                    <span style={{ fontSize: '1.3rem' }}>{tip.icon}</span>
                                    <div>
                                        <div style={{ fontWeight: 700, color: '#EDE9FE', fontSize: '0.9rem' }}>{tip.subject}</div>
                                        <div style={{ fontSize: '0.72rem', color: riskColor[tip.risk] }}>
                                            Score: {tip.score}/100
                                        </div>
                                    </div>
                                </div>
                                <button style={{
                                    padding: '5px 16px', borderRadius: 99, border: 'none', cursor: 'pointer',
                                    background: riskColor[tip.risk], color: 'white',
                                    fontSize: '0.75rem', fontWeight: 700, flexShrink: 0,
                                }}>
                                    {tip.action}
                                </button>
                            </div>
                            <ul style={{ margin: 0, paddingLeft: '1.1rem' }}>
                                {tip.tips.map((t, j) => (
                                    <li key={j} style={{ fontSize: '0.82rem', color: '#C4B5FD', marginBottom: 5, lineHeight: 1.55 }}>
                                        {t}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ))}
                </div>
            </div>

            {/* ── Tutors + Study Groups ─────────────────────────────── */}
            <Row className="g-4 mb-4">
                {/* Available tutors */}
                <Col lg={7}>
                    <div className="glass-panel p-4 h-100">
                        <div className="d-flex align-items-center gap-2 mb-1">
                            <FaChalkboardTeacher color="#8B5CF6" size={14} />
                            <h6 className="fw-bold m-0" style={{ color: '#EDE9FE' }}>Available Tutors</h6>
                        </div>
                        <p style={{ fontSize: '0.82rem', color: '#B8AADA', marginBottom: '1.25rem' }}>
                            Vetted instructors — instant booking, personalised 1-on-1 support
                        </p>

                        <div className="d-flex flex-column gap-3">
                            {TUTORS.map((t, i) => (
                                <div key={i} style={{
                                    display: 'flex', alignItems: 'center', gap: '0.85rem',
                                    padding: '0.85rem 1rem',
                                    background: 'rgba(139,92,246,0.06)',
                                    border: '1px solid rgba(139,92,246,0.13)',
                                    borderRadius: 12,
                                }}>
                                    {/* Avatar */}
                                    <div style={{
                                        width: 46, height: 46, borderRadius: '50%', flexShrink: 0,
                                        background: `linear-gradient(135deg, ${t.color}, ${t.color}88)`,
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        fontWeight: 800, fontSize: '0.85rem', color: 'white',
                                    }}>
                                        {t.avatar}
                                    </div>

                                    {/* Info */}
                                    <div style={{ flex: 1, minWidth: 0 }}>
                                        <div className="d-flex align-items-center gap-2 mb-1 flex-wrap">
                                            <span style={{ fontWeight: 700, color: '#EDE9FE', fontSize: '0.875rem' }}>
                                                {t.name}
                                            </span>
                                            {t.tag && (
                                                <span style={{
                                                    fontSize: '0.62rem', background: 'rgba(139,92,246,0.18)',
                                                    color: '#C4B5FD', padding: '2px 7px', borderRadius: 99,
                                                }}>
                                                    {t.tag}
                                                </span>
                                            )}
                                        </div>
                                        <div style={{ fontSize: '0.75rem', color: '#B8AADA' }}>{t.subject}</div>
                                        <div style={{ fontSize: '0.72rem', color: '#B8AADA', marginTop: 3 }}>
                                            <span style={{ color: '#F59E0B' }}>★</span> {t.rating} ({t.reviews} reviews)
                                            &nbsp;·&nbsp; Next: <span style={{ color: '#10B981' }}>{t.available}</span>
                                        </div>
                                        <div style={{ display: 'flex', gap: 4, marginTop: 5, flexWrap: 'wrap' }}>
                                            {t.specialties.map(sp => (
                                                <span key={sp} style={{
                                                    fontSize: '0.62rem', background: 'rgba(139,92,246,0.1)',
                                                    color: '#A78BFA', padding: '2px 6px', borderRadius: 6,
                                                }}>
                                                    {sp}
                                                </span>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Book button */}
                                    <button
                                        onClick={() => setBooked(b => ({ ...b, [i]: true }))}
                                        style={{
                                            padding: '7px 18px', borderRadius: 9, border: 'none',
                                            cursor: booked[i] ? 'default' : 'pointer',
                                            background: booked[i] ? 'rgba(16,185,129,0.15)' : '#8B5CF6',
                                            color: booked[i] ? '#10B981' : 'white',
                                            fontSize: '0.78rem', fontWeight: 700, flexShrink: 0,
                                            transition: 'all 0.2s',
                                        }}
                                    >
                                        {booked[i] ? '✓ Booked' : 'Book'}
                                    </button>
                                </div>
                            ))}
                        </div>
                    </div>
                </Col>

                {/* Study groups */}
                <Col lg={5}>
                    <div className="glass-panel p-4 h-100">
                        <div className="d-flex align-items-center gap-2 mb-1">
                            <FaUsers color="#8B5CF6" size={13} />
                            <h6 className="fw-bold m-0" style={{ color: '#EDE9FE' }}>Peer Study Groups</h6>
                        </div>
                        <p style={{ fontSize: '0.82rem', color: '#B8AADA', marginBottom: '1.25rem' }}>
                            Students in study groups perform <strong style={{ color: '#10B981' }}>14% better</strong> on average
                        </p>

                        <div className="d-flex flex-column gap-3">
                            {STUDY_GROUPS.map((g, i) => (
                                <div key={i} style={{
                                    padding: '0.85rem 1rem',
                                    background: 'rgba(139,92,246,0.06)',
                                    border: joined[i] ? '1px solid rgba(16,185,129,0.25)' : '1px solid rgba(139,92,246,0.13)',
                                    borderRadius: 12,
                                }}>
                                    <div className="d-flex justify-content-between align-items-start mb-1">
                                        <div style={{ fontWeight: 700, color: '#EDE9FE', fontSize: '0.875rem', lineHeight: 1.3 }}>
                                            {g.name}
                                        </div>
                                        <button
                                            onClick={() => setJoined(j => ({ ...j, [i]: !j[i] }))}
                                            style={{
                                                padding: '4px 12px', borderRadius: 99, border: 'none',
                                                cursor: 'pointer', flexShrink: 0, marginLeft: 8,
                                                background: joined[i] ? 'rgba(16,185,129,0.15)' : 'rgba(139,92,246,0.15)',
                                                color: joined[i] ? '#10B981' : '#A78BFA',
                                                fontSize: '0.72rem', fontWeight: 700,
                                            }}
                                        >
                                            {joined[i] ? '✓ Joined' : 'Join'}
                                        </button>
                                    </div>

                                    <div style={{ fontSize: '0.75rem', color: '#B8AADA', marginBottom: 6 }}>
                                        Topic: <span style={{ color: '#C4B5FD' }}>{g.topic}</span>
                                    </div>

                                    <div className="d-flex justify-content-between mb-2">
                                        <span style={{ fontSize: '0.72rem', color: '#10B981' }}>Next: {g.next}</span>
                                        <span style={{ fontSize: '0.72rem', color: '#B8AADA' }}>{g.members}/{g.max} members</span>
                                    </div>

                                    <div style={{ height: 5, background: 'rgba(139,92,246,0.15)', borderRadius: 99, overflow: 'hidden' }}>
                                        <div style={{
                                            width: `${(g.members / g.max) * 100}%`, height: '100%',
                                            background: joined[i] ? '#10B981' : '#8B5CF6', borderRadius: 99,
                                        }} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </Col>
            </Row>

            {/* ── Learning Resources ────────────────────────────────── */}
            <div className="glass-panel p-4">
                <div className="d-flex align-items-center gap-2 mb-1">
                    <FaBookOpen color="#8B5CF6" size={13} />
                    <h6 className="fw-bold m-0" style={{ color: '#EDE9FE' }}>Learning Resources</h6>
                </div>
                <p style={{ fontSize: '0.82rem', color: '#B8AADA', marginBottom: '1.25rem' }}>
                    Curated materials aligned to your weakest topics — updated weekly
                </p>

                <Row className="g-3">
                    {RESOURCES.map((cat, i) => (
                        <Col md={4} key={i}>
                            <div style={{
                                padding: '1rem', height: '100%',
                                background: 'rgba(139,92,246,0.07)',
                                border: '1px solid rgba(139,92,246,0.15)',
                                borderRadius: 12,
                            }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: '0.85rem' }}>
                                    {cat.icon}
                                    <span style={{ fontWeight: 700, color: '#EDE9FE', fontSize: '0.875rem' }}>
                                        {cat.category}
                                    </span>
                                </div>

                                {cat.items.map((item, j) => (
                                    <div key={j} style={{
                                        display: 'flex', alignItems: 'flex-start', gap: 7,
                                        padding: '0.42rem 0',
                                        borderBottom: j < cat.items.length - 1 ? '1px solid rgba(139,92,246,0.1)' : 'none',
                                        cursor: 'pointer',
                                    }}>
                                        <div style={{
                                            width: 6, height: 6, borderRadius: '50%',
                                            background: '#8B5CF6', flexShrink: 0, marginTop: 5,
                                        }} />
                                        <span style={{
                                            fontSize: '0.78rem', color: '#C4B5FD', lineHeight: 1.45,
                                            transition: 'color 0.15s',
                                        }}
                                            onMouseEnter={e => e.currentTarget.style.color = '#EDE9FE'}
                                            onMouseLeave={e => e.currentTarget.style.color = '#C4B5FD'}
                                        >
                                            {item}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </Col>
                    ))}
                </Row>
            </div>
        </div>
    );
};

export default TutoringCenter;
