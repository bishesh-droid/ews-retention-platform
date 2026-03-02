import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Row, Col, Modal, Spinner, Alert } from 'react-bootstrap';
import {
    FaExclamationTriangle, FaInfoCircle, FaGraduationCap, FaFire,
    FaChartLine, FaBolt, FaShieldAlt, FaCheckCircle, FaSyncAlt,
    FaDownload, FaHistory, FaBullseye, FaArrowUp, FaArrowDown,
} from 'react-icons/fa';
import { motion, AnimatePresence } from 'framer-motion';
import {
    BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
    Tooltip, ResponsiveContainer, Cell, ReferenceLine, Legend,
} from 'recharts';
import { variants } from '../utils/motionConfig';
import { getStudentList, getRiskDistribution, getBatchPredictions } from '../services/api';

/* ─── Palette ────────────────────────────────────────────────── */
const C = {
    purple:  '#7C3AED', purpleL: '#8B5CF6', purpleFaint: 'rgba(124,58,237,0.12)',
    gold:    '#F59E0B', goldFaint:   'rgba(245,158,11,0.12)',
    blue:    '#3B82F6', blueFaint:   'rgba(59,130,246,0.12)',
    green:   '#10B981', greenFaint:  'rgba(16,185,129,0.12)',
    red:     '#EF4444', redFaint:    'rgba(239,68,68,0.12)',
    surface: '#130D23', surfaceHi: '#1A1035',
    border:  'rgba(139,92,246,0.18)',
    text:    '#EDE9FE', textSec: '#B8AADA',
    tt:      '#1E1535',
};

const FACTOR_META = {
    academic:    { color: C.purple, faint: C.purpleFaint, icon: <FaGraduationCap />, label: 'Academic Performance' },
    engagement:  { color: C.gold,   faint: C.goldFaint,   icon: <FaFire />,          label: 'Engagement' },
    consistency: { color: C.blue,   faint: C.blueFaint,   icon: <FaChartLine />,     label: 'Consistency' },
    intent:      { color: C.green,  faint: C.greenFaint,  icon: <FaBolt />,          label: 'Intent & Responsiveness' },
};

/* ─── Static data ────────────────────────────────────────────── */
const FACTOR_DETAILS = {
    academic: {
        title: 'Academic Performance Signals',
        description: 'Measures how well a student is performing on graded work and assessments over time.',
        metrics: [
            { label:'Quiz scores',               icon:'📝', impact:'High' },
            { label:'Assignment grades',         icon:'📋', impact:'High' },
            { label:'Final exam scores',         icon:'🎓', impact:'Critical' },
            { label:'Improvement over time',     icon:'📈', impact:'Medium' },
            { label:'Time spent on assessments', icon:'⏱', impact:'Medium' },
            { label:'Retake count',              icon:'🔄', impact:'High' },
            { label:'Practice test accuracy',    icon:'✅', impact:'Medium' },
            { label:'Difficulty of questions',   icon:'🧩', impact:'Low' },
        ],
        thresholds: [
            { label:'Critical', range:'< 40% avg score',  color: C.red   },
            { label:'High',     range:'40 – 60%',         color: C.gold  },
            { label:'Medium',   range:'60 – 75%',         color: C.blue  },
            { label:'Low',      range:'> 75%',            color: C.green },
        ],
        studentsAffected: 142,
        trend: +8,
    },
    engagement: {
        title: 'Engagement Signals',
        description: 'Tracks how actively students interact with course content, live sessions, and the platform.',
        metrics: [
            { label:'LMS login frequency',     icon:'🔐', impact:'Critical' },
            { label:'Video watch percentage',  icon:'🎬', impact:'High' },
            { label:'Pause / rewind behavior', icon:'⏸',  impact:'Medium' },
            { label:'Live class attendance',   icon:'📡', impact:'Critical' },
            { label:'Time spent per session',  icon:'⏱',  impact:'High' },
            { label:'Forum participation',     icon:'💬', impact:'Medium' },
            { label:'Resource downloads',      icon:'📥', impact:'Low' },
            { label:'Notes opened',            icon:'📓', impact:'Low' },
        ],
        thresholds: [
            { label:'Critical', range:'No activity 14+ days', color: C.red   },
            { label:'High',     range:'1–2× / week',          color: C.gold  },
            { label:'Medium',   range:'3–4× / week',          color: C.blue  },
            { label:'Low',      range:'Daily',                color: C.green },
        ],
        studentsAffected: 218,
        trend: -5,
    },
    consistency: {
        title: 'Consistency Signals',
        description: 'Measures behavioral regularity — sudden drops in activity are strong early warning indicators.',
        metrics: [
            { label:'Std deviation of login times',   icon:'📊', impact:'High' },
            { label:'Gaps between sessions',          icon:'📅', impact:'Critical' },
            { label:'Week-to-week activity drop',     icon:'📉', impact:'Critical' },
            { label:'Streaks of activity',            icon:'🔥', impact:'Medium' },
            { label:'Sudden behavior changes',        icon:'⚡', impact:'High' },
        ],
        thresholds: [
            { label:'Critical', range:'No streaks & high variance',   color: C.red   },
            { label:'High',     range:'Declining weekly',             color: C.gold  },
            { label:'Medium',   range:'Occasional gaps',              color: C.blue  },
            { label:'Low',      range:'Consistent daily activity',    color: C.green },
        ],
        studentsAffected: 96,
        trend: +3,
    },
    intent: {
        title: 'Intent & Responsiveness Signals',
        description: 'Captures forward-looking behaviors like renewal intent, communication responsiveness, and course exploration.',
        metrics: [
            { label:'Course progress %',       icon:'📶', impact:'High' },
            { label:'New courses browsed',     icon:'🔍', impact:'Medium' },
            { label:'Certificates downloaded', icon:'🏆', impact:'Low' },
            { label:'Exam registrations',      icon:'📝', impact:'Medium' },
            { label:'Refund request attempts', icon:'💸', impact:'Critical' },
            { label:'Subscription renewal',    icon:'🔄', impact:'Critical' },
            { label:'Email open rate',         icon:'📧', impact:'High' },
            { label:'WhatsApp reply rate',     icon:'💬', impact:'High' },
            { label:'Click-through rate',      icon:'🖱', impact:'Medium' },
            { label:'Time to respond',         icon:'⏰', impact:'Medium' },
            { label:'Ignore count',            icon:'🔕', impact:'High' },
        ],
        thresholds: [
            { label:'Critical', range:'Refund requested & no engagement', color: C.red   },
            { label:'High',     range:'Declining intent signals',         color: C.gold  },
            { label:'Medium',   range:'Mixed signals',                    color: C.blue  },
            { label:'Low',      range:'Active progression & responsive',  color: C.green },
        ],
        studentsAffected: 74,
        trend: -12,
    },
};

const ACCURACY_HISTORY = [
    { month:'Sep', accuracy:78, recall:72, precision:81 },
    { month:'Oct', accuracy:80, recall:74, precision:83 },
    { month:'Nov', accuracy:82, recall:77, precision:85 },
    { month:'Dec', accuracy:79, recall:73, precision:82 },
    { month:'Jan', accuracy:84, recall:80, precision:87 },
    { month:'Feb', accuracy:86, recall:83, precision:88 },
    { month:'Mar', accuracy:87, recall:84, precision:89 },
];

const CORRELATION_DATA = [
    { factor:'Academic',    correlation:0.74 },
    { factor:'Engagement',  correlation:0.68 },
    { factor:'Consistency', correlation:0.61 },
    { factor:'Intent',      correlation:0.54 },
];

/* ─── Helpers ────────────────────────────────────────────────── */
const TT = {
    contentStyle: { background: C.tt, border:`1px solid ${C.border}`, borderRadius:10, color:C.text, fontSize:12 },
    labelStyle:   { color: C.textSec },
    cursor:       { fill:'rgba(139,92,246,0.07)' },
};

const impactColor = { Critical: C.red, High: C.gold, Medium: C.blue, Low: C.green };

const MetricChip = ({ label, icon, impact }) => (
    <div style={{
        display:'inline-flex', alignItems:'center', gap:5,
        padding:'4px 10px', borderRadius:8, marginRight:6, marginBottom:6,
        background:`${impactColor[impact]}18`,
        border:`1px solid ${impactColor[impact]}33`,
        fontSize:11, color: C.text,
    }}>
        <span>{icon}</span>
        <span style={{ color: C.textSec }}>{label}</span>
        <span style={{ fontSize:9, fontWeight:700, color: impactColor[impact], textTransform:'uppercase' }}>{impact}</span>
    </div>
);

const ThresholdBand = ({ label, range, color }) => (
    <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:6 }}>
        <div style={{ width:10, height:10, borderRadius:3, background:color, flexShrink:0 }} />
        <span style={{ fontSize:11, fontWeight:700, color, minWidth:52 }}>{label}</span>
        <span style={{ fontSize:11, color: C.textSec }}>{range}</span>
    </div>
);

const StatCard = ({ icon, label, value, sub, color = C.purple }) => (
    <div className="glass-panel p-3 h-100" style={{ borderRadius:14, border:`1px solid ${color}33` }}>
        <div className="d-flex justify-content-between align-items-start mb-2">
            <div style={{ fontSize:18, color }}>{icon}</div>
            <div style={{ fontSize:10, color:C.textSec, textTransform:'uppercase', letterSpacing:'0.07em', textAlign:'right' }}>{label}</div>
        </div>
        <div style={{ fontSize:26, fontWeight:800, color:C.text, lineHeight:1 }}>{value}</div>
        {sub && <div style={{ fontSize:11, color:C.textSec, marginTop:5 }}>{sub}</div>}
    </div>
);

/* ─── Main Page ──────────────────────────────────────────────── */
const RiskFactors = () => {
    const [weights, setWeights] = useState({ academic:35, engagement:30, consistency:20, intent:15 });
    const [showModal, setShowModal]         = useState(false);
    const [applied, setApplied]             = useState(false);
    const [expandedFactor, setExpandedFactor] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [students, setStudents] = useState([]);
    const [riskDistribution, setRiskDistribution] = useState(null);
    const [predictions, setPredictions] = useState([]);

    useEffect(() => {
        let isMounted = true;
        const load = async () => {
            setLoading(true);
            setError(null);
            const [studentsResp, distResp, predsResp] = await Promise.all([
                getStudentList(1, 500),
                getRiskDistribution(),
                getBatchPredictions(500),
            ]);

            if (!isMounted) return;

            if (!studentsResp.success || !studentsResp.data) {
                setError(studentsResp.message || 'Failed to load risk data.');
                setLoading(false);
                return;
            }

            const sPayload = studentsResp.data;
            const pageStudents = sPayload.students || [];
            setStudents(pageStudents);

            if (distResp.success) {
                setRiskDistribution(distResp.data);
            }

            if (predsResp.success && predsResp.data) {
                const data = predsResp.data;
                const preds = Array.isArray(data.predictions) ? data.predictions : data.predictions || data;
                setPredictions(Array.isArray(preds) ? preds : []);
            }

            setLoading(false);
        };

        load();
        return () => {
            isMounted = false;
        };
    }, []);

    const topRiskDrivers = useMemo(() => {
        const map = {};
        (students || []).forEach(s => {
            const rb = s.risk_breakdown;
            if (!rb || typeof rb !== 'object') return;
            Object.entries(rb).forEach(([name, value]) => {
                if (!name) return;
                if (!map[name]) {
                    map[name] = { name, count: 0, total: 0 };
                }
                map[name].count += 1;
                const num = typeof value === 'number' ? value : 0;
                map[name].total += num;
            });
        });
        const arr = Object.values(map).map(d => ({
            ...d,
            avg: d.count > 0 ? d.total / d.count : 0,
        }));
        arr.sort((a, b) => b.avg - a.avg);
        return arr.slice(0, 8);
    }, [students]);

    const categoryContrib = useMemo(() => {
        const sums = { academic: 0, engagement: 0, consistency: 0, intent: 0 };
        let n = 0;
        (predictions || []).forEach(p => {
            const sb = p.signal_breakdown || p.signalBreakdown;
            if (!sb || typeof sb !== 'object') return;
            n += 1;
            sums.academic += sb.academic_signal_score ?? 0;
            sums.engagement += sb.engagement_signal_score ?? 0;
            sums.consistency += sb.consistency_signal_score ?? 0;
            sums.intent += sb.intent_signal_score ?? 0;
        });
        if (!n) return [];
        const items = Object.entries(sums).map(([key, total]) => ({
            key,
            avg: total / n,
        }));
        const totalAvg = items.reduce((s, x) => s + x.avg, 0) || 1;
        return items.map(x => ({
            ...x,
            percent: Math.round((x.avg / totalAvg) * 100),
        }));
    }, [predictions]);

    useEffect(() => {
        if (!categoryContrib.length) return;
        const next = { ...weights };
        categoryContrib.forEach(c => {
            if (next[c.key] !== undefined) {
                next[c.key] = c.percent;
            }
        });
        const total = Object.values(next).reduce((s, v) => s + v, 0);
        if (total !== 100) {
            const factorKeys = Object.keys(next);
            if (factorKeys.length) {
                next[factorKeys[0]] += (100 - total);
            }
        }
        setWeights(next);
        setApplied(true);
    }, [categoryContrib]);

    const correlationData = useMemo(() => {
        if (categoryContrib.length) {
            return categoryContrib.map(c => ({
                factor: FACTOR_META[c.key].label.split(' ')[0],
                correlation: c.percent / 100,
            }));
        }
        return [
            { factor: 'Academic', correlation: 0 },
            { factor: 'Engagement', correlation: 0 },
            { factor: 'Consistency', correlation: 0 },
            { factor: 'Intent', correlation: 0 },
        ];
    }, [categoryContrib]);

    const mlSummary = useMemo(() => {
        if (!categoryContrib.length || !topRiskDrivers.length) {
            return 'ML explanation summary is not yet available. Once more predictions are generated, this view will describe which signals and features are most influential.';
        }
        const topCategory = [...categoryContrib].sort((a, b) => b.percent - a.percent)[0];
        const topFactors = topRiskDrivers.slice(0, 3).map(d => d.name).join(', ');
        const catLabel = FACTOR_META[topCategory.key]?.label || topCategory.key;
        return `Across the cohort, ${catLabel.toLowerCase()} accounts for roughly ${topCategory.percent}% of the modelled risk signal, with top drivers including ${topFactors}.`;
    }, [categoryContrib, topRiskDrivers]);

    const total = useMemo(() => Object.values(weights).reduce((s,v) => s+v, 0), [weights]);

    const handleWeightChange = (factor, value) => {
        const newVal = parseInt(value);
        const diff   = newVal - weights[factor];
        const others = Object.keys(weights).filter(f => f !== factor);
        const adj    = -diff / others.length;
        const next   = { ...weights, [factor]: newVal };
        others.forEach(f => { next[f] = Math.max(0, Math.round(next[f] + adj)); });
        const t = Object.values(next).reduce((s,v) => s+v, 0);
        if (t !== 100) next[others[0]] += (100 - t);
        setWeights(next);
        setApplied(false);
    };

    const resetToDefault = () => {
        setWeights({ academic:35, engagement:30, consistency:20, intent:15 });
        setApplied(false);
    };

    const confirmApply = () => { setShowModal(false); setApplied(true); };

    const barData = Object.entries(weights).map(([k,v]) => ({
        name: FACTOR_META[k].label,
        value: v,
        fill: FACTOR_META[k].color,
    }));

    return (
        <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ duration:0.3 }} className="pb-5">

            {/* ── Header ── */}
            <div className="d-flex justify-content-between align-items-end mb-5 flex-wrap gap-3">
                <div>
                    <div className="d-flex align-items-center gap-3 mb-2">
                        <h1 className="display-5 fw-bold text-gradient mb-0">Risk Factor Configuration</h1>
                        <span style={{
                            background: applied ? C.greenFaint : C.purpleFaint,
                            border:`1px solid ${applied ? C.green : C.purple}44`,
                            color: applied ? C.green : C.purpleL,
                            borderRadius:8, padding:'3px 12px', fontSize:11, fontWeight:700,
                        }}>
                            {applied ? '✓ Applied' : 'v2.4 — Draft'}
                        </span>
                    </div>
                    <p className="text-secondary fs-6" style={{ maxWidth:640 }}>
                        Explore how academic performance, engagement, consistency, and intent contribute to student dropout risk, based on live backend data.
                    </p>
                </div>
                <div className="d-flex gap-2">
                    <button onClick={() => {}} style={{
                        background:'rgba(139,92,246,0.1)', border:`1px solid ${C.border}`,
                        borderRadius:10, color:C.textSec, padding:'8px 18px', fontSize:13, fontWeight:600, cursor:'pointer',
                        display:'flex', alignItems:'center', gap:7,
                    }}><FaHistory size={11}/> Version History</button>
                    <button onClick={() => {}} style={{
                        background:'rgba(139,92,246,0.1)', border:`1px solid ${C.border}`,
                        borderRadius:10, color:C.textSec, padding:'8px 18px', fontSize:13, fontWeight:600, cursor:'pointer',
                        display:'flex', alignItems:'center', gap:7,
                    }}><FaDownload size={11}/> Export Config</button>
                </div>
            </div>

            {/* Loading / error / empty states */}
            {loading && (
                <div className="mb-4 d-flex align-items-center gap-2">
                    <Spinner animation="border" variant="primary" size="sm" />
                    <span style={{ color: C.textSec, fontSize: 13 }}>Loading cohort risk factors and ML signals…</span>
                </div>
            )}
            {error && (
                <Alert variant="danger" className="mb-4">
                    {error}
                </Alert>
            )}
            {!loading && !error && students.length === 0 && (
                <Alert variant="info" className="mb-4">
                    No risk data is available yet. Once students are ingested and scored, this view will summarise their key risk drivers.
                </Alert>
            )}

            {/* ── Model Health KPIs ── */}
            <motion.div initial="hidden" animate="visible" variants={variants.container} className="mb-5">
                <Row className="g-3">
                    <Col md={3}><StatCard icon={<FaShieldAlt/>}  label="Model Accuracy"      value="87%"  sub="Mar 2026 — +1% vs last month" color={C.green}  /></Col>
                    <Col md={3}><StatCard icon={<FaBullseye/>}   label="Predictions Made"     value={predictions.length || '—'} sub="Batch risk predictions loaded"                color={C.purple} /></Col>
                    <Col md={3}><StatCard icon={<FaFire/>}       label="Students Flagged"     value={students.filter(s => (s.risk_score ?? 0) >= 70).length || '—'}  sub="Above high-risk threshold"      color={C.gold}   /></Col>
                    <Col md={3}><StatCard icon={<FaSyncAlt/>}    label="Last Recalibration"   value="Feb 28" sub="Next: Mar 31"              color={C.blue}   /></Col>
                </Row>
            </motion.div>

            {/* ── Top Risk Drivers ── */}
            <motion.div initial="hidden" animate="visible" variants={variants.container} className="mb-5">
                <motion.div variants={variants.item} className="glass-panel p-4" style={{ borderRadius:14 }}>
                    <div className="d-flex justify-content-between align-items-center mb-3">
                        <div>
                            <h5 style={{ color:C.text, fontWeight:700, margin:0 }}>Top Risk Drivers Across Cohort</h5>
                            <p style={{ color:C.textSec, fontSize:12, margin:'4px 0 0' }}>
                                Aggregated from per-student risk breakdowns computed by the backend risk engine.
                            </p>
                        </div>
                    </div>
                    {topRiskDrivers.length === 0 ? (
                        <p style={{ color:C.textSec, fontSize:12, margin:0 }}>No risk drivers available yet.</p>
                    ) : (
                        <div className="d-flex flex-wrap gap-2">
                            {topRiskDrivers.map(d => (
                                <div
                                    key={d.name}
                                    style={{
                                        padding:'6px 12px',
                                        borderRadius:999,
                                        background:'rgba(139,92,246,0.08)',
                                        border:`1px solid ${C.border}`,
                                        fontSize:11,
                                        color:C.text,
                                        display:'inline-flex',
                                        alignItems:'center',
                                        gap:8,
                                    }}
                                >
                                    <span style={{ fontWeight:700 }}>{d.name}</span>
                                    <span style={{ color:C.textSec }}>avg impact: {d.avg.toFixed(2)}</span>
                                    <span style={{ color:C.textSec }}>students: {d.count}</span>
                                </div>
                            ))}
                        </div>
                    )}
                </motion.div>
            </motion.div>

            {/* ── Weight Configurator ── */}
            <motion.div initial="hidden" animate="visible" variants={variants.container} className="mb-5">
                <Row className="g-4">
                    {/* Chart */}
                    <Col lg={6}>
                        <motion.div variants={variants.item} className="glass-panel p-4 h-100" style={{ borderRadius:14 }}>
                            <div className="d-flex justify-content-between align-items-center mb-4">
                                <div>
                                    <h5 style={{ color:C.text, fontWeight:700, margin:0 }}>Weight Distribution</h5>
                                    <p style={{ color:C.textSec, fontSize:12, margin:'4px 0 0' }}>Live preview — drag sliders to update</p>
                                </div>
                                <div style={{
                                    background: total === 100 ? C.greenFaint : C.redFaint,
                                    border:`1px solid ${total===100?C.green:C.red}44`,
                                    color: total===100 ? C.green : C.red,
                                    borderRadius:8, padding:'4px 12px', fontSize:12, fontWeight:700,
                                }}>
                                    Total: {total}%
                                </div>
                            </div>
                            <ResponsiveContainer width="100%" height={260}>
                                <BarChart data={barData} layout="vertical" barCategoryGap="20%">
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.1)" horizontal={false} />
                                    <XAxis type="number" domain={[0,100]} tick={{ fill:C.textSec, fontSize:11 }} axisLine={false} tickLine={false} unit="%" />
                                    <YAxis type="category" dataKey="name" tick={{ fill:'#EDE9FE', fontSize:12, fontWeight:600 }} axisLine={false} tickLine={false} width={138} />
                                    <Tooltip {...TT} formatter={v=>[`${v}%`, 'Weight']} />
                                    <ReferenceLine x={25} stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                                    <Bar dataKey="value" radius={[0,6,6,0]}>
                                        {barData.map((d, i) => <Cell key={i} fill={d.fill} />)}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>

                            {/* Factor correlation bar */}
                            <div className="mt-4 pt-3" style={{ borderTop:`1px solid ${C.border}` }}>
                                <div style={{ fontSize:11, color:C.textSec, textTransform:'uppercase', letterSpacing:'0.07em', marginBottom:10 }}>Dropout Correlation Strength</div>
                                {correlationData.map((d, i) => (
                                    <div key={d.factor} className="mb-2">
                                        <div className="d-flex justify-content-between" style={{ fontSize:11, color:C.textSec, marginBottom:3 }}>
                                            <span>{d.factor}</span>
                                            <span style={{ fontWeight:700, color:C.text }}>{Math.round(d.correlation*100)}%</span>
                                        </div>
                                        <div style={{ background:'rgba(255,255,255,0.06)', borderRadius:4, height:5 }}>
                                            <div style={{ width:`${d.correlation*100}%`, background:Object.values(FACTOR_META)[i].color, borderRadius:4, height:'100%', transition:'width 0.6s' }} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </motion.div>
                    </Col>

                    {/* Sliders */}
                    <Col lg={6}>
                        <motion.div variants={variants.item} className="glass-panel p-4 h-100" style={{ borderRadius:14 }}>
                            <h5 style={{ color:C.text, fontWeight:700, marginBottom:6 }}>Adjust Weights</h5>
                            <p style={{ color:C.textSec, fontSize:12, marginBottom:24 }}>
                                Weights auto-balance to 100%. Drag to redistribute importance across signal categories.
                            </p>

                            {Object.entries(weights).map(([factor, weight]) => {
                                const meta = FACTOR_META[factor];
                                const detail = FACTOR_DETAILS[factor];
                                const pctChange = weight - { academic:35, engagement:30, consistency:20, intent:15 }[factor];
                                return (
                                    <div key={factor} className="mb-4">
                                        <div className="d-flex justify-content-between align-items-center mb-2">
                                            <div className="d-flex align-items-center gap-2">
                                                <span style={{ color: meta.color, fontSize:14 }}>{meta.icon}</span>
                                                <span style={{ fontSize:13, fontWeight:600, color:C.text }}>{detail.title}</span>
                                            </div>
                                            <div className="d-flex align-items-center gap-2">
                                                {pctChange !== 0 && (
                                                    <span style={{ fontSize:10, color: pctChange > 0 ? C.green : C.red, fontWeight:700 }}>
                                                        {pctChange > 0 ? <FaArrowUp size={8}/> : <FaArrowDown size={8}/>} {Math.abs(pctChange)}%
                                                    </span>
                                                )}
                                                <span style={{
                                                    background: meta.faint, border:`1px solid ${meta.color}44`,
                                                    color: meta.color, borderRadius:8, padding:'3px 10px',
                                                    fontSize:12, fontWeight:800, minWidth:44, textAlign:'center',
                                                }}>{weight}%</span>
                                            </div>
                                        </div>
                                        {/* Custom slider */}
                                        <div style={{ position:'relative', height:6, borderRadius:4, background:'rgba(255,255,255,0.08)', cursor:'pointer' }}>
                                            <div style={{
                                                position:'absolute', left:0, top:0, height:'100%',
                                                width:`${weight}%`, background: meta.color,
                                                borderRadius:4, transition:'width 0.15s',
                                            }} />
                                            <input
                                                type="range" min="0" max="100" value={weight}
                                                onChange={e => handleWeightChange(factor, e.target.value)}
                                                style={{
                                                    position:'absolute', top:'50%', transform:'translateY(-50%)',
                                                    width:'100%', opacity:0, height:20, cursor:'pointer', margin:0,
                                                }}
                                            />
                                        </div>
                                        <div style={{ display:'flex', justifyContent:'space-between', fontSize:9, color:'rgba(255,255,255,0.2)', marginTop:3 }}>
                                            <span>0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span>
                                        </div>
                                    </div>
                                );
                            })}

                            <div className="d-flex gap-2 mt-3">
                                <button
                                    onClick={() => setShowModal(true)}
                                    disabled={total !== 100}
                                    style={{
                                        flex:1, padding:'10px 0', borderRadius:10, border:'none',
                                        background: total===100 ? `linear-gradient(135deg, ${C.purple}, ${C.purpleL})` : 'rgba(255,255,255,0.06)',
                                        color: total===100 ? '#fff' : C.textSec,
                                        fontSize:13, fontWeight:700, cursor: total===100?'pointer':'not-allowed',
                                        transition:'all 0.2s',
                                    }}
                                >Apply Changes</button>
                                <button
                                    onClick={resetToDefault}
                                    style={{
                                        flex:1, padding:'10px 0', borderRadius:10,
                                        border:`1px solid ${C.border}`, background:'transparent',
                                        color:C.textSec, fontSize:13, fontWeight:600, cursor:'pointer',
                                    }}
                                >Reset to Default</button>
                            </div>

                            <div className="d-flex gap-2 mt-3 p-3" style={{ background:C.blueFaint, border:`1px solid ${C.blue}33`, borderRadius:10 }}>
                                <FaInfoCircle style={{ color:C.blue, marginTop:2, flexShrink:0 }} size={13}/>
                                <span style={{ fontSize:11, color:C.textSec, lineHeight:1.6 }}>
                                    Applying changes will recalculate risk scores for all students. This affects dashboard metrics, risk classifications, and active intervention priorities.
                                </span>
                            </div>
                        </motion.div>
                    </Col>
                </Row>
            </motion.div>

            {/* ── Model Performance History ── */}
            <motion.div initial="hidden" animate="visible" variants={variants.container} className="mb-5">
                <motion.div variants={variants.item} className="glass-panel p-4" style={{ borderRadius:14 }}>
                    <div className="d-flex justify-content-between align-items-start mb-4 flex-wrap gap-3">
                        <div>
                            <h5 style={{ color:C.text, fontWeight:700, margin:0 }}>Model Performance History</h5>
                            <p style={{ color:C.textSec, fontSize:12, margin:'4px 0 0' }}>{mlSummary}</p>
                        </div>
                        <div className="d-flex gap-3">
                            {[['Accuracy',C.green,'87%'],['Recall',C.gold,'84%'],['Precision',C.blue,'89%']].map(([l,c,v]) => (
                                <div key={l} style={{ textAlign:'center' }}>
                                    <div style={{ fontSize:20, fontWeight:800, color:c }}>{v}</div>
                                    <div style={{ fontSize:10, color:C.textSec, textTransform:'uppercase' }}>{l}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                    <ResponsiveContainer width="100%" height={200}>
                        <LineChart data={ACCURACY_HISTORY}>
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(139,92,246,0.1)" />
                            <XAxis dataKey="month" tick={{ fill:C.textSec, fontSize:11 }} axisLine={false} tickLine={false} />
                            <YAxis domain={[65,95]} tick={{ fill:C.textSec, fontSize:11 }} axisLine={false} tickLine={false} unit="%" />
                            <Tooltip {...TT} formatter={v=>`${v}%`} />
                            <Legend wrapperStyle={{ color:C.textSec, fontSize:12 }} />
                            <Line type="monotone" dataKey="accuracy"  name="Accuracy"  stroke={C.green}  strokeWidth={2.5} dot={{ r:3, fill:C.green }} />
                            <Line type="monotone" dataKey="recall"    name="Recall"    stroke={C.gold}   strokeWidth={2.5} dot={{ r:3, fill:C.gold  }} />
                            <Line type="monotone" dataKey="precision" name="Precision" stroke={C.blue}   strokeWidth={2.5} dot={{ r:3, fill:C.blue  }} />
                            <ReferenceLine y={80} stroke="rgba(255,255,255,0.1)" strokeDasharray="4 4" label={{ value:'Target', fill:'rgba(255,255,255,0.3)', fontSize:10 }} />
                        </LineChart>
                    </ResponsiveContainer>
                </motion.div>
            </motion.div>

            {/* ── Factor Deep-Dive Cards ── */}
            <div className="mb-3">
                <h5 style={{ color:C.text, fontWeight:700, margin:0 }}>Signal Category Breakdown</h5>
                <p style={{ color:C.textSec, fontSize:13, margin:'4px 0 0' }}>Click any card to expand sub-metrics and impact data</p>
            </div>

            <motion.div initial="hidden" animate="visible" variants={variants.container}>
                <Row className="g-4">
                    {Object.entries(FACTOR_DETAILS).map(([key, factor]) => {
                        const meta     = FACTOR_META[key];
                        const weight   = weights[key];
                        const expanded = expandedFactor === key;
                        return (
                            <Col lg={6} key={key}>
                                <motion.div variants={variants.item}>
                                    <div
                                        onClick={() => setExpandedFactor(expanded ? null : key)}
                                        className="glass-panel"
                                        style={{
                                            borderRadius:14, cursor:'pointer',
                                            border:`1px solid ${meta.color}33`,
                                            borderLeft:`4px solid ${meta.color}`,
                                            transition:'box-shadow 0.2s',
                                        }}
                                        onMouseEnter={e => e.currentTarget.style.boxShadow=`0 0 20px ${meta.color}22`}
                                        onMouseLeave={e => e.currentTarget.style.boxShadow='none'}
                                    >
                                        {/* Card Header */}
                                        <div className="p-4">
                                            <div className="d-flex justify-content-between align-items-start mb-3">
                                                <div className="d-flex align-items-center gap-3">
                                                    <div style={{
                                                        width:40, height:40, borderRadius:10,
                                                        background: meta.faint, display:'flex',
                                                        alignItems:'center', justifyContent:'center',
                                                        fontSize:18, color: meta.color,
                                                    }}>{meta.icon}</div>
                                                    <div>
                                                        <div style={{ fontSize:15, fontWeight:700, color:C.text }}>{factor.title}</div>
                                                        <div style={{ fontSize:11, color:C.textSec, marginTop:2 }}>{factor.metrics.length} signals tracked</div>
                                                    </div>
                                                </div>
                                                <div style={{ textAlign:'right' }}>
                                                    <div style={{
                                                        background:meta.faint, border:`1px solid ${meta.color}44`,
                                                        color:meta.color, borderRadius:8, padding:'4px 12px',
                                                        fontSize:16, fontWeight:800,
                                                    }}>{weight}%</div>
                                                    <div style={{ fontSize:10, color:C.textSec, marginTop:3 }}>model weight</div>
                                                </div>
                                            </div>

                                            <p style={{ fontSize:12, color:C.textSec, lineHeight:1.6, margin:0 }}>{factor.description}</p>

                                            {/* Summary stats */}
                                            <div className="d-flex gap-4 mt-3 pt-3" style={{ borderTop:`1px solid ${C.border}` }}>
                                                <div>
                                                    <div style={{ fontSize:18, fontWeight:800, color: meta.color }}>{factor.studentsAffected}</div>
                                                    <div style={{ fontSize:10, color:C.textSec, textTransform:'uppercase' }}>Students flagged</div>
                                                </div>
                                                <div>
                                                    <div style={{ fontSize:18, fontWeight:800, color: factor.trend > 0 ? C.green : C.red }}>
                                                        {factor.trend > 0 ? '+' : ''}{factor.trend}%
                                                    </div>
                                                    <div style={{ fontSize:10, color:C.textSec, textTransform:'uppercase' }}>30-day trend</div>
                                                </div>
                                                <div style={{ marginLeft:'auto', alignSelf:'center' }}>
                                                    <div style={{
                                                        fontSize:11, color:C.textSec, fontWeight:600,
                                                        display:'flex', alignItems:'center', gap:4,
                                                    }}>
                                                        {expanded ? '▲ Collapse' : '▼ Expand'}
                                                    </div>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Expandable */}
                                        <AnimatePresence>
                                            {expanded && (
                                                <motion.div
                                                    initial={{ height:0, opacity:0 }}
                                                    animate={{ height:'auto', opacity:1 }}
                                                    exit={{ height:0, opacity:0 }}
                                                    transition={{ duration:0.25 }}
                                                    style={{ overflow:'hidden' }}
                                                >
                                                    <div style={{ padding:'0 16px 20px 16px', borderTop:`1px solid ${C.border}` }}>
                                                        {/* Metric chips */}
                                                        <div style={{ paddingTop:16, marginBottom:14 }}>
                                                            <div style={{ fontSize:11, color:C.textSec, textTransform:'uppercase', letterSpacing:'0.07em', marginBottom:8, fontWeight:600 }}>
                                                                Signal Sub-metrics
                                                            </div>
                                                            <div style={{ display:'flex', flexWrap:'wrap' }}>
                                                                {factor.metrics.map((m, i) => (
                                                                    <MetricChip key={i} {...m} />
                                                                ))}
                                                            </div>
                                                        </div>

                                                        {/* Scoring thresholds */}
                                                        <div style={{
                                                            background:'rgba(255,255,255,0.03)', borderRadius:10,
                                                            padding:'12px 14px', border:`1px solid ${C.border}`,
                                                        }}>
                                                            <div style={{ fontSize:11, color:C.textSec, textTransform:'uppercase', letterSpacing:'0.07em', marginBottom:10, fontWeight:600 }}>
                                                                Scoring Thresholds
                                                            </div>
                                                            {factor.thresholds.map((t, i) => <ThresholdBand key={i} {...t} />)}
                                                        </div>
                                                    </div>
                                                </motion.div>
                                            )}
                                        </AnimatePresence>
                                    </div>
                                </motion.div>
                            </Col>
                        );
                    })}
                </Row>
            </motion.div>

            {/* ── Confirmation Modal ── */}
            <Modal show={showModal} onHide={() => setShowModal(false)} centered>
                <Modal.Header closeButton style={{ background:C.surface, borderColor:C.border }}>
                    <Modal.Title style={{ color:C.text, fontSize:16, fontWeight:700, display:'flex', alignItems:'center', gap:8 }}>
                        <FaExclamationTriangle style={{ color:C.gold }} />
                        Confirm Risk Model Update
                    </Modal.Title>
                </Modal.Header>
                <Modal.Body style={{ background:C.surface, color:C.textSec, fontSize:13 }}>
                    <p style={{ color:C.text, marginBottom:12 }}>You are about to apply new factor weights. This will recalculate risk scores for <strong style={{ color:C.gold }}>all 2,847</strong> students.</p>
                    <div style={{ background:C.surfaceHi, borderRadius:10, padding:'12px 16px', marginBottom:14 }}>
                        {Object.entries(weights).map(([k,v]) => (
                            <div key={k} className="d-flex justify-content-between" style={{ fontSize:12, marginBottom:4 }}>
                                <span style={{ color:FACTOR_META[k].color }}>{FACTOR_DETAILS[k].title}</span>
                                <span style={{ color:C.text, fontWeight:700 }}>{v}%</span>
                            </div>
                        ))}
                    </div>
                    <p style={{ marginBottom:8 }}>Affected areas:</p>
                    <ul style={{ paddingLeft:20, margin:0 }}>
                        {['Dashboard risk metrics','Student risk classifications','Intervention priorities','Alert thresholds'].map(i => (
                            <li key={i} style={{ fontSize:12, marginBottom:3 }}>{i}</li>
                        ))}
                    </ul>
                </Modal.Body>
                <Modal.Footer style={{ background:C.surface, borderColor:C.border }}>
                    <button onClick={() => setShowModal(false)} style={{
                        padding:'8px 20px', borderRadius:8, border:`1px solid ${C.border}`,
                        background:'transparent', color:C.textSec, fontSize:13, fontWeight:600, cursor:'pointer',
                    }}>Cancel</button>
                    <button onClick={confirmApply} style={{
                        padding:'8px 20px', borderRadius:8, border:'none',
                        background:`linear-gradient(135deg,${C.purple},${C.purpleL})`,
                        color:'#fff', fontSize:13, fontWeight:700, cursor:'pointer',
                    }}>Yes, Update Risk Model</button>
                </Modal.Footer>
            </Modal>

        </motion.div>
    );
};

export default RiskFactors;
