import React from 'react';
import { Card } from 'react-bootstrap';

const StudentsLikeThis = ({ currentStudent }) => {
    return (
        <Card className="glass-panel border-0 mb-4">
            <Card.Body>
                <Card.Title>Similar Students Profiling</Card.Title>
                <p className="text-muted">Analysis of students with similar risk factors...</p>
                {/* Placeholder content */}
            </Card.Body>
        </Card>
    );
};

export default StudentsLikeThis;
