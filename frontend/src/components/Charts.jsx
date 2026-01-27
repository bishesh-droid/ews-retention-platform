import React, { useState, useEffect, useMemo } from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import RiskFactorsChart from './RiskFactorsChart';

const Charts = ({ students, onRiskFilterChange, riskFilter, onRiskFactorFilterChange, riskFactorFilter }) => {
  const [riskColors, setRiskColors] = useState({
    high: '#F53F3F',
    medium: '#FF7D00',
    low: '#00B42A',
    veryLow: '#C9CDD4',
  });

  useEffect(() => {
    const rootStyles = getComputedStyle(document.documentElement);
    setRiskColors({
      high: rootStyles.getPropertyValue('--high-risk-color').trim(),
      medium: rootStyles.getPropertyValue('--medium-risk-color').trim(),
      low: rootStyles.getPropertyValue('--low-risk-color').trim(),
      veryLow: rootStyles.getPropertyValue('--very-low-risk-color').trim(),
    });
  }, []);

  const riskDistribution = useMemo(() => {
    return students.reduce((acc, student) => {
      if (student.risk_score > 75) {
        acc.high++;
      } else if (student.risk_score > 50) {
        acc.medium++;
      } else if (student.risk_score > 25) {
        acc.low++;
      } else {
        acc.veryLow++;
      }
      return acc;
    }, { high: 0, medium: 0, low: 0, veryLow: 0 });
  }, [students]);

  const pieData = useMemo(() => [
    { name: 'High Risk', value: riskDistribution.high, color: riskColors.high },
    { name: 'Medium Risk', value: riskDistribution.medium, color: riskColors.medium },
    { name: 'Low Risk', value: riskDistribution.low, color: riskColors.low },
    { name: 'Very Low Risk', value: riskDistribution.veryLow, color: riskColors.veryLow },
  ], [riskDistribution, riskColors]);

  return (
    <div className="row">
      <div className="col-md-6">
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
              outerRadius={80}
              innerRadius={60} // This makes it a donut chart
              fill="#8884d8"
              dataKey="value"
              onClick={(data) => onRiskFilterChange(data.name)}
            >
              {pieData.map((entry, index) => (
                <Cell 
                  key={`cell-${index}`} 
                  fill={entry.color}
                  style={{ opacity: riskFilter && riskFilter !== entry.name ? 0.5 : 1, cursor: 'pointer' }}
                />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="col-md-6">
        <RiskFactorsChart 
          students={students} 
          onRiskFactorFilterChange={onRiskFactorFilterChange}
          riskFactorFilter={riskFactorFilter}
        />
      </div>
    </div>
  );
};

export default Charts;