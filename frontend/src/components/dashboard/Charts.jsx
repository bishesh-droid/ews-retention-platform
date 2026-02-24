import React, { useMemo } from 'react';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  AreaChart, Area, BarChart, Bar
} from 'recharts';

// Mock data for new charts
const engagementData = [
  { name: 'Week 1', score: 65 },
  { name: 'Week 2', score: 59 },
  { name: 'Week 3', score: 80 },
  { name: 'Week 4', score: 81 },
  { name: 'Week 5', score: 86 },
  { name: 'Week 6', score: 92 },
];

const riskTrendData = [
  { name: 'Sep', avgRisk: 42 },
  { name: 'Oct', avgRisk: 48 },
  { name: 'Nov', avgRisk: 55 },
  { name: 'Dec', avgRisk: 40 },
  { name: 'Jan', avgRisk: 38 },
];

const interventionData = [
  { name: 'Tutoring', success: 75, failure: 25 },
  { name: 'Counseling', success: 85, failure: 15 },
  { name: 'Fin-Aid', success: 92, failure: 8 },
  { name: 'Mentoring', success: 68, failure: 32 },
];

const Charts = ({ students, onRiskFilterChange, riskFilter }) => {
  const riskDistribution = useMemo(() => {
    return students.reduce((acc, student) => {
      if (student.risk_score > 75) acc.high++;
      else if (student.risk_score > 50) acc.medium++;
      else if (student.risk_score > 25) acc.low++;
      else acc.veryLow++;
      return acc;
    }, { high: 0, medium: 0, low: 0, veryLow: 0 });
  }, [students]);

  const pieData = useMemo(() => [
    { name: 'High Risk', value: riskDistribution.high, color: 'var(--color-error)' },
    { name: 'Medium Risk', value: riskDistribution.medium, color: 'var(--color-warning)' },
    { name: 'Low Risk', value: riskDistribution.low, color: '#FBBF24' }, // Amber
    { name: 'Very Low Risk', value: riskDistribution.veryLow, color: 'var(--color-success)' },
  ], [riskDistribution]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
      {/* 1. Risk Distribution Chart */}
      <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
        <h4 className="text-sm font-bold text-slate-700 mb-4 text-center">Risk Distribution</h4>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={pieData}
              cx="50%"
              cy="50%"
              labelLine={false}
              outerRadius={80}
              innerRadius={50}
              paddingAngle={5}
              dataKey="value"
              isAnimationActive={true}
              onClick={(data) => onRiskFilterChange(data.name)}
            >
              {pieData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.color}
                  style={{ opacity: riskFilter && riskFilter !== entry.name ? 0.3 : 1, cursor: 'pointer' }}
                />
              ))}
            </Pie>
            <Tooltip />
            <Legend verticalAlign="bottom" height={36} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* 2. Engagement Heatmap / Trend */}
      <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
        <h4 className="text-sm font-bold text-slate-700 mb-4 text-center">Engagement Trend (Cohort Avg)</h4>
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={engagementData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--color-primary)" stopOpacity={0.8} />
                <stop offset="95%" stopColor="var(--color-primary)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#6B7280' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 12, fill: '#6B7280' }} axisLine={false} tickLine={false} />
            <Tooltip />
            <Area type="monotone" dataKey="score" stroke="var(--color-primary)" fillOpacity={1} fill="url(#colorScore)" strokeWidth={3} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* 3. Risk Trend Over Time */}
      <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
        <h4 className="text-sm font-bold text-slate-700 mb-4 text-center">Risk Trend Over Time</h4>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={riskTrendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#6B7280' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 12, fill: '#6B7280' }} axisLine={false} tickLine={false} />
            <Tooltip />
            <Line type="monotone" dataKey="avgRisk" stroke="var(--color-warning)" strokeWidth={3} dot={{ strokeWidth: 2, r: 4 }} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* 4. Intervention Success Graph */}
      <div className="bg-slate-50 p-4 rounded-xl border border-slate-100">
        <h4 className="text-sm font-bold text-slate-700 mb-4 text-center">Intervention Success Rates</h4>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={interventionData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
            <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#6B7280' }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 12, fill: '#6B7280' }} axisLine={false} tickLine={false} />
            <Tooltip cursor={{ fill: '#F3F4F6' }} />
            <Legend verticalAlign="top" height={36} />
            <Bar dataKey="success" stackId="a" fill="var(--color-success)" name="Success %" barSize={30} radius={[0, 0, 4, 4]} />
            <Bar dataKey="failure" stackId="a" fill="#E5E7EB" name="Failure %" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default Charts;