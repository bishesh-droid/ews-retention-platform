import React, { useMemo } from 'react';
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import RiskFactorsChart from '../student/RiskFactorsChart';
const Charts = ({ students, onRiskFilterChange, riskFilter, onRiskFactorFilterChange, riskFactorFilter }) => {
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
    { name: 'High Risk', value: riskDistribution.high, color: 'var(--high-risk-color)' },
    { name: 'Medium Risk', value: riskDistribution.medium, color: 'var(--medium-risk-color)' },
    { name: 'Low Risk', value: riskDistribution.low, color: 'var(--low-risk-color)' },
    { name: 'Very Low Risk', value: riskDistribution.veryLow, color: 'var(--very-low-risk-color)' },
  ], [riskDistribution]);
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
              outerRadius={100}
              innerRadius={60}
              fill="#2B2B88"
              paddingAngle={5}
              dataKey="value"
              isAnimationActive={true}
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
            <Tooltip formatter={(value, name, props) => {
              const total = pieData.reduce((sum, entry) => sum + entry.value, 0);
              const percent = total > 0 ? ((value / total) * 100).toFixed(0) : 0;
              return [`${value} (${percent}%)`, name];
            }} />
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