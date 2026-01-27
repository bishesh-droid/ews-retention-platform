import React, { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { Card, Button, Row, Col, OverlayTrigger, Tooltip, ListGroup } from 'react-bootstrap';
import Charts from '../components/Charts';
import HighestRiskStudentsTable from '../components/HighestRiskStudentsTable';
import InterventionSuggestions from '../components/InterventionSuggestions';
import { useStudentData } from '../context/StudentContext';
import { getPrimaryRiskFactor } from '../utils/studentUtils';

function Dashboard() {
  const { students } = useStudentData();
  const [riskFilter, setRiskFilter] = useState(null);
  const [riskFactorFilter, setRiskFactorFilter] = useState(null);

  // Simulated data for warnings
  const warnings = [
    { id: 1, name: 'John Doe', message: 'Risk score increased by 20 points.' },
    { id: 2, name: 'Jane Smith', message: 'Moved into High Risk category.' },
  ];

  const atRiskStudents = useMemo(() => students.filter(s => s.risk_score > 75).length, [students]);
  const averageRiskScore = useMemo(() => students.length > 0 ? (students.reduce((acc, s) => acc + s.risk_score, 0) / students.length).toFixed(0) : 0, [students]);

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

  const renderTooltip = (props) => (
    <Tooltip id="button-tooltip" {...props}>
      This is the average risk score across all students. It can be used to gauge the overall risk level of the student population.
    </Tooltip>
  );

  if (students.length === 0) {
    return (
      <div className="text-center my-5">
        <h2>No student data available</h2>
        <p>Import or add students to get started.</p>
        <Button as={Link} to="/students" variant="primary">Add Students</Button>
      </div>
    );
  }

  return (
    <div>
      <h1 className="mb-4">Student Retention Dashboard</h1>

      <Row>
        {/* Main Content Column */}
        <Col md={8}>
          <Card className="mb-4">
            <Card.Header as="h2">Highest-Risk Students</Card.Header>
            <Card.Body>
              <HighestRiskStudentsTable students={filteredStudentsForTable} />
            </Card.Body>
          </Card>

          <Card className="mb-4">
            <Card.Header as="h2">Risk Analysis</Card.Header>
            <Card.Body>
              <Charts 
                students={filteredStudentsForChart} 
                onRiskFilterChange={handleRiskFilterChange} 
                riskFilter={riskFilter}
                onRiskFactorFilterChange={handleRiskFactorFilterChange}
                riskFactorFilter={riskFactorFilter}
              />
            </Card.Body>
          </Card>
        </Col>

        {/* Sidebar Column */}
        <Col md={4}>
          <Card className="mb-4">
            <Card.Header as="h3">Overview</Card.Header>
            <Card.Body>
              <div className="text-center mb-3">
                <h5>Total Students</h5>
                <p className="fs-2">{students.length}</p>
              </div>
              <div className="text-center mb-3">
                <h5>At-Risk Students</h5>
                <p className="fs-2">{atRiskStudents}</p>
              </div>
              <div className="text-center">
                <h5>
                  Average Risk Score{' '}
                  <OverlayTrigger
                    placement="top"
                    delay={{ show: 250, hide: 400 }}
                    overlay={renderTooltip}
                  >
                    <i className="bi bi-info-circle"></i>
                  </OverlayTrigger>
                </h5>
                <p className="fs-2">{averageRiskScore}%</p>
              </div>
            </Card.Body>
          </Card>

          <Card className="mb-4">
            <Card.Header as="h3" className="text-danger">
              <i className="bi bi-exclamation-triangle-fill"></i> Warnings
            </Card.Header>
            <ListGroup variant="flush">
              {warnings.map(warning => (
                <ListGroup.Item key={warning.id}>
                  <Link to={`/students/${warning.id}`}>{warning.name}</Link>: {warning.message}
                </ListGroup.Item>
              ))}
            </ListGroup>
          </Card>

          <div className="mb-4">
            <InterventionSuggestions students={students} />
          </div>

          <Card>
            <Card.Header as="h3">Quick Links</Card.Header>
            <Card.Body>
              <div className="d-grid gap-2">
                <Button as={Link} to="/students" variant="primary">View Detailed Student List</Button>
                <Button as={Link} to="/insights" variant="outline-primary">Get AI-Powered Insights</Button>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default Dashboard;
