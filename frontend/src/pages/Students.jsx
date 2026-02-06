import React, { useState, useMemo } from 'react';
import { Form, Row, Col, Button, InputGroup, Badge } from 'react-bootstrap';
import { FaSearch, FaFilter, FaExchangeAlt, FaUserGraduate, FaExclamationTriangle, FaTimes, FaEnvelope, FaDownload, FaClipboardList } from 'react-icons/fa';
import { motion } from 'framer-motion';
import ComparisonModal from '../components/common/ComparisonModal';
import RiskTable from '../components/dashboard/RiskTable';
import StudentDrawer from '../components/student/StudentDrawer';
import Skeleton from '../components/common/Skeleton';
import { useStudentData } from '../context/StudentContext';
import { variants } from '../utils/motionConfig';

const Students = () => {
  const { students, loading, error } = useStudentData();
  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [selectedStudents, setSelectedStudents] = useState([]);
  const [showCompareModal, setShowCompareModal] = useState(false);

  // Advanced filters
  const [gpaRange, setGpaRange] = useState([0, 4.0]);
  const [attendanceRange, setAttendanceRange] = useState([0, 100]);
  const [courseFilter, setCourseFilter] = useState('all');

  // Student drawer
  const [showDrawer, setShowDrawer] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  const filteredStudents = useMemo(() => {
    return students
      .filter(student => {
        const riskScore = Number(student.risk_score);
        if (riskFilter === 'all') return true;
        if (riskFilter === 'high') return riskScore > 75;
        if (riskFilter === 'medium') return riskScore > 50 && riskScore <= 75;
        if (riskFilter === 'low') return riskScore > 25 && riskScore <= 50;
        if (riskFilter === 'very-low') return riskScore <= 25;
        return true;
      })
      .filter(student => {
        // GPA filter
        const gpa = student.gpa || 2.5;
        if (gpa < gpaRange[0] || gpa > gpaRange[1]) return false;

        // Attendance filter
        const attendance = student.attendance || Math.floor(Math.random() * 100);
        if (attendance < attendanceRange[0] || attendance > attendanceRange[1]) return false;

        return true;
      })
      .filter(student =>
        student.id.toLowerCase().includes(searchTerm.toLowerCase())
      );
  }, [students, searchTerm, riskFilter, gpaRange, attendanceRange]);

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

  const handleStudentClick = (student) => {
    setSelectedStudent(student);
    setShowDrawer(true);
  };

  const studentsToCompare = useMemo(() => {
    return students.filter(s => selectedStudents.includes(s.id));
  }, [students, selectedStudents]);

  // Paginated students
  const paginatedStudents = useMemo(() => {
    const startIndex = (currentPage - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return filteredStudents.slice(startIndex, endIndex);
  }, [filteredStudents, currentPage, pageSize]);

  const totalPages = Math.ceil(filteredStudents.length / pageSize);

  const handlePageSizeChange = (newSize) => {
    setPageSize(newSize);
    setCurrentPage(1); // Reset to first page when changing page size
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  const hasActiveFilters = gpaRange[0] !== 0 || gpaRange[1] !== 4.0 ||
    attendanceRange[0] !== 0 || attendanceRange[1] !== 100 ||
    courseFilter !== 'all' || riskFilter !== 'all';

  const clearAllFilters = () => {
    setSearchTerm('');
    setRiskFilter('all');
    setGpaRange([0, 4.0]);
    setAttendanceRange([0, 100]);
    setCourseFilter('all');
  };

  if (error) {
    return (
      <div className="alert alert-danger d-flex align-items-center gap-3 shadow-sm rounded-3">
        <FaExclamationTriangle size={20} />
        <div>
          <h6 className="alert-heading fw-bold mb-1">Error Loading Data</h6>
          <p className="mb-0">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={variants.container}
      className="pb-5"
    >
      <div className="d-flex justify-content-between align-items-end mb-4">
        <div>
          <h1 className="display-5 fw-bold text-gradient mb-2">Students</h1>
          <p className="text-secondary fs-5 mb-0" style={{ maxWidth: '600px' }}>
            Browse, filter, and compare student risk profiles across your cohort.
          </p>
        </div>
        <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
          <Button
            variant="primary"
            disabled={selectedStudents.length < 2}
            onClick={() => setShowCompareModal(true)}
            className="d-flex align-items-center gap-2 shadow-lg px-4 py-2 rounded-pill"
          >
            <FaExchangeAlt /> <span>Compare ({selectedStudents.length})</span>
          </Button>
        </motion.div>
      </div>

      {/* Bulk Actions Toolbar */}
      {selectedStudents.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel p-3 mb-3 d-flex justify-content-between align-items-center"
        >
          <div className="d-flex align-items-center gap-2">
            <Badge bg="primary" className="px-3 py-2">
              ✓ {selectedStudents.length} student{selectedStudents.length !== 1 ? 's' : ''} selected
            </Badge>
          </div>
          <div className="d-flex gap-2">
            <Button variant="primary" size="sm" className="d-flex align-items-center gap-2">
              <FaClipboardList /> Assign Intervention
            </Button>
            <Button variant="outline-secondary" size="sm" className="d-flex align-items-center gap-2">
              <FaEnvelope /> Send Email
            </Button>
            <Button variant="outline-secondary" size="sm" className="d-flex align-items-center gap-2">
              <FaDownload /> Export Selection
            </Button>
            <Button variant="outline-secondary" size="sm" onClick={() => setSelectedStudents([])}>
              Clear Selection
            </Button>
          </div>
        </motion.div>
      )}

      <Row className="g-4 mb-4">
        {/* Advanced Filter Sidebar */}
        <Col lg={3}>
          <motion.div variants={variants.item} className="glass-panel p-4">
            <h6 className="mb-3 fw-semibold d-flex align-items-center gap-2">
              <FaFilter /> Advanced Filters
            </h6>

            {/* Search */}
            <Form.Group className="mb-3">
              <Form.Label className="small text-muted">Search</Form.Label>
              <Form.Control
                type="text"
                placeholder="Name or ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                size="sm"
              />
            </Form.Group>

            {/* Risk Level */}
            <Form.Group className="mb-3">
              <Form.Label className="small text-muted">Risk Level</Form.Label>
              <Form.Select
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value)}
                size="sm"
              >
                <option value="all">All Risk Levels</option>
                <option value="high">Critical/High (&gt;75)</option>
                <option value="medium">Medium (51-75)</option>
                <option value="low">Low (26-50)</option>
                <option value="very-low">Very Low (&lt;25)</option>
              </Form.Select>
            </Form.Group>

            {/* GPA Range */}
            <Form.Group className="mb-3">
              <Form.Label className="small text-muted">
                GPA Range: {gpaRange[0].toFixed(1)} - {gpaRange[1].toFixed(1)}
              </Form.Label>
              <div className="d-flex gap-2 mb-2">
                <Form.Control
                  type="number"
                  min="0"
                  max="4"
                  step="0.1"
                  value={gpaRange[0]}
                  onChange={(e) => setGpaRange([parseFloat(e.target.value), gpaRange[1]])}
                  size="sm"
                />
                <Form.Control
                  type="number"
                  min="0"
                  max="4"
                  step="0.1"
                  value={gpaRange[1]}
                  onChange={(e) => setGpaRange([gpaRange[0], parseFloat(e.target.value)])}
                  size="sm"
                />
              </div>
              <Form.Range
                min="0"
                max="4"
                step="0.1"
                value={gpaRange[1]}
                onChange={(e) => setGpaRange([gpaRange[0], parseFloat(e.target.value)])}
              />
            </Form.Group>

            {/* Attendance Range */}
            <Form.Group className="mb-3">
              <Form.Label className="small text-muted">
                Attendance: {attendanceRange[0]}% - {attendanceRange[1]}%
              </Form.Label>
              <div className="d-flex gap-2 mb-2">
                <Form.Control
                  type="number"
                  min="0"
                  max="100"
                  value={attendanceRange[0]}
                  onChange={(e) => setAttendanceRange([parseInt(e.target.value), attendanceRange[1]])}
                  size="sm"
                />
                <Form.Control
                  type="number"
                  min="0"
                  max="100"
                  value={attendanceRange[1]}
                  onChange={(e) => setAttendanceRange([attendanceRange[0], parseInt(e.target.value)])}
                  size="sm"
                />
              </div>
              <Form.Range
                min="0"
                max="100"
                value={attendanceRange[1]}
                onChange={(e) => setAttendanceRange([attendanceRange[0], parseInt(e.target.value)])}
              />
            </Form.Group>

            {/* Course Filter */}
            <Form.Group className="mb-3">
              <Form.Label className="small text-muted">Course</Form.Label>
              <Form.Select
                value={courseFilter}
                onChange={(e) => setCourseFilter(e.target.value)}
                size="sm"
              >
                <option value="all">All Courses</option>
                <option value="MATH-201">MATH-201</option>
                <option value="ENG-101">ENG-101</option>
                <option value="BIO-301">BIO-301</option>
                <option value="CS-101">CS-101</option>
              </Form.Select>
            </Form.Group>

            {hasActiveFilters && (
              <Button
                variant="outline-secondary"
                size="sm"
                className="w-100"
                onClick={clearAllFilters}
              >
                <FaTimes /> Clear All Filters
              </Button>
            )}
          </motion.div>
        </Col>

        {/* Students Table */}
        <Col lg={9}>
          {/* Active Filters Display */}
          {hasActiveFilters && (
            <div className="mb-3 d-flex flex-wrap gap-2">
              {riskFilter !== 'all' && (
                <Badge bg="secondary" className="d-flex align-items-center gap-2">
                  Risk: {riskFilter}
                  <FaTimes
                    style={{ cursor: 'pointer' }}
                    onClick={() => setRiskFilter('all')}
                  />
                </Badge>
              )}
              {(gpaRange[0] !== 0 || gpaRange[1] !== 4.0) && (
                <Badge bg="secondary" className="d-flex align-items-center gap-2">
                  GPA: {gpaRange[0].toFixed(1)}-{gpaRange[1].toFixed(1)}
                  <FaTimes
                    style={{ cursor: 'pointer' }}
                    onClick={() => setGpaRange([0, 4.0])}
                  />
                </Badge>
              )}
              {(attendanceRange[0] !== 0 || attendanceRange[1] !== 100) && (
                <Badge bg="secondary" className="d-flex align-items-center gap-2">
                  Attendance: {attendanceRange[0]}%-{attendanceRange[1]}%
                  <FaTimes
                    style={{ cursor: 'pointer' }}
                    onClick={() => setAttendanceRange([0, 100])}
                  />
                </Badge>
              )}
              {courseFilter !== 'all' && (
                <Badge bg="secondary" className="d-flex align-items-center gap-2">
                  Course: {courseFilter}
                  <FaTimes
                    style={{ cursor: 'pointer' }}
                    onClick={() => setCourseFilter('all')}
                  />
                </Badge>
              )}
              <Button
                variant="link"
                size="sm"
                className="p-0 text-decoration-none"
                onClick={clearAllFilters}
              >
                Clear All
              </Button>
            </div>
          )}

          <motion.div variants={variants.item} className="glass-panel p-4 overflow-hidden">
            {loading ? (
              <Skeleton type="table" count={10} />
            ) : filteredStudents.length > 0 ? (
              <>
                <RiskTable
                  students={paginatedStudents}
                  onSelectStudent={handleSelectStudent}
                  selectedStudents={selectedStudents}
                  onStudentClick={handleStudentClick}
                />

                {/* Pagination Controls */}
                <div className="d-flex justify-content-between align-items-center mt-4 pt-3 border-top" style={{ borderColor: 'var(--border-color)' }}>
                  <div className="d-flex align-items-center gap-3">
                    <small className="text-muted">
                      Showing {((currentPage - 1) * pageSize) + 1}-{Math.min(currentPage * pageSize, filteredStudents.length)} of {filteredStudents.length} students
                    </small>
                    <div className="d-flex align-items-center gap-2">
                      <small className="text-muted">Per page:</small>
                      <Form.Select
                        size="sm"
                        value={pageSize}
                        onChange={(e) => handlePageSizeChange(parseInt(e.target.value))}
                        style={{ width: 'auto' }}
                      >
                        <option value="25">25</option>
                        <option value="50">50</option>
                        <option value="100">100</option>
                        <option value="200">200</option>
                      </Form.Select>
                    </div>
                  </div>

                  <div className="d-flex gap-2">
                    <Button
                      variant="outline-secondary"
                      size="sm"
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1}
                    >
                      ← Previous
                    </Button>

                    {/* Page numbers */}
                    <div className="d-flex align-items-center gap-1">
                      {currentPage > 2 && (
                        <>
                          <Button
                            variant="outline-secondary"
                            size="sm"
                            onClick={() => handlePageChange(1)}
                          >
                            1
                          </Button>
                          {currentPage > 3 && <span className="text-muted">...</span>}
                        </>
                      )}

                      {currentPage > 1 && (
                        <Button
                          variant="outline-secondary"
                          size="sm"
                          onClick={() => handlePageChange(currentPage - 1)}
                        >
                          {currentPage - 1}
                        </Button>
                      )}

                      <Button variant="primary" size="sm" disabled>
                        {currentPage}
                      </Button>

                      {currentPage < totalPages && (
                        <Button
                          variant="outline-secondary"
                          size="sm"
                          onClick={() => handlePageChange(currentPage + 1)}
                        >
                          {currentPage + 1}
                        </Button>
                      )}

                      {currentPage < totalPages - 1 && (
                        <>
                          {currentPage < totalPages - 2 && <span className="text-muted">...</span>}
                          <Button
                            variant="outline-secondary"
                            size="sm"
                            onClick={() => handlePageChange(totalPages)}
                          >
                            {totalPages}
                          </Button>
                        </>
                      )}
                    </div>

                    <Button
                      variant="outline-secondary"
                      size="sm"
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === totalPages}
                    >
                      Next →
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <div className="text-center my-5 py-5 d-flex flex-column align-items-center">
                <div className="bg-surface-hover p-4 rounded-circle mb-3">
                  <FaUserGraduate size={32} className="text-muted opacity-50" />
                </div>
                <h3 className="text-muted mb-2">No students found</h3>
                <p className="text-muted mb-4">No results match your current filters.</p>
                <Button variant="outline-primary" onClick={clearAllFilters} className="rounded-pill px-4">
                  Clear All Filters
                </Button>
              </div>
            )}
          </motion.div>
        </Col>
      </Row>

      <ComparisonModal
        show={showCompareModal}
        onHide={() => setShowCompareModal(false)}
        students={studentsToCompare}
      />

      <StudentDrawer
        show={showDrawer}
        onHide={() => setShowDrawer(false)}
        student={selectedStudent}
      />
    </motion.div>
  );
};

export default Students;