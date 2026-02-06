import React from 'react';
import { Modal, Button, Row, Col, Card } from 'react-bootstrap';

const ComparisonModal = ({ show, onHide, students }) => {
  return (
    <Modal show={show} onHide={onHide} size="xl" centered>
      <Modal.Header closeButton>
        <Modal.Title>Compare Students</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        <Row>
          {students.map(student => (
            <Col key={student.id} md={12 / students.length}>
              <Card>
                <Card.Header as="h5">{student.name}</Card.Header>
                <Card.Body>
                  <p><strong>Risk Score:</strong> {student.risk_score}%</p>
                  <p><strong>Engagement:</strong> {student.engagement_score}%</p>
                  <p><strong>Attendance:</strong> {student.attendance}%</p>
                  <p><strong>Assignments:</strong> {student.assignments}%</p>
                  <p><strong>Grades:</strong> {student.grades}%</p>
                  <p><strong>Retention Likelihood:</strong> {student.retention_likelihood}</p>
                </Card.Body>
              </Card>
            </Col>
          ))}
        </Row>
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={onHide}>
          Close
        </Button>
      </Modal.Footer>
    </Modal>
  );
};

export default ComparisonModal;
