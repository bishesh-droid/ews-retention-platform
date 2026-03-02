import React from 'react';

/**
 * Lumivance Logo Mark
 * Concept: A glowing "eye of insight" above a horizon line with an amber early-warning beacon —
 * representing AI-powered vigilance over student retention.
 */
const LumivanceMark = ({ size = 40 }) => (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="lv-bg" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#7C3AED" />
                <stop offset="100%" stopColor="#5B21B6" />
            </linearGradient>
            <radialGradient id="lv-glow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#F59E0B" stopOpacity="0.35" />
                <stop offset="100%" stopColor="#F59E0B" stopOpacity="0" />
            </radialGradient>
            <filter id="lv-blur">
                <feGaussianBlur stdDeviation="1.5" />
            </filter>
        </defs>

        {/* Background rounded square */}
        <rect width="40" height="40" rx="10" fill="url(#lv-bg)" />

        {/* Outer arc — the "eye of insight" / radar sweep */}
        <path
            d="M9 26 Q20 7 31 26"
            stroke="rgba(255,255,255,0.25)"
            strokeWidth="1.5"
            fill="none"
            strokeLinecap="round"
        />
        {/* Inner arc */}
        <path
            d="M13 26 Q20 13 27 26"
            stroke="rgba(255,255,255,0.55)"
            strokeWidth="1.8"
            fill="none"
            strokeLinecap="round"
        />

        {/* Horizon baseline */}
        <line x1="8" y1="26" x2="32" y2="26" stroke="rgba(255,255,255,0.2)" strokeWidth="1.2" strokeLinecap="round" />

        {/* Amber beacon glow (blurred) */}
        <circle cx="20" cy="26" r="6" fill="url(#lv-glow)" filter="url(#lv-blur)" />

        {/* Amber beacon core */}
        <circle cx="20" cy="26" r="2.8" fill="#F59E0B" />
        {/* Beacon highlight */}
        <circle cx="19.2" cy="25.2" r="0.9" fill="rgba(255,255,255,0.7)" />

        {/* Upward tick mark — the "early warning" pulse */}
        <line x1="20" y1="26" x2="20" y2="19" stroke="rgba(255,255,255,0.5)" strokeWidth="1.2" strokeLinecap="round" />
        <line x1="17.5" y1="21" x2="20" y2="19" stroke="rgba(255,255,255,0.5)" strokeWidth="1.2" strokeLinecap="round" />
        <line x1="22.5" y1="21" x2="20" y2="19" stroke="rgba(255,255,255,0.5)" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
);

/**
 * Full horizontal logo: mark + wordmark
 */
const Logo = ({ size = 40, showText = true, textSize = 'xl' }) => (
    <div className="flex items-center gap-3">
        <LumivanceMark size={size} />
        {showText && (
            <div className="flex flex-col leading-none">
                <span
                    className={`font-bold tracking-tight text-${textSize}`}
                    style={{
                        color: '#F0EEFF',
                        letterSpacing: '-0.02em',
                        fontFamily: 'Inter, system-ui, sans-serif',
                    }}
                >
                    Lumivance
                </span>
                <span
                    className="text-[9px] font-semibold uppercase tracking-widest mt-0.5"
                    style={{ color: '#8B5CF6', letterSpacing: '0.15em' }}
                >
                    Retention AI
                </span>
            </div>
        )}
    </div>
);

export { LumivanceMark };
export default Logo;
