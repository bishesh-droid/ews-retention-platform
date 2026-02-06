import React from 'react';
import { OverlayTrigger, Tooltip } from 'react-bootstrap';
import { FaQuestionCircle, FaInfoCircle } from 'react-icons/fa';

/**
 * ChartExplainerTooltip Component
 * Provides AI-generated explanations for chart elements on hover.
 * Helps users understand what they're seeing in data visualizations.
 */
const ChartExplainerTooltip = ({ chartType, dataPoint, explanation, children }) => {
    const renderTooltip = (props) => (
        <Tooltip id={`tooltip-${chartType}-${dataPoint}`} {...props} className="ai-tooltip">
            <div className="ai-tooltip-content">
                <div className="d-flex align-items-center gap-2 mb-2">
                    <FaInfoCircle size={14} />
                    <strong className="small">AI Insight</strong>
                </div>
                <p className="small mb-0 ai-text">
                    {explanation}
                </p>
            </div>
        </Tooltip>
    );

    return (
        <OverlayTrigger
            placement="top"
            delay={{ show: 250, hide: 400 }}
            overlay={renderTooltip}
        >
            <span className="chart-explainer-wrapper">
                {children}
                <FaQuestionCircle
                    className="chart-explainer-icon ms-1"
                    size={12}
                    style={{ opacity: 0.6, cursor: 'help' }}
                />
            </span>
        </OverlayTrigger>
    );
};

export default ChartExplainerTooltip;
