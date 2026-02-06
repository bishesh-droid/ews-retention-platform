import React from 'react';
import { Container } from 'react-bootstrap';
import { FaLightbulb } from 'react-icons/fa';
import { motion } from 'framer-motion';
import Recommendations from '../components/interventions/Recommendations';
import { useStudentData } from '../context/StudentContext'; // Import the context hook
import Skeleton from '../components/common/Skeleton';

const Insights = () => {
  const { students, loading, error } = useStudentData(); // Get data from context

  if (loading) {
    return (
      <Container className="page-container">
        <h1 className="h3 mb-4"><FaLightbulb className="me-2 text-warning" />AI Insights</h1>
        <Skeleton type="list" count={5} />
      </Container>
    );
  }

  if (error) {
    return <div className="alert alert-danger m-4">{error}</div>;
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.5 }}
    >
      <div className="mb-4">
        <h1 className="h3 mb-0 text-gradient"><FaLightbulb className="me-2 text-warning" />AI Insights</h1>
        <p className="text-muted">Automated recommendations ensuring student success.</p>
      </div>

      <div className="glass-panel p-4">
        <Recommendations students={students} />
      </div>
    </motion.div>
  );
};

export default Insights;