import React from 'react';
import { Card, Form, Button } from 'react-bootstrap';

const FacultyAnnotations = ({ studentId }) => {
    return (
        <Card className="glass-panel border-0 mb-4">
            <Card.Body>
                <Card.Title>Faculty Annotations</Card.Title>
                <Form>
                    <Form.Group className="mb-3">
                        <Form.Label>Add Note</Form.Label>
                        <Form.Control as="textarea" rows={3} placeholder="Enter observations..." />
                    </Form.Group>
                    <Button variant="primary" size="sm">Save Note</Button>
                </Form>
            </Card.Body>
        </Card>
    );
};

export default FacultyAnnotations;
