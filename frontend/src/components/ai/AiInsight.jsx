import React, { useState } from 'react';
import { FaRobot, FaInfoCircle, FaChevronDown, FaChevronUp, FaUserShield } from 'react-icons/fa';
import { motion, AnimatePresence } from 'framer-motion';

const AiInsight = ({ title, content, confidence = 'medium', sources = [], type = 'explanation' }) => {
    const [showSources, setShowSources] = useState(false);

    const getConfidenceConfig = (level) => {
        switch (level?.toLowerCase()) {
            case 'high':
                return { color: 'text-emerald-500 bg-emerald-50 border-emerald-100', icon: 'High Confidence' };
            case 'medium':
                return { color: 'text-amber-500 bg-amber-50 border-amber-100', icon: 'Medium Confidence' };
            case 'low':
                return { color: 'text-rose-500 bg-rose-50 border-rose-100', icon: 'Low (Review Needed)' };
            default:
                return { color: 'text-slate-500 bg-slate-50 border-slate-100', icon: 'Unknown' };
        }
    };

    const confConfig = getConfidenceConfig(confidence);

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            className="group relative"
        >
            {/* AI Glow Effect */}
            <div className="absolute -inset-0.5 bg-gradient-to-r from-primary-500 to-blue-600 rounded-3xl blur opacity-10 group-hover:opacity-20 transition duration-1000"></div>

            <div className="relative bg-white p-8 rounded-3xl border border-primary-50 shadow-soft overflow-hidden">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                    <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-2xl bg-primary-500 text-white flex items-center justify-center shadow-glow animate-pulse-slow">
                            <FaRobot size={22} />
                        </div>
                        <div>
                            <h3 className="text-xl font-display font-bold text-slate-900 tracking-tight">{title}</h3>
                            <p className="text-[10px] font-bold text-primary-500 uppercase tracking-widest">EWS-AI Engine</p>
                        </div>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className={`px-3 py-1 rounded-full border text-[10px] font-bold flex items-center gap-1.5 ${confConfig.color}`}>
                            <FaUserShield size={10} />
                            {confConfig.icon}
                        </div>

                        <div className="relative group/tooltip">
                            <FaInfoCircle className="text-slate-300 hover:text-primary-500 cursor-help transition-colors" size={16} />
                            <div className="absolute bottom-full right-0 mb-2 w-64 p-3 bg-slate-900 text-white text-[10px] rounded-xl opacity-0 invisible group-hover/tooltip:opacity-100 group-hover/tooltip:visible transition-all shadow-xl z-20">
                                <p className="font-bold mb-1">Algorithmic Transparency</p>
                                This insight is generated using institutional data (LMS interaction, grades, attendance). Always verify AI-driven recommendations before intervention.
                            </div>
                        </div>
                    </div>
                </div>

                <div className="text-slate-600 leading-relaxed text-sm mb-8 border-l-2 border-primary-100 pl-6 py-1 italic">
                    "{content}"
                </div>

                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div className="flex -space-x-2">
                            {[1, 2, 3].map(i => (
                                <div key={i} className="w-6 h-6 rounded-full bg-slate-100 border-2 border-white flex items-center justify-center text-[8px] font-bold text-slate-400">D{i}</div>
                            ))}
                        </div>
                        <span className="text-[10px] font-medium text-slate-400">Institutional Data Sources</span>
                    </div>

                    {sources.length > 0 && (
                        <button
                            onClick={() => setShowSources(!showSources)}
                            className="text-xs font-bold text-slate-400 hover:text-primary-500 transition-colors flex items-center gap-2 px-3 py-1 rounded-lg hover:bg-slate-50"
                        >
                            {showSources ? 'Hide Trace' : 'View Data Trace'}
                            {showSources ? <FaChevronUp size={10} /> : <FaChevronDown size={10} />}
                        </button>
                    )}
                </div>

                <AnimatePresence>
                    {showSources && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            className="mt-6 overflow-hidden"
                        >
                            <div className="bg-slate-50 rounded-2xl p-6 border border-slate-100">
                                <h4 className="text-[10px] font-bold text-slate-900 uppercase tracking-widest mb-4">Underlying Data Points</h4>
                                <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                    {sources.map((source, idx) => (
                                        <li key={idx} className="flex items-center gap-3 text-xs text-slate-500">
                                            <div className="w-1.5 h-1.5 rounded-full bg-primary-400"></div>
                                            {source}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </motion.div>
    );
};

export default AiInsight;
