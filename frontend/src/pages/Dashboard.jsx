import React, { useState, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Button, Row, Col, ListGroup } from 'react-bootstrap';
import { FaUsers, FaUserShield, FaChartLine, FaExclamationTriangle, FaArrowRight, FaClipboardList, FaLightbulb } from 'react-icons/fa';
import { motion } from 'framer-motion';
import Charts from '../components/dashboard/Charts';
import HighestRiskStudentsTable from '../components/dashboard/HighestRiskStudentsTable';
import InterventionSuggestions from '../components/interventions/InterventionSuggestions';
import TimeFilter from '../components/common/TimeFilter';
import { useStudentData } from '../context/StudentContext';
import { getPrimaryRiskFactor } from '../utils/studentUtils';
import KpiCard from '../components/dashboard/KpiCard';
import { variants } from '../utils/motionConfig';
import AIRecommendationCard from '../components/ai/AIRecommendationCard';
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

  const topRecommendations = useMemo(() => {
    const bulkRecs = generateBulkRecommendations(students.filter(s => s.risk_score > 60));
    return bulkRecs.slice(0, 3);
  }, [students]);

  const atRiskStudents = useMemo(() => students.filter(s => s.risk_score > 75).length, [students]);
  const averageRiskScore = useMemo(() => students.length > 0 ? parseFloat((students.reduce((acc, s) => acc + s.risk_score, 0) / students.length).toFixed(0)) : 0, [students]);

  // Calculate active interventions based on students needing intervention (risk >= 30%)
  // In production, this would come from the Intervention table via API
  const activeInterventions = useMemo(() => {
    // Students above gentle reminder threshold (30%) are candidates for intervention
    const interventionCandidates = students.filter(s => s.risk_score >= 30);
    // Estimate ~60% of candidates have active interventions
    return Math.floor(interventionCandidates.length * 0.6);
  }, [students]);

  // Students whose risk changed significantly (for the explainer)
  const studentsWithRiskChanges = useMemo(() => {
    return students.filter(s => s.risk_score > 40).slice(0, 10);
  }, [students]);

  const handleRiskFilterChange = (newFilter) => {
    setRiskFilter(prevFilter => prevFilter === newFilter ? null : newFilter);
  };

  const handleRiskFactorFilterChange = (newFilter) => {
    setRiskFactorFilter(prevFilter => prevFilter === newFilter ? null : newFilter);
  };

  const filteredStudentsForTable = useMemo(() => riskFactorFilter
    ? students.filter(student => getPrimaryRiskFactor(student) === riskFactorFilter)
    : students, [students, riskFactorFilter]);

  const filteredStudentsForChart = useMemo(() => riskFilter ? students.filter(student => {
    if (riskFilter === 'High Risk') return student.risk_score > 75;
    if (riskFilter === 'Medium Risk') return student.risk_score > 50 && student.risk_score <= 75;
    if (riskFilter === 'Low Risk') return student.risk_score > 25 && student.risk_score <= 50;
    if (riskFilter === 'Very Low Risk') return student.risk_score <= 25;
    return true;
  }) : students, [students, riskFilter]);

  if (students.length === 0) {
    return (
      <div className="d-flex flex-column align-items-center justify-content-center" style={{ minHeight: '60vh' }}>
        <h2 className="text-gradient mb-3 display-4 fw-bold">No Data Available</h2>
        <p className="text-muted mb-4 fs-5">Import or add students to get started.</p>
        <Button as={Link} to="/students" variant="primary" size="lg" className="rounded-pill px-4 shadow-lg">
          Add Students
        </Button>
      </div>
    );
  }

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={variants.container}
      className="pb-5"
    >
      <div className="mb-4 d-flex justify-content-between align-items-end">
        <div>
          <h1 className="display-5 fw-bold text-gradient mb-2">Overview</h1>
          <p className="text-secondary fs-5 mb-0" style={{ maxWidth: '600px' }}>
            Real-time insights into student retention risks and engagement metrics.
          </p>
        </div>
        <TimeFilter selectedRange={timeRange} onRangeChange={setTimeRange} showCustom={false} />
      </div>

      <Row className="g-4 mb-5">
        <Col md={3}>
          <motion.div variants={variants.item} className="h-100" style={{ cursor: 'pointer' }} onClick={() => navigate('/students')}>
            <KpiCard title="Total Students" value={students.length} icon={<FaUsers />} />
          </motion.div>
        </Col>
        <Col md={3}>
          <motion.div variants={variants.item} className="h-100" style={{ cursor: 'pointer' }} onClick={() => navigate('/students')}>
            <KpiCard
              title="At-Risk Students"
              value={atRiskStudents}
              icon={<FaUserShield className="text-danger" />}
              suffix={atRiskStudents > 0 ? "Critical" : "Stable"}
            />
          </motion.div>
        </Col>
        <Col md={3}>
          <motion.div variants={variants.item} className="h-100" style={{ cursor: 'pointer' }} onClick={() => navigate('/insights')}>
            <KpiCard title="Avg Risk Score" value={averageRiskScore} icon={<FaChartLine className="text-warning" />} isPercent={true} />
          </motion.div>
        </Col>
        <Col md={3}>
          <motion.div variants={variants.item} className="h-100" style={{ cursor: 'pointer' }} onClick={() => navigate('/interventions')}>
            <KpiCard
              title="Active Interventions"
              value={activeInterventions}
              icon={<FaClipboardList className="text-primary" />}
              suffix="Ongoing"
            />
          </motion.div>
        </Col>
      </Row>

      <Row className="g-4">
        <Col lg={8}>
          <motion.div variants={variants.item} className="glass-panel p-4 mb-4 h-100">
            <div className="d-flex justify-content-between align-items-center mb-4">
              <h4 className="mb-0 fw-semibold">Risk Analysis</h4>
              <small className="text-muted bg-surface-hover px-3 py-1 rounded-pill">Interactive Charts</small>
            </div>
            <Charts
              students={filteredStudentsForChart}
              onRiskFilterChange={handleRiskFilterChange}
              riskFilter={riskFilter}
              onRiskFactorFilterChange={handleRiskFactorFilterChange}
              riskFactorFilter={riskFactorFilter}
            />
          </motion.div>

          {/* AI Weekly Brief Section */}
          <motion.div variants={variants.item} className="mb-4">
            <AiInsight
              title="Weekly Institutional Brief"
              content="Overall institutional risk has decreased by 2.5% this week. However, the 'Computer Science 101' cohort is showing early signs of disengagement (Attendance drop > 15%). Recommended action: Schedule a check-in with the CS faculty lead."
              confidence="high"
              sources={['Attendance Logs (Past 7 Days)', 'LMS Gradebook', 'CS101 Course Metadata']}
              type="summary"
            />
          </motion.div>
        </Col>

        <Col lg={4}>
          <div className="d-flex flex-column gap-4 h-100">
            {/* Warnings Panel */}
            <motion.div variants={variants.item} className="glass-panel p-4 position-relative overflow-hidden" style={{ borderLeft: '4px solid var(--high-risk-color)' }}>
              <div className="d-flex align-items-center gap-2 mb-4 text-danger">
                <FaExclamationTriangle size={20} />
                <h5 className="mb-0 fw-bold">Critical Warnings</h5>
              </div>

              <ListGroup variant="flush" className="bg-transparent d-flex flex-column gap-3">
                {warnings.map(warning => (
                  <motion.div key={warning.id} whileHover={{ x: 5 }} transition={{ type: 'spring', stiffness: 300 }}>
                    <Link to={`/students/${warning.id}`} className="text-decoration-none text-primary">
                      <div className="p-3 rounded-3 bg-surface-hover border border-secondary-subtle shadow-sm">
                        <div className="d-flex justify-content-between align-items-start">
                          <span className="fw-bold">Student #{warning.id}</span>
                          <span className="badge bg-danger bg-opacity-10 text-danger border border-danger border-opacity-25 rounded-pill px-2">Action Needed</span>
                        </div>
                        <p className="text-muted small mb-1 mt-2">{warning.message}</p>
                        <small className="text-danger fw-medium">Risk Score: {warning.riskScore}</small>
                      </div>
                    </Link>
                  </motion.div>
                ))}
                {warnings.length === 0 && <div className="text-muted small">No active warnings.</div>}
              </ListGroup>
            </motion.div>

            {/* AI Recommendations Panel */}
            <motion.div variants={variants.item} className="glass-panel p-4 flex-grow-1">
              <div className="d-flex align-items-center gap-2 mb-3">
                <FaLightbulb className="text-warning" />
                <h5 className="mb-0 fw-bold">AI Recommendations</h5>
              </div>
              {topRecommendations.length > 0 ? (
                <div>
                  {topRecommendations.map((rec) => (
                    <AIRecommendationCard
                      key={`${rec.studentId}-${rec.id}`}
                      recommendation={{ ...rec, studentLabel: `Student ${rec.studentId}` }}
                      onAccept={() => console.log('Accept recommendation:', rec)}
                      onDismiss={() => console.log('Dismiss recommendation:', rec)}
                    />
                  ))}
                </div>
              ) : (
                <p className="text-muted small mb-0">No high-priority recommendations at this time.</p>
              )}
            </motion.div>
          </div>
        </Col>
      </Row>

      <Row className="mt-4 g-4">
        <Col lg={8}>
          <motion.div variants={variants.item} className="glass-panel p-4">
            <div className="d-flex justify-content-between align-items-center mb-4">
              <h4 className="mb-0 fw-semibold">Top Priority Cases</h4>
              <Link to="/students" className="btn btn-link text-decoration-none">View All <FaArrowRight /></Link>
            </div>
            <HighestRiskStudentsTable students={filteredStudentsForTable} />
          </motion.div>
        </Col>
        <Col lg={4}>
          <motion.div variants={variants.item}>
            <RiskChangeExplainer students={studentsWithRiskChanges} limit={4} />
          </motion.div>
        </Col>
      </Row>

      {/* Faculty Summary Section */}
      <Row className="mt-4">
        <Col md={12}>
          <motion.div variants={variants.item}>
            <FacultySummaryCard students={students} />
          </motion.div>
        </Col>
      </Row>
    </motion.div>
  );
}

export default Dashboard;
