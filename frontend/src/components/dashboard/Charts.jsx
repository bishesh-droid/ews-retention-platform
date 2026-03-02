import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
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
    { name: 'High Risk',     value: riskDistribution.high,    color: '#E879F9' }, // fuchsia — danger in violet family
    { name: 'Medium Risk',  value: riskDistribution.medium,  color: '#FBBF24' }, // amber — brand accent
    { name: 'Low Risk',     value: riskDistribution.low,     color: '#A78BFA' }, // violet-400 — on-theme
    { name: 'Very Low Risk',value: riskDistribution.veryLow, color: '#6EE7B7' }, // muted emerald — safe
  ], [riskDistribution]);

  const cardStyle = {
    backgroundColor: '#130D23',
    border: '1px solid rgba(139,92,246,0.18)',
    borderRadius: '16px',
    padding: '20px',
    cursor: 'default',
  };

  const hoverProps = {
    whileHover: { y: -5, boxShadow: '0 0 28px rgba(139,92,246,0.2), 0 8px 32px rgba(0,0,0,0.4)', borderColor: 'rgba(139,92,246,0.45)' },
    transition: { duration: 0.2 },
  };

  const titleStyle = {
    fontSize: '13px',
    fontWeight: '700',
    color: '#C4B5FD',
    textAlign: 'center',
    marginBottom: '16px',
  };

  const gridStroke = 'rgba(139,92,246,0.12)';
  const tickStyle = { fontSize: 11, fill: '#6B5E8E' };
  const tooltipStyle = { backgroundColor: '#1A1035', border: '1px solid rgba(139,92,246,0.3)', borderRadius: '10px', color: '#EDE9FE' };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* 1. Risk Distribution Chart */}
      <motion.div style={cardStyle} {...hoverProps}>
        <h4 style={titleStyle}>Risk Distribution</h4>
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
            <Legend verticalAlign="bottom" height={36} wrapperStyle={{ color: '#8B7DB8', fontSize: '12px' }} />
          </PieChart>
        </ResponsiveContainer>
      </motion.div>

      {/* 2. Engagement Trend */}
      <motion.div style={cardStyle} {...hoverProps}>
        <h4 style={titleStyle}>Engagement Trend (Cohort Avg)</h4>
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={engagementData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8B5CF6" stopOpacity={0.5} />
                <stop offset="95%" stopColor="#8B5CF6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridStroke} />
            <XAxis dataKey="name" tick={tickStyle} axisLine={false} tickLine={false} />
            <YAxis tick={tickStyle} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} />
            <Area type="monotone" dataKey="score" stroke="#8B5CF6" fillOpacity={1} fill="url(#colorScore)" strokeWidth={2.5} />
          </AreaChart>
        </ResponsiveContainer>
      </motion.div>

      {/* 3. Risk Trend Over Time */}
      <motion.div style={cardStyle} {...hoverProps}>
        <h4 style={titleStyle}>Risk Trend Over Time</h4>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={riskTrendData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridStroke} />
            <XAxis dataKey="name" tick={tickStyle} axisLine={false} tickLine={false} />
            <YAxis tick={tickStyle} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} />
            <Line type="monotone" dataKey="avgRisk" stroke="#F59E0B" strokeWidth={2.5} dot={{ strokeWidth: 2, r: 4, fill: '#F59E0B' }} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      </motion.div>

      {/* 4. Intervention Success Rates */}
      <motion.div style={cardStyle} {...hoverProps}>
        <h4 style={titleStyle}>Intervention Success Rates</h4>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={interventionData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridStroke} />
            <XAxis dataKey="name" tick={tickStyle} axisLine={false} tickLine={false} />
            <YAxis tick={tickStyle} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgba(139,92,246,0.06)' }} />
            <Legend verticalAlign="top" height={36} wrapperStyle={{ color: '#8B7DB8', fontSize: '12px' }} />
            <Bar dataKey="success" stackId="a" fill="#10B981" name="Success %" barSize={30} radius={[0, 0, 4, 4]} />
            <Bar dataKey="failure" stackId="a" fill="rgba(239,68,68,0.5)" name="Failure %" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </motion.div>
    </div>
  );
};

export default Charts;