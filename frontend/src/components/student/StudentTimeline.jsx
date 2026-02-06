import React, { useState } from 'react';
import { Card, Badge, Button, Form } from 'react-bootstrap';
import { FaFilter } from 'react-icons/fa';
import { generateTimelineEvents, filterEventsByType, formatEventDate } from '../../utils/timelineDataGenerator';

/**
 * StudentTimeline Component
 * Interactive timeline view of student activity and events
 */
const StudentTimeline = ({ student }) => {
    const [filter, setFilter] = useState('all');
    const events = generateTimelineEvents(student);
    const filteredEvents = filterEventsByType(events, filter);

    const eventTypes = [
        { value: 'all', label: 'All Events', count: events.length },
        { value: 'attendance', label: 'Attendance', count: events.filter(e => e.type === 'attendance').length },
        { value: 'grade', label: 'Grades', count: events.filter(e => e.type === 'grade').length },
        { value: 'risk', label: 'Risk Changes', count: events.filter(e => e.type === 'risk').length },
        { value: 'intervention', label: 'Interventions', count: events.filter(e => e.type === 'intervention').length },
        { value: 'engagement', label: 'Engagement', count: events.filter(e => e.type === 'engagement').length },
    ];

    return (
        <Card className="glass-panel border-0">
            <Card.Body>
                <div className="d-flex justify-content-between align-items-center mb-3">
                    <h5 className="mb-0 fw-semibold">Activity Timeline</h5>
                    <div className="d-flex align-items-center gap-2">
                        <FaFilter className="text-muted" size={14} />
                        <Form.Select
                            size="sm"
                            value={filter}
                            onChange={(e) => setFilter(e.target.value)}
                            style={{ width: 'auto' }}
                        >
                            {eventTypes.map(type => (
                                <option key={type.value} value={type.value}>
                                    {type.label} ({type.count})
                                </option>
                            ))}
                        </Form.Select>
                    </div>
                </div>

                <div className="position-relative">
                    {/* Timeline Line */}
                    <div
                        className="position-absolute bg-secondary opacity-25"
                        style={{
                            left: '20px',
                            top: '0',
                            bottom: '0',
                            width: '2px'
                        }}
                    />

                    {/* Timeline Events */}
                    <div className="d-flex flex-column gap-3">
                        {filteredEvents.length === 0 ? (
                            <p className="text-muted text-center py-4">No events to display</p>
                        ) : (
                            filteredEvents.map((event, index) => (
                                <div key={event.id} className="d-flex gap-3 position-relative">
                                    {/* Event Dot */}
                                    <div
                                        className="rounded-circle d-flex align-items-center justify-content-center flex-shrink-0"
                                        style={{
                                            width: '40px',
                                            height: '40px',
                                            backgroundColor: event.color,
                                            fontSize: '1.2rem',
                                            zIndex: 1
                                        }}
                                    >
                                        {event.icon}
                                    </div>

                                    {/* Event Card */}
                                    <div className="flex-grow-1">
                                        <div
                                            className="p-3 rounded-3 bg-surface-hover border border-secondary-subtle"
                                            style={{ borderLeft: `3px solid ${event.color}` }}
                                        >
                                            <div className="d-flex justify-content-between align-items-start mb-1">
                                                <div>
                                                    <h6 className="mb-1 fw-semibold">{event.title}</h6>
                                                    <small className="text-muted">{event.category}</small>
                                                </div>
                                                <Badge
                                                    bg={event.severity === 'danger' ? 'danger' : event.severity === 'warning' ? 'warning' : event.severity === 'success' ? 'success' : 'info'}
                                                    className="opacity-75"
                                                >
                                                    {event.severity}
                                                </Badge>
                                            </div>
                                            <p className="mb-1 small">{event.description}</p>
                                            <small className="text-muted">{formatEventDate(event.date)}</small>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {filteredEvents.length > 0 && (
                    <div className="text-center mt-3">
                        <Button variant="link" size="sm" className="text-decoration-none">
                            Load More Events
                        </Button>
                    </div>
                )}
            </Card.Body>
        </Card>
    );
};

export default StudentTimeline;
