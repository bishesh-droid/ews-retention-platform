import React, { useState, useMemo } from 'react';
import { Container, Form, Row, Col, Button } from 'react-bootstrap';
import ComparisonModal from '../components/ComparisonModal';
import RiskTable from '../components/RiskTable';
import Spinner from '../components/Spinner';
import { useStudentData } from '../context/StudentContext';

const Students = () => {
  const { students, loading, error } = useStudentData();
  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [selectedStudents, setSelectedStudents] = useState([]);
  const [showCompareModal, setShowCompareModal] = useState(false);

  const filteredStudents = useMemo(() => {
    return students
      .filter(student => {
        if (riskFilter === 'all') return true;
        if (riskFilter === 'high') return student.risk_score > 75;
        if (riskFilter === 'medium') return student.risk_score > 50 && student.risk_score <= 75;
        if (riskFilter === 'low') return student.risk_score > 25 && student.risk_score <= 50;
        if (riskFilter === 'very-low') return student.risk_score <= 25;
        return true;
      })
      .filter(student =>
        student.name.toLowerCase().includes(searchTerm.toLowerCase())
      );
  }, [students, searchTerm, riskFilter]);

  const handleSelectStudent = (studentId, isSelectAll) => {
    if (isSelectAll) {
      if (selectedStudents.length === filteredStudents.length) {
        setSelectedStudents([]);
      } else {
        setSelectedStudents(filteredStudents.map(s => s.id));
      }
    } else {
      setSelectedStudents(prev => 
        prev.includes(studentId) 
          ? prev.filter(id => id !== studentId)
          : [...prev, studentId]
      );
    }
  };

  const studentsToCompare = useMemo(() => {
    return students.filter(s => selectedStudents.includes(s.id));
  }, [students, selectedStudents]);

  if (loading) {
    return <Spinner />;
  }

  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }

  return (
    <Container>
      <h1 className="my-4">Students</h1>
      <Row className="mb-4">
        <Col md={5}>
          <Form.Group controlId="searchTerm">
            <Form.Label>Search by Name</Form.Label>
            <Form.Control
              type="text"
              placeholder="Enter student name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </Form.Group>
        </Col>
        <Col md={5}>
          <Form.Group controlId="riskFilter">
            <Form.Label>Filter by Risk</Form.Label>
            <Form.Control
              as="select"
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
            >
              <option value="all">All Risk Levels</option>
              <option value="high">High Risk (&gt;75)</option>
              <option value="medium">Medium Risk (51-75)</option>
              <option value="low">Low Risk (26-50)</option>
              <option value="very-low">Very Low Risk (&lt;25)</option>
            </Form.Control>
          </Form.Group>
        </Col>
        <Col md={2} className="d-flex align-items-end">
          <Button 
            variant="primary" 
            disabled={selectedStudents.length < 2}
            className="w-100"
            onClick={() => setShowCompareModal(true)}
          >
            Compare ({selectedStudents.length})
          </Button>
        </Col>
      </Row>
      {filteredStudents.length > 0 ? (
        <RiskTable 
          students={filteredStudents} 
          onSelectStudent={handleSelectStudent}
          selectedStudents={selectedStudents}
        />
      ) : (
        <div className="text-center my-5">
          <h2>No students found</h2>
          <p>Try adjusting your search or filter criteria.</p>
        </div>
      )}
      <ComparisonModal 
        show={showCompareModal}
        onHide={() => setShowCompareModal(false)}
        students={studentsToCompare}
      />
    </Container>
  );
};

export default Students;