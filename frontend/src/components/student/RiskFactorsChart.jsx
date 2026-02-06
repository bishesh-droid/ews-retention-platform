import React, { useState, useEffect, useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import { getPrimaryRiskFactor } from '../../utils/studentUtils';

const RiskFactorsChart = ({ students, onRiskFactorFilterChange, riskFactorFilter }) => {
  const [primaryColor, setPrimaryColor] = useState('#2B2B88');

  useEffect(() => {
    const rootStyles = getComputedStyle(document.documentElement);
    setPrimaryColor(rootStyles.getPropertyValue('--primary-color').trim());
  }, []);

  const atRiskStudents = useMemo(() => students.filter(s => s.risk_score > 50), [students]);

  const factorCounts = useMemo(() => {
    return atRiskStudents.reduce((acc, student) => {
      const primaryFactor = getPrimaryRiskFactor(student);
      acc[primaryFactor] = (acc[primaryFactor] || 0) + 1;
      return acc;
    }, {});
  }, [atRiskStudents]);

  const chartData = useMemo(() => {
    return Object.keys(factorCounts).map(key => ({
      name: key,
      'Number of Students': factorCounts[key],
    }));
  }, [factorCounts]);

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis allowDecimals={false} />
        <Tooltip />
        <Legend />
        <Bar dataKey="Number of Students" onClick={(data) => onRiskFactorFilterChange(data.name)} cursor="pointer">
          {chartData.map((entry, index) => (
            <Cell 
              key={`cell-${index}`} 
              fill={primaryColor}
              style={{ opacity: riskFactorFilter && riskFactorFilter !== entry.name ? 0.5 : 1 }}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
};

export default RiskFactorsChart;