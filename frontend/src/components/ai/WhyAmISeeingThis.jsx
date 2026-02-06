import React, { useState } from 'react';
import { Card, Collapse } from 'react-bootstrap';
import { FaQuestionCircle, FaChevronDown, FaChevronUp, FaShieldAlt, FaDatabase } from 'react-icons/fa';

/**
 * WhyAmISeeingThis Component
 * Provides transparency for AI suggestions by explaining:
 * - Context for the suggestion
 * - Data sources used
 * - Algorithm disclosure
 * - User's ability to provide feedback
 */
const WhyAmISeeingThis = ({
    context,
    dataSources = [],
    algorithm,
    userRole,
    compactMode = false
}) => {
    const [expanded, setExpanded] = useState(false);

    return (
        <div className="why-seeing-this">
            <div
                className="why-seeing-this-header"
                onClick={() => setExpanded(!expanded)}
                style={{ cursor: 'pointer' }}
            >
                <FaQuestionCircle />
                <span>Why am I seeing this?</span>
                {expanded ? <FaChevronUp /> : <FaChevronDown />}
            </div>

            <Collapse in={expanded}>
                <div className="why-seeing-this-content" id="why-seeing-this-content">
                    {/* Context Explanation */}
                    <div className="mb-3">
                        <h6 className="small fw-semibold mb-2">
                            <FaShieldAlt className="me-2" size={14} />
                            Context
                        </h6>
                        <p className="small mb-0">
                            {context || `This insight was generated based on your role as ${userRole} and 
                            is relevant to the current academic period. The AI analyzed patterns in the data 
                            to surface this information.`}
                        </p>
                    </div>

                    {/* Data Sources */}
                    {dataSources && dataSources.length > 0 && (
                        <div className="mb-3">
                            <h6 className="small fw-semibold mb-2">
                                <FaDatabase className="me-2" size={14} />
                                Data Sources Used
                            </h6>
                            <ul className="small mb-0 ps-3">
                                {dataSources.map((source, index) => (
                                    <li key={index} className="mb-1">{source}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Algorithm Disclosure */}
                    {algorithm && (
                        <div className="mb-3">
                            <h6 className="small fw-semibold mb-2">How it works</h6>
                            <p className="small mb-0">
                                {algorithm}
                            </p>
                        </div>
                    )}

                    {/* Privacy Note */}
                    <div className="mt-3 pt-2" style={{ borderTop: '1px solid var(--gray-200)' }}>
                        <p className="small text-muted mb-0">
                            <strong>Your Privacy:</strong> This analysis uses only authorized data you have
                            access to. All LLM interactions are logged for audit purposes and to improve
                            system accuracy.
                        </p>
                    </div>
                </div>
            </Collapse>
        </div>
    );
};

export default WhyAmISeeingThis;
