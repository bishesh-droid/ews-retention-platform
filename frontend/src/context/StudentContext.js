import React, { createContext, useState, useEffect, useContext, useCallback } from 'react';
import { getStudents as fetchStudentsFromApi, getBatchPredictions } from '../api';
import { validateRiskScore, isValidPrediction, getSafeDefaultPrediction, sanitizePrediction } from '../utils/riskScoreValidator';
import Spinner from '../components/common/Spinner';

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

      // Fetch all students and predictions in parallel
      const [fetchedStudents, predictions] = await Promise.all([
        fetchStudentsFromApi(1500),
        getBatchPredictions(1500)
      ]);

      setTotalStudents(fetchedStudents.length);

      // Merge students with their predictions
      const studentsWithPredictions = fetchedStudents.map((student) => {
        let prediction = predictions[student.id];

        // If prediction is missing or invalid, use safe default
        if (!prediction || !isValidPrediction(prediction)) {
          console.warn(`Missing or invalid prediction for student ${student.id}, using safe default`);
          prediction = getSafeDefaultPrediction();
        } else {
          // Sanitize prediction to ensure all values are valid
          prediction = sanitizePrediction(prediction);
        }

        // Ensure risk_score is in valid range
        const riskScore = validateRiskScore(prediction.risk_score, 50);

        return {
          ...student,
          ...prediction,
          risk_score: riskScore  // Override with validated value
        };
      });

      setStudents(studentsWithPredictions);
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

  // Function to refresh student data
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