import React, { useState } from 'react';
import { Card, Collapse, Button } from 'react-bootstrap';
import { FaChevronDown, FaChevronUp } from 'react-icons/fa';

/**
 * CollapsiblePanel Component
 * Provides progressive disclosure for complex content
 */
const CollapsiblePanel = ({
    title,
    children,
    defaultExpanded = false,
    icon = null,
    badge = null,
    variant = 'default'
}) => {
    const [expanded, setExpanded] = useState(defaultExpanded);

    const toggleExpanded = () => {
        setExpanded(!expanded);
    };

    if (variant === 'simple') {
        return (
            <div className="mb-3">
                <Button
                    variant="link"
                    onClick={toggleExpanded}
                    className="p-0 text-decoration-none d-flex align-items-center gap-2 mb-2"
                >
                    {expanded ? <FaChevronUp size={14} /> : <FaChevronDown size={14} />}
                    {icon && <span>{icon}</span>}
                    <span className="fw-semibold">{title}</span>
                    {badge && <span className="ms-auto">{badge}</span>}
                </Button>
                <Collapse in={expanded}>
                    <div className="ps-4">
                        {children}
                    </div>
                </Collapse>
            </div>
        );
    }

    return (
        <Card className="glass-panel border-0 mb-3">
            <Card.Header
                className="bg-transparent border-0 cursor-pointer d-flex justify-content-between align-items-center"
                onClick={toggleExpanded}
                style={{ cursor: 'pointer' }}
            >
                <div className="d-flex align-items-center gap-2">
                    {icon && <span>{icon}</span>}
                    <span className="fw-semibold">{title}</span>
                    {badge && badge}
                </div>
                <div>
                    {expanded ? <FaChevronUp /> : <FaChevronDown />}
                </div>
            </Card.Header>
            <Collapse in={expanded}>
                <Card.Body className="pt-0">
                    {children}
                </Card.Body>
            </Collapse>
        </Card>
    );
};

export default CollapsiblePanel;
