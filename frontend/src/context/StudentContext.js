import React, { createContext, useState, useEffect, useContext } from 'react';
import { getStudents, getPredictions } from '../api';
import Spinner from '../components/Spinner';

const StudentContext = createContext();

export const useStudentData = () => useContext(StudentContext);

export const StudentProvider = ({ children }) => {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        // In a real-world scenario with large datasets, the API should handle
        // joining and paginating data. The client would fetch pages as needed.
        const [studentsData, predictionsData] = await Promise.all([
          getStudents(),
          getPredictions(),
        ]);

        // The client-side join is a performance bottleneck for large datasets.
        // This should be moved to the backend.
        const combinedData = studentsData.map(student => {
          const prediction = predictionsData.find(p => p.student_id === student.id);
          return { ...student, ...prediction };
        });

        setStudents(combinedData);
      } catch (err) {
        setError('Failed to fetch student data.');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const value = {
    students,
    loading,
    error,
  };

  return (
    <StudentContext.Provider value={value}>
      {loading ? <Spinner /> : error ? <div className="alert alert-danger">{error}</div> : children}
    </StudentContext.Provider>
  );
};
