import React, { useMemo } from 'react';
import { Button, OverlayTrigger, Tooltip } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { getPrimaryRiskFactor } from '../../utils/studentUtils';
import { FaArrowRight } from 'react-icons/fa';

const RiskScore = ({ value }) => {
  const roundedValue = Math.round(value);
  let riskLevel = 'low';
  if (roundedValue > 75) {
    riskLevel = 'high';
  } else if (roundedValue > 50) {
    riskLevel = 'medium';
  }
  return (
    <span className={`risk-badge ${riskLevel}`}>
      {roundedValue}%
    </span>
  );
};

const HighestRiskStudentsTable = ({ students }) => {
  const top5Students = useMemo(() =>
    [...students].sort((a, b) => b.risk_score - a.risk_score).slice(0, 5),
    [students]
  );

  const getIntervention = (factor) => {
    switch (factor) {
      case 'Exam Attendance':
        return 'Schedule 1-on-1 meeting';
      case 'Content Completion':
        return 'Encourage course engagement';
      case 'Graded Quiz Performance':
        return 'Offer tutoring resources';
      case 'Graded Assignment Performance':
        return 'Recommend assignment support';
      case 'Exam Performance':
        return 'Recommend academic counseling';
      case 'Login Consistency':
      case 'Time Investment':
        return 'Check in on engagement';
      default:
        return 'Monitor closely';
    }
  };

  const renderTooltip = (props) => (
    <Tooltip id="button-tooltip" {...props}>
      High Risk: &gt;75%<br />
      Medium Risk: 51-75%<br />
      Low Risk: 26-50%<br />
      Very Low Risk: 0-25%
    </Tooltip>
  );

  return (
    <div className="table-responsive">
      <table className="modern-table">
        <thead>
          <tr>
            <th>Student</th>
            <th>
              <OverlayTrigger
                placement="top"
                delay={{ show: 250, hide: 400 }}
                overlay={renderTooltip}
              >
                <span style={{ cursor: 'help' }}>Risk Score</span>
              </OverlayTrigger>
            </th>
            <th>Primary Risk Factor</th>
            <th>Suggested Intervention</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {top5Students.map((student, index) => {
            const primaryRiskFactor = getPrimaryRiskFactor(student);
            return (
              <motion.tr
                key={student.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <td className="fw-medium">{student.name || student.id}</td>
                <td><RiskScore value={student.risk_score} /></td>
                <td>{primaryRiskFactor}</td>
                <td className="text-muted">{getIntervention(primaryRiskFactor)}</td>
                <td>
                  <Button
                    as={Link}
                    to={`/students/${student.id}`}
                    variant="link"
                    className="p-0 text-primary d-flex align-items-center gap-1 text-decoration-none"
                  >
                    Details <FaArrowRight size={12} />
                  </Button>
                </td>
              </motion.tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default HighestRiskStudentsTable;
