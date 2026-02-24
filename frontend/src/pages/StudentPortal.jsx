import React, { useState, useEffect } from 'react';
import { Row, Col, Container } from 'react-bootstrap';
import { motion } from 'framer-motion';
import StudentHealthScore from '../components/student/StudentHealthScore';
import WeeklyProgressBrief from '../components/ai/WeeklyProgressBrief';
import RiskChangeExplainer from '../components/ai/RiskChangeExplainer';
import WhatIfSimulatorPanel from '../components/ai/WhatIfSimulator';
import MicroGoalsSuggester from '../components/interventions/MicroGoalsSuggester';
import MicroGoalsStreaks from '../components/interventions/MicroGoalsStreaks';

/**
 * Student Portal Page - Enhanced with LLM Intelligence
 * 
 * Student-facing dashboard with empowering, personalized AI features
 * NEW: Risk explanations, what-if simulator, AI-generated micro-goals
 */

const StudentPortal = () => {
    const [studentData, setStudentData] = useState(null);
    const [weekData, setWeekData] = useState(null);

    useEffect(() => {
        fetchStudentData();
    }, []);

    const fetchStudentData = async () => {
        // Mock student data - replace with actual API call
        setStudentData({
            id: '1001',  // Use actual student ID from auth
            name: 'Alex Johnson',
            dropout_risk: 0.25,
            engagement_score: 75,
            performance_score: 82,
            attendance_score: 90,
            historical_scores: [65, 70, 75],
            risk_score: 45,
            attendance: 90,
            grades: 3.2
        });

        setWeekData({
            assignmentsCompleted: 4,
            attendanceRate: 0.95,
            engagementImprovement: 8,
            missedAssignments: 1,
            lowEngagementDays: 1,
            totalStudyTimeMinutes: 580,
            facultyInteractions: 3,
            resourcesViewed: 12
        });
    };

    const handleRunSimulation = (scenarios) => {
        return Promise.resolve({
            newScore: 85,
            delta: 10,
            confidence: 0.87
        });
    };

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.3 }}
        >
            <Container fluid className="py-4" style={{ maxWidth: '1400px' }}>
                {/* Page Header */}
                <div className="mb-4">
                    <h1 className="display-5 fw-bold text-gradient mb-2">
                        Welcome Back, {studentData?.name || 'Student'}!
                    </h1>
                    <p className="text-secondary fs-5">
                        Track your progress, understand your risk factors, and explore how your choices impact your success.
                    </p>
                </div>

                {/* Main Content Grid */}
                <Row className="g-4">
                    {/* Left Column - 2/3 width */}
                    <Col lg={8}>
                        <div className="d-flex flex-column gap-4">
                            {/* Student Health Score */}
                            <StudentHealthScore studentData={studentData} />

                            {/* NEW: AI Risk Explanation */}
                            {studentData && (
                                <RiskChangeExplainer studentId={studentData.id} />
                            )}

                            {/* NEW: What-If Simulator with AI */}
                            {studentData && (
                                <WhatIfSimulatorPanel
                                    studentId={studentData.id}
                                    currentMetrics={{
                                        attendance: studentData.attendance_score,
                                        grades: studentData.grades,
                                        risk_score: studentData.risk_score
                                    }}
                                />
                            )}
                        </div>
                    </Col>

                    {/* Right Column - 1/3 width */}
                    <Col lg={4}>
                        <div className="d-flex flex-column gap-4">
                            {/* Weekly Progress Brief */}
                            <WeeklyProgressBrief
                                weekData={weekData}
                                studentName={studentData?.name}
                            />

                            {/* NEW: AI-Generated Micro Goals */}
                            {studentData && (
                                <MicroGoalsSuggester studentId={studentData.id} />
                            )}

                            {/* Micro Goals Streaks */}
                            <MicroGoalsStreaks />
                        </div>
                    </Col>
                </Row>

                {/* AI Attribution Footer */}
                <div className="mt-5 pt-4 border-top text-center">
                    <small className="text-muted">
                        🤖 Powered by AI-driven insights based on your real academic data
                    </small>
                </div>
            </Container>
        </motion.div>
    );
};

export default StudentPortal;

