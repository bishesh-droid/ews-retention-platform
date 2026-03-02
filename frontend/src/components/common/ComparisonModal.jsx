import React from 'react';
import { Modal, Button, Row, Col, Card } from 'react-bootstrap';

const modalStyle = { backgroundColor: '#130D23', border: '1px solid rgba(139,92,246,0.25)', color: '#EDE9FE' };
const cardStyle = { backgroundColor: '#1A1035', border: '1px solid rgba(139,92,246,0.2)', borderRadius: '12px', padding: '16px', color: '#EDE9FE' };

const ComparisonModal = ({ show, onHide, students }) => {
  return (
    <Modal show={show} onHide={onHide} size="xl" centered>
      <Modal.Header closeButton style={modalStyle}>
        <Modal.Title style={{ color: '#EDE9FE' }}>Compare Students</Modal.Title>
      </Modal.Header>
      <Modal.Body style={modalStyle}>
        {students.length < 2 ? (
          <div className="text-center py-5">
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>👆</div>
            <p style={{ color: '#C4B5FD', fontSize: '16px', fontWeight: 600 }}>
              Click on student rows to select them
            </p>
            <p style={{ color: '#8B7DB8', fontSize: '13px' }}>
              Select at least 2 students to compare their profiles side by side.<br />
              Currently selected: <strong style={{ color: '#A78BFA' }}>{students.length}</strong>
            </p>
          </div>
        ) : (
          <Row>
            {students.map(student => (
              <Col key={student.id} md={Math.floor(12 / students.length)}>
                <div style={cardStyle}>
                  <h5 style={{ color: '#EDE9FE', marginBottom: '12px', fontSize: '14px', fontWeight: 700 }}>
                    {student.name || student.id}
                  </h5>
                  {[
                    ['Risk Score', `${Math.round(student.risk_score)}%`],
                    ['Quiz Score', `${Math.round(student.graded_quiz_score ?? 0)}%`],
                    ['Attendance', `${Math.round(student.exam_attendance_rate ?? 0)}%`],
                    ['Engagement', `${Math.round(student.engagement_score ?? 0)}%`],
                  ].map(([label, val]) => (
                    <div key={label} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(139,92,246,0.12)' }}>
                      <span style={{ color: '#8B7DB8', fontSize: '13px' }}>{label}</span>
                      <span style={{ color: '#EDE9FE', fontWeight: 600, fontSize: '13px' }}>{val}</span>
                    </div>
                  ))}
                </div>
              </Col>
            ))}
          </Row>
        )}
      </Modal.Body>
      <Modal.Footer style={modalStyle}>
        <button onClick={onHide} style={{ backgroundColor: 'rgba(139,92,246,0.2)', color: '#C4B5FD', border: '1px solid rgba(139,92,246,0.3)', borderRadius: '8px', padding: '8px 20px', cursor: 'pointer', fontWeight: 600 }}>
          Close
        </button>
      </Modal.Footer>
    </Modal>
  );
};

export default ComparisonModal;
