import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FaEye, FaEyeSlash, FaLock, FaUser } from 'react-icons/fa';
import { MeridianMark } from '../components/common/Logo';
import { useAuth } from '../context/AuthContext';

/* --------------------------------------------------
   Solar-system background — sits behind the form
   -------------------------------------------------- */
const SolarSystem = () => (
    <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        pointerEvents: 'none', zIndex: 0,
    }}>
        {/* Central glow */}
        <div style={{
            position: 'absolute',
            width: 220, height: 220,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(139,92,246,0.22) 0%, transparent 70%)',
            filter: 'blur(28px)',
        }} />

        {/* Pulse rings */}
        <motion.div
            animate={{ scale: [1, 1.07, 1], opacity: [0.18, 0.35, 0.18] }}
            transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
            style={{ position: 'absolute', width: 180, height: 180, borderRadius: '50%', border: '1px solid rgba(139,92,246,0.5)' }}
        />
        <motion.div
            animate={{ scale: [1, 1.12, 1], opacity: [0.1, 0.22, 0.1] }}
            transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut', delay: 0.8 }}
            style={{ position: 'absolute', width: 240, height: 240, borderRadius: '50%', border: '1px solid rgba(139,92,246,0.3)' }}
        />

        {/* Orbit 1 — 300px, 10s CW, violet dot */}
        <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 10, repeat: Infinity, ease: 'linear' }}
            style={{ position: 'absolute', width: 300, height: 300, borderRadius: '50%', border: '1px dashed rgba(139,92,246,0.28)' }}
        >
            <div style={{ position: 'absolute', top: -5, left: '50%', transform: 'translateX(-50%)', width: 9, height: 9, borderRadius: '50%', backgroundColor: '#8B5CF6', boxShadow: '0 0 10px #8B5CF6' }} />
        </motion.div>

        {/* Orbit 2 — 420px, 17s CCW, amber dot */}
        <motion.div
            animate={{ rotate: -360 }}
            transition={{ duration: 17, repeat: Infinity, ease: 'linear' }}
            style={{ position: 'absolute', width: 420, height: 420, borderRadius: '50%', border: '1px dashed rgba(245,158,11,0.22)' }}
        >
            <div style={{ position: 'absolute', bottom: -5, left: '50%', transform: 'translateX(-50%)', width: 8, height: 8, borderRadius: '50%', backgroundColor: '#F59E0B', boxShadow: '0 0 10px #F59E0B' }} />
        </motion.div>

        {/* Orbit 3 — 560px, 26s CW, green dot */}
        <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 26, repeat: Infinity, ease: 'linear' }}
            style={{ position: 'absolute', width: 560, height: 560, borderRadius: '50%', border: '1px solid rgba(16,185,129,0.14)' }}
        >
            <div style={{ position: 'absolute', top: -4, left: '50%', transform: 'translateX(-50%)', width: 7, height: 7, borderRadius: '50%', backgroundColor: '#10B981', boxShadow: '0 0 8px #10B981' }} />
        </motion.div>

        {/* Orbit 4 — 710px, 38s CCW, violet dot */}
        <motion.div
            animate={{ rotate: -360 }}
            transition={{ duration: 38, repeat: Infinity, ease: 'linear' }}
            style={{ position: 'absolute', width: 710, height: 710, borderRadius: '50%', border: '1px solid rgba(139,92,246,0.1)' }}
        >
            <div style={{ position: 'absolute', top: -4, left: '50%', transform: 'translateX(-50%)', width: 6, height: 6, borderRadius: '50%', backgroundColor: '#C4B5FD', boxShadow: '0 0 8px #C4B5FD' }} />
        </motion.div>

        {/* Orbit 5 — 880px, 52s CW, amber dot — outermost ring */}
        <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 52, repeat: Infinity, ease: 'linear' }}
            style={{ position: 'absolute', width: 880, height: 880, borderRadius: '50%', border: '1px solid rgba(245,158,11,0.08)' }}
        >
            <div style={{ position: 'absolute', top: -3, left: '50%', transform: 'translateX(-50%)', width: 5, height: 5, borderRadius: '50%', backgroundColor: '#F59E0B', boxShadow: '0 0 6px #F59E0B' }} />
        </motion.div>
    </div>
);

/* --------------------------------------------------
   Login Page
   -------------------------------------------------- */
const Login = () => {
    const [username, setUsername]         = useState('');
    const [password, setPassword]         = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError]               = useState('');
    const { login } = useAuth();
    const navigate  = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        const result = await login(username, password);
        if (result?.success) {
            navigate('/');
        } else {
            setError(result?.error || 'Invalid username or password.');
        }
    };

    return (
        <div style={{ position: 'fixed', inset: 0, overflow: 'hidden' }}>
            {/* Page background */}
            <div style={{
                position: 'absolute', inset: 0,
                background: `
                    radial-gradient(ellipse 70% 55% at 30% 25%, rgba(124,58,237,0.16) 0%, transparent 60%),
                    radial-gradient(ellipse 55% 45% at 70% 75%, rgba(109,40,217,0.12) 0%, transparent 55%),
                    linear-gradient(135deg, #0F0920 0%, #0B0714 45%, #100820 100%)
                `,
            }} />

            {/* Dot grid */}
            <div style={{
                position: 'absolute', inset: 0, pointerEvents: 'none',
                backgroundImage: 'radial-gradient(circle, rgba(139,92,246,0.09) 1px, transparent 1px)',
                backgroundSize: '32px 32px',
            }} />

            {/* Solar system behind everything */}
            <SolarSystem />

            {/* ── Login box — truly centred ── */}
            <div style={{
                position: 'absolute',
                top: '50%', left: '50%',
                transform: 'translate(-50%, -50%)',
                width: '360px',
                maxWidth: 'calc(100vw - 2rem)',
                zIndex: 1,
            }}>

                {/* Logo */}
                <motion.div
                    initial={{ opacity: 0, y: -20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '2rem' }}
                >
                    <MeridianMark size={60} />
                    <h1 style={{ color: '#F0EEFF', fontSize: '22px', fontWeight: 700, letterSpacing: '-0.02em', marginTop: '14px', marginBottom: '2px' }}>
                        Meridian
                    </h1>
                    <span style={{ color: '#8B5CF6', fontSize: '10px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.15em' }}>
                        Retention AI
                    </span>
                    <p style={{ color: '#8B7DB8', fontSize: '13px', marginTop: '6px' }}>
                        Sign in to your dashboard
                    </p>
                </motion.div>

                {/* Form card */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6, delay: 0.12 }}
                    style={{
                        backgroundColor: 'rgba(19,13,35,0.88)',
                        border: '1px solid rgba(139,92,246,0.25)',
                        borderRadius: '18px',
                        padding: '2rem',
                        backdropFilter: 'blur(20px)',
                        boxShadow: '0 0 60px rgba(124,58,237,0.14), 0 24px 48px rgba(0,0,0,0.4)',
                    }}
                >
                    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

                        {/* Username */}
                        <div>
                            <label style={{ color: '#A899CF', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: '6px' }}>
                                Username
                            </label>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', backgroundColor: '#1A1035', border: '1px solid rgba(139,92,246,0.25)', borderRadius: '12px', padding: '10px 14px' }}>
                                <FaUser size={13} style={{ color: '#8B7DB8', flexShrink: 0 }} />
                                <input
                                    type="text"
                                    value={username}
                                    onChange={e => setUsername(e.target.value)}
                                    placeholder="admin"
                                    required
                                    style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: '#EDE9FE', fontSize: '14px' }}
                                />
                            </div>
                        </div>

                        {/* Password */}
                        <div>
                            <label style={{ color: '#A899CF', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: '6px' }}>
                                Password
                            </label>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', backgroundColor: '#1A1035', border: '1px solid rgba(139,92,246,0.25)', borderRadius: '12px', padding: '10px 14px' }}>
                                <FaLock size={13} style={{ color: '#8B7DB8', flexShrink: 0 }} />
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    placeholder="••••••••"
                                    required
                                    style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none', color: '#EDE9FE', fontSize: '14px' }}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(v => !v)}
                                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#8B7DB8', padding: 0, flexShrink: 0 }}
                                >
                                    {showPassword ? <FaEyeSlash size={13} /> : <FaEye size={13} />}
                                </button>
                            </div>
                        </div>

                        {/* Error */}
                        {error && (
                            <p style={{ color: '#F87171', fontSize: '12px', backgroundColor: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)', borderRadius: '8px', padding: '8px 12px', margin: 0 }}>
                                {error}
                            </p>
                        )}

                        {/* Submit */}
                        <button
                            type="submit"
                            style={{
                                width: '100%',
                                backgroundColor: '#7C3AED',
                                color: '#fff',
                                fontWeight: 600,
                                fontSize: '14px',
                                border: 'none',
                                borderRadius: '12px',
                                padding: '11px',
                                cursor: 'pointer',
                                marginTop: '4px',
                                transition: 'background-color 0.15s',
                            }}
                            onMouseEnter={e => e.currentTarget.style.backgroundColor = '#6D28D9'}
                            onMouseLeave={e => e.currentTarget.style.backgroundColor = '#7C3AED'}
                        >
                            Sign In
                        </button>
                    </form>

                    <p style={{ textAlign: 'center', fontSize: '12px', color: '#6B5E8E', marginTop: '20px', marginBottom: 0 }}>
                        No account?{' '}
                        <Link to="/signup" style={{ color: '#A78BFA', fontWeight: 600, textDecoration: 'none' }}>
                            Request access
                        </Link>
                    </p>
                </motion.div>
            </div>
        </div>
    );
};

export default Login;
