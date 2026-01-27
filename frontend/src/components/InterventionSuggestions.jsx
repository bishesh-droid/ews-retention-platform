import React from 'react';
import { Card, ListGroup } from 'react-bootstrap';

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
    switch (profile) {
      case 'high':
        return [
          'Focus on immediate, direct interventions for high-risk students.',
          'Organize a team meeting to discuss high-risk student strategies.',
          'Review and intensify monitoring for students in the 50-75% risk range.'
        ];
      case 'medium':
        return [
          'Implement targeted workshops for common risk factors (e.g., study skills).',
          'Increase communication with students in the medium-risk category.',
          'Monitor students approaching the high-risk threshold.'
        ];
      case 'low':
        return [
          'Focus on proactive and preventative measures.',
          'Reinforce positive behaviors and academic habits.',
          'Develop enrichment programs to keep students engaged.'
        ];
      default:
        return ['No student data available to generate suggestions.'];
    }
  };

  const suggestions = getSuggestions();

  return (
    <Card>
      <Card.Header as="h3">Intervention Suggestions</Card.Header>
      <ListGroup variant="flush">
        {suggestions.map((suggestion, index) => (
          <ListGroup.Item key={index}>{suggestion}</ListGroup.Item>
        ))}
      </ListGroup>
    </Card>
  );
};

export default InterventionSuggestions;
