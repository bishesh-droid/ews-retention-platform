import React, { useState, useMemo } from 'react';
import { Form, Badge } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { FaSort, FaSortUp, FaSortDown } from 'react-icons/fa';
import { variants } from '../../utils/motionConfig';
import { RiskTrendIndicator } from '../common/TrendIndicator';
import ConfidenceBadge from '../common/ConfidenceBadge';

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

// Get risk category badge
const RiskCategoryBadge = ({ student }) => {
  const score = student.risk_score ?? 50;
  if (score >= 70) {
    return <Badge bg="danger" className="px-2">High Risk</Badge>;
  } else if (score >= 40) {
    return <Badge bg="warning" className="px-2">Medium</Badge>;
  }
  return <Badge bg="success" className="px-2">Low Risk</Badge>;
};

const RiskTable = ({ students, onSelectStudent, selectedStudents }) => {
  const [sortConfig, setSortConfig] = useState({ key: 'risk_score', direction: 'descending' });
  const navigate = useNavigate();

  const sortedStudents = useMemo(() => {
    let sortableItems = [...students];
    if (sortConfig !== null) {
      sortableItems.sort((a, b) => {
        let aVal = a[sortConfig.key];
        let bVal = b[sortConfig.key];

        // Handle computed fields
        if (sortConfig.key === 'graded_quiz_score') {
          aVal = getQuizScore(a);
          bVal = getQuizScore(b);
        } else if (sortConfig.key === 'exam_attendance_rate') {
          aVal = getAttendanceRate(a);
          bVal = getAttendanceRate(b);
        }

        if (aVal < bVal) {
          return sortConfig.direction === 'ascending' ? -1 : 1;
        }
        if (aVal > bVal) {
          return sortConfig.direction === 'ascending' ? 1 : -1;
        }
        return 0;
      });
    }
    return sortableItems;
  }, [students, sortConfig]);

  const requestSort = (key) => {
    let direction = 'ascending';
    if (sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
  };

  const getSortIndicator = (key) => {
    if (sortConfig.key === key) {
      return sortConfig.direction === 'ascending' ? <FaSortUp /> : <FaSortDown />;
    }
    return <FaSort className="text-muted opacity-50" />;
  };

  const handleRowClick = (studentId, target) => {
    if (target.type === 'checkbox') return;
    navigate(`/students/${studentId}`);
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
              <div className="d-flex align-items-center gap-2">
                Risk Score {getSortIndicator('risk_score')}
              </div>
            </th>
            <th onClick={() => requestSort('graded_quiz_score')} style={{ cursor: 'pointer' }}>
              <div className="d-flex align-items-center gap-2">
                Quiz Score {getSortIndicator('graded_quiz_score')}
              </div>
            </th>
            <th onClick={() => requestSort('exam_attendance_rate')} style={{ cursor: 'pointer' }}>
              <div className="d-flex align-items-center gap-2">
                Exam Attendance {getSortIndicator('exam_attendance_rate')}
              </div>
            </th>
            <th onClick={() => requestSort('engagement_score')} style={{ cursor: 'pointer' }}>
              <div className="d-flex align-items-center gap-2">
                Engagement {getSortIndicator('engagement_score')}
              </div>
            </th>
            <th onClick={() => requestSort('risk_score')} style={{ cursor: 'pointer' }}>
              <div className="d-flex align-items-center gap-2">
                Status {getSortIndicator('risk_score')}
              </div>
            </th>
            <th>Confidence</th>
          </tr>
        </thead>
        <tbody>
          {sortedStudents.map((student, index) => (
            <motion.tr
              key={student.id}
              onClick={(e) => handleRowClick(student.id, e.target)}
              style={{ cursor: 'pointer' }}
              variants={variants.item}
              whileHover={{ backgroundColor: 'var(--surface-hover)' }}
              transition={{ type: 'tween', duration: 0.2 }}
            >
              <td>
                <Form.Check
                  type="checkbox"
                  checked={selectedStudents.includes(student.id)}
                  onChange={() => onSelectStudent(student.id)}
                  onClick={(e) => e.stopPropagation()}
                />
              </td>
              <td className="fw-medium">{student.name || student.id}</td>
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
              <td><RiskCategoryBadge student={student} /></td>
              <td><ConfidenceBadge student={student} size="sm" showLabel={false} /></td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default RiskTable;
