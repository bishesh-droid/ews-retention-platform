import React, { useState, useEffect } from 'react';
import { Container } from 'react-bootstrap';
import Recommendations from '../components/Recommendations';
import { getStudents, getPredictions } from '../api';

const Insights = () => {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [studentsData, predictionsData] = await Promise.all([
          getStudents(),
          getPredictions(),
        ]);

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

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div>Error: {error}</div>;
  }

  return (
    <Container>
      <h1 className="my-4">Insights</h1>
      <Recommendations students={students} />
    </Container>
  );
};

export default Insights;