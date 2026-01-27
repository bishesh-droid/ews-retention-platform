import React, { useMemo } from 'react';
import { Table, Button, OverlayTrigger, Tooltip } from 'react-bootstrap';
import { Link } from 'react-router-dom';
import { getPrimaryRiskFactor } from '../utils/studentUtils';

const RiskScore = ({ value }) => {
  let color;
  if (value > 75) {
    color = 'var(--high-risk-color)';
  } else if (value > 50) {
    color = 'var(--medium-risk-color)';
  } else if (value > 25) {
    color = 'var(--low-risk-color)';
  } else {
    color = 'var(--very-low-risk-color)';
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center' }}>
      <span style={{
        height: '10px',
        width: '10px',
        backgroundColor: color,
        borderRadius: '50%',
        display: 'inline-block',
        marginRight: '8px'
      }}></span>
      {value}
    </div>
  );
};

const HighestRiskStudentsTable = ({ students }) => {
  const top5Students = useMemo(() => 
    [...students].sort((a, b) => b.risk_score - a.risk_score).slice(0, 5), 
    [students]
  );

  const getIntervention = (factor) => {
    switch (factor) {
      case 'Attendance':
        return 'Schedule 1-on-1 meeting';
      case 'Assignments':
        return 'Offer tutoring resources';
      case 'Grades':
        return 'Recommend academic counseling';
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
    <Table striped bordered hover>
      <thead>
        <tr>
          <th>Name</th>
          <th>
            <OverlayTrigger
              placement="top"
              delay={{ show: 250, hide: 400 }}
              overlay={renderTooltip}
            >
              <span>Risk Score (%) <i className="bi bi-info-circle"></i></span>
            </OverlayTrigger>
          </th>
          <th>Primary Risk Factor</th>
          <th>Suggested Intervention</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {top5Students.map((student) => {
          const primaryRiskFactor = getPrimaryRiskFactor(student);
          return (
            <tr key={student.id}>
              <td>{student.name}</td>
              <td><RiskScore value={student.risk_score} /></td>
              <td>{primaryRiskFactor}</td>
              <td>{getIntervention(primaryRiskFactor)}</td>
              <td>
                <Button as={Link} to={`/students/${student.id}`} variant="primary" size="sm">
                  View Details
                </Button>
              </td>
            </tr>
          );
        })}
      </tbody>
    </Table>
  );
};

export default HighestRiskStudentsTable;
