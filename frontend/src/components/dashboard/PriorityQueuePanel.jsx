import React from 'react';
import { Card, ListGroup, Badge } from 'react-bootstrap';

const PriorityQueuePanel = ({ limit = 5 }) => {
    return (
        <Card className="glass-panel border-0 h-100">
            <Card.Body>
                <Card.Title>AI Priority Queue</Card.Title>
                <ListGroup variant="flush">
                    {/* Placeholder items */}
                    <ListGroup.Item className="bg-transparent">Student A (Risk: High)</ListGroup.Item>
                    <ListGroup.Item className="bg-transparent">Student B (Risk: Med)</ListGroup.Item>
                </ListGroup>
            </Card.Body>
        </Card>
    );
};

export default PriorityQueuePanel;
