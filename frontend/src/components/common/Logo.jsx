import React from 'react';

/**
 * Meridian Logo Mark
 * Concept: A globe with a glowing vertical meridian line and an amber zenith point —
 * representing the highest point of student insight and the precise moment of early intervention.
 */
const MeridianMark = ({ size = 40 }) => (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
        <defs>
            <linearGradient id="md-bg" x1="0" y1="0" x2="40" y2="40" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#7C3AED" />
                <stop offset="100%" stopColor="#4C1D95" />
            </linearGradient>
            <radialGradient id="md-zenith-glow" cx="50%" cy="22%" r="35%">
                <stop offset="0%" stopColor="#F59E0B" stopOpacity="0.5" />
                <stop offset="100%" stopColor="#F59E0B" stopOpacity="0" />
            </radialGradient>
            <radialGradient id="md-core-glow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stopColor="#8B5CF6" stopOpacity="0.3" />
                <stop offset="100%" stopColor="#8B5CF6" stopOpacity="0" />
            </radialGradient>
            <filter id="md-blur-sm">
                <feGaussianBlur stdDeviation="1.2" />
            </filter>
            <filter id="md-blur-md">
                <feGaussianBlur stdDeviation="2" />
            </filter>
            <clipPath id="md-globe-clip">
                <circle cx="20" cy="22" r="11.5" />
            </clipPath>
        </defs>

        {/* Background rounded square */}
        <rect width="40" height="40" rx="10" fill="url(#md-bg)" />

        {/* Subtle core glow */}
        <circle cx="20" cy="22" r="14" fill="url(#md-core-glow)" filter="url(#md-blur-md)" />

        {/* Globe outline */}
        <circle cx="20" cy="22" r="11.5" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2" fill="none" />

        {/* Latitude arc — upper (clipped to globe) */}
        <path
            d="M10.5 17 Q20 13.5 29.5 17"
            stroke="rgba(255,255,255,0.14)"
            strokeWidth="0.9"
            fill="none"
            clipPath="url(#md-globe-clip)"
        />

        {/* Latitude arc — equator (clipped to globe) */}
        <path
            d="M8.5 22 Q20 18.5 31.5 22"
            stroke="rgba(255,255,255,0.14)"
            strokeWidth="0.9"
            fill="none"
            clipPath="url(#md-globe-clip)"
        />

        {/* Latitude arc — lower (clipped to globe) */}
        <path
            d="M10.5 27 Q20 30.5 29.5 27"
            stroke="rgba(255,255,255,0.10)"
            strokeWidth="0.9"
            fill="none"
            clipPath="url(#md-globe-clip)"
        />

        {/* Meridian line — vertical through globe (the main element) */}
        <line
            x1="20" y1="10.5"
            x2="20" y2="33.5"
            stroke="rgba(255,255,255,0.65)"
            strokeWidth="1.4"
            strokeLinecap="round"
        />

        {/* Zenith glow (blurred amber behind the top dot) */}
        <circle cx="20" cy="10.5" r="5" fill="url(#md-zenith-glow)" filter="url(#md-blur-sm)" />

        {/* Zenith dot — the peak / highest point */}
        <circle cx="20" cy="10.5" r="2.6" fill="#F59E0B" />
        {/* Zenith highlight */}
        <circle cx="19.2" cy="9.7" r="0.85" fill="rgba(255,255,255,0.75)" />

        {/* Subtle arc above globe — celestial meridian sweep */}
        <path
            d="M14 10.5 Q20 5.5 26 10.5"
            stroke="rgba(245,158,11,0.35)"
            strokeWidth="1"
            fill="none"
            strokeLinecap="round"
        />
    </svg>
);

/**
 * Full horizontal logo: mark + wordmark
 */
const Logo = ({ size = 40, showText = true, textSize = 'xl' }) => (
    <div className="flex items-center gap-3">
        <MeridianMark size={size} />
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
                    Meridian
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

export { MeridianMark };
export default Logo;
