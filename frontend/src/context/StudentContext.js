import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';
import { getStudents as fetchStudentsFromApi } from '../api';
import { validateRiskScore } from '../utils/riskScoreValidator';

const StudentContext = createContext();

export const useStudentData = () => useContext(StudentContext);

export const StudentProvider = ({ children }) => {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [totalStudents, setTotalStudents] = useState(0);

  const loadStudents = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Backend returns students pre-computed with risk scores and features
      const fetchedStudents = await fetchStudentsFromApi(2000);
      setTotalStudents(fetchedStudents.length);

      // Validate risk scores
      const studentsWithData = fetchedStudents.map(student => ({
        ...student,
        risk_score: validateRiskScore(student.risk_score, 50),
      }));

      setStudents(studentsWithData);
    } catch (err) {
      setError('Failed to fetch student data: ' + err.message);
      console.error('Error loading students:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStudents();
  }, [loadStudents]);

  const refreshStudents = useCallback(() => {
    loadStudents();
  }, [loadStudents]);

  const value = {
    students,
    loading,
    error,
    totalStudents,
    refreshStudents,
  };

  return (
    <StudentContext.Provider value={value}>
      {children}
    </StudentContext.Provider>
  );
};
