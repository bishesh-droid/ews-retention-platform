import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Row, Col, Button, Spinner as BootstrapSpinner, Form, Badge } from 'react-bootstrap';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { motion } from 'framer-motion';
import { FaArrowLeft, FaHistory, FaLightbulb, FaClipboardList, FaHeartbeat } from 'react-icons/fa';
import { getStudent, getStudentPrediction, getStudentRiskHistory, getAIAdvice, getInterventions, createIntervention, getStudentMLPrediction } from '../api';
import Spinner from '../components/common/Spinner';
import { variants } from '../utils/motionConfig';
import RiskExplanation from '../components/ai/RiskExplanation';
import MLRiskCard from '../components/student/MLRiskCard';
import RiskBreakdownChart from '../components/student/RiskBreakdownChart';
import DataQualityPanel from '../components/quality/DataQualityPanel';
import AIRecommendationCard from '../components/ai/AIRecommendationCard';
import StudentTimeline from '../components/student/StudentTimeline';
import InterventionHistoryCard from '../components/interventions/InterventionHistoryCard';
import ConfidenceBadge from '../components/common/ConfidenceBadge';
import { RiskTrendIndicator } from '../components/common/TrendIndicator';
import { getTopRecommendations } from '../utils/recommendationEngine';
import CollapsiblePanel from '../components/common/CollapsiblePanel';

function StudentProfile() {
  const [student, setStudent] = useState(null);
  const [prediction, setPrediction] = useState(null);
  const [mlPrediction, setMlPrediction] = useState(null);
  const [riskHistory, setRiskHistory] = useState([]);
  const [interventions, setInterventions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [aiAdvice, setAiAdvice] = useState('');
  const [loadingAdvice, setLoadingAdvice] = useState(false);
  const [adviceError, setAdviceError] = useState(null);
  const [newInterventionUser, setNewInterventionUser] = useState('');
  const [newInterventionAction, setNewInterventionAction] = useState('');
  const { id } = useParams();

  const fetchInterventions = async (studentId) => {
    try {
      const fetchedInterventions = await getInterventions(studentId);
      setInterventions(fetchedInterventions);
    } catch (err) {
      console.error("Error fetching interventions:", err);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const studentData = await getStudent(id);
        const predictionData = await getStudentPrediction(id);
        const mlData = await getStudentMLPrediction(id);
        const riskHistoryData = await getStudentRiskHistory(id, predictionData.risk_score);

        setStudent(studentData);
        setPrediction(predictionData);
        setMlPrediction(mlData);
        setRiskHistory(riskHistoryData);
        await fetchInterventions(id);
      } catch (err) {
        setError('Failed to fetch student data. Please try again later.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [id]);

  const fetchAdvice = async (promptType) => {
    setLoadingAdvice(true);
    setAdviceError(null);
    try {
      const adviceText = await getAIAdvice(id, promptType);
      setAiAdvice(adviceText);
    } catch (err) {
      setAdviceError('Failed to fetch AI advice.');
      console.error(err);
    } finally {
      setLoadingAdvice(false);
    }
  };

  const handleAddIntervention = async (e) => {
    e.preventDefault();
    if (!newInterventionUser || !newInterventionAction) {
      alert("Please fill in both user and action for the intervention.");
      return;
    }
    try {
      const interventionData = {
        user: newInterventionUser,
        action: newInterventionAction,
      };
      await createIntervention(id, interventionData);
      setNewInterventionUser('');
      setNewInterventionAction('');
      await fetchInterventions(id);
    } catch (err) {
      console.error("Error adding intervention:", err);
      alert("Failed to add intervention.");
    }
  };

  if (loading) {
    return <Spinner />;
  }

  if (error) {
    return <div className="alert alert-danger shadow-sm">{error}</div>;
  }

  if (!student || !prediction) {
    return (
      <div className="text-center my-5">
        <h2>Student not found</h2>
        <p>The student with ID "{id}" does not exist.</p>
        <Button as={Link} to="/students" variant="secondary">Back to List</Button>
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
      <div className="mb-4">
        <Link to="/students" className="text-decoration-none text-muted mb-2 d-inline-flex align-items-center gap-2 hover-text-primary transition-colors">
          <FaArrowLeft size={14} /> Back to Directory
        </Link>
        <div className="d-flex justify-content-between align-items-end mt-2">
          <h1 className="display-6 fw-bold text-gradient mb-0">{student.name || id} <span className="text-secondary opacity-50 fs-6">{student.department || ''}</span></h1>
          <div className="d-flex align-items-center gap-2">
            <RiskTrendIndicator student={{ ...student, risk_score: prediction.risk_score }} showDelta={true} />
            <ConfidenceBadge student={{ ...student, risk_score: prediction.risk_score }} size="md" showLabel={true} />
          </div>
        </div>
      </div>

      {/* ML Risk Assessment Card */}
      {mlPrediction && (
        <motion.div variants={variants.item} className="mb-4">
          <MLRiskCard mlPrediction={mlPrediction} ruleRiskScore={prediction.risk_score} />
        </motion.div>
      )}

      {/* Risk Explanation - Full Width */}
      <motion.div variants={variants.item} className="mb-4">
        <RiskExplanation student={{ ...student, risk_score: prediction.risk_score }} variant="full" />
      </motion.div>

      <Row className="g-4">
        <Col md={8}>
          <motion.div variants={variants.item} className="glass-panel p-4 mb-4 h-100">
            <div className="d-flex align-items-center gap-2 mb-4 text-primary">
              <FaHistory />
              <h5 className="mb-0 fw-bold">Risk Score Trend</h5>
            </div>
            <div style={{ width: '100%', height: 350 }}>
              <ResponsiveContainer>
                <LineChart data={riskHistory}>
                  <defs>
                    <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--primary-color)" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="var(--primary-color)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" vertical={false} />
                  <XAxis dataKey="date" stroke="var(--text-secondary)" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 100]} stroke="var(--text-secondary)" tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'var(--surface-color)', borderColor: 'var(--border-color)', borderRadius: '12px', boxShadow: 'var(--shadow-lg)' }}
                    itemStyle={{ color: 'var(--text-primary)' }}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="risk_score"
                    stroke="var(--primary-color)"
                    strokeWidth={3}
                    dot={{ fill: 'var(--bg-color)', stroke: 'var(--primary-color)', strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 8 }}
                    name="Risk Score"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </motion.div>

          {/* Intervention Log */}
          <motion.div variants={variants.item} className="glass-panel p-4 mb-4">
            <div className="d-flex justify-content-between align-items-center mb-4">
              <div className="d-flex align-items-center gap-2 text-secondary">
                <FaClipboardList />
                <h5 className="mb-0 fw-bold">Intervention Log</h5>
              </div>
              <Badge bg="secondary" className="bg-opacity-10 text-secondary border border-secondary-subtle">
                {interventions.length} Records
              </Badge>
            </div>

            <div className="table-responsive mb-4 rounded-3 overflow-hidden border border-secondary-subtle">
              <table className="modern-table mb-0">
                <thead className="bg-surface-hover">
                  <tr>
                    <th>Date</th>
                    <th>User</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {interventions.length > 0 ? (
                    interventions.map((item) => (
                      <tr key={item.id}>
                        <td className="text-nowrap">{new Date(item.date).toLocaleDateString()}</td>
                        <td className="fw-medium text-primary">{item.user}</td>
                        <td>{item.action}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="3" className="text-center py-5 text-muted">No interventions logged yet.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="p-4 bg-surface-hover rounded-3 border border-secondary-subtle">
              <h6 className="mb-3 fw-bold text-gradient">Recorded New Intervention</h6>
              <Form onSubmit={handleAddIntervention}>
                <Row className="g-3 mb-3">
                  <Col md={4}>
                    <Form.Group controlId="interventionUser">
                      <Form.Label className="small text-muted fw-bold text-uppercase">User</Form.Label>
                      <Form.Control
                        type="text"
                        placeholder="Name"
                        value={newInterventionUser}
                        onChange={(e) => setNewInterventionUser(e.target.value)}
                        className="bg-surface border-secondary-subtle"
                      />
                    </Form.Group>
                  </Col>
                  <Col md={8}>
                    <Form.Group controlId="interventionAction">
                      <Form.Label className="small text-muted fw-bold text-uppercase">Action</Form.Label>
                      <Form.Control
                        type="text"
                        placeholder="Action description..."
                        value={newInterventionAction}
                        onChange={(e) => setNewInterventionAction(e.target.value)}
                        className="bg-surface border-secondary-subtle"
                      />
                    </Form.Group>
                  </Col>
                </Row>
                <div className="text-end">
                  <Button variant="primary" type="submit" size="sm" className="px-4">
                    Add Record
                  </Button>
                </div>
              </Form>
            </div>
          </motion.div>

          {/* Engagement Metrics */}
          <motion.div variants={variants.item} className="glass-panel p-4 mb-4">
            <h5 className="mb-4 fw-bold">Engagement Metrics</h5>
            <Row className="g-3">
              <Col md={6}>
                <div className="p-3 bg-surface-hover rounded-3">
                  <small className="text-muted d-block mb-2 text-uppercase fw-bold">Academic Performance</small>
                  <ul className="list-unstyled mb-0">
                    <li className="mb-2 d-flex justify-content-between"><span>Graded Quiz Score:</span> <span className={`fw-bold ${(student.graded_quiz_score ?? 0) < 40 ? 'text-danger' : ''}`}>{Math.round(student.graded_quiz_score ?? 0)}%</span></li>
                    <li className="mb-2 d-flex justify-content-between"><span>Graded Assignment Score:</span> <span className="fw-bold">{Math.round(student.graded_assignment_score ?? 0)}%</span></li>
                    <li className="mb-2 d-flex justify-content-between"><span>Exam Score:</span> <span className="fw-bold">{Math.round(student.exam_score ?? 0)}%</span></li>
                    <li className="mb-2 d-flex justify-content-between"><span>Exam Attendance:</span> <span className={`fw-bold ${(student.exam_attendance_rate ?? 0) < 70 ? 'text-warning' : ''}`}>{Math.round(student.exam_attendance_rate ?? 0)}%</span></li>
                  </ul>
                </div>
              </Col>
              <Col md={6}>
                <div className="p-3 bg-surface-hover rounded-3">
                  <small className="text-muted d-block mb-2 text-uppercase fw-bold">LMS Engagement</small>
                  <ul className="list-unstyled mb-0">
                    <li className="mb-2 d-flex justify-content-between"><span>Content Completion:</span> <span className="fw-bold">{Math.round(student.content_completion_score ?? 0)}%</span></li>
                    <li className="mb-2 d-flex justify-content-between"><span>Quiz Engagement:</span> <span className="fw-bold">{Math.round(student.quiz_engagement_score ?? 0)}%</span></li>
                    <li className="mb-2 d-flex justify-content-between"><span>Login Consistency:</span> <span className="fw-bold">{Math.round(student.login_consistency_score ?? 0)}%</span></li>
                    <li className="mb-2 d-flex justify-content-between"><span>Time Investment:</span> <span className="fw-bold">{Math.round(student.time_investment_score ?? 0)}%</span></li>
                  </ul>
                </div>
              </Col>
            </Row>
            {student.dominant_risk_factor && (
              <div className="mt-3 p-2 bg-surface-hover rounded-3 text-center">
                <small className="text-muted">Primary Risk Factor: </small>
                <span className="fw-bold text-danger">{student.dominant_risk_factor}</span>
              </div>
            )}
          </motion.div>
        </Col>

        <Col md={4}>
          <motion.div variants={variants.item} className="glass-panel p-4 mb-4 text-center position-relative overflow-hidden">
            {/* Decorative Background */}
            <div style={{ position: 'absolute', top: -50, right: -50, width: 200, height: 200, background: 'radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%)', zIndex: 0 }} />

            <div className="d-flex align-items-center justify-content-center gap-2 mb-4 text-danger position-relative" style={{ zIndex: 1 }}>
              <FaHeartbeat />
              <h5 className="mb-0 fw-bold">Current Vitals</h5>
            </div>

            <div className="mb-4 position-relative d-inline-block">
              <div className="d-flex align-items-center justify-content-center rounded-circle shadow-glow transition-all"
                style={{
                  width: '180px',
                  height: '180px',
                  border: `12px solid ${Math.round(prediction.risk_score) > 75 ? 'var(--high-risk-color)' : 'var(--low-risk-color)'}`,
                  background: 'var(--surface-color)'
                }}>
                <div>
                  <span className="display-4 fw-bold letter-spacing-tight">{Math.round(prediction.risk_score)}</span>
                  <span className="fs-5 d-block text-muted opacity-75">%</span>
                </div>
              </div>
              <div className="mt-3 text-secondary text-uppercase small fw-bold letter-spacing-widest">Risk Score</div>
            </div>

            <div className="text-start mt-4 pt-4 border-top border-light">
              <Row className="g-3">
                <Col xs={6}>
                  <div className="p-2 rounded bg-surface-hover text-center">
                    <small className="d-block text-muted mb-1">Retention</small>
                    <span className="fw-bold fs-5 text-primary">{prediction.retention_likelihood}%</span>
                  </div>
                </Col>
                <Col xs={6}>
                  <div className="p-2 rounded bg-surface-hover text-center">
                    <small className="d-block text-muted mb-1">Engagement</small>
                    <span className="fw-bold fs-5 text-success">{Math.round(prediction.engagement_score)}%</span>
                  </div>
                </Col>
              </Row>
              <div className="mt-3">
                <div className="d-flex justify-content-between mb-1 small text-muted">
                  <span>Exam Attendance</span>
                  <span>{Math.round(student.exam_attendance_rate ?? 0)}%</span>
                </div>
                <div className="progress" style={{ height: '6px' }}>
                  <div className="progress-bar bg-info" role="progressbar" style={{ width: `${Math.round(student.exam_attendance_rate ?? 0)}%` }}></div>
                </div>
              </div>
              <div className="mt-2">
                <div className="d-flex justify-content-between mb-1 small text-muted">
                  <span>Quiz Score</span>
                  <span>{Math.round(student.graded_quiz_score ?? 0)}%</span>
                </div>
                <div className="progress" style={{ height: '6px' }}>
                  <div className="progress-bar bg-primary" role="progressbar" style={{ width: `${Math.round(student.graded_quiz_score ?? 0)}%` }}></div>
                </div>
              </div>
              <div className="mt-2">
                <div className="d-flex justify-content-between mb-1 small text-muted">
                  <span>Content Completion</span>
                  <span>{Math.round(student.content_completion_score ?? 0)}%</span>
                </div>
                <div className="progress" style={{ height: '6px' }}>
                  <div className="progress-bar bg-success" role="progressbar" style={{ width: `${Math.round(student.content_completion_score ?? 0)}%` }}></div>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Additional Info - Collapsible */}
          <motion.div variants={variants.item} className="mb-4">
            <CollapsiblePanel title="Student Details" defaultExpanded={false}>
              <ul className="list-unstyled mb-0">
                <li className="mb-2 d-flex justify-content-between"><span>Student ID:</span> <span className="fw-medium">{student.id}</span></li>
                <li className="mb-2 d-flex justify-content-between"><span>Department:</span> <span className="fw-medium">{student.department || 'N/A'}</span></li>
                <li className="mb-2 d-flex justify-content-between"><span>Program:</span> <span className="fw-medium">{student.program || 'N/A'}</span></li>
                <li className="mb-2 d-flex justify-content-between"><span>Risk Category:</span> <span className={`fw-bold ${student.risk_category === 'high' ? 'text-danger' : student.risk_category === 'medium' ? 'text-warning' : 'text-success'}`}>{(student.risk_category || 'N/A').toUpperCase()}</span></li>
                <li className="mb-2 d-flex justify-content-between"><span>Total Courses:</span> <span className="fw-medium">{student.total_courses ?? 'N/A'}</span></li>
              </ul>
            </CollapsiblePanel>
          </motion.div>
        </Col>
      </Row>
    </motion.div>
  );
}

export default StudentProfile;