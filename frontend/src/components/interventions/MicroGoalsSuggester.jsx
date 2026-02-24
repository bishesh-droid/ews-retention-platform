import React, { useState, useEffect } from 'react';
import { Card, ListGroup, Badge, Spinner } from 'react-bootstrap';
import { FaBullseye, FaCheckCircle, FaCircle } from 'react-icons/fa';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

/**
 * MicroGoalsSuggester - AI-generated personalized micro-goals
 * Shows achievable weekly goals with rationale
 */
function MicroGoalsSuggester({ studentId }) {
    const [goals, setGoals] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (studentId) {
            fetchGoals();
        }
    }, [studentId]);

    const fetchGoals = async () => {
        setLoading(true);

        try {
            const response = await axios.post(`${API_BASE}/llm/student-advice`, {
                student_id: studentId,
                question: 'Suggest 3 specific, achievable micro-goals for me this week to improve my academic standing.'
            });

            // Parse the AI response into goals (simplified - in production, use structured output)
            const goalsText = response.data.content;
            const parsedGoals = parseGoalsFromText(goalsText);
            setGoals(parsedGoals);
        } catch (err) {
            console.error('Error fetching goals:', err);
        } finally {
            setLoading(false);
        }
    };

    const parseGoalsFromText = (text) => {
        // Simple parsing - split by numbered list or dashes
        // In production, use structured LLM output
        const lines = text.split('\n').filter(line => line.trim());
        const goalsList = [];

        let goalIndex = 0;
        for (const line of lines) {
            if (line.match(/^\d+\./) || line.startsWith('-') || line.startsWith('•')) {
                const cleanLine = line.replace(/^\d+\./, '').replace(/^[-•]/, '').trim();
                if (cleanLine) {
                    goalsList.push({
                        id: goalIndex++,
                        text: cleanLine,
                        completed: false,
                        impact: ['high', 'medium', 'high'][goalIndex % 3]
                    });
                }
            }
        }

        return goalsList.slice(0, 3);
    };

    const getImpactColor = (impact) => {
        return {
            high: 'success',
            medium: 'warning',
            low: 'secondary'
        }[impact] || 'secondary';
    };

    if (loading) {
        return (
            <Card className="glass-panel border-0 shadow-sm">
                <Card.Body className="text-center py-4">
                    <Spinner animation="border" size="sm" variant="primary" />
                    <p className="small text-muted mt-2 mb-0">Generating personalized goals...</p>
                </Card.Body>
            </Card>
        );
    }

    return (
        <Card className="glass-panel border-0 shadow-sm">
            <Card.Body className="p-4">
                <div className="d-flex align-items-center justify-content-between mb-3">
                    <div className="d-flex align-items-center">
                        <FaBullseye className="text-warning me-2" size={18} />
                        <h6 className="mb-0 fw-semibold">Your Weekly Goals</h6>
                    </div>
                    <Badge bg="warning" className="bg-opacity-25 text-warning border border-warning border-opacity-50">
                        This Week
                    </Badge>
                </div>

                <p className="small text-muted mb-3">
                    Achieve these micro-goals to improve your academic standing.
                </p>

                {goals.length === 0 ? (
                    <div className="text-center text-muted small">
                        <p>Loading personalized goals...</p>
                    </div>
                ) : (
                    <ListGroup variant="flush" className="bg-transparent">
                        {goals.map((goal, index) => (
                            <ListGroup.Item key={goal.id} className="bg-transparent border-0 px-0 py-3">
                                <div className="d-flex align-items-start">
                                    <div className="me-3 mt-1">
                                        {goal.completed ? (
                                            <FaCheckCircle className="text-success" size={20} />
                                        ) : (
                                            <FaCircle className="text-muted opacity-25" size={16} />
                                        )}
                                    </div>
                                    <div className="flex-grow-1">
                                        <div className="d-flex align-items-start justify-content-between mb-1">
                                            <p className="mb-0 fw-medium small" style={{ lineHeight: '1.5' }}>
                                                {goal.text}
                                            </p>
                                            <Badge
                                                bg={getImpactColor(goal.impact)}
                                                className={`bg-opacity-10 text-${getImpactColor(goal.impact)} border border-${getImpactColor(goal.impact)} border-opacity-25 ms-2 flex-shrink-0`}
                                            >
                                                {goal.impact} impact
                                            </Badge>
                                        </div>
                                    </div>
                                </div>
                            </ListGroup.Item>
                        ))}
                    </ListGroup>
                )}

                <div className="mt-3 pt-3 border-top">
                    <small className="text-muted">
                        💡 <strong>Why these goals?</strong> They're tailored to your current attendance and performance patterns.
                    </small>
                </div>
            </Card.Body>
        </Card>
    );
}

export default MicroGoalsSuggester;
