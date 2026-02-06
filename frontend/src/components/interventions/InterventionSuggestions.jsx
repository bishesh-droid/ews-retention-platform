import React from 'react';
import { Badge, Button, ListGroup, ProgressBar } from 'react-bootstrap';
import { FaLightbulb, FaCheck, FaTimes } from 'react-icons/fa';

const InterventionSuggestions = ({ students }) => {
  const getRiskProfile = () => {
    if (!students || students.length === 0) {
      return 'default';
    }

    const riskCounts = students.reduce((acc, student) => {
      if (student.risk_score > 75) {
        acc.high++;
      } else if (student.risk_score > 50) {
        acc.medium++;
      } else {
        acc.low++;
      }
      return acc;
    }, { high: 0, medium: 0, low: 0 });

    if (riskCounts.high >= riskCounts.medium && riskCounts.high >= riskCounts.low) {
      return 'high';
    } else if (riskCounts.medium >= riskCounts.low) {
      return 'medium';
    } else {
      return 'low';
    }
  };

  const getSuggestions = () => {
    const profile = getRiskProfile();
    const highRiskStudents = students.filter(s => s.risk_score > 75);

    switch (profile) {
      case 'high':
        return [
          {
            text: `Schedule 1-on-1 meetings for ${highRiskStudents.length} critical students`,
            confidence: 92,
            reason: 'High-risk students show patterns matching those who benefit from direct counseling',
            type: 'individual'
          },
          {
            text: 'Implement attendance monitoring program',
            confidence: 87,
            reason: 'Attendance is the primary risk factor for 68% of at-risk students',
            type: 'group'
          },
          {
            text: 'Review and intensify monitoring for medium-risk students',
            confidence: 79,
            reason: 'Early intervention prevents escalation to high-risk category',
            type: 'preventative'
          }
        ];
      case 'medium':
        return [
          {
            text: 'Implement targeted study skills workshops',
            confidence: 84,
            reason: 'Common risk factors indicate academic skills gap',
            type: 'group'
          },
          {
            text: 'Increase communication with at-risk cohort',
            confidence: 81,
            reason: 'Engagement metrics show declining LMS activity',
            type: 'communication'
          },
          {
            text: 'Launch peer mentoring program',
            confidence: 88,
            reason: 'Historical data shows 91% success rate for this cohort type',
            type: 'program'
          }
        ];
      case 'low':
        return [
          {
            text: 'Focus on proactive wellness initiatives',
            confidence: 76,
            reason: 'Preventative measures maintain low-risk status',
            type: 'preventative'
          },
          {
            text: 'Develop academic enrichment programs',
            confidence: 82,
            reason: 'Engaged students have 96% retention rate',
            type: 'program'
          }
        ];
      default:
        return [{
          text: 'No student data available to generate suggestions',
          confidence: 0,
          reason: 'Import student data to receive AI-powered recommendations',
          type: 'info'
        }];
    }
  };

  const suggestions = getSuggestions();

  return (
    <div>
      <ListGroup variant="flush" className="bg-transparent">
        {suggestions.map((suggestion, index) => (
          <ListGroup.Item key={index} className="bg-transparent border-bottom px-0" style={{ borderColor: 'var(--border-color)' }}>
            <div className="d-flex align-items-start gap-2 mb-2">
              <FaLightbulb className="text-warning mt-1" />
              <div className="flex-grow-1">
                <p className="mb-2 fw-medium">{suggestion.text}</p>
                {suggestion.confidence > 0 && (
                  <>
                    <div className="d-flex align-items-center gap-2 mb-2">
                      <small className="text-muted">Confidence:</small>
                      <ProgressBar
                        now={suggestion.confidence}
                        variant={suggestion.confidence >= 85 ? 'success' : 'primary'}
                        style={{ height: '6px', flex: 1 }}
                      />
                      <Badge bg={suggestion.confidence >= 85 ? 'success' : 'primary'}>
                        {suggestion.confidence}%
                      </Badge>
                    </div>
                    <small className="text-muted d-block mb-2">
                      <strong>Why:</strong> {suggestion.reason}
                    </small>
                    <div className="d-flex gap-2">
                      <Button variant="success" size="sm" className="d-flex align-items-center gap-1">
                        <FaCheck /> Accept
                      </Button>
                      <Button variant="outline-secondary" size="sm" className="d-flex align-items-center gap-1">
                        <FaTimes /> Dismiss
                      </Button>
                    </div>
                  </>
                )}
              </div>
            </div>
          </ListGroup.Item>
        ))}
      </ListGroup>
    </div>
  );
};

export default InterventionSuggestions;
