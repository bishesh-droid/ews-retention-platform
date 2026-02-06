import React from 'react';
import { Card } from 'react-bootstrap';

const Recommendations = ({ students }) => {
    return (
        <div>
            {/* Placeholder for Recommendations */}
            <Card className="glass-panel border-0 mb-3">
                <Card.Body>
                    <Card.Title>System Recommendations</Card.Title>
                    <p>No active recommendations available.</p>
                </Card.Body>
            </Card>
        </div>
    );
};

export default Recommendations;
