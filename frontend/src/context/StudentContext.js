import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';
import { getStudentList } from '../services/api';
import { validateRiskScore } from '../utils/riskScoreValidator';

const StudentContext = createContext();

export const useStudentData = () => useContext(StudentContext);

const parseStudentCsv = (csvText) => {
  const lines = (csvText || '').split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) return [];

  const headers = lines[0].split(',').map((h) => h.trim());
  const idx = {
    id: headers.findIndex((h) => h.toLowerCase() === 'id'),
    absrate1: headers.findIndex((h) => h.toLowerCase() === 'absrate1'),
    q1mpa1: headers.findIndex((h) => h.toLowerCase() === 'q1mpa1'),
  };

  const rows = [];
  for (let i = 1; i < lines.length; i += 1) {
    const cols = lines[i].split(',').map((c) => c.trim());
    if (!cols[idx.id]) continue;

    const id = cols[idx.id];
    const attendance = Number(cols[idx.absrate1] || 0);
    const quiz = Number(cols[idx.q1mpa1] || 0);
    const risk = validateRiskScore(100 - attendance, 50);

    rows.push({
      id,
      name: id,
      risk_score: risk,
      graded_quiz_score: Number.isFinite(quiz) ? quiz : 0,
      exam_attendance_rate: Number.isFinite(attendance) ? Math.max(0, Math.min(100, 100 - attendance)) : 0,
      engagement_score: 0,
      risk_label: risk >= 70 ? 'High Risk' : risk >= 40 ? 'Medium' : 'Low Risk',
    });
  }
  return rows;
};

const tryLoadLocalFallback = async () => {
  const res = await fetch('/data/student_data_test.csv');
  if (!res.ok) {
    throw new Error(`Local fallback file load failed (${res.status})`);
  }
  const csvText = await res.text();
  const parsed = parseStudentCsv(csvText);
  console.log('[StudentContext] local CSV fallback rows:', parsed.length);
  return parsed;
};

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
      console.log('[StudentContext] getStudentList raw response:', response);

      if (!response.success || !Array.isArray(response.data?.students)) {
        throw new Error(response.message || 'Failed to load students');
      }

      const fetchedStudents = response.data.students;
      if (fetchedStudents.length === 0) {
        throw new Error('API returned empty students array');
      }
      setTotalStudents(response.data.total || fetchedStudents.length);

      const studentsWithData = fetchedStudents.map(student => ({
        ...student,
        name: student.name || student.id,
        risk_score: validateRiskScore(student.risk_score, 50),
      }));

      console.log('[StudentContext] normalized students count:', studentsWithData.length);
      setStudents(studentsWithData);
    } catch (err) {
      console.error('Error loading students from API, trying local fallback:', err);
      try {
        const fallbackStudents = await tryLoadLocalFallback();
        setStudents(fallbackStudents);
        setTotalStudents(fallbackStudents.length);
        setError(null);
      } catch (fallbackErr) {
        setError('Failed to fetch student data: ' + err.message);
        console.error('Local fallback also failed:', fallbackErr);
      }
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
