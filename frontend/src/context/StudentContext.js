import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';
import { getStudentList } from '../services/api';
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

      const response = await getStudentList(1, 2000, 'risk_score', 'desc');
      if (!response.success || !Array.isArray(response.data?.items)) {
        throw new Error(response.message || 'Failed to load students');
      }

      const fetchedStudents = response.data.items;
      setTotalStudents(response.data.total || fetchedStudents.length);

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
