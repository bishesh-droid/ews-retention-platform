import React, { useState, useMemo } from 'react';
import { Table, Form } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';

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


const RiskTable = ({ students, onSelectStudent, selectedStudents }) => {
  const [sortConfig, setSortConfig] = useState({ key: 'risk_score', direction: 'descending' });
  const navigate = useNavigate();

  const sortedStudents = useMemo(() => {
    let sortableItems = [...students];
    if (sortConfig !== null) {
      sortableItems.sort((a, b) => {
        if (a[sortConfig.key] < b[sortConfig.key]) {
          return sortConfig.direction === 'ascending' ? -1 : 1;
        }
        if (a[sortConfig.key] > b[sortConfig.key]) {
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
      return sortConfig.direction === 'ascending' ? ' 🔼' : ' 🔽';
    }
    return null;
  };

  const handleRowClick = (studentId, target) => {
    // Don't navigate if the click was on the checkbox
    if (target.type === 'checkbox') return;
    navigate(`/students/${studentId}`);
  };

  return (
    <Table striped bordered hover>
      <thead>
        <tr>
          <th>
            <Form.Check 
              type="checkbox"
              onChange={(e) => onSelectStudent(null, e.target.checked)}
            />
          </th>
          <th onClick={() => requestSort('id')}>
            Student ID {getSortIndicator('id')}
          </th>
          <th onClick={() => requestSort('name')}>
            Name {getSortIndicator('name')}
          </th>
          <th onClick={() => requestSort('risk_score')}>
            Risk Score (%) {getSortIndicator('risk_score')}
          </th>
          <th onClick={() => requestSort('engagement_score')}>
            Engagement Score {getSortIndicator('engagement_score')}
          </th>
          <th onClick={() => requestSort('retention_likelihood')}>
            Retention Likelihood {getSortIndicator('retention_likelihood')}
          </th>
        </tr>
      </thead>
      <tbody>
        {sortedStudents.map((student) => (
          <tr key={student.id} onClick={(e) => handleRowClick(student.id, e.target)} className="clickable-row">
            <td>
              <Form.Check 
                type="checkbox"
                checked={selectedStudents.includes(student.id)}
                onChange={() => onSelectStudent(student.id)}
              />
            </td>
            <td>{student.id}</td>
            <td>{student.name}</td>
            <td><RiskScore value={student.risk_score} /></td>
            <td>{student.engagement_score}</td>
            <td>{student.retention_likelihood}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
};

export default RiskTable;
