import React, { useState, useMemo } from 'react';
import { Form, Badge, OverlayTrigger, Tooltip as BootstrapTooltip } from 'react-bootstrap';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FaSort, FaSortUp, FaSortDown } from 'react-icons/fa';
import { variants } from '../../utils/motionConfig';
import { RiskTrendIndicator } from '../common/TrendIndicator';
import ConfidenceBadge from '../common/ConfidenceBadge';

const generateTrendData = (currentScore) => {
  return [
    { value: currentScore + Math.floor(Math.random() * 10 - 5) },
    { value: currentScore + Math.floor(Math.random() * 10 - 5) },
    { value: currentScore + Math.floor(Math.random() * 10 - 5) },
    { value: currentScore }
  ];
};

const Sparkline = ({ score }) => {
  const data = useMemo(() => generateTrendData(score), [score]);
  const color = score > 75 ? 'var(--color-error)' : score > 50 ? 'var(--color-warning)' : 'var(--color-success)';
  return (
    <div style={{ width: '60px', height: '24px' }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <YAxis domain={['dataMin - 10', 'dataMax + 10']} hide />
          <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

const getRiskDrivers = (student) => {
  const drivers = [];
  if ((student.exam_attendance_rate ?? 100) < 75) drivers.push('Low Attendance');
  if ((student.graded_quiz_score ?? 100) < 60) drivers.push('Poor Quiz Scores');
  if ((student.engagement_score ?? 100) < 50) drivers.push('Low Engagement');
  if (drivers.length < 3 && student.risk_score > 60) drivers.push('Historical Risk');
  if (drivers.length === 0) drivers.push('Stable');
  return drivers.slice(0, 3);
};

const RiskScore = ({ student }) => {
  const value = Math.round(student.risk_score);
  let riskLevel = 'low';
  if (value > 75) {
    riskLevel = 'high';
  } else if (value > 50) {
    riskLevel = 'medium';
  }
  return (
    <div className="d-flex align-items-center gap-2 flex-wrap">
      <span className={`risk-badge ${riskLevel}`}>
        {value}%
      </span>
      <Sparkline score={value} />
      <RiskTrendIndicator student={student} showDelta={false} />
    </div>
  );
};

// Get quiz score from backend
const getQuizScore = (student) => {
  return Math.round(student.graded_quiz_score ?? 0);
};

// Get exam attendance rate from backend
const getAttendanceRate = (student) => {
  return Math.round(student.exam_attendance_rate ?? 0);
};

// Get risk category badge (prefer backend risk_label when available)
const RiskCategoryBadge = ({ student }) => {
  const score = student.risk_score ?? 50;
  const label = student.risk_label || (score >= 70 ? 'High Risk' : score >= 40 ? 'Medium' : 'Low Risk');

  if (label.toLowerCase().includes('high')) {
    return <Badge bg="danger" className="px-2">{label}</Badge>;
  }
  if (label.toLowerCase().includes('medium')) {
    return <Badge bg="warning" className="px-2">{label}</Badge>;
  }
  return <Badge bg="success" className="px-2">{label}</Badge>;
};

const RiskTable = ({ students, onSelectStudent, selectedStudents, sortConfig, onSortChange }) => {
  const navigate = useNavigate();

  const requestSort = (key) => {
    if (!onSortChange) return;
    let direction = 'ascending';
    if (sortConfig && sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    onSortChange({ key, direction });
  };

  const getSortIndicator = (key) => {
    if (sortConfig && sortConfig.key === key) {
      return sortConfig.direction === 'ascending' ? <FaSortUp /> : <FaSortDown />;
    }
    return <FaSort className="text-muted opacity-50" />;
  };

  const handleRowClick = (studentId) => {
    onSelectStudent(studentId);
  };

  return (
    <div className="table-responsive">
      <table className="modern-table">
        <thead>
          <tr>
            <th style={{ width: '50px' }}>
              <Form.Check
                type="checkbox"
                onChange={(e) => onSelectStudent(null, e.target.checked)}
              />
            </th>
            <th onClick={() => requestSort('id')} style={{ cursor: 'pointer' }}>
              <div className="d-flex align-items-center gap-2">
                Student {getSortIndicator('id')}
              </div>
            </th>
            <th onClick={() => requestSort('risk_score')} style={{ cursor: 'pointer' }}>
              <OverlayTrigger placement="top" overlay={<BootstrapTooltip>Overall calculated risk of student attrition.</BootstrapTooltip>}>
                <div className="d-flex align-items-center gap-2">
                  Risk Score {getSortIndicator('risk_score')}
                </div>
              </OverlayTrigger>
            </th>
            <th onClick={() => requestSort('graded_quiz_score')} style={{ cursor: 'pointer' }}>
              <OverlayTrigger placement="top" overlay={<BootstrapTooltip>Average score across all graded quizzes.</BootstrapTooltip>}>
                <div className="d-flex align-items-center gap-2">
                  Quiz Score {getSortIndicator('graded_quiz_score')}
                </div>
              </OverlayTrigger>
            </th>
            <th onClick={() => requestSort('exam_attendance_rate')} style={{ cursor: 'pointer' }}>
              <OverlayTrigger placement="top" overlay={<BootstrapTooltip>Percentage of exams and lectures attended.</BootstrapTooltip>}>
                <div className="d-flex align-items-center gap-2">
                  Exam Attendance {getSortIndicator('exam_attendance_rate')}
                </div>
              </OverlayTrigger>
            </th>
            <th onClick={() => requestSort('engagement_score')} style={{ cursor: 'pointer' }}>
              <OverlayTrigger placement="top" overlay={<BootstrapTooltip>LMS activity and forum participation.</BootstrapTooltip>}>
                <div className="d-flex align-items-center gap-2">
                  Engagement {getSortIndicator('engagement_score')}
                </div>
              </OverlayTrigger>
            </th>
            <th>Primary Drivers</th>
            <th onClick={() => requestSort('risk_score')} style={{ cursor: 'pointer' }}>
              <div className="d-flex align-items-center gap-2">
                Status {getSortIndicator('risk_score')}
              </div>
            </th>
            <th>
              <OverlayTrigger placement="top" overlay={<BootstrapTooltip>ML model confidence in the predicted risk score.</BootstrapTooltip>}>
                <span>Confidence</span>
              </OverlayTrigger>
            </th>
          </tr>
        </thead>
        <tbody>
          {students.map((student, index) => {
            const isSelected = selectedStudents.includes(student.id);
            return (
            <motion.tr
              key={student.id}
              onClick={() => handleRowClick(student.id)}
              style={{
                cursor: 'pointer',
                backgroundColor: isSelected ? 'rgba(139,92,246,0.15)' : undefined,
                outline: isSelected ? '1px solid rgba(139,92,246,0.5)' : 'none',
              }}
              variants={variants.item}
              whileHover={{ backgroundColor: isSelected ? 'rgba(139,92,246,0.2)' : 'rgba(139,92,246,0.06)' }}
              transition={{ type: 'tween', duration: 0.15 }}
            >
              <td onClick={(e) => e.stopPropagation()}>
                <Form.Check
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => onSelectStudent(student.id)}
                />
              </td>
              <td className="fw-medium" style={{ color: '#EDE9FE' }}>{student.name || student.id}</td>
              <td><RiskScore student={student} /></td>
              <td>
                <span className={getQuizScore(student) < 40 ? 'text-danger fw-bold' : ''}>
                  {getQuizScore(student)}%
                </span>
              </td>
              <td>
                <span className={getAttendanceRate(student) < 70 ? 'text-warning fw-bold' : ''}>
                  {getAttendanceRate(student)}%
                </span>
              </td>
              <td>{Math.round(student.engagement_score || 0)}%</td>
              <td>
                <div className="d-flex flex-wrap gap-1">
                  {getRiskDrivers(student).map((driver, i) => (
                    <span key={i} style={{
                      fontSize: '11px', fontWeight: 600, padding: '2px 8px',
                      borderRadius: '6px', backgroundColor: 'rgba(139,92,246,0.18)',
                      color: '#C4B5FD', border: '1px solid rgba(139,92,246,0.3)',
                      whiteSpace: 'nowrap'
                    }}>{driver}</span>
                  ))}
                </div>
              </td>
              <td><RiskCategoryBadge student={student} /></td>
              <td onClick={(e) => e.stopPropagation()}>
                <ConfidenceBadge student={student} size="sm" showLabel={false} />
              </td>
            </motion.tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default RiskTable;
