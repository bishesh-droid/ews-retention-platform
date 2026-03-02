import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Row, Col, Modal, Spinner } from 'react-bootstrap';
import {
    FaFilePdf, FaFileExcel, FaFilePowerpoint, FaDownload,
    FaCalendarAlt, FaClock, FaCheckCircle, FaExclamationCircle,
    FaSearch, FaFilter, FaEllipsisV, FaEnvelope, FaPause,
    FaPlay, FaTrash, FaEdit, FaPlus, FaRobot, FaChartLine,
    FaUsers, FaGraduationCap, FaBullhorn, FaShieldAlt,
    FaEye, FaStar, FaLock, FaTimes,
} from 'react-icons/fa';
import { motion, AnimatePresence } from 'framer-motion';
import { variants } from '../utils/motionConfig';
import {
    downloadGeneratedReportFile,
    generateReport,
    getGeneratedReports,
    getReportTemplates,
} from '../services/api';

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
};

const TYPE_COLORS = {
    Impact:   C.green, Monthly: C.purple, Risk: C.red,
    Semester: C.gold,  Dept:    C.blue,   default: C.textSec,
};

const AUDIENCE_COLORS = {
    Executive: C.gold, Faculty: C.purple, Admin: C.blue,
    Counselors: C.green, Marketing: C.red, Board: C.gold,
    Leadership: C.purple,
};

const FORMAT_ICON = { PDF: <FaFilePdf size={10}/>, Excel: <FaFileExcel size={10}/>, PowerPoint: <FaFilePowerpoint size={10}/>, PPTX: <FaFilePowerpoint size={10}/> };
const FORMAT_COLOR = { PDF: C.red, Excel: C.green, PowerPoint: C.blue, PPTX: C.blue };

/* ─── Helpers ────────────────────────────────────────────────── */
const Btn = ({ children, onClick, variant='primary', disabled=false, style={} }) => {
    const base = {
        padding:'8px 18px', borderRadius:10, fontSize:13, fontWeight:700,
        cursor: disabled ? 'not-allowed' : 'pointer', border:'none',
        display:'flex', alignItems:'center', gap:6, transition:'all 0.2s',
        opacity: disabled ? 0.5 : 1, ...style,
    };
    const styles = {
        primary: { background:`linear-gradient(135deg,${C.purple},${C.purpleL})`, color:'#fff' },
        ghost:   { background:'rgba(139,92,246,0.1)', border:`1px solid ${C.border}`, color:C.textSec },
        danger:  { background:C.redFaint, border:`1px solid ${C.red}33`, color:C.red },
        success: { background:C.greenFaint, border:`1px solid ${C.green}33`, color:C.green },
    };
    return <button onClick={onClick} disabled={disabled} style={{ ...base, ...styles[variant] }}>{children}</button>;
};

const SectionTitle = ({ children, sub, action }) => (
    <div className="d-flex justify-content-between align-items-end mb-4 flex-wrap gap-2">
        <div>
            <h5 style={{ color:C.text, fontWeight:700, margin:0 }}>{children}</h5>
            {sub && <p style={{ color:C.textSec, fontSize:13, margin:'3px 0 0' }}>{sub}</p>}
        </div>
        {action}
    </div>
);

const Chip = ({ label, color }) => (
    <span style={{
        background:`${color}18`, color, border:`1px solid ${color}30`,
        borderRadius:6, padding:'2px 8px', fontSize:10, fontWeight:700,
        display:'inline-flex', alignItems:'center', gap:3,
    }}>{label}</span>
);

/* ─── Report Template Card ───────────────────────────────────── */
const TemplateCard = ({ report, onGenerate }) => (
    <motion.div variants={variants.item}>
        <div
            className="glass-panel h-100"
            style={{
                borderRadius:14, border:`1px solid ${report.color}33`,
                borderTop:`3px solid ${report.color}`,
                display:'flex', flexDirection:'column',
            }}
            onMouseEnter={e => e.currentTarget.style.boxShadow=`0 0 22px ${report.color}18`}
            onMouseLeave={e => e.currentTarget.style.boxShadow='none'}
        >
            <div className="p-4" style={{ flex:1 }}>
                {/* Header */}
                <div className="d-flex justify-content-between align-items-start mb-3">
                    <div style={{
                        width:42, height:42, borderRadius:10, background:`${report.color}18`,
                        display:'flex', alignItems:'center', justifyContent:'center',
                        fontSize:18, color:report.color,
                    }}>{report.icon}</div>
                    <div className="d-flex gap-2 align-items-center">
                        {report.popular && (
                            <Chip label="Popular" color={C.gold} />
                        )}
                        {typeof report.downloads === 'number' && (
                            <span style={{ fontSize:11, color:C.textSec }}>
                                <FaDownload size={9} style={{ marginRight:3 }}/>{report.downloads}
                            </span>
                        )}
                    </div>
                </div>

                <div style={{ fontSize:15, fontWeight:700, color:C.text, marginBottom:6 }}>{report.name}</div>
                <p style={{ fontSize:12, color:C.textSec, lineHeight:1.6, marginBottom:12 }}>{report.description}</p>

                {/* Audience tags */}
                <div className="d-flex flex-wrap gap-1 mb-3">
                    {report.audience.map(a => <Chip key={a} label={a} color={AUDIENCE_COLORS[a] ?? C.textSec} />)}
                </div>

                {/* Sections preview */}
                <div style={{ background:'rgba(255,255,255,0.03)', borderRadius:8, padding:'10px 12px', marginBottom:12 }}>
                    <div style={{ fontSize:10, color:C.textSec, textTransform:'uppercase', letterSpacing:'0.07em', marginBottom:6, fontWeight:600 }}>Includes</div>
                    <div className="d-flex flex-wrap gap-1">
                        {report.sections.map(s => (
                            <span key={s} style={{ fontSize:10, color:C.textSec, background:'rgba(255,255,255,0.06)', borderRadius:4, padding:'2px 7px' }}>{s}</span>
                        ))}
                    </div>
                </div>

                {/* Meta row */}
                <div className="d-flex gap-3" style={{ fontSize:11, color:C.textSec }}>
                    <span><FaFilePdf size={9} style={{ marginRight:3 }}/>{report.pages}</span>
                    <span><FaClock size={9} style={{ marginRight:3 }}/>{report.estimatedTime}</span>
                    <div className="d-flex gap-1">
                        {report.formats.map(f => (
                            <span key={f} style={{ color:FORMAT_COLOR[f] }}>{FORMAT_ICON[f]} {f}</span>
                        ))}
                    </div>
                </div>
            </div>

            {/* Action */}
            <div className="p-4 pt-0">
                <button
                    onClick={() => onGenerate(report)}
                    style={{
                        width:'100%', padding:'9px 0', borderRadius:10, border:'none',
                        background:`linear-gradient(135deg,${report.color}dd,${report.color}99)`,
                        color:'#fff', fontSize:13, fontWeight:700, cursor:'pointer',
                        display:'flex', alignItems:'center', justifyContent:'center', gap:6,
                    }}
                >
                    <FaFilePdf size={12}/> Generate Report
                </button>
            </div>
        </div>
    </motion.div>
);

/* ─── Generation Wizard ──────────────────────────────────────── */
const STEPS = ['Configure','Generating','Complete'];

const Wizard = ({ show, report, onClose, onGenerated }) => {
    const [step, setStep]           = useState(0);
    const [generating, setGenerating] = useState(false);
    const [error, setError]           = useState(null);
    const [generated, setGenerated]   = useState(null);
    const [opts, setOpts] = useState({
        dateRange:'lastMonth', execSummary:true, charts:true, tables:true,
        names:false, aggregated:true, format:'PDF', logo:true, footer:true,
    });

    const toggle = k => setOpts(o => ({ ...o, [k]: !o[k] }));
    const setOpt = (k,v) => setOpts(o => ({ ...o, [k]:v }));

    const run = async () => {
        setStep(1); setGenerating(true); setError(null);
        try {
            const resp = await generateReport({
                template_id: report?.id,
                format: opts.format,
                options: opts,
            });
            if (!resp.success) {
                throw new Error(resp.message || 'Generation failed');
            }
            setGenerated(resp.data);
            setStep(2);
            if (onGenerated) onGenerated(resp.data);
        } catch {
            setError('Generation failed. Please try again.');
            setStep(0);
        } finally { setGenerating(false); }
    };

    const handleClose = () => { setStep(0); setGenerated(null); setError(null); onClose(); };

    const inputStyle = {
        background:'rgba(255,255,255,0.04)', border:`1px solid ${C.border}`,
        borderRadius:8, padding:'8px 12px', color:C.text, fontSize:13, width:'100%',
    };
    const checkStyle = { accentColor: C.purple };

    return (
        <Modal show={show} onHide={handleClose} size="lg" centered>
            <div style={{ background:C.surface, borderRadius:16, border:`1px solid ${C.border}`, overflow:'hidden' }}>
                {/* Header */}
                <div style={{ padding:'20px 24px', borderBottom:`1px solid ${C.border}`, display:'flex', justifyContent:'space-between', alignItems:'center' }}>
                    <div>
                        <div style={{ fontSize:16, fontWeight:700, color:C.text }}>Generate: {report?.name}</div>
                        <div style={{ fontSize:12, color:C.textSec, marginTop:2 }}>{report?.estimatedTime} estimated generation time</div>
                    </div>
                    <button onClick={handleClose} style={{ background:'none', border:'none', color:C.textSec, cursor:'pointer', fontSize:18 }}><FaTimes/></button>
                </div>

                {/* Step Progress */}
                <div style={{ padding:'16px 24px', borderBottom:`1px solid ${C.border}`, display:'flex', gap:8 }}>
                    {STEPS.map((s,i) => (
                        <div key={s} style={{ display:'flex', alignItems:'center', gap:6 }}>
                            <div style={{
                                width:24, height:24, borderRadius:'50%', fontSize:11, fontWeight:700,
                                display:'flex', alignItems:'center', justifyContent:'center',
                                background: i < step ? C.green : i === step ? C.purple : 'rgba(255,255,255,0.08)',
                                color: i <= step ? '#fff' : C.textSec,
                            }}>
                                {i < step ? <FaCheckCircle size={12}/> : i+1}
                            </div>
                            <span style={{ fontSize:12, color: i === step ? C.text : C.textSec, fontWeight: i===step?700:400 }}>{s}</span>
                            {i < STEPS.length-1 && <div style={{ width:32, height:1, background: i < step ? C.green : C.border, marginLeft:4 }}/>}
                        </div>
                    ))}
                </div>

                {/* Body */}
                <div style={{ padding:'24px', minHeight:340 }}>
                    <AnimatePresence mode="wait">
                        {step === 0 && (
                            <motion.div key="step0" initial={{opacity:0,y:8}} animate={{opacity:1,y:0}} exit={{opacity:0}}>
                                <Row className="g-4">
                                    <Col md={6}>
                                        <div style={{ fontSize:12, color:C.textSec, fontWeight:600, textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:10 }}>Date Range</div>
                                        <div className="d-flex gap-2 mb-3">
                                            {[['thisMonth','This Month'],['lastMonth','Last Month'],['custom','Custom']].map(([v,l]) => (
                                                <button key={v} onClick={() => setOpt('dateRange',v)} style={{
                                                    flex:1, padding:'7px 0', borderRadius:8, border:'none', fontSize:12, fontWeight:600, cursor:'pointer',
                                                    background: opts.dateRange===v ? C.purple : 'rgba(255,255,255,0.06)',
                                                    color: opts.dateRange===v ? '#fff' : C.textSec,
                                                }}>{l}</button>
                                            ))}
                                        </div>
                                        {opts.dateRange === 'custom' && (
                                            <div className="d-flex gap-2">
                                                <input type="date" style={inputStyle}/>
                                                <input type="date" style={inputStyle}/>
                                            </div>
                                        )}

                                        <div style={{ fontSize:12, color:C.textSec, fontWeight:600, textTransform:'uppercase', letterSpacing:'0.06em', margin:'16px 0 10px' }}>Output Format</div>
                                        <div className="d-flex gap-2">
                                            {report?.formats.map(f => (
                                                <button key={f} onClick={() => setOpt('format',f)} style={{
                                                    flex:1, padding:'7px 0', borderRadius:8, border:'none', fontSize:12, fontWeight:700, cursor:'pointer',
                                                    background: opts.format===f ? `${FORMAT_COLOR[f]}dd` : 'rgba(255,255,255,0.06)',
                                                    color: opts.format===f ? '#fff' : FORMAT_COLOR[f]??C.textSec,
                                                }}>{FORMAT_ICON[f]} {f}</button>
                                            ))}
                                        </div>
                                    </Col>
                                    <Col md={6}>
                                        <div style={{ fontSize:12, color:C.textSec, fontWeight:600, textTransform:'uppercase', letterSpacing:'0.06em', marginBottom:10 }}>Include Sections</div>
                                        {[
                                            ['execSummary','Executive Summary'],
                                            ['charts','Risk Score Charts'],
                                            ['tables','Student Progress Tables'],
                                            ['names','Student Names (requires auth)'],
                                            ['aggregated','Aggregated Metrics Only'],
                                        ].map(([k,l]) => (
                                            <label key={k} style={{ display:'flex', alignItems:'center', gap:8, marginBottom:10, cursor:'pointer', fontSize:13, color: k==='names' ? C.textSec : C.text }}>
                                                <input type="checkbox" checked={opts[k]} onChange={() => toggle(k)} style={checkStyle}/>
                                                {k === 'names' && <FaLock size={10} style={{ color:C.gold }}/>}
                                                {l}
                                            </label>
                                        ))}
                                        <div style={{ borderTop:`1px solid ${C.border}`, marginTop:8, paddingTop:12 }}>
                                            <div style={{ fontSize:12, color:C.textSec, fontWeight:600, marginBottom:8, textTransform:'uppercase', letterSpacing:'0.06em' }}>Branding</div>
                                            {[['logo','Include institution logo'],['footer','Add confidentiality footer']].map(([k,l]) => (
                                                <label key={k} style={{ display:'flex', alignItems:'center', gap:8, marginBottom:8, cursor:'pointer', fontSize:13, color:C.text }}>
                                                    <input type="checkbox" checked={opts[k]} onChange={() => toggle(k)} style={checkStyle}/>{l}
                                                </label>
                                            ))}
                                        </div>
                                    </Col>
                                </Row>
                                {error && <div style={{ background:C.redFaint, border:`1px solid ${C.red}44`, borderRadius:10, padding:'10px 14px', marginTop:16, fontSize:12, color:C.red }}>{error}</div>}
                            </motion.div>
                        )}

                        {step === 1 && (
                            <motion.div key="step1" initial={{opacity:0}} animate={{opacity:1}} exit={{opacity:0}} style={{ textAlign:'center', paddingTop:48 }}>
                                <div style={{ position:'relative', width:64, height:64, margin:'0 auto 20px' }}>
                                    <div style={{
                                        width:64, height:64, borderRadius:'50%',
                                        border:`3px solid ${C.purpleFaint}`,
                                        borderTop:`3px solid ${C.purple}`,
                                        animation:'spin 1s linear infinite',
                                    }}/>
                                    <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
                                    <div style={{ position:'absolute', top:'50%', left:'50%', transform:'translate(-50%,-50%)', color:C.purple }}>
                                        <FaRobot size={22}/>
                                    </div>
                                </div>
                                <div style={{ fontSize:16, fontWeight:700, color:C.text, marginBottom:8 }}>Generating Report…</div>
                                <div style={{ fontSize:13, color:C.textSec }}>Analyzing student data and generating executive narrative…</div>
                            </motion.div>
                        )}

                        {step === 2 && (
                            <motion.div key="step2" initial={{opacity:0,y:8}} animate={{opacity:1,y:0}}>
                                <div style={{ textAlign:'center', marginBottom:24 }}>
                                    <FaCheckCircle size={44} style={{ color:C.green, marginBottom:12 }}/>
                                    <div style={{ fontSize:16, fontWeight:700, color:C.green }}>Report Generated Successfully</div>
                                    <div style={{ fontSize:12, color:C.textSec, marginTop:4 }}>
                                        {generated?.file_name || `${report?.name || 'Report'}`} • {opts.format}
                                    </div>
                                </div>
                                <div style={{ display:'flex', gap:10 }}>
                                    <button style={{
                                        flex:1, padding:'10px 0', borderRadius:10, border:'none',
                                        background:`linear-gradient(135deg,${C.purple},${C.purpleL})`,
                                        color:'#fff', fontSize:13, fontWeight:700, cursor:'pointer',
                                        display:'flex', alignItems:'center', justifyContent:'center', gap:6,
                                    }}
                                        onClick={async () => {
                                            if (!generated?.id) return;
                                            const res = await downloadGeneratedReportFile(generated.id);
                                            if (!res.success || !res.blob) return;
                                            const url = window.URL.createObjectURL(res.blob);
                                            const a = document.createElement('a');
                                            a.href = url;
                                            a.download = res.filename || generated.file_name || 'report';
                                            document.body.appendChild(a);
                                            a.click();
                                            a.remove();
                                            window.URL.revokeObjectURL(url);
                                        }}
                                    ><FaDownload size={12}/> Download {opts.format}</button>
                                    <button style={{
                                        flex:1, padding:'10px 0', borderRadius:10,
                                        border:`1px solid ${C.border}`, background:'transparent',
                                        color:C.textSec, fontSize:13, fontWeight:600, cursor:'pointer',
                                        display:'flex', alignItems:'center', justifyContent:'center', gap:6,
                                    }}><FaEnvelope size={12}/> Email to Stakeholders</button>
                                </div>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* Footer */}
                {step === 0 && (
                    <div style={{ padding:'16px 24px', borderTop:`1px solid ${C.border}`, display:'flex', justifyContent:'flex-end' }}>
                        <button onClick={run} style={{
                            padding:'10px 28px', borderRadius:10, border:'none',
                            background:`linear-gradient(135deg,${C.purple},${C.purpleL})`,
                            color:'#fff', fontSize:13, fontWeight:700, cursor:'pointer',
                        }}>Generate Report →</button>
                    </div>
                )}
                {step === 2 && (
                    <div style={{ padding:'16px 24px', borderTop:`1px solid ${C.border}`, display:'flex', justifyContent:'flex-end' }}>
                        <button onClick={handleClose} style={{
                            padding:'10px 24px', borderRadius:10, border:`1px solid ${C.border}`,
                            background:'transparent', color:C.textSec, fontSize:13, fontWeight:600, cursor:'pointer',
                        }}>Close</button>
                    </div>
                )}
            </div>
        </Modal>
    );
};

/* ─── Main Page ──────────────────────────────────────────────── */
const Reports = () => {
    const [showWizard, setShowWizard]     = useState(false);
    const [selectedReport, setSelectedReport] = useState(null);
    const [archiveSearch, setArchiveSearch]   = useState('');
    const [templates, setTemplates] = useState([]);
    const [generatedReports, setGeneratedReports] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const openWizard = (report) => { setSelectedReport(report); setShowWizard(true); };
    const iconForName = (name) => {
        const n = (name || '').toLowerCase();
        if (n.includes('monthly')) return <FaChartLine/>;
        if (n.includes('high-risk') || n.includes('high risk')) return <FaExclamationCircle/>;
        if (n.includes('intervention')) return <FaShieldAlt/>;
        if (n.includes('department')) return <FaGraduationCap/>;
        return <FaFilePdf/>;
    };
    const colorForName = (name) => {
        const n = (name || '').toLowerCase();
        if (n.includes('monthly')) return C.purple;
        if (n.includes('high-risk') || n.includes('high risk')) return C.red;
        if (n.includes('intervention')) return C.green;
        if (n.includes('department')) return C.blue;
        return C.purpleL;
    };

    useEffect(() => {
        let isMounted = true;
        const load = async () => {
            setLoading(true);
            setError(null);
            const [tResp, gResp] = await Promise.all([
                getReportTemplates(),
                getGeneratedReports(200),
            ]);
            if (!isMounted) return;

            if (!tResp.success) {
                setError(tResp.message || 'Failed to load report templates.');
                setTemplates([]);
                setGeneratedReports([]);
                setLoading(false);
                return;
            }

            setTemplates(Array.isArray(tResp.data) ? tResp.data : []);
            setGeneratedReports(gResp.success && Array.isArray(gResp.data) ? gResp.data : []);
            setLoading(false);
        };
        load();
        return () => { isMounted = false; };
    }, []);

    const templatesUi = useMemo(() => {
        return (templates || []).map((t) => ({
            id: t.id,
            name: t.name,
            description: t.description,
            pages: t.pages || '—',
            formats: Array.isArray(t.formats) ? t.formats : ['PDF'],
            audience: Array.isArray(t.audience) ? t.audience : [],
            icon: iconForName(t.name),
            color: colorForName(t.name),
            popular: !!t.popular,
            downloads: typeof t.downloads === 'number' ? t.downloads : undefined,
            estimatedTime: t.estimated_time || t.estimatedTime || '—',
            sections: Array.isArray(t.sections) ? t.sections : [],
        }));
    }, [templates]);

    const archiveRows = useMemo(() => {
        const q = (archiveSearch || '').toLowerCase().trim();
        const rows = (generatedReports || []).map((r) => {
            const name = r.file_name || r.template_name || `Report ${r.id}`;
            const format = r.format || 'PDF';
            return {
                id: r.id,
                name,
                type: r.template_name || 'Report',
                generated: r.generated_at ? new Date(r.generated_at).toLocaleDateString() : '—',
                sizeBytes: r.size_bytes,
                format,
                status: r.status || 'ready',
            };
        });
        const filtered = q ? rows.filter((r) => (r.name || '').toLowerCase().includes(q) || (r.type || '').toLowerCase().includes(q)) : rows;
        return filtered;
    }, [generatedReports, archiveSearch]);

    const kpis = useMemo(() => {
        const now = new Date();
        const thisMonth = now.getMonth();
        const thisYear = now.getFullYear();
        const generatedThisMonth = (generatedReports || []).filter((r) => {
            if (!r.generated_at) return false;
            const d = new Date(r.generated_at);
            return d.getMonth() === thisMonth && d.getFullYear() === thisYear;
        }).length;
        return {
            generatedThisMonth,
            totalGenerated: (generatedReports || []).length,
            templates: (templates || []).length,
        };
    }, [generatedReports, templates]);

    const onGenerated = async () => {
        const gResp = await getGeneratedReports(200);
        if (gResp.success && Array.isArray(gResp.data)) {
            setGeneratedReports(gResp.data);
        }
    };

    return (
        <motion.div initial={{ opacity:0 }} animate={{ opacity:1 }} transition={{ duration:0.3 }} className="pb-5">

            {/* ── Header ── */}
            <div className="d-flex justify-content-between align-items-end mb-5 flex-wrap gap-3">
                <div>
                    <h1 className="display-5 fw-bold text-gradient mb-2">Reports & Exports</h1>
                    <p className="text-secondary fs-6" style={{ maxWidth:620 }}>
                        Generate, schedule, and manage standardised reports for faculty, leadership, counselors, and marketing teams.
                    </p>
                </div>
                <button onClick={() => {}} style={{
                    background:'rgba(139,92,246,0.1)', border:`1px solid ${C.border}`,
                    borderRadius:10, color:C.textSec, padding:'8px 18px', fontSize:13,
                    fontWeight:600, cursor:'pointer', display:'flex', alignItems:'center', gap:7,
                }}>
                    <FaCalendarAlt size={11}/> Schedule New Report
                </button>
            </div>

            {error && (
                <Alert variant="danger" className="mb-4">
                    {error}
                </Alert>
            )}

            {/* ── KPI Strip ── */}
            <motion.div initial="hidden" animate="visible" variants={variants.container} className="mb-5">
                <Row className="g-3">
                    {[
                        { icon:<FaFilePdf/>,       label:'Reports This Month',  value: String(kpis.generatedThisMonth),    sub:'Generated reports',     color:C.purple },
                        { icon:<FaDownload/>,       label:'Total Generated',     value: String(kpis.totalGenerated),        sub:'In archive',           color:C.blue   },
                        { icon:<FaCalendarAlt/>,    label:'Templates',           value: String(kpis.templates),             sub:'Available to generate',color:C.green  },
                        { icon:<FaRobot/>,          label:'AI Narratives Gen.',  value:'—',                                   sub:'Not available yet',    color:C.gold   },
                    ].map((k,i) => (
                        <Col md={3} key={i}>
                            <motion.div variants={variants.item}>
                                <div className="glass-panel p-4" style={{ borderRadius:14, border:`1px solid ${k.color}33` }}>
                                    <div className="d-flex justify-content-between mb-2">
                                        <div style={{ fontSize:20, color:k.color }}>{k.icon}</div>
                                        <div style={{ fontSize:10, color:C.textSec, textTransform:'uppercase', letterSpacing:'0.07em', textAlign:'right' }}>{k.label}</div>
                                    </div>
                                    <div style={{ fontSize:28, fontWeight:800, color:C.text, lineHeight:1 }}>{k.value}</div>
                                    <div style={{ fontSize:11, color:C.textSec, marginTop:5 }}>{k.sub}</div>
                                </div>
                            </motion.div>
                        </Col>
                    ))}
                </Row>
            </motion.div>

            {/* ── Templates ── */}
            <motion.div initial="hidden" animate="visible" variants={variants.container} className="mb-5">
                <SectionTitle sub="Click any template to configure and generate" action={
                    <div className="d-flex gap-2">
                        <Chip label={`${kpis.templates} Templates`} color={C.purple}/>
                        <Chip label="AI-Powered Narratives" color={C.gold}/>
                    </div>
                }>Pre-built Report Templates</SectionTitle>
                {loading ? (
                    <div className="text-muted d-flex align-items-center gap-2">
                        <Spinner animation="border" size="sm" />
                        <span>Loading templates…</span>
                    </div>
                ) : templatesUi.length === 0 ? (
                    <div className="text-muted">No templates available.</div>
                ) : (
                    <Row className="g-4">
                        {templatesUi.map(r => (
                            <Col lg={4} md={6} key={r.id}>
                                <TemplateCard report={r} onGenerate={openWizard} />
                            </Col>
                        ))}
                    </Row>
                )}
            </motion.div>

            {/* ── Report Archive ── */}
            <motion.div initial="hidden" animate="visible" variants={variants.container}>
                <SectionTitle
                    sub={`${generatedReports.length} reports in archive`}
                    action={
                        <div style={{ position:'relative' }}>
                            <FaSearch style={{ position:'absolute', left:10, top:'50%', transform:'translateY(-50%)', color:C.textSec, fontSize:12 }}/>
                            <input
                                value={archiveSearch}
                                onChange={e => setArchiveSearch(e.target.value)}
                                placeholder="Search archive…"
                                style={{
                                    background:'rgba(255,255,255,0.05)', border:`1px solid ${C.border}`,
                                    borderRadius:10, padding:'7px 12px 7px 30px', color:C.text, fontSize:13,
                                    width:220, outline:'none',
                                }}
                            />
                        </div>
                    }
                >Report Archive</SectionTitle>

                <motion.div variants={variants.item} className="glass-panel p-0" style={{ borderRadius:14, overflow:'hidden' }}>
                    <table style={{ width:'100%', borderCollapse:'collapse' }}>
                        <thead>
                            <tr style={{ background:'rgba(124,58,237,0.1)', borderBottom:`1px solid ${C.border}` }}>
                                {['Report Name','Type','Generated','Pages','Size','Format','Actions'].map(h => (
                                    <th key={h} style={{ padding:'12px 16px', fontSize:11, fontWeight:700, color:C.textSec, textTransform:'uppercase', letterSpacing:'0.07em', textAlign:'left' }}>{h}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {archiveRows.map((r,i) => {
                                const typeColor = TYPE_COLORS.default;
                                return (
                                    <tr key={r.id}
                                        style={{ borderBottom:`1px solid ${C.border}`, background: i%2===0?'transparent':'rgba(139,92,246,0.02)', transition:'background 0.2s' }}
                                        onMouseEnter={e => e.currentTarget.style.background='rgba(124,58,237,0.06)'}
                                        onMouseLeave={e => e.currentTarget.style.background= i%2===0?'transparent':'rgba(139,92,246,0.02)'}
                                    >
                                        <td style={{ padding:'13px 16px' }}>
                                            <div style={{ display:'flex', alignItems:'center', gap:10 }}>
                                                <div style={{
                                                    width:34, height:34, borderRadius:8, flexShrink:0,
                                                    background:`${FORMAT_COLOR[r.format]??C.textSec}18`,
                                                    display:'flex', alignItems:'center', justifyContent:'center',
                                                    fontSize:14, color:FORMAT_COLOR[r.format]??C.textSec,
                                                }}>{FORMAT_ICON[r.format]}</div>
                                                <span style={{ fontSize:13, fontWeight:600, color:C.text }}>{r.name}</span>
                                            </div>
                                        </td>
                                        <td style={{ padding:'13px 16px' }}>
                                            <span style={{
                                                background:`${typeColor}18`, color:typeColor,
                                                border:`1px solid ${typeColor}33`, borderRadius:6,
                                                padding:'2px 10px', fontSize:11, fontWeight:700,
                                            }}>{r.type}</span>
                                        </td>
                                        <td style={{ padding:'13px 16px', fontSize:12, color:C.textSec }}>{r.generated}</td>
                                        <td style={{ padding:'13px 16px', fontSize:12, color:C.textSec }}>{'—'}</td>
                                        <td style={{ padding:'13px 16px', fontSize:12, color:C.textSec, fontFamily:'monospace' }}>
                                            {typeof r.sizeBytes === 'number'
                                                ? (r.sizeBytes >= 1024 * 1024
                                                    ? `${(r.sizeBytes / (1024 * 1024)).toFixed(1)} MB`
                                                    : `${Math.round(r.sizeBytes / 1024)} KB`)
                                                : '—'}
                                        </td>
                                        <td style={{ padding:'13px 16px' }}>
                                            <span style={{ color:FORMAT_COLOR[r.format]??C.textSec, fontSize:12, fontWeight:700, display:'flex', alignItems:'center', gap:4 }}>
                                                {FORMAT_ICON[r.format]}{r.format}
                                            </span>
                                        </td>
                                        <td style={{ padding:'13px 16px' }}>
                                            <div className="d-flex gap-1">
                                                <button title="Download" style={{
                                                    background:C.purpleFaint, border:`1px solid ${C.border}`, borderRadius:7,
                                                    padding:'5px 10px', cursor:'pointer', color:C.purpleL, fontSize:11, fontWeight:700,
                                                    display:'flex', alignItems:'center', gap:4,
                                                }}
                                                    onClick={async () => {
                                                        const res = await downloadGeneratedReportFile(r.id);
                                                        if (!res.success || !res.blob) return;
                                                        const url = window.URL.createObjectURL(res.blob);
                                                        const a = document.createElement('a');
                                                        a.href = url;
                                                        a.download = res.filename || 'report';
                                                        document.body.appendChild(a);
                                                        a.click();
                                                        a.remove();
                                                        window.URL.revokeObjectURL(url);
                                                    }}
                                                ><FaDownload/> Download</button>
                                                <button title="Preview" style={{
                                                    background:'rgba(255,255,255,0.05)', border:'none', borderRadius:7,
                                                    padding:'5px 8px', cursor:'pointer', color:C.textSec, fontSize:11,
                                                }}><FaEye/></button>
                                                <button title="Delete" style={{
                                                    background:C.redFaint, border:'none', borderRadius:7,
                                                    padding:'5px 8px', cursor:'pointer', color:C.red, fontSize:11,
                                                }}><FaTrash/></button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                            {archiveRows.length === 0 && (
                                <tr><td colSpan={7} style={{ padding:'32px', textAlign:'center', color:C.textSec, fontSize:13 }}>No reports match your search.</td></tr>
                            )}
                        </tbody>
                    </table>
                </motion.div>
            </motion.div>

            {/* ── Wizard ── */}
            <Wizard show={showWizard} report={selectedReport} onClose={() => setShowWizard(false)} onGenerated={onGenerated} />

        </motion.div>
    );
};

export default Reports;
