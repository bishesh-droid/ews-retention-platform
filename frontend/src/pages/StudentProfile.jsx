import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { Card, Row, Col, Table } from 'react-bootstrap';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { getStudent, getStudentRiskHistory } from '../api';
import Spinner from '../components/Spinner';

const mockInterventions = [
    { date: '2023-01-23', user: 'J. Doe', action: 'Sent low engagement warning email.' },
    { date: '2023-01-30', user: 'A. Smith', action: 'Scheduled meeting with advisor.' },
    { date: '2023-02-06', user: 'A. Smith', action: 'Student attended advisor meeting. Discussed study habits.' },
];

function StudentProfile() {
  const [student, setStudent] = useState(null);
  const [riskHistory, setRiskHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { id } = useParams();

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [studentData, riskHistoryData] = await Promise.all([
          getStudent(id),
          getStudentRiskHistory(id),
        ]);
        setStudent(studentData);
        setRiskHistory(riskHistoryData);
      } catch (err) {
        setError('Failed to fetch student data. Please try again later.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [id]);

  if (loading) {
    return <Spinner />;
  }

  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }

  if (!student) {
    return (
      <div className="text-center my-5">
        <h2>Student not found</h2>
        <p>The student with ID "{id}" does not exist.</p>
      </div>
    );
  }

  return (
    <div>
      <h1>{student.name}</h1>
      <p className="text-muted">Student ID: {student.id}</p>

      <Row>
        <Col md={8}>
          <Card className="mb-4">
            <Card.Header as="h2" className="fs-5">Risk Score Trend</Card.Header>
            <Card.Body>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={riskHistory}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="risk_score" stroke="var(--high-risk-color)" name="Risk Score" />
                </LineChart>
              </ResponsiveContainer>
            </Card.Body>
          </Card>

          <Card className="mb-4">
            <Card.Header as="h2" className="fs-5">Intervention Log</Card.Header>
            <Card.Body>
                <Table striped bordered hover size="sm">
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>User</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {mockInterventions.map((item, index) => (
                            <tr key={index}>
                                <td>{item.date}</td>
                                <td>{item.user}</td>
                                <td>{item.action}</td>
                            </tr>
                        ))}
                    </tbody>
                </Table>
            </Card.Body>
          </Card>
        </Col>
        <Col md={4}>
          <Card className="mb-4">
            <Card.Header as="h2" className="fs-5">Current Vitals</Card.Header>
            <Card.Body>
              <div className="text-center">
                <h5>Current Risk Score</h5>
                <p className="fs-1">{student.risk_score}%</p>
              </div>
              <hr />
              <div>
                <p><strong>Attendance:</strong> {student.attendance}%</p>
                <p><strong>Assignments:</strong> {student.assignments}%</p>
                <p><strong>Grades:</strong> {student.grades}%</p>
                <p><strong>Engagement:</strong> {student.engagement_score}%</p>
              </div>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

export default StudentProfile;
