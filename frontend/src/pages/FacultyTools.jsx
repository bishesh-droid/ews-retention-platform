import React, { useState, useEffect } from 'react';
import { Row, Col, Container } from 'react-bootstrap';
import { motion } from 'framer-motion';
import ExplainableRiskNarrative from '../components/ai/ExplainableRiskNarrative';
import StudentsLikeThis from '../components/student/StudentsLikeThis';
import InterventionEffectiveness from '../components/interventions/InterventionEffectiveness';
import VolatilityScore from '../components/student/VolatilityScore';
import FacultyAnnotations from '../components/common/FacultyAnnotations';
import AIStudentSummary from '../components/ai/AIStudentSummary';
import PriorityQueuePanel from '../components/dashboard/PriorityQueuePanel';

/**
 * Faculty Tools Page - Enhanced with AI Decision Support
 * 
 * Faculty decision support interface with AI-powered analytical insights
 * NEW: AI student summaries, priority queue, intervention suggestions
 */

const FacultyTools = () => {
    const [selectedStudent, setSelectedStudent] = useState(null);
    const [riskFactors, setRiskFactors] = useState([]);

    useEffect(() => {
        // Mock data - replace with actual API
        setSelectedStudent({
            id: '1001',
            name: 'Alex Johnson',
            dropout_risk: 0.68,
            riskCategory: 'high'
        });

        setRiskFactors([
            { factor: 'attendance', importance: 0.42, value: 65 },
            { factor: 'assignment_completion', importance: 0.28, value: 58 },
            { factor: 'engagement_decline', importance: 0.18, value: -22 },
            { factor: 'peer_interaction', importance: 0.12, value: 35 }
        ]);
    }, []);

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
        >
            <Container fluid className="py-4" style={{ maxWidth: '1600px' }}>
                {/* Page Header */}
                <div className="mb-4">
                    <h1 className="display-5 fw-bold text-gradient mb-2">
                        Faculty Decision Support
                    </h1>
                    <p className="text-secondary fs-5">
                        AI-powered insights to help you understand student needs, prioritize interventions, and save time.
                    </p>
                </div>

                <Row className="g-4">
                    {/* Left Column - 2/3 */}
                    <Col lg={8}>
                        <Row className="g-4 mb-4">
                            {/* AI Summary and Risk Narrative */}
                            <Col md={6}>
                                {selectedStudent && (
                                    <AIStudentSummary
                                        studentId={selectedStudent.id}
                                        riskCategory={selectedStudent.riskCategory}
                                    />
                                )}
                            </Col>
                            <Col md={6}>
                                <VolatilityScore studentId={selectedStudent?.id} />
                            </Col>
                        </Row>

                        {/* Explainable Risk */}
                        <div className="mb-4">
                            <ExplainableRiskNarrative
                                studentData={selectedStudent}
                                riskFactors={riskFactors}
                            />
                        </div>

                        {/* Similar Students */}
                        <div className="mb-4">
                            <StudentsLikeThis currentStudent={selectedStudent} />
                        </div>

                        {/* Faculty Annotations */}
                        <FacultyAnnotations studentId={selectedStudent?.id} />
                    </Col>

                    {/* Right Column -1/3 */}
                    <Col lg={4}>
                        {/* NEW: AI Priority Queue */}
                        <PriorityQueuePanel limit={10} />
                    </Col>
                </Row>

                {/* Intervention Effectiveness - Full Width */}
                <Row className="mt-4">
                    <Col>
                        <InterventionEffectiveness />
                    </Col>
                </Row>

                {/* AI Attribution */}
                <div className="mt-5 pt-4 border-top text-center">
                    <small className="text-muted">
                        🤖 AI-powered prioritization and summaries save you 5-10 minutes per student
                    </small>
                </div>
            </Container>
        </motion.div>
    );
};

export default FacultyTools;

