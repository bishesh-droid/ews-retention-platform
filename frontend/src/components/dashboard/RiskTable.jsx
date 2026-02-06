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

// Calculate average GPA from latest semester's quarterly marks
const getLatestGPA = (student) => {
  const q1 = student.q1mpa7 || 0;
  const q2 = student.q2mpa7 || 0;
  const q3 = student.q3mpa7 || 0;
  const q4 = student.q4mpa7 || 0;
  const avg = (q1 + q2 + q3 + q4) / 4;
  return avg.toFixed(2);
};

// Get attendance rate from latest semester
const getAttendanceRate = (student) => {
  const absRate = student.absrate7 || 0;
  // absrate can be negative (standardized), so we normalize it
  // Lower is better, typical range is -10 to +30
  const normalized = Math.max(0, Math.min(100, 100 - (absRate * 3)));
  return Math.round(normalized);
};

// Get graduation status badge
const GradStatusBadge = ({ nograd }) => {
  if (nograd === 1) {
    return <Badge bg="danger" className="px-2">At Risk</Badge>;
  }
  return <Badge bg="success" className="px-2">On Track</Badge>;
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
        if (sortConfig.key === 'latestGPA') {
          aVal = parseFloat(getLatestGPA(a));
          bVal = parseFloat(getLatestGPA(b));
        } else if (sortConfig.key === 'attendance') {
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
            <th onClick={() => requestSort('latestGPA')} style={{ cursor: 'pointer' }}>
              <div className="d-flex align-items-center gap-2">
                Latest GPA {getSortIndicator('latestGPA')}
              </div>
            </th>
            <th onClick={() => requestSort('attendance')} style={{ cursor: 'pointer' }}>
              <div className="d-flex align-items-center gap-2">
                Attendance {getSortIndicator('attendance')}
              </div>
            </th>
            <th onClick={() => requestSort('engagement_score')} style={{ cursor: 'pointer' }}>
              <div className="d-flex align-items-center gap-2">
                Engagement {getSortIndicator('engagement_score')}
              </div>
            </th>
            <th onClick={() => requestSort('nograd')} style={{ cursor: 'pointer' }}>
              <div className="d-flex align-items-center gap-2">
                Status {getSortIndicator('nograd')}
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
              <td className="fw-medium">{student.id}</td>
              <td><RiskScore student={student} /></td>
              <td>
                <span className={parseFloat(getLatestGPA(student)) < 2.0 ? 'text-danger fw-bold' : ''}>
                  {getLatestGPA(student)}
                </span>
              </td>
              <td>
                <span className={getAttendanceRate(student) < 70 ? 'text-warning fw-bold' : ''}>
                  {getAttendanceRate(student)}%
                </span>
              </td>
              <td>{Math.round(student.engagement_score || 0)}%</td>
              <td><GradStatusBadge nograd={student.nograd} /></td>
              <td><ConfidenceBadge student={student} size="sm" showLabel={false} /></td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default RiskTable;
