import React, { useState, useMemo, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FaUsers, FaUserShield, FaChartLine, FaExclamationTriangle, FaArrowRight, FaClipboardList, FaLightbulb, FaRobot, FaCheckCircle, FaProjectDiagram } from 'react-icons/fa';
import { motion } from 'framer-motion';
import Charts from '../components/dashboard/Charts';
import HighestRiskStudentsTable from '../components/dashboard/HighestRiskStudentsTable';
import { useStudentData } from '../context/StudentContext';
import { getPrimaryRiskFactor } from '../utils/studentUtils';
import KpiCard from '../components/dashboard/KpiCard';
import { variants } from '../utils/motionConfig';
import AiInsight from '../components/ai/AiInsight';
import { generateBulkRecommendations } from '../utils/recommendationEngine';
import { generateShortRiskSummary } from '../utils/riskNarrativeGenerator';
import RiskChangeExplainer from '../components/ai/RiskChangeExplainer';
import FacultySummaryCard from '../components/dashboard/FacultySummaryCard';
import { getCohortSummary } from '../services/api';

function Dashboard() {
  const { students, loading, error } = useStudentData();
  const navigate = useNavigate();
  const [riskFilter, setRiskFilter] = useState(null);
  const [riskFactorFilter, setRiskFactorFilter] = useState(null);
  const [timeRange, setTimeRange] = useState('semester');
  const [cohortSummary, setCohortSummary] = useState(null);
  const [cohortLoading, setCohortLoading] = useState(false);
  const [cohortError, setCohortError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      setCohortLoading(true);
      setCohortError(null);
      const response = await getCohortSummary();
      if (!isMounted) return;
      if (response.success && response.data) {
        setCohortSummary(response.data);
      } else {
        setCohortError(response.message || 'Failed to load cohort summary');
      }
      setCohortLoading(false);
    };
    load();
    return () => {
      isMounted = false;
    };
  }, []);

  const warnings = useMemo(() => {
    const sortedStudents = [...students].sort((a, b) => b.risk_score - a.risk_score);
    return sortedStudents.slice(0, 6).map(student => ({
      id: student.id,
      message: generateShortRiskSummary(student),
      riskScore: student.risk_score
    }));
  }, [students]);

  const atRiskStudents = useMemo(() => students.filter(s => s.risk_score > 75).length, [students]);
  // Cohort-level KPIs from backend summary (with safe fallbacks)
  const overallRiskPercent = cohortSummary?.overallRiskPercent ?? 0;
  const highRiskStudentsCount = cohortSummary?.highRiskCount ?? 0;
  const interventionSuccessRate = cohortSummary?.interventionRate ?? 0;
  const weeklyEngagementTrend = cohortSummary?.engagementTrend ?? 0;
  const modelVersion = cohortSummary?.modelVersion || 'N/A';

  const studentsWithRiskChanges = useMemo(() => {
    return students.filter(s => s.risk_score > 40).slice(0, 10);
  }, [students]);

  const handleRiskFilterChange = (newFilter) => {
    setRiskFilter(prevFilter => prevFilter === newFilter ? null : newFilter);
  };

  const handleRiskFactorFilterChange = (newFilter) => {
    setRiskFactorFilter(prevFilter => prevFilter === newFilter ? null : newFilter);
  };

  const filteredStudentsForChart = useMemo(() => riskFilter ? students.filter(student => {
    if (riskFilter === 'High Risk') return student.risk_score > 75;
    if (riskFilter === 'Medium Risk') return student.risk_score > 50 && student.risk_score <= 75;
    if (riskFilter === 'Low Risk') return student.risk_score > 25 && student.risk_score <= 50;
    if (riskFilter === 'Very Low Risk') return student.risk_score <= 25;
    return true;
  }) : students, [students, riskFilter]);

  console.log('[Dashboard] render state:', {
    loading,
    error,
    studentsCount: students.length,
  });

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
        <h2 className="text-2xl font-display font-bold text-slate-900 mb-3 tracking-tight">Loading Overview...</h2>
        <p className="text-slate-500">Fetching student and cohort metrics.</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
        <h2 className="text-2xl font-display font-bold text-rose-500 mb-3 tracking-tight">Failed to Load Data</h2>
        <p className="text-slate-500 max-w-md">{error}</p>
      </div>
    );
  }

  if (students.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center">
        <h2 className="text-4xl font-display font-bold text-slate-900 mb-4 tracking-tight">No Data Available</h2>
        <p className="text-slate-500 mb-8 max-w-md">Import or add students to get started with the Early Warning System.</p>
        <Link to="/students" className="bg-primary-500 text-white px-8 py-3 rounded-xl font-semibold shadow-glow hover:bg-primary-600 transition-all">
          Add Students
        </Link>
      </div>
    );
  }

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={variants.container}
      className="space-y-8 pb-12"
    >
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h1 className="text-4xl font-display font-bold text-slate-900 tracking-tight">Overview</h1>
          <p className="text-slate-500 mt-2">
            Real-time insights into student retention risks and institutional health.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <motion.div variants={variants.item}>
          <KpiCard title="Overall Risk %" value={overallRiskPercent} isPercent={true} icon={<FaChartLine className="text-warning-500" />} />
        </motion.div>
        <motion.div variants={variants.item} className="cursor-pointer" onClick={() => navigate('/students')}>
          <KpiCard
            title="High Risk Students"
            value={highRiskStudentsCount}
            icon={<FaUserShield className="text-danger-500" />}
            suffix="Critical"
          />
        </motion.div>
        <motion.div variants={variants.item}>
          <KpiCard title="Intervention Rate" value={interventionSuccessRate} isPercent={true} icon={<FaCheckCircle className="text-success-500" />} />
        </motion.div>
        <motion.div variants={variants.item}>
          <KpiCard
            title="Engagement Trend vs Target"
            value={weeklyEngagementTrend}
            icon={<FaProjectDiagram className="text-primary-500" />}
            suffix="%"
          />
        </motion.div>
        <motion.div variants={variants.item}>
          <KpiCard
            title="Model Version"
            value={0}
            icon={<FaRobot className="text-slate-500" />}
          >
            <p className="text-xs font-medium mt-1" style={{ color: '#8B7DB8' }}>
              {cohortLoading ? 'Loading…' : modelVersion}
            </p>
          </KpiCard>
        </motion.div>
      </div>

      {cohortLoading && (
        <p className="text-xs text-slate-500">Loading cohort metrics…</p>
      )}
      {!cohortLoading && cohortError && (
        <p className="text-xs text-rose-400">Unable to load cohort metrics: {cohortError}</p>
      )}

      {/* ── Risk Analysis — full width ──────────────────────────── */}
      <motion.div variants={variants.item}>
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-xl font-display font-bold" style={{ color: '#EDE9FE' }}>Risk Analysis</h3>
          <span
            className="text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider"
            style={{ color: '#A78BFA', backgroundColor: 'rgba(139,92,246,0.15)', border: '1px solid rgba(139,92,246,0.25)' }}
          >
            Interactive
          </span>
        </div>
        <Charts
          students={filteredStudentsForChart}
          onRiskFilterChange={handleRiskFilterChange}
          riskFilter={riskFilter}
          onRiskFactorFilterChange={handleRiskFactorFilterChange}
          riskFactorFilter={riskFactorFilter}
        />
      </motion.div>

      {/* ── Weekly Institutional Brief — full width ──────────── */}
      <motion.div variants={variants.item}>
        <AiInsight
          title="Weekly Institutional Brief"
          content="Overall institutional risk has decreased by 2.5% this week. However, the 'Computer Science 101' cohort is showing early signs of disengagement (Attendance drop > 15%). Recommended action: Schedule a check-in with the faculty lead."
          confidence="high"
          sources={['Attendance Logs', 'LMS Gradebook']}
          type="summary"
        />
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8">
          <motion.div variants={variants.item}>
            <div className="flex justify-between items-center mb-8">
              <h3 className="text-xl font-display font-bold text-slate-900">Top Priority Cases</h3>
              <Link to="/students" className="text-sm font-bold transition-colors flex items-center gap-1" style={{ color: '#8B5CF6', textDecoration: 'none' }}>
                View All Students <FaArrowRight size={12} />
              </Link>
            </div>
            <HighestRiskStudentsTable students={students} />
          </motion.div>
        </div>
        <div className="lg:col-span-4">
          <motion.div variants={variants.item} className="h-full">
            <RiskChangeExplainer students={studentsWithRiskChanges} limit={3} />
          </motion.div>
        </div>
      </div>

      {/* ── Critical Warnings + Insights ────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">

        {/* Critical Warnings — 7 cols */}
        <div className="lg:col-span-7">
          <motion.div variants={variants.item}>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: 'rgba(239,68,68,0.15)', color: '#F87171' }}>
                <FaExclamationTriangle size={18} />
              </div>
              <div>
                <h3 className="text-lg font-display font-bold" style={{ color: '#EDE9FE' }}>Critical Warnings</h3>
                <p className="text-xs" style={{ color: '#8B7DB8' }}>Top students requiring immediate attention</p>
              </div>
              {warnings.length > 0 && (
                <span className="ml-auto text-xs font-bold px-2 py-0.5 rounded-full" style={{ backgroundColor: 'rgba(239,68,68,0.15)', color: '#F87171' }}>
                  {warnings.length} flagged
                </span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {warnings.map(warning => (
                <Link to={`/students/${warning.id}`} key={warning.id} style={{ textDecoration: 'none' }}>
                  <div
                    className="p-4 rounded-2xl transition-all duration-200 cursor-pointer h-full"
                    style={{ backgroundColor: '#1A1035', border: '1px solid rgba(239,68,68,0.15)' }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(239,68,68,0.4)'; e.currentTarget.style.backgroundColor = '#1E1035'; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(239,68,68,0.15)'; e.currentTarget.style.backgroundColor = '#1A1035'; }}
                  >
                    {/* Risk score badge + Priority label */}
                    <div className="flex justify-between items-center mb-2">
                      <div className="flex items-center gap-2">
                        <div
                          className="text-xs font-bold px-2 py-0.5 rounded-full"
                          style={{
                            backgroundColor: warning.riskScore >= 80 ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)',
                            color: warning.riskScore >= 80 ? '#F87171' : '#FBBF24',
                          }}
                        >
                          {warning.riskScore}%
                        </div>
                      </div>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase" style={{ color: '#F87171', backgroundColor: 'rgba(239,68,68,0.12)' }}>
                        Priority
                      </span>
                    </div>

                    <p className="text-sm font-bold mb-1" style={{ color: '#EDE9FE' }}>
                      Student #{warning.id}
                    </p>
                    <p className="text-xs line-clamp-2 mb-3" style={{ color: '#A899CF', lineHeight: '1.5' }}>
                      {warning.message}
                    </p>

                    {/* Progress bar for risk score */}
                    <div style={{ height: 4, background: 'rgba(139,92,246,0.12)', borderRadius: 99, overflow: 'hidden' }}>
                      <div style={{
                        width: `${warning.riskScore}%`, height: '100%', borderRadius: 99,
                        background: warning.riskScore >= 80 ? '#EF4444' : '#F59E0B',
                      }} />
                    </div>

                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs font-bold" style={{ color: '#F87171' }}>Risk: {warning.riskScore}%</span>
                      <FaArrowRight size={11} style={{ color: '#6B5E8E' }} />
                    </div>
                  </div>
                </Link>
              ))}
              {warnings.length === 0 && (
                <p className="text-sm italic col-span-2" style={{ color: '#6B5E8E' }}>No active warnings.</p>
              )}
            </div>
          </motion.div>
        </div>

        {/* Insights — 5 cols */}
        <div className="lg:col-span-5">
          <motion.div variants={variants.item} className="h-full">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: 'rgba(245,158,11,0.15)', color: '#F59E0B' }}>
                <FaLightbulb size={18} />
              </div>
              <div>
                <h3 className="text-lg font-display font-bold" style={{ color: '#EDE9FE' }}>Insights</h3>
                <p className="text-xs" style={{ color: '#8B7DB8' }}>AI-generated observations from this week</p>
              </div>
            </div>

            <div className="space-y-3 mb-6">
              {[
                { icon: '📈', text: '12% of medium-risk students improved their engagement scores this week.', color: '#10B981' },
                { icon: '⚠️', text: 'Computer Science 101 cohort shows early disengagement — attendance drop exceeds 15%.', color: '#F59E0B' },
                { icon: '✅', text: 'Tutoring interventions have the highest success rate at 75% across all cohorts.', color: '#A78BFA' },
                { icon: '🔻', text: `${atRiskStudents} students are in the critical risk band (>75%) and have not received any intervention yet.`, color: '#F87171' },
              ].map((insight, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 p-3 rounded-xl"
                  style={{ backgroundColor: '#1A1035', border: '1px solid rgba(139,92,246,0.15)' }}
                >
                  <span style={{ fontSize: '1.1rem', flexShrink: 0 }}>{insight.icon}</span>
                  <p className="text-sm leading-relaxed" style={{ color: '#C4B5FD', margin: 0 }}>
                    {insight.text}
                  </p>
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-2">
              <button
                className="w-full py-3 rounded-xl font-bold text-sm transition-all"
                style={{ backgroundColor: 'rgba(139,92,246,0.15)', color: '#C4B5FD', border: '1px solid rgba(139,92,246,0.25)' }}
                onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'rgba(139,92,246,0.28)'; }}
                onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'rgba(139,92,246,0.15)'; }}
              >
                Compare Cohorts
              </button>
              <Link to="/students" style={{ textDecoration: 'none' }}>
                <button
                  className="w-full py-3 rounded-xl font-bold text-sm transition-all"
                  style={{ backgroundColor: 'rgba(239,68,68,0.1)', color: '#F87171', border: '1px solid rgba(239,68,68,0.2)' }}
                  onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'rgba(239,68,68,0.2)'; }}
                  onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'rgba(239,68,68,0.1)'; }}
                >
                  View All At-Risk Students →
                </button>
              </Link>
            </div>
          </motion.div>
        </div>
      </div>

      <motion.div variants={variants.item}>
        <FacultySummaryCard students={students} />
      </motion.div>
    </motion.div>
  );
}

export default Dashboard;
