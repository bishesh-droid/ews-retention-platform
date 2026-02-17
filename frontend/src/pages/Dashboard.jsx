import React, { useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FaUsers, FaUserShield, FaChartLine, FaExclamationTriangle, FaArrowRight, FaClipboardList, FaLightbulb } from 'react-icons/fa';
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

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <motion.div variants={variants.item} className="cursor-pointer" onClick={() => navigate('/students')}>
          <KpiCard title="Total Students" value={students.length} icon={<FaUsers />} />
        </motion.div>
        <motion.div variants={variants.item} className="cursor-pointer" onClick={() => navigate('/students')}>
          <KpiCard
            title="At-Risk Students"
            value={atRiskStudents}
            icon={<FaUserShield className="text-rose-500" />}
            suffix={atRiskStudents > 0 ? "Critical" : "Stable"}
          />
        </motion.div>
        <motion.div variants={variants.item} className="cursor-pointer" onClick={() => navigate('/insights')}>
          <KpiCard title="Avg Risk Score" value={averageRiskScore} icon={<FaChartLine className="text-amber-500" />} isPercent={true} />
        </motion.div>
        <motion.div variants={variants.item} className="cursor-pointer" onClick={() => navigate('/interventions')}>
          <KpiCard
            title="Active Interventions"
            value={activeInterventions}
            icon={<FaClipboardList className="text-primary-500" />}
            suffix="Ongoing"
          />
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8 space-y-8">
          <motion.div variants={variants.item} className="bg-white p-8 rounded-3xl border border-slate-100 shadow-soft">
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
          <motion.div variants={variants.item} className="bg-white p-6 rounded-3xl border border-slate-100 shadow-soft border-l-4 border-l-rose-500">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-500 flex items-center justify-center">
                <FaExclamationTriangle size={18} />
              </div>
              <h3 className="text-lg font-display font-bold text-slate-900">Critical Warnings</h3>
            </div>

            <div className="space-y-4">
              {warnings.map(warning => (
                <Link to={`/students/${warning.id}`} key={warning.id} className="block group">
                  <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100 group-hover:bg-white group-hover:border-primary-200 transition-all duration-200 group-hover:shadow-md">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-bold text-slate-900">Student #{warning.id}</span>
                      <span className="text-[10px] font-bold text-rose-500 bg-rose-50 px-2 py-0.5 rounded-full uppercase">Priority</span>
                    </div>
                    <p className="text-sm text-slate-500 line-clamp-2 mb-2">{warning.message}</p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-rose-600">Risk: {warning.riskScore}%</span>
                      <FaArrowRight size={12} className="text-slate-300 group-hover:text-primary-500 transition-colors" />
                    </div>
                  </div>
                </Link>
              ))}
              {warnings.length === 0 && <p className="text-slate-400 text-sm italic">No active warnings.</p>}
            </div>
          </motion.div>

          <motion.div variants={variants.item} className="bg-white p-6 rounded-3xl border border-slate-100 shadow-soft">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-500 flex items-center justify-center">
                <FaLightbulb size={18} />
              </div>
              <h3 className="text-lg font-display font-bold text-slate-900">Insights</h3>
            </div>
            <p className="text-sm text-slate-500 mb-6 leading-relaxed">
              Based on recent activity, 12% of your medium-risk students have improved their engagement scores this week.
            </p>
            <button className="w-full py-3 rounded-xl bg-slate-100 text-slate-900 font-bold text-sm hover:bg-slate-200 transition-colors">
              Compare Cohorts
            </button>
          </motion.div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-8">
          <motion.div variants={variants.item} className="bg-white p-8 rounded-3xl border border-slate-100 shadow-soft">
            <div className="flex justify-between items-center mb-8">
              <h3 className="text-xl font-display font-bold text-slate-900">Top Priority Cases</h3>
              <Link to="/students" className="text-sm font-bold text-primary-500 hover:text-primary-600 transition-colors flex items-center gap-1">
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
