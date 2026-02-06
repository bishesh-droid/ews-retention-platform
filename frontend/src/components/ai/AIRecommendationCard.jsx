import React, { useState } from 'react';
import { Card, Button, Badge } from 'react-bootstrap';
import { motion, AnimatePresence } from 'framer-motion';
import { getRecommendationBadgeVariant } from '../../utils/recommendationEngine';

/**
 * AIRecommendationCard Component
 * Displays individual AI-generated recommendations with accept/dismiss actions
 */
const AIRecommendationCard = ({ recommendation, onAccept, onDismiss, onSnooze }) => {
    const [dismissed, setDismissed] = useState(false);

    const handleDismiss = () => {
        setDismissed(true);
        setTimeout(() => {
            if (onDismiss) onDismiss(recommendation.id);
        }, 300);
    };

    const handleAccept = () => {
        if (onAccept) onAccept(recommendation);
    };

    const handleSnooze = () => {
        if (onSnooze) onSnooze(recommendation.id);
    };

    const getPriorityColor = () => {
        const colorMap = {
            'critical': '#CF2027',  // BITS Fire Engine Red
            'high': '#B78A2D',      // BITS Gold
            'medium': '#5CCAE8',    // BITS Sky Blue
            'low': '#9E9E9E'
        };
        return colorMap[recommendation.priority] || '#9E9E9E';
    };

    return (
        <AnimatePresence>
            {!dismissed && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, x: -100 }}
                    transition={{ duration: 0.3 }}
                >
                    <Card
                        className="mb-3 border-0 shadow-sm"
                        style={{ borderLeft: `4px solid ${getPriorityColor()}` }}
                    >
                        <Card.Body>
                            <div className="d-flex justify-content-between align-items-start mb-2">
                                <div className="d-flex align-items-center gap-2">
                                    <span style={{ fontSize: '1.5rem' }}>{recommendation.icon}</span>
                                    <div>
                                        <h6 className="mb-1 fw-semibold">{recommendation.title}</h6>
                                        <Badge bg={getRecommendationBadgeVariant(recommendation.priority)}>
                                            {recommendation.priority.toUpperCase()} PRIORITY
                                        </Badge>
                                    </div>
                                </div>
                            </div>

                            <p className="mb-2 small">{recommendation.description}</p>

                            <div className="bg-surface-hover p-2 rounded mb-3">
                                <small className="text-muted">
                                    <strong>Why this recommendation:</strong> {recommendation.reasoning}
                                </small>
                            </div>

                            {(recommendation.successRate !== null || recommendation.similarCases !== null) && (
                                <div className="d-flex gap-3 mb-3">
                                    {recommendation.successRate && (
                                        <div>
                                            <small className="text-muted d-block">Success Rate</small>
                                            <strong className="text-success">{recommendation.successRate}%</strong>
                                        </div>
                                    )}
                                    {recommendation.similarCases && (
                                        <div>
                                            <small className="text-muted d-block">Similar Cases</small>
                                            <strong>{recommendation.similarCases}</strong>
                                        </div>
                                    )}
                                </div>
                            )}

                            <div className="d-flex gap-2 flex-wrap">
                                {recommendation.actions.map((action, idx) => (
                                    <Button
                                        key={idx}
                                        size="sm"
                                        variant={action.type === 'primary' ? 'primary' : 'outline-secondary'}
                                        onClick={() => {
                                            if (action.action === 'dismiss') handleDismiss();
                                            else if (action.action === 'snooze') handleSnooze();
                                            else handleAccept();
                                        }}
                                    >
                                        {action.label}
                                    </Button>
                                ))}
                            </div>
                        </Card.Body>
                    </Card>
                </motion.div>
            )}
        </AnimatePresence>
    );
};

export default AIRecommendationCard;
