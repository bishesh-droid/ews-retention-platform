import React, { useState, useMemo, useEffect } from 'react';
import { Row, Col, Container, Badge, Spinner, Alert } from 'react-bootstrap';
import { motion, AnimatePresence } from 'framer-motion';
import {
    BarChart, Bar, LineChart, Line, RadarChart, Radar, PolarGrid,
    PolarAngleAxis, PolarRadiusAxis, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, Legend, Cell, ReferenceLine
} from 'recharts';
import {
    FaChalkboardTeacher, FaExclamationTriangle, FaCheckCircle,
    FaArrowUp, FaArrowDown, FaMinus, FaUsers, FaBullseye,
    FaClock, FaFire, FaStar, FaDownload, FaFilter,
    FaChartBar, FaBell, FaLightbulb, FaRocket, FaShieldAlt,
    FaGraduationCap, FaHandshake, FaBullhorn, FaRegCalendarCheck
} from 'react-icons/fa';
import { variants } from '../utils/motionConfig';
import { getFacultyStudents, getFacultyAtRiskStudents, getFacultyAlerts } from '../services/api';

/* ─── Colour tokens ──────────────────────────────────────────── */
const C = {
    purple: '#7C3AED',
    purpleLight: '#8B5CF6',
    purpleFaint: 'rgba(124,58,237,0.12)',
    gold: '#F59E0B',
    goldFaint: 'rgba(245,158,11,0.12)',
    red: '#EF4444',
    redFaint: 'rgba(239,68,68,0.12)',
    green: '#10B981',
    greenFaint: 'rgba(16,185,129,0.12)',
    blue: '#3B82F6',
    blueFaint: 'rgba(59,130,246,0.12)',
    surface: '#130D23',
    surfaceHover: '#1A1035',
    border: 'rgba(139,92,246,0.18)',
    textPrimary: '#EDE9FE',
    textSecondary: '#B8AADA',
    tooltipBg: '#1E1535',
};

const TABS = [
    { id: 'courses',       label: 'My Courses',         icon: <FaChalkboardTeacher /> },
    { id: 'alerts',        label: 'Student Alerts',      icon: <FaBell /> },
    { id: 'interventions', label: 'Intervention Hub',    icon: <FaHandshake /> },
    { id: 'program',       label: 'Program Analytics',   icon: <FaChartBar /> },
];

/* ─── Static data for charts & insights ─────────────────────────── */
const RADAR_DATA = [
    { factor: 'Attendance',   cs: 78, math: 82, sci: 75, hum: 85 },
    { factor: 'Grades',       cs: 72, math: 68, sci: 74, hum: 80 },
    { factor: 'Engagement',   cs: 65, math: 70, sci: 72, hum: 78 },
    { factor: 'Completion',   cs: 70, math: 75, sci: 68, hum: 82 },
    { factor: 'Retention',    cs: 75, math: 72, sci: 76, hum: 88 },
];

const MARKET_INSIGHTS = [
    { area: 'Early Warning System Alerts', priority: 'HIGH', impact: '15 at-risk students identified this week requiring immediate advisor outreach', action: 'Launch retention campaign: send personalized intervention emails' },
    { area: 'Course Completion Risk', priority: 'MEDIUM', impact: 'Computer Science showing 12% below-target completion rates', action: 'Schedule TA office hours & create study groups for struggling cohorts' },
    { area: 'Engagement Opportunity', priority: 'LOW', impact: 'Humanities students show highest forum participation - leverage for peer mentoring', action: 'Recruit high-engagement students as peer mentors for at-risk departments' },
];

/* ─── Derived data helpers (runtime from backend) ────────────── */

/* ─── Tooltip ────────────────────────────────────────────────── */
const TooltipStyle = {
    contentStyle: { background: C.tooltipBg, border: `1px solid ${C.border}`, borderRadius: 10, color: C.textPrimary, fontSize: 12 },
    labelStyle:   { color: C.textSecondary },
    cursor:       { fill: 'rgba(139,92,246,0.08)' },
};

/* ─── Helper sub-components ──────────────────────────────────── */
const StatCard = ({ icon, label, value, sub, color = C.purple, delay = 0 }) => (
    <motion.div variants={variants.item} custom={delay}>
        <div className="glass-panel p-4 h-100" style={{ borderRadius: 14, border: `1px solid ${color}33` }}>
            <div className="d-flex justify-content-between align-items-start mb-3">
                <div style={{ fontSize: 22, color }}>{icon}</div>
                <div style={{ fontSize: 11, color: C.textSecondary, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</div>
            </div>
            <div style={{ fontSize: 30, fontWeight: 800, color: C.textPrimary, lineHeight: 1 }}>{value}</div>
            {sub && <div style={{ fontSize: 12, color: C.textSecondary, marginTop: 6 }}>{sub}</div>}
        </div>
    </motion.div>
);

const SectionTitle = ({ children, sub }) => (
    <div className="mb-4">
        <h5 style={{ color: C.textPrimary, fontWeight: 700, margin: 0 }}>{children}</h5>
        {sub && <p style={{ color: C.textSecondary, fontSize: 13, margin: '4px 0 0' }}>{sub}</p>}
    </div>
);

const RiskBadge = ({ score }) => {
    const color = score >= 75 ? C.red : score >= 55 ? C.gold : C.green;
    const label = score >= 75 ? 'Critical' : score >= 55 ? 'High' : 'Moderate';
    return (
        <span style={{ background: `${color}22`, color, border: `1px solid ${color}44`, borderRadius: 6, padding: '2px 10px', fontSize: 11, fontWeight: 700 }}>
            {label} · {score}%
        </span>
    );
};

const TrendChip = ({ up, value }) => (
    <span style={{ display:'inline-flex', alignItems:'center', gap:3, fontSize:12, color: up ? C.green : C.red, fontWeight:600 }}>
        {up ? <FaArrowUp size={9}/> : <FaArrowDown size={9}/>} {value}
    </span>
);

const MiniBar = ({ value, max = 100, color = C.purple }) => (
    <div style={{ background: 'rgba(255,255,255,0.06)', borderRadius: 4, height: 6, width: '100%', marginTop: 4 }}>
        <div style={{ width: `${(value/max)*100}%`, background: color, borderRadius: 4, height: '100%', transition: 'width 0.6s ease' }} />
    </div>
);

/* ─── Tab: My Courses ─────────────────────────────────────────── */
const CoursesTab = ({ students, loading, error }) => {
    const [sort, setSort] = useState('riskCorr');

    const courses = useMemo(() => {
        const map = {};
        (students || []).forEach(s => {
            const dept = s.department || 'Unknown';
            if (!map[dept]) {
                map[dept] = {
                    id: dept,
                    name: dept,
                    enrolled: 0,
                    atRisk: 0,
                    completion: 0,
                    avgGrade: 0,
                    engagement: 0,
                    satisfaction: 0,
                };
            }
            const entry = map[dept];
            entry.enrolled += 1;
            const risk = s.risk_score ?? 0;
            if (risk >= 60) entry.atRisk += 1;
            entry.completion += s.content_completion_score ?? 0;
            entry.avgGrade += s.graded_quiz_score ?? 0;
            entry.engagement += s.quiz_engagement_score ?? 0;
        });
        return Object.values(map).map(c => {
            const denom = c.enrolled || 1;
            const completion = Math.round(c.completion / denom);
            const avgGrade = Math.round(c.avgGrade / denom);
            const engagement = Math.round(c.engagement / denom);
            const riskCorr = c.enrolled > 0 ? c.atRisk / c.enrolled : 0;
            return {
                ...c,
                completion,
                avgGrade,
                engagement,
                riskCorr,
                trend: '',
                up: riskCorr < 0.25,
            };
        });
    }, [students]);

    const weeklyTrend = useMemo(() => {
        if (!students || students.length === 0) return [];
        // Approximate 8 points using risk deciles of the cohort
        const sorted = [...students].sort((a, b) => (a.risk_score ?? 0) - (b.risk_score ?? 0));
        const points = [];
        const buckets = 8;
        for (let i = 1; i <= buckets; i++) {
            const idx = Math.floor((i / (buckets + 1)) * sorted.length);
            const s = sorted[idx] || sorted[sorted.length - 1];
            points.push({
                week: `P${i}`,
                attendance: Math.round(s.exam_attendance_rate ?? 0),
                engagement: Math.round(s.quiz_engagement_score ?? 0),
                completion: Math.round(s.content_completion_score ?? 0),
            });
        }
        return points;
    }, [students]);

    const sorted = useMemo(() => [...courses].sort((a, b) =>
        sort === 'riskCorr' ? b.riskCorr - a.riskCorr :
        sort === 'atRisk'   ? b.atRisk - a.atRisk :
        sort === 'enrolled' ? b.enrolled - a.enrolled :
        b.completion - a.completion
    ), [courses, sort]);

    const riskBarData = courses.map(c => ({
        name: c.id,
        'At Risk': c.atRisk,
        'On Track': c.enrolled - c.atRisk,
    }));

    return (
        <motion.div initial="hidden" animate="visible" variants={variants.container}>
            {/* Weekly Engagement Trend */}
            <motion.div variants={variants.item} className="glass-panel p-4 mb-4" style={{ borderRadius: 14 }}>
                <SectionTitle sub="Summarised from your current teaching cohort">
                    Engagement Trend Overview
                </SectionTitle>
                <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={weeklyTrend}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.1)" />
                        <XAxis dataKey="week" tick={{ fill: C.textSecondary, fontSize: 11 }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fill: C.textSecondary, fontSize: 11 }} axisLine={false} tickLine={false} domain={[60, 100]} unit="%" />
                        <Tooltip {...TooltipStyle} formatter={(v) => `${v}%`} />
                        <Legend wrapperStyle={{ color: C.textSecondary, fontSize: 12 }} />
                        <Line type="monotone" dataKey="attendance"  stroke={C.purple}     strokeWidth={2.5} dot={false} />
                        <Line type="monotone" dataKey="engagement"  stroke={C.gold}       strokeWidth={2.5} dot={false} />
                        <Line type="monotone" dataKey="completion"  stroke={C.green}      strokeWidth={2.5} dot={false} />
                        <ReferenceLine y={75} stroke={C.red} strokeDasharray="4 4" label={{ value:'Alert threshold', fill:C.red, fontSize:10 }} />
                    </LineChart>
                </ResponsiveContainer>
            </motion.div>

            {/* Course Cards Grid */}
            <motion.div variants={variants.item} className="glass-panel p-4 mb-4" style={{ borderRadius: 14 }}>
                <div className="d-flex justify-content-between align-items-center mb-4">
                    <SectionTitle sub="Sorted by risk correlation to dropout">Course Health Cards</SectionTitle>
                    <div className="d-flex gap-2">
                        {[['riskCorr','Risk'], ['atRisk','At-Risk #'], ['enrolled','Enrolled'], ['completion','Completion']].map(([k,l]) => (
                            <button key={k} onClick={() => setSort(k)} style={{
                                padding:'4px 12px', borderRadius:8, fontSize:12, fontWeight:600, cursor:'pointer', border:'none',
                                background: sort===k ? C.purple : 'rgba(139,92,246,0.1)',
                                color: sort===k ? '#fff' : C.textSecondary,
                            }}>{l}</button>
                        ))}
                    </div>
                </div>
                <Row className="g-3">
                    {sorted.map((c) => {
                        const pct = Math.round((c.atRisk / c.enrolled) * 100);
                        const borderColor = pct >= 25 ? C.red : pct >= 15 ? C.gold : C.green;
                        return (
                            <Col key={c.id} lg={4} md={6}>
                                <div style={{
                                    background: C.surface, borderRadius: 12, padding: '18px 20px',
                                    border: `1px solid ${borderColor}44`, borderLeft: `4px solid ${borderColor}`,
                                    height: '100%',
                                }}>
                                    <div className="d-flex justify-content-between mb-2">
                                        <div>
                                            <div style={{ fontSize:11, color: C.textSecondary, fontFamily:'monospace' }}>{c.id}</div>
                                            <div style={{ fontSize:14, fontWeight:700, color: C.textPrimary }}>{c.name}</div>
                                        </div>
                                        <TrendChip up={c.up} value={c.trend} />
                                    </div>
                                    <div className="d-flex gap-3 mt-3 mb-2" style={{ fontSize:11, color: C.textSecondary }}>
                                        <span><FaUsers size={9} style={{ marginRight:3 }}/>{c.enrolled} enrolled</span>
                                        <span style={{ color: borderColor }}><FaExclamationTriangle size={9} style={{ marginRight:3 }}/>{c.atRisk} at-risk ({pct}%)</span>
                                    </div>
                                    <div className="mt-3">
                                        {[
                                            ['Completion', c.completion, C.purple],
                                            ['Avg Grade', c.avgGrade, C.blue],
                                            ['Engagement', c.engagement, C.gold],
                                        ].map(([lbl, val, col]) => (
                                            <div key={lbl} className="mb-2">
                                                <div className="d-flex justify-content-between" style={{ fontSize:11, color: C.textSecondary }}>
                                                    <span>{lbl}</span><span style={{ color: C.textPrimary, fontWeight:600 }}>{val}%</span>
                                                </div>
                                                <MiniBar value={val} color={col} />
                                            </div>
                                        ))}
                                    </div>
                                    <div className="d-flex justify-content-between mt-3 pt-2" style={{ borderTop:`1px solid ${C.border}`, fontSize:11 }}>
                                        <span style={{ color: C.textSecondary }}>Risk correlation</span>
                                        <span style={{ color: borderColor, fontWeight:700 }}>{Math.round(c.riskCorr * 100)}%</span>
                                    </div>
                                </div>
                            </Col>
                        );
                    })}
                </Row>
            </motion.div>

            {/* At-Risk Distribution Bar */}
            <motion.div variants={variants.item} className="glass-panel p-4" style={{ borderRadius: 14 }}>
                <SectionTitle sub="Students on-track vs at-risk by course">Student Distribution by Course</SectionTitle>
                <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={riskBarData} layout="vertical" barCategoryGap="25%">
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.1)" horizontal={false} />
                        <XAxis type="number" tick={{ fill: C.textSecondary, fontSize:11 }} axisLine={false} tickLine={false} />
                        <YAxis type="category" dataKey="name" tick={{ fill: C.textSecondary, fontSize:11 }} axisLine={false} tickLine={false} width={60} />
                        <Tooltip {...TooltipStyle} />
                        <Legend wrapperStyle={{ color: C.textSecondary, fontSize:12 }} />
                        <Bar dataKey="On Track" stackId="a" fill={C.green}      radius={[0,0,0,0]} />
                        <Bar dataKey="At Risk"  stackId="a" fill={C.red}        radius={[0,4,4,0]} />
                    </BarChart>
                </ResponsiveContainer>
            </motion.div>
        </motion.div>
    );
};

/* ─── Tab: Student Alerts ─────────────────────────────────────── */
const AlertsTab = ({ alerts, loading, error }) => {
    const [filter, setFilter] = useState('all');
    const [actionLog, setActionLog] = useState({});

    const normalizedAlerts = useMemo(
        () =>
            (alerts || []).map(a => ({
                id: a.student_id,
                name: a.name,
                course: a.department || 'N/A',
                risk: Math.round(a.risk_score ?? 0),
                drop: a.primary_reason || 'Engagement',
                days: 0,
                status: 'uncontacted',
                attendance: Math.round(a.exam_attendance_rate ?? 0),
            })),
        [alerts],
    );

    const filtered = filter === 'all'
        ? normalizedAlerts
        : normalizedAlerts.filter(s => s.status === filter);

    const markAction = (id, action) => setActionLog(prev => ({ ...prev, [id]: action }));

    const statusColors = {
        uncontacted: C.red,
        contacted: C.gold,
        intervention: C.green,
    };

    return (
        <motion.div initial="hidden" animate="visible" variants={variants.container}>
            {/* Summary Row */}
            <motion.div variants={variants.item}>
                <Row className="g-3 mb-4">
                    {[
                        { label:'Uncontacted', count: filtered.filter(s=>s.status==='uncontacted').length, color: C.red, icon:<FaFire/> },
                        { label:'Contacted',   count: filtered.filter(s=>s.status==='contacted').length,   color: C.gold, icon:<FaClock/> },
                        { label:'In Intervention', count: filtered.filter(s=>s.status==='intervention').length, color: C.green, icon:<FaCheckCircle/> },
                        { label:'Avg Risk Score', count: filtered.length ? `${Math.round(filtered.reduce((a,s)=>a+s.risk,0)/filtered.length)}%` : '—', color: C.purple, icon:<FaBullseye/> },
                    ].map((item, i) => (
                        <Col key={i} md={3}>
                            <div className="glass-panel p-3 text-center" style={{ borderRadius:12, border:`1px solid ${item.color}33` }}>
                                <div style={{ fontSize:22, color:item.color, marginBottom:6 }}>{item.icon}</div>
                                <div style={{ fontSize:26, fontWeight:800, color: C.textPrimary }}>{item.count}</div>
                                <div style={{ fontSize:11, color: C.textSecondary, textTransform:'uppercase', letterSpacing:'0.06em' }}>{item.label}</div>
                            </div>
                        </Col>
                    ))}
                </Row>
            </motion.div>

            {/* Filter Bar */}
            <motion.div variants={variants.item} className="d-flex gap-2 mb-3">
                {['all','uncontacted','contacted','intervention'].map(f => (
                    <button key={f} onClick={() => setFilter(f)} style={{
                        padding:'5px 14px', borderRadius:8, fontSize:12, fontWeight:600, cursor:'pointer', border:'none',
                        background: filter===f ? C.purple : 'rgba(139,92,246,0.1)',
                        color: filter===f ? '#fff' : C.textSecondary,
                        textTransform:'capitalize',
                    }}>{f === 'all' ? 'All Students' : f}</button>
                ))}
            </motion.div>

            {/* Student Priority Table */}
            <motion.div variants={variants.item} className="glass-panel p-0" style={{ borderRadius:14, overflow:'hidden' }}>
                <table style={{ width:'100%', borderCollapse:'collapse' }}>
                    <thead>
                        <tr style={{ background:'rgba(124,58,237,0.12)', borderBottom:`1px solid ${C.border}` }}>
                            {['Student','Course','Risk Score','Primary Drop Factor','Days Since Contact','Status','Actions'].map(h => (
                                <th key={h} style={{ padding:'12px 16px', fontSize:11, fontWeight:700, color:C.textSecondary, textTransform:'uppercase', letterSpacing:'0.07em', textAlign:'left' }}>{h}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {filtered.map((s, i) => {
                            const logged = actionLog[s.id];
                            return (
                                <tr key={s.id} style={{
                                    borderBottom:`1px solid ${C.border}`,
                                    background: i%2===0 ? 'transparent' : 'rgba(139,92,246,0.03)',
                                    transition:'background 0.2s',
                                }}
                                    onMouseEnter={e => e.currentTarget.style.background='rgba(124,58,237,0.07)'}
                                    onMouseLeave={e => e.currentTarget.style.background= i%2===0 ? 'transparent' : 'rgba(139,92,246,0.03)'}
                                >
                                    <td style={{ padding:'12px 16px' }}>
                                        <div style={{ fontWeight:600, color:C.textPrimary, fontSize:13 }}>{s.name}</div>
                                        <div style={{ fontSize:11, color:C.textSecondary, fontFamily:'monospace' }}>{s.id}</div>
                                    </td>
                                    <td style={{ padding:'12px 16px', fontSize:12, color:C.textSecondary, fontFamily:'monospace' }}>{s.course}</td>
                                    <td style={{ padding:'12px 16px' }}><RiskBadge score={s.risk} /></td>
                                    <td style={{ padding:'12px 16px', fontSize:12, color:C.textSecondary }}>{s.drop}</td>
                                    <td style={{ padding:'12px 16px' }}>
                                        <span style={{ color: s.attendance < 70 ? C.red : s.attendance < 80 ? C.gold : C.green, fontWeight:700, fontSize:12 }}>
                                            {s.attendance}%
                                        </span>
                                    </td>
                                    <td style={{ padding:'12px 16px' }}>
                                        <span style={{
                                            background:`${statusColors[s.status]}22`, color:statusColors[s.status],
                                            border:`1px solid ${statusColors[s.status]}44`, borderRadius:6,
                                            padding:'2px 10px', fontSize:11, fontWeight:700, textTransform:'capitalize'
                                        }}>{s.status}</span>
                                    </td>
                                    <td style={{ padding:'12px 16px' }}>
                                        {logged ? (
                                            <span style={{ fontSize:11, color:C.green, fontWeight:600 }}>✓ {logged}</span>
                                        ) : (
                                            <div className="d-flex gap-1">
                                                {['Schedule','Email','Flag'].map(a => (
                                                    <button key={a} onClick={() => markAction(s.id, a)} style={{
                                                        padding:'3px 9px', borderRadius:6, fontSize:11, fontWeight:600, cursor:'pointer', border:'none',
                                                        background:'rgba(139,92,246,0.15)', color:C.textSecondary,
                                                    }}>{a}</button>
                                                ))}
                                            </div>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </motion.div>
        </motion.div>
    );
};

/* ─── Tab: Intervention Hub ───────────────────────────────────── */
const InterventionsTab = ({ atRiskStudents }) => {
    const [filterDrop, setFilterDrop] = useState('All');
    const rankColors = [C.gold, C.textSecondary, '#CD7F32', C.purple, C.blue, C.green];

    const interventions = useMemo(() => {
        const buckets = {
            Attendance: { name: 'Attendance nudges', bestFor: 'Attendance', cost: 'Low' },
            Assignment: { name: 'Assignment coaching', bestFor: 'Assignment', cost: 'Low' },
            Engagement: { name: 'Engagement boost', bestFor: 'Engagement', cost: 'Medium' },
            General: { name: 'Advisor outreach', bestFor: 'General', cost: 'Low' },
        };
        (atRiskStudents || []).forEach(s => {
            const risk = s.risk_score ?? 0;
            const attendance = s.exam_attendance_rate ?? 0;
            const quiz = s.graded_quiz_score ?? 0;
            const engagement = s.content_completion_score ?? 0;
            if (attendance < 70) buckets.Attendance.sample = (buckets.Attendance.sample || 0) + 1;
            if (quiz < 50) buckets.Assignment.sample = (buckets.Assignment.sample || 0) + 1;
            if (engagement < 60) buckets.Engagement.sample = (buckets.Engagement.sample || 0) + 1;
            if (risk >= 70) buckets.General.sample = (buckets.General.sample || 0) + 1;
        });
        return Object.values(buckets).map(b => ({
            ...b,
            effectiveness: Math.min(90, 40 + (b.sample || 0) * 2),
            improvement: Math.min(25, (b.sample || 0) * 0.8),
            confidence: Math.min(95, 70 + (b.sample || 0) * 0.5),
            timeToImpact: '2–4 wks',
            sample: b.sample || 0,
        }));
    }, [atRiskStudents]);

    const filtered = filterDrop === 'All'
        ? interventions
        : interventions.filter(i => i.bestFor === filterDrop || i.bestFor === 'General');

    const barData = interventions.map(i => ({ name:i.name.split(' ').slice(0,3).join(' '), effectiveness:i.effectiveness }));

    return (
        <motion.div initial="hidden" animate="visible" variants={variants.container}>
            {/* Bar Chart Overview */}
            <motion.div variants={variants.item} className="glass-panel p-4 mb-4" style={{ borderRadius:14 }}>
                <SectionTitle sub="Ranked by historical success rate across all students">Effectiveness at a Glance</SectionTitle>
                <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={barData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.1)" />
                        <XAxis dataKey="name" tick={{ fill:C.textSecondary, fontSize:10 }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fill:C.textSecondary, fontSize:11 }} axisLine={false} tickLine={false} unit="%" domain={[0,100]} />
                        <Tooltip {...TooltipStyle} formatter={v=>`${v}%`} />
                        <Bar dataKey="effectiveness" radius={[6,6,0,0]}>
                            {barData.map((_, i) => <Cell key={i} fill={i===0?C.gold:i===1?C.purple:C.blue} fillOpacity={1-i*0.1} />)}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </motion.div>

            {/* Filter */}
            <motion.div variants={variants.item} className="d-flex gap-2 mb-3 flex-wrap">
                <span style={{ fontSize:12, color:C.textSecondary, alignSelf:'center', marginRight:4 }}><FaFilter size={10}/> Filter by dropout factor:</span>
                {['All','Attendance','Assignment','Engagement','Peer'].map(f => (
                    <button key={f} onClick={() => setFilterDrop(f)} style={{
                        padding:'4px 12px', borderRadius:8, fontSize:12, fontWeight:600, cursor:'pointer', border:'none',
                        background: filterDrop===f ? C.purple : 'rgba(139,92,246,0.1)',
                        color: filterDrop===f ? '#fff' : C.textSecondary,
                    }}>{f}</button>
                ))}
            </motion.div>

            {/* Intervention Cards */}
            <motion.div variants={variants.item}>
                {filtered.map((item, idx) => (
                    <div key={item.name} className="glass-panel mb-3" style={{ borderRadius:12, padding:'18px 22px', border:`1px solid ${C.border}` }}>
                        <div className="d-flex gap-4 align-items-start">
                            {/* Rank */}
                            <div style={{ minWidth:52, textAlign:'center' }}>
                                <div style={{ fontSize:34, fontWeight:900, color: rankColors[idx] ?? C.textSecondary, lineHeight:1, fontFamily:'monospace' }}>{idx+1}</div>
                                {idx < 3 && <div style={{ fontSize:16 }}>{idx===0?'🥇':idx===1?'🥈':'🥉'}</div>}
                            </div>
                            {/* Content */}
                            <div style={{ flex:1 }}>
                                <div className="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
                                    <div style={{ fontSize:15, fontWeight:700, color:C.textPrimary }}>{item.name}</div>
                                    <div className="d-flex gap-2">
                                        <span style={{ background:C.goldFaint, color:C.gold, border:`1px solid ${C.gold}44`, borderRadius:6, padding:'2px 10px', fontSize:11, fontWeight:700 }}>
                                            Best for: {item.bestFor}
                                        </span>
                                        <span style={{ background:`${item.cost==='None'?C.green:item.cost==='Low'?C.blue:C.gold}22`,
                                            color: item.cost==='None'?C.green:item.cost==='Low'?C.blue:C.gold,
                                            borderRadius:6, padding:'2px 10px', fontSize:11, fontWeight:700 }}>
                                            Cost: {item.cost}
                                        </span>
                                    </div>
                                </div>
                                {/* Metrics Grid */}
                                <Row className="g-2 mt-1">
                                    {[
                                        ['Effectiveness',    `${item.effectiveness}%`, C.gold],
                                        ['Avg Improvement',  `+${item.improvement}%`,  C.green],
                                        ['Sample Size',      item.sample,               C.blue],
                                        ['Confidence',       `${item.confidence}%`,     C.purple],
                                        ['Time to Impact',   item.timeToImpact,         C.textSecondary],
                                    ].map(([l,v,col]) => (
                                        <Col key={l} xs={6} sm={4} md={2} style={{ minWidth:100 }}>
                                            <div style={{ fontSize:10, color:C.textSecondary, textTransform:'uppercase', letterSpacing:'0.07em', marginBottom:2 }}>{l}</div>
                                            <div style={{ fontSize:l==='Effectiveness'?18:14, fontWeight: l==='Effectiveness'?800:600, color: col, fontFamily:'monospace' }}>{v}</div>
                                        </Col>
                                    ))}
                                </Row>
                                {/* Effectiveness bar */}
                                <div className="mt-3">
                                    <MiniBar value={item.effectiveness} color={rankColors[idx] ?? C.purple} />
                                </div>
                            </div>
                        </div>
                    </div>
                ))}
            </motion.div>
        </motion.div>
    );
};

/* ─── Tab: Program Analytics ─────────────────────────────────── */
const ProgramTab = ({ students }) => {
    const deptStats = useMemo(() => {
        const map = {};
        (students || []).forEach(s => {
            const dept = s.department || 'Unknown';
            if (!map[dept]) {
                map[dept] = {
                    dept,
                    enrolled: 0,
                    atRisk: 0,
                    retention: 0,
                    satisfaction: 4.0,
                };
            }
            const entry = map[dept];
            entry.enrolled += 1;
            const risk = s.risk_score ?? 0;
            if (risk >= 60) entry.atRisk += 1;
        });
        return Object.values(map).map(d => {
            const atRiskPct = d.enrolled ? (d.atRisk / d.enrolled) * 100 : 0;
            const retention = Math.round(100 - atRiskPct);
            return { ...d, retention };
        });
    }, [students]);

    const deptBarData = deptStats.map(d => ({
        name: d.dept.split(' ')[0],
        'Enrolled': d.enrolled,
        'At Risk': d.atRisk,
        'Retention %': d.retention,
    }));

    const priorityColor = { HIGH: C.red, MEDIUM: C.gold, LOW: C.green };

    return (
        <motion.div initial="hidden" animate="visible" variants={variants.container}>

            {/* Dept Risk Bar */}
            <motion.div variants={variants.item} className="glass-panel p-4 mb-4" style={{ borderRadius:14 }}>
                <SectionTitle sub="Enrolled students and at-risk counts by department — key resource allocation data">Department Risk Overview</SectionTitle>
                <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={deptBarData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.1)" />
                        <XAxis dataKey="name" tick={{ fill:C.textSecondary, fontSize:11 }} axisLine={false} tickLine={false} />
                        <YAxis tick={{ fill:C.textSecondary, fontSize:11 }} axisLine={false} tickLine={false} />
                        <Tooltip {...TooltipStyle} />
                        <Legend wrapperStyle={{ color:C.textSecondary, fontSize:12 }} />
                        <Bar dataKey="Enrolled" fill={C.purple}  radius={[4,4,0,0]} />
                        <Bar dataKey="At Risk"  fill={C.red}     radius={[4,4,0,0]} />
                    </BarChart>
                </ResponsiveContainer>
            </motion.div>

            {/* Radar — Department Engagement Factors */}
            <Row className="g-4 mb-4">
                <Col lg={6}>
                    <motion.div variants={variants.item} className="glass-panel p-4 h-100" style={{ borderRadius:14 }}>
                        <SectionTitle sub="Cross-departmental engagement factor comparison">Multi-Department Radar</SectionTitle>
                        <ResponsiveContainer width="100%" height={260}>
                            <RadarChart data={RADAR_DATA}>
                                <PolarGrid stroke="rgba(139,92,246,0.15)" />
                                <PolarAngleAxis dataKey="factor" tick={{ fill:C.textSecondary, fontSize:11 }} />
                                <PolarRadiusAxis angle={90} domain={[50,100]} tick={{ fill:C.textSecondary, fontSize:9 }} />
                                <Radar name="Comp. Sci"  dataKey="cs"   stroke={C.purple} fill={C.purple} fillOpacity={0.15} strokeWidth={2} />
                                <Radar name="Math"       dataKey="math" stroke={C.gold}   fill={C.gold}   fillOpacity={0.1}  strokeWidth={2} />
                                <Radar name="Sciences"   dataKey="sci"  stroke={C.blue}   fill={C.blue}   fillOpacity={0.1}  strokeWidth={2} />
                                <Radar name="Humanities" dataKey="hum"  stroke={C.green}  fill={C.green}  fillOpacity={0.1}  strokeWidth={2} />
                                <Legend wrapperStyle={{ color:C.textSecondary, fontSize:12 }} />
                                <Tooltip {...TooltipStyle} />
                            </RadarChart>
                        </ResponsiveContainer>
                    </motion.div>
                </Col>

                {/* Dept Scorecards */}
                <Col lg={6}>
                    <motion.div variants={variants.item} className="glass-panel p-4 h-100" style={{ borderRadius:14 }}>
                        <SectionTitle sub="Retention rate and revenue at stake per department">Department Scorecards</SectionTitle>
                        <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
                            {deptStats.map(d => {
                                const atRiskPct = Math.round((d.atRisk / d.enrolled) * 100);
                                const col = atRiskPct >= 28 ? C.red : atRiskPct >= 20 ? C.gold : C.green;
                                return (
                                    <div key={d.dept} style={{
                                        background:C.surface, borderRadius:10, padding:'12px 16px',
                                        border:`1px solid ${col}33`, borderLeft:`3px solid ${col}`,
                                    }}>
                                        <div className="d-flex justify-content-between mb-1">
                                            <span style={{ fontSize:13, fontWeight:700, color:C.textPrimary }}>{d.dept}</span>
                                            <span style={{ fontSize:12, color: col, fontWeight:700 }}>{d.retention}% retention</span>
                                        </div>
                                        <div className="d-flex gap-4" style={{ fontSize:11, color:C.textSecondary }}>
                                            <span><FaUsers size={8}/> {d.enrolled} enrolled</span>
                                            <span style={{ color:col }}><FaExclamationTriangle size={8}/> {d.atRisk} at-risk ({atRiskPct}%)</span>
                                            <span>★ {d.satisfaction}</span>
                                        </div>
                                        <MiniBar value={d.retention} color={col} />
                                    </div>
                                );
                            })}
                        </div>
                    </motion.div>
                </Col>
            </Row>

            {/* Marketing Insights */}
            <motion.div variants={variants.item} className="glass-panel p-4" style={{ borderRadius:14 }}>
                <div className="d-flex align-items-center gap-2 mb-4">
                    <FaBullhorn style={{ color:C.gold, fontSize:18 }} />
                    <div>
                        <h5 style={{ color:C.textPrimary, fontWeight:700, margin:0 }}>Marketing & Staff Priority Insights</h5>
                        <p style={{ color:C.textSecondary, fontSize:13, margin:0 }}>Actionable intelligence for resource allocation and outreach campaigns</p>
                    </div>
                </div>
                <div style={{ display:'flex', flexDirection:'column', gap:14 }}>
                    {MARKET_INSIGHTS.map((insight, i) => (
                        <div key={i} style={{
                            background:C.surface, borderRadius:12, padding:'16px 20px',
                            border:`1px solid ${priorityColor[insight.priority]}33`,
                            borderLeft:`4px solid ${priorityColor[insight.priority]}`,
                        }}>
                            <div className="d-flex justify-content-between align-items-start mb-2 gap-2 flex-wrap">
                                <div style={{ fontSize:14, fontWeight:700, color:C.textPrimary }}>{insight.area}</div>
                                <span style={{
                                    background:`${priorityColor[insight.priority]}22`, color:priorityColor[insight.priority],
                                    border:`1px solid ${priorityColor[insight.priority]}44`, borderRadius:6,
                                    padding:'2px 10px', fontSize:11, fontWeight:700,
                                }}>{insight.priority} PRIORITY</span>
                            </div>
                            <div style={{ fontSize:12, color:C.textSecondary, marginBottom:8, lineHeight:1.6 }}>
                                <FaChartBar size={10} style={{ marginRight:5, color:C.textSecondary }} />{insight.impact}
                            </div>
                            <div style={{ fontSize:12, color:C.green, fontWeight:600 }}>
                                <FaRocket size={10} style={{ marginRight:5 }} />{insight.action}
                            </div>
                        </div>
                    ))}
                </div>
            </motion.div>
        </motion.div>
    );
};

/* ─── Main Page ───────────────────────────────────────────────── */
const FacultyTools = () => {
    const [activeTab, setActiveTab] = useState('courses');
    const [facultyStudents, setFacultyStudents] = useState([]);
    const [atRiskStudents, setAtRiskStudents] = useState([]);
    const [alerts, setAlerts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let isMounted = true;
        const load = async () => {
            setLoading(true);
            setError(null);
            const [studentsResp, atRiskResp, alertsResp] = await Promise.all([
                getFacultyStudents(200),
                getFacultyAtRiskStudents(60, 200),
                getFacultyAlerts(100),
            ]);

            if (!isMounted) return;

            if (!studentsResp.success) {
                setError(studentsResp.message || 'Failed to load faculty cohort.');
                setLoading(false);
                return;
            }

            setFacultyStudents(studentsResp.data?.students || []);
            setAtRiskStudents(atRiskResp.success ? atRiskResp.data?.students || [] : []);
            setAlerts(alertsResp.success ? alertsResp.data?.alerts || [] : []);
            setLoading(false);
        };
        load();
        return () => {
            isMounted = false;
        };
    }, []);

    const summary = useMemo(() => {
        const totalEnrolled = facultyStudents.length;
        const atRisk = atRiskStudents.length;
        const critical = atRiskStudents.filter(s => (s.risk_score ?? 0) >= 80).length;
        const interventionSuccess = totalEnrolled > 0 ? Math.round(((totalEnrolled - atRisk) / totalEnrolled) * 100) : 0;
        return { totalEnrolled, atRisk, critical, interventionSuccess };
    }, [facultyStudents, atRiskStudents]);

    const tabContent = {
        courses:       <CoursesTab students={facultyStudents} loading={loading} error={error} />,
        alerts:        <AlertsTab alerts={alerts} loading={loading} error={error} />,
        interventions: <InterventionsTab atRiskStudents={atRiskStudents} />,
        program:       <ProgramTab students={facultyStudents} />,
    };

    return (
        <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ duration:0.3 }}>
            <Container fluid className="py-4" style={{ maxWidth:'1600px' }}>

                {/* Header */}
                <div className="d-flex justify-content-between align-items-end mb-5 flex-wrap gap-3">
                    <div>
                        <h1 className="display-5 fw-bold text-gradient mb-2">Faculty & Staff Command Center</h1>
                        <p className="text-secondary fs-6" style={{ maxWidth:620 }}>
                            Course performance, student risk intelligence, intervention playbooks, and program-level analytics for faculty, staff, and marketing teams.
                        </p>
                    </div>
                    <button style={{
                        background:'rgba(124,58,237,0.15)', border:`1px solid ${C.border}`, borderRadius:10,
                        color:C.textSecondary, padding:'8px 20px', fontSize:13, fontWeight:600, cursor:'pointer',
                        display:'flex', alignItems:'center', gap:8,
                    }}>
                        <FaDownload size={12}/> Export Report
                    </button>
                </div>

                {/* KPI Cards */}
                <motion.div initial="hidden" animate="visible" variants={variants.container} className="mb-5">
                    <Row className="g-4">
                        <Col md={3}><StatCard icon={<FaGraduationCap/>} label="Active Courses"       value={summary.totalEnrolled}                          sub="Students in your cohort"          color={C.purple} /></Col>
                        <Col md={3}><StatCard icon={<FaExclamationTriangle/>} label="Students Needing Attention" value={summary.atRisk}             sub={`${summary.critical} critical`} color={C.red}    /></Col>
                        <Col md={3}><StatCard icon={<FaRegCalendarCheck/>} label="Avg Completion Rate" value={facultyStudents.length ? `${Math.round(facultyStudents.reduce((a,s)=>a+(s.content_completion_score ?? 0),0)/facultyStudents.length)}%` : '—'} sub="Across your cohort" color={C.green} /></Col>
                        <Col md={3}><StatCard icon={<FaStar/>} label="Intervention Success Rate" value={`${summary.interventionSuccess || 0}%`}           sub="Derived from current risk mix"                color={C.gold}   /></Col>
                    </Row>
                </motion.div>

                {/* Tab Bar */}
                <div className="d-flex gap-2 mb-4 flex-wrap" style={{ borderBottom:`1px solid ${C.border}`, paddingBottom:8 }}>
                    {TABS.map(tab => (
                        <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
                            display:'flex', alignItems:'center', gap:7, padding:'8px 20px', borderRadius:'10px 10px 0 0',
                            fontSize:13, fontWeight:700, cursor:'pointer', border:'none', transition:'all 0.2s',
                            background: activeTab===tab.id ? C.purple : 'transparent',
                            color: activeTab===tab.id ? '#fff' : C.textSecondary,
                            borderBottom: activeTab===tab.id ? `2px solid ${C.purpleLight}` : '2px solid transparent',
                        }}>
                            {tab.icon} {tab.label}
                        </button>
                    ))}
                </div>

                {/* Loading / Error states */}
                {loading && (
                    <div className="mb-4">
                        <Spinner animation="border" variant="primary" size="sm" className="me-2" />
                        <span style={{ color: C.textSecondary, fontSize: 13 }}>Loading faculty cohort and alerts…</span>
                    </div>
                )}
                {error && (
                    <Alert variant="danger" className="mb-4">
                        {error}
                    </Alert>
                )}

                {/* Tab Content */}
                <AnimatePresence mode="wait">
                    <motion.div
                        key={activeTab}
                        initial={{ opacity:0, y:8 }}
                        animate={{ opacity:1, y:0 }}
                        exit={{ opacity:0, y:-8 }}
                        transition={{ duration:0.2 }}
                    >
                        {tabContent[activeTab]}
                    </motion.div>
                </AnimatePresence>

            </Container>
        </motion.div>
    );
};

export default FacultyTools;
