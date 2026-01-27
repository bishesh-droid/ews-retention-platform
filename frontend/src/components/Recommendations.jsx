import React, { useState, useEffect } from 'react';
import { getRecommendations } from '../api';

const Recommendations = ({ students }) => {
  const [role, setRole] = useState('faculty');
  const [recommendations, setRecommendations] = useState('');

  useEffect(() => {
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

    const fetchRecommendations = async () => {
      const riskProfile = getRiskProfile();
      const result = await getRecommendations(role, riskProfile);
      setRecommendations(result.advice);
    };

    fetchRecommendations();
  }, [role, students]);

  return (
    <div>
      <div className="mb-3">
        <label htmlFor="role-select" className="form-label">Select Role:</label>
        <select id="role-select" className="form-select" onChange={(e) => setRole(e.target.value)} value={role}>
          <option value="faculty">Faculty</option>
          <option value="sales">Sales</option>
          <option value="marketing">Marketing</option>
        </select>
      </div>
      <div>
        <p>{recommendations}</p>
      </div>
    </div>
  );
};

export default Recommendations;
