import React, { useState, useMemo } from 'react';
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
import RiskChangeExplainer from '../components/dashboard/RiskChangeExplainer';
import FacultySummaryCard from '../components/dashboard/FacultySummaryCard';

function Dashboard() {
  const { students } = useStudentData();
  const navigate = useNavigate();
  const [riskFilter, setRiskFilter] = useState(null);
  const [riskFactorFilter, setRiskFactorFilter] = useState(null);
  const [timeRange, setTimeRange] = useState('semester');

  const warnings = useMemo(() => {
    const sortedStudents = [...students].sort((a, b) => b.risk_score - a.risk_score);
    const top2 = sortedStudents.slice(0, 2);
    return top2.map(student => ({
      id: student.id,
      message: generateShortRiskSummary(student),
      riskScore: student.risk_score
    }));
  }, [students]);

  const atRiskStudents = useMemo(() => students.filter(s => s.risk_score > 75).length, [students]);
  const averageRiskScore = useMemo(() => students.length > 0 ? parseFloat((students.reduce((acc, s) => acc + s.risk_score, 0) / students.length).toFixed(0)) : 0, [students]);

  const activeInterventions = useMemo(() => {
    const interventionCandidates = students.filter(s => s.risk_score >= 30);
    return Math.floor(interventionCandidates.length * 0.6);
  }, [students]);

  // Derived KPIs
  const highRiskStudentsCount = useMemo(() => students.filter(s => s.risk_score >= 75).length, [students]);
  const overallRiskPercent = useMemo(() => {
    if (students.length === 0) return 0;
    return parseFloat((students.reduce((acc, s) => acc + s.risk_score, 0) / students.length).toFixed(1));
  }, [students]);
  // Mock Intervention Success Rate for demo purposes
  const interventionSuccessRate = 72.4;
  // Mock internal engagement trend delta
  const weeklyEngagementTrend = "+3.2";
  // ML Model confidence
  const mlModelConfidence = 91.5;

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
          <KpiCard title="Intervention Success" value={interventionSuccessRate} isPercent={true} icon={<FaCheckCircle className="text-success-500" />} />
        </motion.div>
        <motion.div variants={variants.item}>
          <KpiCard
            title="Weekly Engagement"
            value={weeklyEngagementTrend}
            icon={<FaProjectDiagram className="text-primary-500" />}
            suffix="%"
          />
        </motion.div>
        <motion.div variants={variants.item}>
          <KpiCard title="ML Model Confidence" value={mlModelConfidence} isPercent={true} icon={<FaRobot className="text-slate-500" />} />
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8 space-y-8">
          <motion.div variants={variants.item}>
            <div className="flex justify-between items-center mb-8">
              <h3 className="text-xl font-display font-bold text-slate-900">Risk Analysis</h3>
              <span className="text-xs font-bold text-slate-400 bg-slate-100 px-3 py-1 rounded-full uppercase tracking-wider">Interactive</span>
            </div>
            <Charts
              students={filteredStudentsForChart}
              onRiskFilterChange={handleRiskFilterChange}
              riskFilter={riskFilter}
              onRiskFactorFilterChange={handleRiskFactorFilterChange}
              riskFactorFilter={riskFactorFilter}
            />
          </motion.div>

          <motion.div variants={variants.item}>
            <AiInsight
              title="Weekly Institutional Brief"
              content="Overall institutional risk has decreased by 2.5% this week. However, the 'Computer Science 101' cohort is showing early signs of disengagement (Attendance drop > 15%). Recommended action: Schedule a check-in with the faculty lead."
              confidence="high"
              sources={['Attendance Logs', 'LMS Gradebook']}
              type="summary"
            />
          </motion.div>
        </div>

        <div className="lg:col-span-4 space-y-8">
          <motion.div variants={variants.item}>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: 'rgba(239,68,68,0.15)', color: '#F87171' }}>
                <FaExclamationTriangle size={18} />
              </div>
              <h3 className="text-lg font-display font-bold" style={{ color: '#EDE9FE' }}>Critical Warnings</h3>
            </div>

            <div className="space-y-4">
              {warnings.map(warning => (
                <Link to={`/students/${warning.id}`} key={warning.id} style={{ textDecoration: 'none', display: 'block' }}>
                  <div
                    className="p-4 rounded-2xl transition-all duration-200 cursor-pointer"
                    style={{ backgroundColor: '#1A1035', border: '1px solid rgba(139,92,246,0.2)' }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(139,92,246,0.5)'; e.currentTarget.style.backgroundColor = '#211445'; }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(139,92,246,0.2)'; e.currentTarget.style.backgroundColor = '#1A1035'; }}
                  >
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-bold text-sm" style={{ color: '#EDE9FE' }}>Student #{warning.id}</span>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full uppercase" style={{ color: '#F87171', backgroundColor: 'rgba(239,68,68,0.15)' }}>Priority</span>
                    </div>
                    <p className="text-sm line-clamp-2 mb-2" style={{ color: '#A899CF' }}>{warning.message}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold" style={{ color: '#F87171' }}>Risk: {warning.riskScore}%</span>
                      <FaArrowRight size={12} style={{ color: '#6B5E8E' }} />
                    </div>
                  </div>
                </Link>
              ))}
              {warnings.length === 0 && <p className="text-sm italic" style={{ color: '#6B5E8E' }}>No active warnings.</p>}
            </div>
          </motion.div>

          <motion.div variants={variants.item}>
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ backgroundColor: 'rgba(245,158,11,0.15)', color: '#F59E0B' }}>
                <FaLightbulb size={18} />
              </div>
              <h3 className="text-lg font-display font-bold" style={{ color: '#EDE9FE' }}>Insights</h3>
            </div>
            <p className="text-sm mb-6 leading-relaxed" style={{ color: '#A899CF' }}>
              Based on recent activity, 12% of your medium-risk students have improved their engagement scores this week.
            </p>
            <button
              className="w-full py-3 rounded-xl font-bold text-sm transition-colors"
              style={{ backgroundColor: 'rgba(139,92,246,0.15)', color: '#C4B5FD', border: '1px solid rgba(139,92,246,0.25)' }}
              onMouseEnter={e => { e.currentTarget.style.backgroundColor = 'rgba(139,92,246,0.25)'; }}
              onMouseLeave={e => { e.currentTarget.style.backgroundColor = 'rgba(139,92,246,0.15)'; }}
            >
              Compare Cohorts
            </button>
          </motion.div>
        </div>
      </div>

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

      <motion.div variants={variants.item}>
        <FacultySummaryCard students={students} />
      </motion.div>
    </motion.div>
  );
}

export default Dashboard;
