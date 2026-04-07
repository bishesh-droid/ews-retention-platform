import React, { useState, useMemo, useEffect } from 'react';
import { Form, Row, Col, Button, InputGroup, Badge } from 'react-bootstrap';
import { FaSearch, FaFilter, FaExchangeAlt, FaUserGraduate, FaExclamationTriangle, FaTimes, FaEnvelope, FaDownload, FaClipboardList } from 'react-icons/fa';
import { motion } from 'framer-motion';
import ComparisonModal from '../components/common/ComparisonModal';
import RiskTable from '../components/dashboard/RiskTable';
import StudentDrawer from '../components/student/StudentDrawer';
import Skeleton from '../components/common/Skeleton';
import { variants } from '../utils/motionConfig';
import useDebounce from '../hooks/useDebounce';
import { getStudentList } from '../services/api';

const Students = () => {
  const [students, setStudents] = useState([]);
  const [totalStudents, setTotalStudents] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [selectedStudents, setSelectedStudents] = useState([]);
  const [showCompareModal, setShowCompareModal] = useState(false);

  // Advanced filters
  const [quizScoreRange, setQuizScoreRange] = useState([0, 100]);
  const [attendanceRange, setAttendanceRange] = useState([0, 100]);
  const [departmentFilter, setDepartmentFilter] = useState('all');

  // Student drawer
  const [showDrawer, setShowDrawer] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);

  // Pagination (server-side)
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [sortConfig, setSortConfig] = useState({ key: 'risk_score', direction: 'descending' });

  // Fetch students from backend when page or page size changes
  useEffect(() => {
    let isMounted = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      const sortBy = sortConfig.key || 'risk_score';
      const order = sortConfig.direction === 'ascending' ? 'asc' : 'desc';
      const response = await getStudentList(currentPage, pageSize, sortBy, order);
      if (!isMounted) return;
      if (response.success && response.data) {
        const { students: pageStudents = [], total = 0 } = response.data;
        const normalizedStudents = pageStudents.map((student) => {
          const first = (student.first_name || '').trim();
          const last = (student.last_name || '').trim();
          const fullName = `${first} ${last}`.trim();
          return {
            ...student,
            // Keep a stable display name for table/search.
            name: student.name || fullName || student.id,
          };
        });
        setStudents(normalizedStudents);
        setTotalStudents(total || pageStudents.length);
      } else {
        setError(response.message || 'Failed to load students');
        setStudents([]);
        setTotalStudents(0);
      }
      setLoading(false);
    };
    load();
    return () => {
      isMounted = false;
    };
  }, [currentPage, pageSize, sortConfig]);

  const departments = useMemo(() => {
    const depts = new Set(students.map(s => s.department).filter(Boolean));
    return [...depts].sort();
  }, [students]);

  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  const filteredStudents = useMemo(() => {
    const term = debouncedSearchTerm.toLowerCase();
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
        // Quiz score filter
        const quizScore = student.graded_quiz_score ?? 0;
        if (quizScore < quizScoreRange[0] || quizScore > quizScoreRange[1]) return false;

        // Attendance filter
        const attendance = student.exam_attendance_rate ?? 0;
        if (attendance < attendanceRange[0] || attendance > attendanceRange[1]) return false;

        // Department filter
        if (departmentFilter !== 'all' && student.department !== departmentFilter) return false;

        return true;
      })
      .filter(student => {
        if (!term) return true;
        const name = (student.name || '').toLowerCase();
        const id = (student.id || '').toLowerCase();
        return name.includes(term) || id.includes(term);
      });
  }, [students, searchTerm, riskFilter, quizScoreRange, attendanceRange, departmentFilter]);

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

  // Server-side pagination: filteredStudents already represent current page
  const paginatedStudents = filteredStudents;

  const totalPages = Math.max(1, Math.ceil((totalStudents || 0) / pageSize));

  const handlePageSizeChange = (newSize) => {
    setPageSize(newSize);
    setCurrentPage(1); // Reset to first page when changing page size
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setCurrentPage(newPage);
    }
  };

  const hasActiveFilters = quizScoreRange[0] !== 0 || quizScoreRange[1] !== 100 ||
    attendanceRange[0] !== 0 || attendanceRange[1] !== 100 ||
    departmentFilter !== 'all' || riskFilter !== 'all';

  const clearAllFilters = () => {
    setSearchTerm('');
    setRiskFilter('all');
    setQuizScoreRange([0, 100]);
    setAttendanceRange([0, 100]);
    setDepartmentFilter('all');
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
        <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
          <button
            onClick={() => setShowCompareModal(true)}
            className="d-flex align-items-center gap-2 px-4 py-2 rounded-pill"
            style={{
              backgroundColor: selectedStudents.length >= 2 ? '#7C3AED' : 'rgba(139,92,246,0.25)',
              color: selectedStudents.length >= 2 ? '#fff' : '#A78BFA',
              border: '1px solid rgba(139,92,246,0.5)',
              fontWeight: 600,
              fontSize: '14px',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
          >
            <FaExchangeAlt />
            <span>Compare ({selectedStudents.length})</span>
          </button>
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
            <h6 className="mb-3 fw-semibold d-flex align-items-center gap-2" style={{ color: '#C4B5FD' }}>
              <FaFilter /> Advanced Filters
            </h6>

            {/* Search */}
            <Form.Group className="mb-3">
              <Form.Label className="small" style={{ color: '#C4B5FD' }}>Search</Form.Label>
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
              <Form.Label className="small" style={{ color: '#C4B5FD' }}>Risk Level</Form.Label>
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

            {/* Quiz Score Range */}
            <Form.Group className="mb-3">
              <Form.Label className="small" style={{ color: '#C4B5FD' }}>
                Quiz Score: {quizScoreRange[0]} – {quizScoreRange[1]}
              </Form.Label>
              <div className="d-flex gap-2 mb-2">
                <Form.Control
                  type="number"
                  min="0"
                  max="100"
                  value={quizScoreRange[0]}
                  onChange={(e) => setQuizScoreRange([parseInt(e.target.value), quizScoreRange[1]])}
                  size="sm"
                />
                <Form.Control
                  type="number"
                  min="0"
                  max="100"
                  value={quizScoreRange[1]}
                  onChange={(e) => setQuizScoreRange([quizScoreRange[0], parseInt(e.target.value)])}
                  size="sm"
                />
              </div>
              <Form.Range
                min="0"
                max="100"
                value={quizScoreRange[1]}
                onChange={(e) => setQuizScoreRange([quizScoreRange[0], parseInt(e.target.value)])}
              />
            </Form.Group>

            {/* Attendance Range */}
            <Form.Group className="mb-3">
              <Form.Label className="small" style={{ color: '#C4B5FD' }}>
                Attendance: {attendanceRange[0]}% – {attendanceRange[1]}%
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

            {/* Department Filter */}
            <Form.Group className="mb-3">
              <Form.Label className="small" style={{ color: '#C4B5FD' }}>Department</Form.Label>
              <Form.Select
                value={departmentFilter}
                onChange={(e) => setDepartmentFilter(e.target.value)}
                size="sm"
              >
                <option value="all">All Departments</option>
                {departments.map(dept => (
                  <option key={dept} value={dept}>{dept}</option>
                ))}
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
              {(quizScoreRange[0] !== 0 || quizScoreRange[1] !== 100) && (
                <Badge bg="secondary" className="d-flex align-items-center gap-2">
                  Quiz Score: {quizScoreRange[0]}-{quizScoreRange[1]}
                  <FaTimes
                    style={{ cursor: 'pointer' }}
                    onClick={() => setQuizScoreRange([0, 100])}
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
              {departmentFilter !== 'all' && (
                <Badge bg="secondary" className="d-flex align-items-center gap-2">
                  Dept: {departmentFilter}
                  <FaTimes
                    style={{ cursor: 'pointer' }}
                    onClick={() => setDepartmentFilter('all')}
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
                  sortConfig={sortConfig}
                  onSortChange={setSortConfig}
                />

                {/* Pagination Controls */}
                <div className="d-flex justify-content-between align-items-center mt-4 pt-3 border-top" style={{ borderColor: 'var(--border-color)' }}>
                  <div className="d-flex align-items-center gap-3">
                      <small className="text-muted">
                        Showing {((currentPage - 1) * pageSize) + 1}-{((currentPage - 1) * pageSize) + paginatedStudents.length} of {totalStudents || paginatedStudents.length} students
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