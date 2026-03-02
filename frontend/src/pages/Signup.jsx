import React, { useState, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
    FaUser, FaEnvelope, FaLock, FaEye, FaEyeSlash,
    FaChevronDown, FaCheckCircle, FaArrowLeft,
} from 'react-icons/fa';
import { MeridianMark } from '../components/common/Logo';

/* ── Animated meridian-grid background ── */
const MeridianGrid = () => (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0, overflow: 'hidden' }}>
        {/* Ambient base glow */}
        <div style={{
            position: 'absolute', inset: 0,
            background: `
                radial-gradient(ellipse 60% 50% at 20% 20%, rgba(124,58,237,0.18) 0%, transparent 65%),
                radial-gradient(ellipse 50% 60% at 80% 80%, rgba(109,40,217,0.14) 0%, transparent 60%),
                radial-gradient(ellipse 40% 40% at 50% 50%, rgba(139,92,246,0.08) 0%, transparent 70%)
            `,
        }} />

        {/* Dot grid */}
        <div style={{
            position: 'absolute', inset: 0,
            backgroundImage: 'radial-gradient(circle, rgba(139,92,246,0.08) 1px, transparent 1px)',
            backgroundSize: '28px 28px',
        }} />

        {/* Vertical meridian lines */}
        {[15, 30, 50, 70, 85].map((pct, i) => (
            <motion.div
                key={`vline-${i}`}
                initial={{ opacity: 0, scaleY: 0 }}
                animate={{ opacity: [0.04, 0.1, 0.04], scaleY: 1 }}
                transition={{ duration: 4 + i * 1.2, repeat: Infinity, ease: 'easeInOut', delay: i * 0.6 }}
                style={{
                    position: 'absolute',
                    left: `${pct}%`,
                    top: 0, bottom: 0,
                    width: '1px',
                    background: 'linear-gradient(to bottom, transparent, rgba(139,92,246,0.6), transparent)',
                    transformOrigin: 'center',
                }}
            />
        ))}

        {/* Horizontal latitude lines */}
        {[20, 40, 60, 80].map((pct, i) => (
            <motion.div
                key={`hline-${i}`}
                initial={{ opacity: 0, scaleX: 0 }}
                animate={{ opacity: [0.03, 0.08, 0.03], scaleX: 1 }}
                transition={{ duration: 5 + i * 1.5, repeat: Infinity, ease: 'easeInOut', delay: i * 0.8 + 1 }}
                style={{
                    position: 'absolute',
                    top: `${pct}%`,
                    left: 0, right: 0,
                    height: '1px',
                    background: 'linear-gradient(to right, transparent, rgba(139,92,246,0.5), transparent)',
                    transformOrigin: 'center',
                }}
            />
        ))}

        {/* Floating particles */}
        {[
            { x: '12%', y: '18%', size: 3, color: '#8B5CF6', dur: 6 },
            { x: '85%', y: '12%', size: 4, color: '#F59E0B', dur: 8 },
            { x: '72%', y: '65%', size: 2.5, color: '#10B981', dur: 7 },
            { x: '8%',  y: '75%', size: 3, color: '#C4B5FD', dur: 9 },
            { x: '90%', y: '45%', size: 2, color: '#8B5CF6', dur: 5 },
            { x: '45%', y: '90%', size: 3.5, color: '#F59E0B', dur: 11 },
            { x: '28%', y: '55%', size: 2, color: '#10B981', dur: 7.5 },
            { x: '65%', y: '30%', size: 2.5, color: '#C4B5FD', dur: 6.5 },
        ].map((p, i) => (
            <motion.div
                key={`particle-${i}`}
                animate={{
                    y: [0, -18, 0],
                    opacity: [0.3, 0.8, 0.3],
                    scale: [1, 1.3, 1],
                }}
                transition={{ duration: p.dur, repeat: Infinity, ease: 'easeInOut', delay: i * 0.7 }}
                style={{
                    position: 'absolute',
                    left: p.x, top: p.y,
                    width: p.size, height: p.size,
                    borderRadius: '50%',
                    backgroundColor: p.color,
                    boxShadow: `0 0 ${p.size * 3}px ${p.color}`,
                }}
            />
        ))}

        {/* Zenith arc (decorative top-right) */}
        <motion.svg
            animate={{ opacity: [0.06, 0.14, 0.06], rotate: [0, 4, 0] }}
            transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
            style={{ position: 'absolute', top: -80, right: -80, width: 340, height: 340 }}
            viewBox="0 0 340 340"
        >
            <circle cx="170" cy="170" r="160" stroke="#7C3AED" strokeWidth="1" fill="none" />
            <circle cx="170" cy="170" r="120" stroke="#8B5CF6" strokeWidth="0.8" fill="none" />
            <line x1="170" y1="10" x2="170" y2="330" stroke="#8B5CF6" strokeWidth="0.8" />
            <line x1="10" y1="170" x2="330" y2="170" stroke="#8B5CF6" strokeWidth="0.6" />
        </motion.svg>
    </div>
);

/* ── Password strength util ── */
const getStrength = (pw) => {
    let score = 0;
    if (pw.length >= 8)  score++;
    if (pw.length >= 12) score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[0-9]/.test(pw)) score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;
    return score; // 0-5
};
const strengthLabel = ['', 'Weak', 'Fair', 'Good', 'Strong', 'Excellent'];
const strengthColor = ['', '#EF4444', '#F59E0B', '#EAB308', '#10B981', '#8B5CF6'];

/* ── Animated input field ── */
const Field = ({ label, icon: Icon, type = 'text', value, onChange, placeholder, delay = 0, required, children }) => (
    <motion.div
        initial={{ opacity: 0, x: -24 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.45, delay, ease: [0.22, 1, 0.36, 1] }}
    >
        <label style={{ color: '#A899CF', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: '6px' }}>
            {label}
        </label>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', backgroundColor: '#1A1035', border: '1px solid rgba(139,92,246,0.25)', borderRadius: '12px', padding: '10px 14px', transition: 'border-color 0.2s' }}
            onFocus={e => e.currentTarget.style.borderColor = 'rgba(139,92,246,0.6)'}
            onBlur={e => e.currentTarget.style.borderColor = 'rgba(139,92,246,0.25)'}
        >
            <Icon size={13} style={{ color: '#8B7DB8', flexShrink: 0 }} />
            {children || (
                <input
                    type={type}
                    value={value}
                    onChange={onChange}
                    placeholder={placeholder}
                    required={required}
                    style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: '#EDE9FE', fontSize: '14px' }}
                />
            )}
        </div>
    </motion.div>
);

/* ── Success overlay ── */
const SuccessScreen = ({ name, onBack }) => (
    <motion.div
        key="success"
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '2.5rem 2rem', gap: '1rem' }}
    >
        <motion.div
            initial={{ scale: 0, rotate: -90 }}
            animate={{ scale: 1, rotate: 0 }}
            transition={{ duration: 0.6, delay: 0.2, type: 'spring', stiffness: 200 }}
        >
            <div style={{ width: 72, height: 72, borderRadius: '50%', background: 'rgba(16,185,129,0.15)', border: '2px solid rgba(16,185,129,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <FaCheckCircle size={32} style={{ color: '#10B981' }} />
            </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} style={{ textAlign: 'center' }}>
            <h2 style={{ color: '#F0EEFF', fontSize: '20px', fontWeight: 700, margin: 0 }}>Request Submitted!</h2>
            <p style={{ color: '#8B7DB8', fontSize: '13px', marginTop: '8px', lineHeight: 1.6 }}>
                Thanks, <span style={{ color: '#A78BFA', fontWeight: 600 }}>{name}</span>. Your access request has been sent to the administrator. You'll receive credentials shortly.
            </p>
        </motion.div>

        <motion.button
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            onClick={onBack}
            style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'none', border: 'none', color: '#8B5CF6', fontSize: '13px', fontWeight: 600, cursor: 'pointer', marginTop: '0.5rem' }}
        >
            <FaArrowLeft size={11} /> Back to Sign In
        </motion.button>
    </motion.div>
);

/* ── Main Signup Page ── */
const Signup = () => {
    const navigate = useNavigate();
    const [form, setForm] = useState({ name: '', email: '', role: '', password: '', confirm: '' });
    const [showPassword, setShowPassword]   = useState(false);
    const [showConfirm,  setShowConfirm]    = useState(false);
    const [submitted,    setSubmitted]      = useState(false);
    const [error,        setError]          = useState('');

    const set = useCallback((field) => (e) => setForm(f => ({ ...f, [field]: e.target.value })), []);

    const pwStrength  = getStrength(form.password);
    const strengthPct = (pwStrength / 5) * 100;

    const handleSubmit = (e) => {
        e.preventDefault();
        setError('');
        if (!form.role) { setError('Please select your role.'); return; }
        if (form.password !== form.confirm) { setError('Passwords do not match.'); return; }
        if (pwStrength < 2) { setError('Password is too weak. Use at least 8 characters.'); return; }
        setSubmitted(true);
    };

    return (
        <div style={{ position: 'fixed', inset: 0, overflow: 'hidden', background: 'linear-gradient(135deg, #0F0920 0%, #0B0714 45%, #100820 100%)' }}>
            <MeridianGrid />

            {/* Centered card */}
            <div style={{
                position: 'absolute',
                top: '50%', left: '50%',
                transform: 'translate(-50%, -50%)',
                width: '400px',
                maxWidth: 'calc(100vw - 2rem)',
                zIndex: 1,
            }}>
                {/* Logo header */}
                <motion.div
                    initial={{ opacity: 0, y: -24 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '1.75rem' }}
                >
                    <motion.div
                        animate={{ rotate: [0, 4, -4, 0] }}
                        transition={{ duration: 6, repeat: Infinity, ease: 'easeInOut' }}
                    >
                        <MeridianMark size={62} />
                    </motion.div>
                    <h1 style={{ color: '#F0EEFF', fontSize: '22px', fontWeight: 700, letterSpacing: '-0.02em', marginTop: '14px', marginBottom: '2px' }}>
                        Meridian
                    </h1>
                    <span style={{ color: '#8B5CF6', fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.15em' }}>
                        Retention AI
                    </span>
                    <p style={{ color: '#8B7DB8', fontSize: '13px', marginTop: '6px' }}>
                        Request access to your institution's platform
                    </p>
                </motion.div>

                {/* Card */}
                <motion.div
                    initial={{ opacity: 0, y: 28 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.1 }}
                    style={{
                        backgroundColor: 'rgba(19,13,35,0.90)',
                        border: '1px solid rgba(139,92,246,0.25)',
                        borderRadius: '20px',
                        backdropFilter: 'blur(24px)',
                        boxShadow: '0 0 80px rgba(124,58,237,0.15), 0 28px 56px rgba(0,0,0,0.45)',
                        overflow: 'hidden',
                    }}
                >
                    <AnimatePresence mode="wait">
                        {submitted ? (
                            <SuccessScreen key="success" name={form.name.split(' ')[0]} onBack={() => navigate('/login')} />
                        ) : (
                            <motion.form
                                key="form"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                onSubmit={handleSubmit}
                                style={{ display: 'flex', flexDirection: 'column', gap: '14px', padding: '2rem' }}
                            >
                                {/* Full Name */}
                                <Field label="Full Name" icon={FaUser} value={form.name} onChange={set('name')} placeholder="Jane Smith" delay={0.15} required />

                                {/* Email */}
                                <Field label="Email Address" icon={FaEnvelope} type="email" value={form.email} onChange={set('email')} placeholder="jane@institution.edu" delay={0.22} required />

                                {/* Role */}
                                <motion.div
                                    initial={{ opacity: 0, x: -24 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ duration: 0.45, delay: 0.29, ease: [0.22, 1, 0.36, 1] }}
                                >
                                    <label style={{ color: '#A899CF', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: '6px' }}>
                                        Role
                                    </label>
                                    <div style={{ position: 'relative' }}>
                                        <select
                                            value={form.role}
                                            onChange={set('role')}
                                            style={{ width: '100%', appearance: 'none', backgroundColor: '#1A1035', border: '1px solid rgba(139,92,246,0.25)', borderRadius: '12px', padding: '10px 36px 10px 14px', color: form.role ? '#EDE9FE' : '#6B5E8E', fontSize: '14px', outline: 'none', cursor: 'pointer' }}
                                        >
                                            <option value="" disabled>Select your role…</option>
                                            <option value="admin">Administrator</option>
                                            <option value="faculty">Faculty</option>
                                            <option value="advisor">Academic Advisor</option>
                                            <option value="counselor">Counselor</option>
                                        </select>
                                        <FaChevronDown size={11} style={{ position: 'absolute', right: 13, top: '50%', transform: 'translateY(-50%)', color: '#8B7DB8', pointerEvents: 'none' }} />
                                    </div>
                                </motion.div>

                                {/* Password */}
                                <motion.div
                                    initial={{ opacity: 0, x: -24 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ duration: 0.45, delay: 0.36, ease: [0.22, 1, 0.36, 1] }}
                                >
                                    <label style={{ color: '#A899CF', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: '6px' }}>
                                        Password
                                    </label>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', backgroundColor: '#1A1035', border: '1px solid rgba(139,92,246,0.25)', borderRadius: '12px', padding: '10px 14px' }}>
                                        <FaLock size={13} style={{ color: '#8B7DB8', flexShrink: 0 }} />
                                        <input
                                            type={showPassword ? 'text' : 'password'}
                                            value={form.password}
                                            onChange={set('password')}
                                            placeholder="Create a strong password"
                                            required
                                            style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: '#EDE9FE', fontSize: '14px' }}
                                        />
                                        <button type="button" onClick={() => setShowPassword(v => !v)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8B7DB8', padding: 0, flexShrink: 0 }}>
                                            {showPassword ? <FaEyeSlash size={13} /> : <FaEye size={13} />}
                                        </button>
                                    </div>
                                    {/* Strength bar */}
                                    {form.password && (
                                        <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} style={{ marginTop: '8px' }}>
                                            <div style={{ height: '4px', backgroundColor: 'rgba(255,255,255,0.08)', borderRadius: '4px', overflow: 'hidden' }}>
                                                <motion.div
                                                    animate={{ width: `${strengthPct}%` }}
                                                    transition={{ duration: 0.3 }}
                                                    style={{ height: '100%', borderRadius: '4px', backgroundColor: strengthColor[pwStrength] }}
                                                />
                                            </div>
                                            <p style={{ fontSize: '10px', color: strengthColor[pwStrength], marginTop: '4px', fontWeight: 600 }}>
                                                {strengthLabel[pwStrength]}
                                            </p>
                                        </motion.div>
                                    )}
                                </motion.div>

                                {/* Confirm Password */}
                                <motion.div
                                    initial={{ opacity: 0, x: -24 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    transition={{ duration: 0.45, delay: 0.43, ease: [0.22, 1, 0.36, 1] }}
                                >
                                    <label style={{ color: '#A899CF', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: '6px' }}>
                                        Confirm Password
                                    </label>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', backgroundColor: '#1A1035', border: '1px solid rgba(139,92,246,0.25)', borderRadius: '12px', padding: '10px 14px' }}>
                                        <FaLock size={13} style={{ color: '#8B7DB8', flexShrink: 0 }} />
                                        <input
                                            type={showConfirm ? 'text' : 'password'}
                                            value={form.confirm}
                                            onChange={set('confirm')}
                                            placeholder="Repeat your password"
                                            required
                                            style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: form.confirm && form.confirm !== form.password ? '#F87171' : '#EDE9FE', fontSize: '14px' }}
                                        />
                                        <button type="button" onClick={() => setShowConfirm(v => !v)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8B7DB8', padding: 0, flexShrink: 0 }}>
                                            {showConfirm ? <FaEyeSlash size={13} /> : <FaEye size={13} />}
                                        </button>
                                    </div>
                                </motion.div>

                                {/* Error */}
                                <AnimatePresence>
                                    {error && (
                                        <motion.p
                                            initial={{ opacity: 0, height: 0 }}
                                            animate={{ opacity: 1, height: 'auto' }}
                                            exit={{ opacity: 0, height: 0 }}
                                            style={{ color: '#F87171', fontSize: '12px', backgroundColor: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: '8px', padding: '8px 12px', margin: 0 }}
                                        >
                                            {error}
                                        </motion.p>
                                    )}
                                </AnimatePresence>

                                {/* Submit */}
                                <motion.button
                                    initial={{ opacity: 0, y: 12 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.5 }}
                                    whileHover={{ scale: 1.02, boxShadow: '0 0 28px rgba(124,58,237,0.45)' }}
                                    whileTap={{ scale: 0.98 }}
                                    type="submit"
                                    style={{
                                        width: '100%',
                                        background: 'linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%)',
                                        color: '#fff',
                                        fontWeight: 700,
                                        fontSize: '14px',
                                        border: 'none',
                                        borderRadius: '12px',
                                        padding: '12px',
                                        cursor: 'pointer',
                                        marginTop: '4px',
                                        letterSpacing: '0.02em',
                                    }}
                                >
                                    Request Access
                                </motion.button>

                                {/* Link to login */}
                                <motion.p
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ delay: 0.6 }}
                                    style={{ textAlign: 'center', fontSize: '12px', color: '#6B5E8E', margin: 0 }}
                                >
                                    Already have access?{' '}
                                    <Link to="/login" style={{ color: '#A78BFA', fontWeight: 600, textDecoration: 'none' }}>
                                        Sign in
                                    </Link>
                                </motion.p>
                            </motion.form>
                        )}
                    </AnimatePresence>
                </motion.div>
            </div>
        </div>
    );
};

export default Signup;
