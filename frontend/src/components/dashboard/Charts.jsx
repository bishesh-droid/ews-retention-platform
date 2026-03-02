import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  AreaChart, Area, BarChart, Bar, ReferenceLine,
} from 'recharts';

const Charts = ({ students, onRiskFilterChange, riskFilter, engagementSeries = [], riskTrendSeries = [], interventionSummary = [], riskFactorSummary = [] }) => {
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
    { name: 'High Risk',     value: riskDistribution.high,    color: '#E879F9' },
    { name: 'Medium Risk',  value: riskDistribution.medium,  color: '#FBBF24' },
    { name: 'Low Risk',     value: riskDistribution.low,     color: '#A78BFA' },
    { name: 'Very Low Risk',value: riskDistribution.veryLow, color: '#6EE7B7' },
  ], [riskDistribution]);

  // Risk Score Distribution histogram (5 buckets)
  const histogramData = useMemo(() => {
    const buckets = [
      { range: '0–20',   count: 0, fill: '#6EE7B7' },
      { range: '21–40',  count: 0, fill: '#A78BFA' },
      { range: '41–60',  count: 0, fill: '#FBBF24' },
      { range: '61–80',  count: 0, fill: '#F87171' },
      { range: '81–100', count: 0, fill: '#E879F9' },
    ];
    students.forEach(s => {
      const i = Math.min(Math.floor(s.risk_score / 20), 4);
      buckets[i].count++;
    });
    return buckets;
  }, [students]);

  const avgRisk = useMemo(() =>
    students.length > 0 ? Math.round(students.reduce((a, s) => a + s.risk_score, 0) / students.length) : 0,
  [students]);

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
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
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
          <AreaChart data={engagementSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
          <LineChart data={riskTrendSeries} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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
          <BarChart data={interventionSummary} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
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

      {/* 5. Risk Score Distribution (Histogram) */}
      <motion.div style={cardStyle} {...hoverProps}>
        <h4 style={titleStyle}>Risk Score Distribution</h4>
        <p style={{ fontSize: '11px', color: '#6B5E8E', textAlign: 'center', marginBottom: '8px' }}>
          Students bucketed by risk score range
        </p>
        <ResponsiveContainer width="100%" height={230}>
          <BarChart data={histogramData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridStroke} />
            <XAxis dataKey="range" tick={tickStyle} axisLine={false} tickLine={false} />
            <YAxis tick={tickStyle} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={tooltipStyle}
              cursor={{ fill: 'rgba(139,92,246,0.06)' }}
              formatter={(v) => [v, 'Students']}
            />
            <ReferenceLine
              y={0}
              stroke="transparent"
              label={{ value: `Avg Risk: ${avgRisk}%`, fill: '#8B7DB8', fontSize: 10, position: 'insideTopRight' }}
            />
            <Bar dataKey="count" name="Students" radius={[4, 4, 0, 0]} barSize={32}>
              {histogramData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </motion.div>

      {/* 6. Top Risk Factors (Horizontal Bar) */}
      <motion.div style={cardStyle} {...hoverProps}>
        <h4 style={titleStyle}>Top Risk Factor Contributions</h4>
        <p style={{ fontSize: '11px', color: '#6B5E8E', textAlign: 'center', marginBottom: '8px' }}>
          Primary drivers of student risk scores (%)
        </p>
        <ResponsiveContainer width="100%" height={230}>
          <BarChart
            data={riskFactorSummary}
            layout="vertical"
            margin={{ top: 5, right: 20, left: 10, bottom: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={gridStroke} />
            <XAxis type="number" tick={tickStyle} axisLine={false} tickLine={false} unit="%" domain={[0, 40]} />
            <YAxis type="category" dataKey="factor" tick={{ ...tickStyle, fontSize: 10 }} axisLine={false} tickLine={false} width={110} />
            <Tooltip contentStyle={tooltipStyle} formatter={(v) => [`${v}%`, 'Contribution']} />
            <Bar dataKey="score" name="Contribution %" radius={[0, 4, 4, 0]} barSize={18}>
              {riskFactorSummary.map((_, i) => (
                <Cell key={`rfcell-${i}`} fill={['#E879F9', '#F87171', '#FBBF24', '#A78BFA', '#6EE7B7'][i % 5]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </motion.div>
    </div>
  );
};

export default Charts;