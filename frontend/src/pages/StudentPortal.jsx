import React, { useState, useEffect, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { Row, Col, Container } from 'react-bootstrap';
import { motion } from 'framer-motion';
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import {
    FaTachometerAlt, FaGraduationCap, FaChalkboardTeacher, FaBullseye,
    FaCalendarAlt, FaClock, FaBookOpen, FaUsers, FaCheckCircle,
    FaExclamationTriangle, FaHeart,
} from 'react-icons/fa';
import StudentHealthScore from '../components/student/StudentHealthScore';
import WeeklyProgressBrief from '../components/ai/WeeklyProgressBrief';
import RiskChangeExplainer from '../components/ai/RiskChangeExplainer';
import WhatIfSimulatorPanel from '../components/ai/WhatIfSimulator';
import MicroGoalsSuggester from '../components/interventions/MicroGoalsSuggester';
import MicroGoalsStreaks from '../components/interventions/MicroGoalsStreaks';
import AcademicPerformance from '../components/student/AcademicPerformance';
import TutoringCenter from '../components/student/TutoringCenter';
import { variants } from '../utils/motionConfig';
import { getStudentDetails, getMLPrediction, getWeeklySummary, getStudentRiskTrend } from '../services/api';
import { useStudentData } from '../context/StudentContext';
import ConfidenceBadge from '../components/common/ConfidenceBadge';
import TrendIndicator from '../components/common/TrendIndicator';
import MLRiskCard from '../components/student/MLRiskCard';

/* ─── Constants ─────────────────────────────────────────────── */

const PORTAL_TABS = [
    { id: 'dashboard', label: 'Dashboard',  Icon: FaTachometerAlt   },
    { id: 'academic',  label: 'Academic',   Icon: FaGraduationCap    },
    { id: 'tutoring',  label: 'Tutoring',   Icon: FaChalkboardTeacher },
    { id: 'goals',     label: 'Goals & AI', Icon: FaBullseye          },
];

const ACTIVITY_DATA = [
    { day: 'Mon', studyHours: 2.5, classes: 2, tasks: 1 },
    { day: 'Tue', studyHours: 3.0, classes: 3, tasks: 2 },
    { day: 'Wed', studyHours: 1.5, classes: 2, tasks: 0 },
    { day: 'Thu', studyHours: 4.0, classes: 3, tasks: 2 },
    { day: 'Fri', studyHours: 2.0, classes: 2, tasks: 1 },
    { day: 'Sat', studyHours: 3.5, classes: 0, tasks: 1 },
    { day: 'Sun', studyHours: 1.0, classes: 0, tasks: 0 },
];

const SCHEDULE = [
    { time: 'Today, 2:00 PM',     type: 'class',    label: 'Data Science Lecture',    location: 'Room 201',   urgent: false },
    { time: 'Today, 5:00 PM',     type: 'deadline', label: 'Stats Assignment Due',     location: 'Submit online', urgent: true  },
    { time: 'Tomorrow, 10:00 AM', type: 'class',    label: 'Mathematics Tutorial',     location: 'Room 105',   urgent: false },
    { time: 'Wed, 2:00 PM',       type: 'tutoring', label: 'Tutoring: Data Science',   location: 'Office B12', urgent: false },
    { time: 'Thu, 11:00 AM',      type: 'exam',     label: 'Statistics Quiz',          location: 'Hall A',     urgent: true  },
    { time: 'Fri, 4:00 PM',       type: 'group',    label: 'Study Group Meeting',      location: 'Library',    urgent: false },
];

const scheduleIcon  = { class: '📚', deadline: '📋', tutoring: '👨‍🏫', exam: '📝', group: '👥' };
const scheduleColor = { class: '#8B5CF6', deadline: '#EF4444', tutoring: '#10B981', exam: '#F59E0B', group: '#3B82F6' };

const tooltipStyle = {
    contentStyle: { background: '#1E1535', border: '1px solid rgba(139,92,246,0.3)', borderRadius: 10 },
    labelStyle: { color: '#EDE9FE', fontWeight: 600 },
    itemStyle: { color: '#C4B5FD' },
};

/* ─── StudentPortal Page ─────────────────────────────────────── */

const StudentPortal = () => {
    const { id: routeId } = useParams();
    const { students: allStudents, loading: studentsLoading } = useStudentData();
    const [activeTab,   setActiveTab]   = useState('dashboard');
    const [studentData, setStudentData] = useState(null);
    const [weekData,    setWeekData]    = useState(null);
    const [mlPrediction, setMlPrediction] = useState(null);
    const [riskTrend, setRiskTrend] = useState([]);
    const [loading,     setLoading]     = useState(true);
    const [error,       setError]       = useState(null);

    useEffect(() => {
        let isMounted = true;

        const load = async () => {
            if (studentsLoading) return;
            setLoading(true);
            setError(null);
            setStudentData(null);
            setWeekData(null);

            const requestedId = (routeId || '').toString().trim();
            console.log('ROUTE ID:', requestedId, 'type:', typeof requestedId);
            console.log('DATASET:', allStudents);

            if (!Array.isArray(allStudents) || allStudents.length === 0) {
                setError("No students available for portal lookup.");
                setLoading(false);
                return;
            }

            const normalizedRequested = requestedId.toLowerCase();
            const digitsRequested = requestedId.replace(/\D/g, '');
            const matchedStudent = requestedId
                ? (
                    allStudents.find((s) => (s?.id || '').toString().toLowerCase() === normalizedRequested) ||
                    allStudents.find((s) => (s?.org_defined_id || '').toString().toLowerCase() === normalizedRequested) ||
                    (digitsRequested
                        ? allStudents.find((s) => (s?.org_defined_id || '').toString().replace(/\D/g, '').endsWith(digitsRequested))
                        : null)
                )
                : allStudents[0];

            console.log('Matched student:', matchedStudent || null);
            if (!matchedStudent?.id) {
                setError(`Student '${requestedId || '(none)'}' not found`);
                setLoading(false);
                return;
            }
            const studentId = matchedStudent.id.toString();

            const [studentResp, mlResp, weeklyResp, trendResp] = await Promise.all([
                getStudentDetails(studentId),
                getMLPrediction(studentId),
                getWeeklySummary(studentId),
                getStudentRiskTrend(studentId, 8),
            ]);

            if (!isMounted) {
                return;
            }

            if (!studentResp.success || !studentResp.data) {
                setError(
                    studentResp.message ||
                    'We could not load your overview right now. Please try again in a moment.',
                );
                setStudentData(null);
                setWeekData(null);
                setLoading(false);
                return;
            }

            const s = studentResp.data || {};

            // Derive a portal-friendly shape from backend metrics + ML prediction + weekly summary
            const rawRisk = typeof s.risk_score === 'number' ? s.risk_score : 0;
            const dropoutRisk = rawRisk / 100;

            const mlData = mlResp && mlResp.success ? mlResp.data : null;
            setMlPrediction(mlData || null);
            const mlPredictions = mlData && mlData.predictions ? mlData.predictions : null;

            const weekly = weeklyResp && weeklyResp.success ? weeklyResp.data || {} : {};

            const trendPointsRaw =
                trendResp && trendResp.success && trendResp.data
                    ? (trendResp.data.points || [])
                    : [];
            setRiskTrend(Array.isArray(trendPointsRaw) ? trendPointsRaw : []);

            const derivedStudent = {
                id: s.id ?? studentId,
                name: [s.first_name, s.last_name].filter(Boolean).join(' ') || 'Student',
                program: s.department || 'Programme not available',
                avatar: (s.first_name && s.first_name[0]) || 'S',
                // Health score uses inverse of risk (0–1)
                dropout_risk: Number.isFinite(dropoutRisk) ? dropoutRisk : 0,
                // Map engagement / performance / attendance from backend metrics where possible
                engagement_score:
                    s.content_completion_score ??
                    s.quiz_engagement_score ??
                    0,
                performance_score:
                    s.exam_score ??
                    s.graded_quiz_score ??
                    s.graded_assignment_score ??
                    0,
                attendance_score:
                    s.attendance_score ??
                    s.exam_attendance_rate ??
                    0,
                historical_scores: Array.isArray(s.historical_scores)
                    ? s.historical_scores
                    : [],
                risk_score: rawRisk,
                attendance:
                    typeof weekly.attendanceRate === 'number'
                        ? Math.round(weekly.attendanceRate * 100)
                        : typeof weekly.attendance_rate === 'number'
                            ? Math.round(weekly.attendance_rate * 100)
                            : Math.round(s.exam_attendance_rate ?? 0),
                grades:
                    (mlPredictions && typeof mlPredictions.grades === 'number'
                        ? mlPredictions.grades
                        : s.grades) ?? null,
                studyHoursThisWeek: (() => {
                    const minutes =
                        (typeof weekly.totalStudyTimeMinutes === 'number'
                            ? weekly.totalStudyTimeMinutes
                            : typeof weekly.total_study_time_minutes === 'number'
                                ? weekly.total_study_time_minutes
                                : 0);
                    const hours = minutes / 60;
                    return Number.isFinite(hours) ? Math.round(hours * 10) / 10 : 0;
                })(),
            };

            setStudentData(derivedStudent);

            if (weekly && Object.keys(weekly).length > 0) {
                setWeekData({
                    assignmentsCompleted:
                        weekly.assignmentsCompleted ??
                        weekly.assignments_completed ??
                        0,
                    attendanceRate:
                        typeof weekly.attendanceRate === 'number'
                            ? weekly.attendanceRate
                            : typeof weekly.attendance_rate === 'number'
                                ? weekly.attendance_rate
                                : (s.exam_attendance_rate ?? 0) / 100,
                    engagementImprovement:
                        weekly.engagementImprovement ??
                        weekly.engagement_improvement ??
                        0,
                    missedAssignments:
                        weekly.missedAssignments ??
                        weekly.missed_assignments ??
                        0,
                    lowEngagementDays:
                        weekly.lowEngagementDays ??
                        weekly.low_engagement_days ??
                        0,
                    totalStudyTimeMinutes:
                        weekly.totalStudyTimeMinutes ??
                        weekly.total_study_time_minutes ??
                        0,
                    facultyInteractions:
                        weekly.facultyInteractions ??
                        weekly.faculty_interactions ??
                        0,
                    resourcesViewed:
                        weekly.resourcesViewed ??
                        weekly.resources_viewed ??
                        0,
                });
            } else {
                setWeekData(null);
            }

            setLoading(false);
        };

        load();

        return () => {
            isMounted = false;
        };
    }, [routeId, allStudents, studentsLoading]);

    const healthScore = studentData ? Math.round((1 - (studentData.dropout_risk ?? 0)) * 100) : 0;
    const mlDropoutPercent = useMemo(() => {
        const raw = typeof mlPrediction?.dropout_probability === 'number' ? mlPrediction.dropout_probability : null;
        if (raw === null) return null;
        const pct = raw * 100;
        return Number.isFinite(pct) ? parseFloat(pct.toFixed(2)) : null;
    }, [mlPrediction]);

    const trendCurrent = riskTrend && riskTrend.length > 0 ? riskTrend[riskTrend.length - 1]?.risk_score : null;
    const trendPrevious = riskTrend && riskTrend.length > 1 ? riskTrend[riskTrend.length - 2]?.risk_score : null;

    const kpis = [
        {
            label: 'Health Score',
            value: healthScore,
            unit: '/100',
            color: healthScore >= 80 ? '#10B981' : '#F59E0B',
            icon: <FaHeart />,
            sub: healthScore >= 80 ? 'Thriving' : 'On Track',
        },
        {
            label: 'Current GPA',
            value: studentData?.grades ?? '—',
            unit: '',
            color: '#8B5CF6',
            icon: <FaGraduationCap />,
            sub: 'Target: 3.5',
        },
        {
            label: 'Attendance',
            value: `${studentData?.attendance ?? 0}%`,
            unit: '',
            color: studentData?.attendance >= 90 ? '#10B981' : '#F59E0B',
            icon: <FaCheckCircle />,
            sub: 'Target: 95%',
        },
        {
            label: 'Study Hours',
            value: studentData?.studyHoursThisWeek ?? 0,
            unit: 'h',
            color: '#F59E0B',
            icon: <FaClock />,
            sub: 'This week',
        },
    ];

    if (loading) {
        return (
            <motion.div initial="hidden" animate="visible" variants={variants.container}>
                <Container fluid className="py-4" style={{ maxWidth: '1500px' }}>
                    <div className="glass-panel p-4 mb-4 placeholder-glow">
                        <div className="d-flex justify-content-between align-items-center mb-4">
                            <div className="d-flex align-items-center gap-4">
                                <div className="rounded-circle bg-secondary placeholder col-2" style={{ height: 56 }} />
                                <div>
                                    <div className="placeholder col-7 mb-2" />
                                    <div className="placeholder col-4" />
                                </div>
                            </div>
                            <div className="placeholder col-3" style={{ height: 32 }} />
                        </div>
                        <Row className="g-3">
                            {[1, 2, 3, 4].map((i) => (
                                <Col xs={6} md={3} key={i}>
                                    <div className="glass-panel p-3 h-100">
                                        <div className="placeholder col-4 mb-3" />
                                        <div className="placeholder col-6 mb-2" style={{ height: 32 }} />
                                        <div className="placeholder col-5" />
                                    </div>
                                </Col>
                            ))}
                        </Row>
                    </div>
                </Container>
            </motion.div>
        );
    }

    if (error) {
        return (
            <motion.div initial="hidden" animate="visible" variants={variants.container}>
                <Container fluid className="py-4" style={{ maxWidth: '1500px' }}>
                    <div className="glass-panel p-5 text-center">
                        <h2 className="fw-bold mb-2" style={{ color: '#EDE9FE' }}>
                            We couldn&apos;t load your overview
                        </h2>
                        <p className="text-muted mb-3" style={{ fontSize: '0.95rem' }}>
                            {error}
                        </p>
                        <p className="text-muted small mb-0">
                            Please refresh the page or try again later. If the issue persists, contact your advisor.
                        </p>
                    </div>
                </Container>
            </motion.div>
        );
    }

    if (!studentData) {
        return (
            <motion.div initial="hidden" animate="visible" variants={variants.container}>
                <Container fluid className="py-4" style={{ maxWidth: '1500px' }}>
                    <div className="glass-panel p-5 text-center">
                        <h2 className="fw-bold mb-2" style={{ color: '#EDE9FE' }}>
                            No student data available
                        </h2>
                        <p className="text-muted mb-0">
                            We couldn&apos;t find any data to populate your portal yet. Once your courses start generating
                            activity, your overview will appear here.
                        </p>
                    </div>
                </Container>
            </motion.div>
        );
    }

    return (
        <motion.div initial="hidden" animate="visible" variants={variants.container}>
            <Container fluid className="py-4" style={{ maxWidth: '1500px' }}>

                {/* ── Portal Header ─────────────────────────────────── */}
                <motion.div variants={variants.item} className="d-flex justify-content-between align-items-center mb-5">
                    <div className="d-flex align-items-center gap-4">
                        {/* Avatar */}
                        <div style={{
                            width: 56, height: 56, borderRadius: '50%', flexShrink: 0,
                            background: 'linear-gradient(135deg, #7C3AED, #8B5CF6)',
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                            fontWeight: 800, fontSize: '1.1rem', color: 'white',
                            boxShadow: '0 0 0 3px rgba(139,92,246,0.35)',
                        }}>
                            {studentData?.avatar ?? 'S'}
                        </div>
                        <div>
                            <h1 className="display-6 fw-bold text-gradient mb-0">
                                Welcome back, {studentData?.name ?? 'Student'}!
                            </h1>
                            <p className="text-secondary mb-0" style={{ fontSize: '0.9rem' }}>
                                {studentData?.program ?? 'Loading programme…'}
                                &nbsp;·&nbsp;
                                <span style={{ color: '#8B5CF6' }}>
                                    {new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' })}
                                </span>
                            </p>
                        </div>
                    </div>

                    {/* Portal status / ML widgets (no layout change) */}
                    <div className="d-flex align-items-center gap-2">
                        {mlPrediction && (
                            <div style={{
                                padding: '8px 14px', borderRadius: 10,
                                background: 'rgba(139,92,246,0.08)',
                                border: '1px solid rgba(139,92,246,0.18)',
                                display: 'flex', alignItems: 'center', gap: 10,
                            }}>
                                <div style={{ fontSize: '0.8rem', color: '#C4B5FD', fontWeight: 700 }}>
                                    ML Risk
                                    <span style={{ marginLeft: 8, color: '#EDE9FE' }}>
                                        {mlDropoutPercent !== null ? `${mlDropoutPercent.toFixed(2)}%` : '—'}
                                    </span>
                                </div>
                                {typeof trendCurrent === 'number' && typeof trendPrevious === 'number' && (
                                    <div style={{ fontSize: '0.8rem', color: '#B8AADA', fontWeight: 600 }}>
                                        Trend
                                        <TrendIndicator
                                            current={trendCurrent}
                                            previous={trendPrevious}
                                            metricType="risk"
                                            unit="pts"
                                            size="sm"
                                            showDelta={true}
                                            showPercent={false}
                                        />
                                    </div>
                                )}
                            </div>
                        )}

                        {mlPrediction && (
                            <ConfidenceBadge student={studentData || {}} size="sm" showLabel={true} />
                        )}

                        {!mlPrediction && weekData?.missedAssignments > 0 && (
                            <div style={{
                                padding: '8px 18px', borderRadius: 10,
                                background: 'rgba(239,68,68,0.1)',
                                border: '1px solid rgba(239,68,68,0.25)',
                                display: 'flex', alignItems: 'center', gap: 7,
                            }}>
                                <FaExclamationTriangle color="#EF4444" size={12} />
                                <span style={{ fontSize: '0.8rem', color: '#EF4444', fontWeight: 600 }}>
                                    {weekData.missedAssignments} assignment{weekData.missedAssignments !== 1 ? 's' : ''} to catch up
                                </span>
                            </div>
                        )}
                    </div>
                </motion.div>

                {/* ── KPI Cards ─────────────────────────────────────── */}
                <motion.div variants={variants.item} className="mb-4">
                    <Row className="g-3">
                        {kpis.map(k => (
                            <Col xs={6} md={3} key={k.label}>
                                <div className="glass-panel p-3 h-100">
                                    <div className="d-flex align-items-center gap-2 mb-3">
                                        <div style={{
                                            width: 32, height: 32, borderRadius: 8,
                                            background: 'rgba(139,92,246,0.15)',
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            color: k.color, fontSize: 13, flexShrink: 0,
                                        }}>
                                            {k.icon}
                                        </div>
                                        <span style={{ fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#B8AADA' }}>
                                            {k.label}
                                        </span>
                                    </div>
                                    <div style={{ fontSize: '1.85rem', fontWeight: 800, fontFamily: 'var(--font-family-mono)', color: k.color, lineHeight: 1, marginBottom: 4 }}>
                                        {k.value}<span style={{ fontSize: '0.85rem', color: '#B8AADA' }}>{k.unit}</span>
                                    </div>
                                    <div style={{ fontSize: '0.75rem', color: '#B8AADA' }}>{k.sub}</div>
                                </div>
                            </Col>
                        ))}
                    </Row>
                </motion.div>

                {/* ── Tab Bar ───────────────────────────────────────── */}
                <motion.div variants={variants.item} className="mb-4">
                    <div className="d-flex gap-1 p-1 rounded-3" style={{
                        background: 'rgba(139,92,246,0.07)',
                        border: '1px solid rgba(139,92,246,0.15)',
                        width: 'fit-content',
                    }}>
                        {PORTAL_TABS.map(tab => (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                style={{
                                    display: 'flex', alignItems: 'center', gap: 7,
                                    padding: '8px 20px', borderRadius: 8, border: 'none',
                                    cursor: 'pointer', fontWeight: 600, fontSize: '0.875rem',
                                    transition: 'all 0.2s',
                                    background: activeTab === tab.id ? '#8B5CF6' : 'transparent',
                                    color:      activeTab === tab.id ? '#fff'    : '#C4B5FD',
                                    boxShadow:  activeTab === tab.id ? '0 2px 8px rgba(139,92,246,0.35)' : 'none',
                                }}
                            >
                                <tab.Icon size={12} />
                                {tab.label}
                            </button>
                        ))}
                    </div>
                </motion.div>

                {/* ── Tab Content ───────────────────────────────────── */}
                <motion.div variants={variants.item}>

                    {/* DASHBOARD ─────────────────────────────────────── */}
                    {activeTab === 'dashboard' && (
                        <Row className="g-4">
                            {/* Left column */}
                            <Col lg={8}>
                                <div className="d-flex flex-column gap-4">
                                    {/* Health score */}
                                    <StudentHealthScore studentData={studentData} />

                                    {/* ML prediction details (if available) */}
                                    {mlPrediction && (
                                        <MLRiskCard mlPrediction={mlPrediction} ruleRiskScore={studentData?.risk_score ?? 0} />
                                    )}

                                    {/* Risk explainer */}
                                    {studentData && (
                                        <RiskChangeExplainer studentId={studentData.id} />
                                    )}

                                    {/* Weekly activity chart */}
                                    <div className="glass-panel p-4">
                                        <h6 className="fw-bold mb-1" style={{ color: '#EDE9FE' }}>
                                            Weekly Activity — This Week
                                        </h6>
                                        <p style={{ fontSize: '0.82rem', color: '#B8AADA', marginBottom: '1.25rem' }}>
                                            Study hours, classes attended & tasks completed by day
                                        </p>
                                        <ResponsiveContainer width="100%" height={210}>
                                            <AreaChart data={ACTIVITY_DATA} margin={{ top: 5, right: 16, left: -16, bottom: 0 }}>
                                                <defs>
                                                    <linearGradient id="studyGrad" x1="0" y1="0" x2="0" y2="1">
                                                        <stop offset="5%"  stopColor="#8B5CF6" stopOpacity={0.35} />
                                                        <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
                                                    </linearGradient>
                                                    <linearGradient id="classGrad" x1="0" y1="0" x2="0" y2="1">
                                                        <stop offset="5%"  stopColor="#10B981" stopOpacity={0.25} />
                                                        <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                                                    </linearGradient>
                                                </defs>
                                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.1)" />
                                                <XAxis dataKey="day" tick={{ fill: '#B8AADA', fontSize: 11 }} axisLine={false} tickLine={false} />
                                                <YAxis tick={{ fill: '#B8AADA', fontSize: 11 }} axisLine={false} tickLine={false} />
                                                <Tooltip {...tooltipStyle} />
                                                <Area type="monotone" dataKey="studyHours" name="Study Hours"       stroke="#8B5CF6" fill="url(#studyGrad)" strokeWidth={2} dot={false} />
                                                <Area type="monotone" dataKey="classes"    name="Classes Attended"  stroke="#10B981" fill="url(#classGrad)"  strokeWidth={2} dot={false} />
                                                <Area type="monotone" dataKey="tasks"      name="Tasks Completed"   stroke="#F59E0B" fill="none"              strokeWidth={2} strokeDasharray="5 3" dot={false} />
                                                <Legend wrapperStyle={{ color: '#B8AADA', fontSize: 12, paddingTop: 10 }} />
                                            </AreaChart>
                                        </ResponsiveContainer>
                                    </div>

                                    {/* Upcoming schedule */}
                                    <div className="glass-panel p-4">
                                        <div className="d-flex align-items-center gap-2 mb-1">
                                            <FaCalendarAlt color="#8B5CF6" size={13} />
                                            <h6 className="fw-bold m-0" style={{ color: '#EDE9FE' }}>
                                                Upcoming Schedule
                                            </h6>
                                        </div>
                                        <p style={{ fontSize: '0.82rem', color: '#B8AADA', marginBottom: '1.25rem' }}>
                                            Classes, deadlines & sessions for the next 7 days
                                        </p>

                                        <div className="d-flex flex-column gap-2">
                                            {SCHEDULE.map((ev, i) => (
                                                <div key={i} style={{
                                                    display: 'flex', alignItems: 'center', gap: '1rem',
                                                    padding: '0.7rem 1rem',
                                                    background: ev.urgent ? 'rgba(239,68,68,0.07)' : 'rgba(139,92,246,0.05)',
                                                    border: `1px solid ${ev.urgent ? 'rgba(239,68,68,0.2)' : 'rgba(139,92,246,0.1)'}`,
                                                    borderLeft: `3px solid ${scheduleColor[ev.type]}`,
                                                    borderRadius: 10,
                                                }}>
                                                    <span style={{ fontSize: '1.1rem', flexShrink: 0 }}>{scheduleIcon[ev.type]}</span>
                                                    <div style={{ flex: 1 }}>
                                                        <div style={{ fontWeight: 600, color: '#EDE9FE', fontSize: '0.875rem' }}>
                                                            {ev.label}
                                                            {ev.urgent && (
                                                                <span style={{
                                                                    marginLeft: 8, fontSize: '0.62rem', background: 'rgba(239,68,68,0.15)',
                                                                    color: '#EF4444', padding: '2px 7px', borderRadius: 99,
                                                                }}>
                                                                    Urgent
                                                                </span>
                                                            )}
                                                        </div>
                                                        <div style={{ fontSize: '0.72rem', color: '#B8AADA', marginTop: 2 }}>
                                                            {ev.location}
                                                        </div>
                                                    </div>
                                                    <div style={{ fontSize: '0.75rem', color: scheduleColor[ev.type], fontWeight: 600, flexShrink: 0 }}>
                                                        {ev.time}
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </Col>

                            {/* Right sidebar */}
                            <Col lg={4}>
                                <div className="d-flex flex-column gap-4">
                                    <WeeklyProgressBrief weekData={weekData} studentName={studentData?.name} />
                                    <MicroGoalsStreaks />

                                    {/* Quick links */}
                                    <div className="glass-panel p-4">
                                        <h6 className="fw-bold mb-3" style={{ color: '#EDE9FE' }}>Quick Links</h6>
                                        <div className="d-flex flex-column gap-2">
                                            {[
                                                { icon: <FaGraduationCap size={13} />, label: 'View Academic Performance', tab: 'academic', color: '#8B5CF6' },
                                                { icon: <FaChalkboardTeacher size={13} />, label: 'Book a Tutoring Session', tab: 'tutoring', color: '#10B981' },
                                                { icon: <FaUsers size={13} />, label: 'Find a Study Group', tab: 'tutoring', color: '#F59E0B' },
                                                { icon: <FaBullseye size={13} />, label: 'Run What-If Simulator', tab: 'goals', color: '#3B82F6' },
                                            ].map((link, i) => (
                                                <button
                                                    key={i}
                                                    onClick={() => setActiveTab(link.tab)}
                                                    style={{
                                                        display: 'flex', alignItems: 'center', gap: 10,
                                                        padding: '0.6rem 0.85rem', borderRadius: 9,
                                                        border: '1px solid rgba(139,92,246,0.15)',
                                                        background: 'rgba(139,92,246,0.07)',
                                                        cursor: 'pointer', color: link.color,
                                                        fontSize: '0.82rem', fontWeight: 600,
                                                        transition: 'background 0.15s', textAlign: 'left',
                                                    }}
                                                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(139,92,246,0.13)'}
                                                    onMouseLeave={e => e.currentTarget.style.background = 'rgba(139,92,246,0.07)'}
                                                >
                                                    {link.icon}
                                                    {link.label}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </Col>
                        </Row>
                    )}

                    {/* ACADEMIC ──────────────────────────────────────── */}
                    {activeTab === 'academic' && (
                        <AcademicPerformance />
                    )}

                    {/* TUTORING ──────────────────────────────────────── */}
                    {activeTab === 'tutoring' && (
                        <TutoringCenter />
                    )}

                    {/* GOALS & AI ─────────────────────────────────────── */}
                    {activeTab === 'goals' && (
                        <Row className="g-4">
                            <Col lg={8}>
                                {studentData && (
                                    <WhatIfSimulatorPanel
                                        studentId={studentData.id}
                                        currentMetrics={{
                                            attendance: studentData.attendance_score,
                                            grades:     studentData.grades,
                                            risk_score: studentData.risk_score,
                                        }}
                                    />
                                )}
                            </Col>
                            <Col lg={4}>
                                <div className="d-flex flex-column gap-4">
                                    {studentData && (
                                        <MicroGoalsSuggester studentId={studentData.id} />
                                    )}
                                    <MicroGoalsStreaks />

                                    {/* Tips card */}
                                    <div className="glass-panel p-4">
                                        <h6 className="fw-bold mb-3" style={{ color: '#EDE9FE' }}>
                                            💡 How to Use the Simulator
                                        </h6>
                                        <div className="d-flex flex-column gap-3">
                                            {[
                                                'Drag the sliders to simulate attending more classes or completing more assignments.',
                                                'Run the simulation to see how your health score would change.',
                                                'Use the results to prioritise which areas to focus on this week.',
                                            ].map((tip, i) => (
                                                <div key={i} style={{ display: 'flex', gap: 10 }}>
                                                    <div style={{
                                                        width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                                                        background: 'rgba(139,92,246,0.2)', color: '#A78BFA',
                                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                        fontWeight: 700, fontSize: '0.72rem',
                                                    }}>
                                                        {i + 1}
                                                    </div>
                                                    <p style={{ fontSize: '0.82rem', color: '#C4B5FD', margin: 0, lineHeight: 1.55 }}>
                                                        {tip}
                                                    </p>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                </div>
                            </Col>
                        </Row>
                    )}
                </motion.div>

                {/* Footer */}
                <div className="mt-5 pt-4 border-top text-center">
                    <small className="text-muted">
                        Meridian Student Portal · Data refreshed in real-time · All advice is AI-assisted and reviewed by your academic advisor.
                    </small>
                </div>

            </Container>
        </motion.div>
    );
};

export default StudentPortal;
