import React, { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { getPrimaryRiskFactor } from '../../utils/studentUtils';
import { FaArrowRight, FaQuestionCircle } from 'react-icons/fa';

const RiskScore = ({ value }) => {
  const roundedValue = Math.round(value);
  let colorClass = 'text-emerald-600 bg-emerald-50 border-emerald-100';
  if (roundedValue > 75) {
    colorClass = 'text-rose-600 bg-rose-50 border-rose-100';
  } else if (roundedValue > 50) {
    colorClass = 'text-amber-600 bg-amber-50 border-amber-100';
  } else if (roundedValue > 25) {
    colorClass = 'text-blue-600 bg-blue-50 border-blue-100';
  }

  return (
    <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${colorClass}`}>
      {roundedValue}%
    </span>
  );
};

const HighestRiskStudentsTable = ({ students }) => {
  const top5Students = useMemo(() =>
    [...students].sort((a, b) => b.risk_score - a.risk_score).slice(0, 5),
    [students]
  );

  const getIntervention = (factor) => {
    switch (factor) {
      case 'Exam Attendance': return 'Schedule 1-on-1 meeting';
      case 'Content Completion': return 'Encourage course engagement';
      case 'Graded Quiz Performance': return 'Offer tutoring resources';
      case 'Graded Assignment Performance': return 'Recommend assignment support';
      case 'Exam Performance': return 'Recommend academic counseling';
      case 'Login Consistency':
      case 'Time Investment': return 'Check in on engagement';
      default: return 'Monitor closely';
    }
  };

  return (
    <div className="overflow-x-auto -mx-8 px-8">
      <table className="w-full text-left border-separate border-spacing-y-2">
        <thead>
          <tr className="text-slate-400 text-[10px] font-bold uppercase tracking-widest">
            <th className="px-4 py-2">Student</th>
            <th className="px-4 py-2 flex items-center gap-1">
              Risk Score
              <FaQuestionCircle className="text-slate-300" size={10} title="High: >75%, Medium: 51-75%, Low: 26-50%" />
            </th>
            <th className="px-4 py-2">Primary Risk Factor</th>
            <th className="px-4 py-2">Suggested Intervention</th>
            <th className="px-4 py-2 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {top5Students.map((student, index) => {
            const primaryRiskFactor = getPrimaryRiskFactor(student);
            return (
              <motion.tr
                key={student.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                className="group bg-slate-50 hover:bg-white hover:shadow-soft transition-all duration-200"
              >
                <td className="px-4 py-4 rounded-l-2xl border-y border-l border-transparent group-hover:border-slate-100">
                  <span className="font-bold text-slate-900">{student.name || `Student #${student.id}`}</span>
                </td>
                <td className="px-4 py-4 border-y border-transparent group-hover:border-slate-100">
                  <RiskScore value={student.risk_score} />
                </td>
                <td className="px-4 py-4 border-y border-transparent group-hover:border-slate-100 italic text-slate-900 text-sm">
                  {primaryRiskFactor}
                </td>
                <td className="px-4 py-4 border-y border-transparent group-hover:border-slate-100">
                  <span className="text-sm text-slate-500">{getIntervention(primaryRiskFactor)}</span>
                </td>
                <td className="px-4 py-4 rounded-r-2xl border-y border-r border-transparent group-hover:border-slate-100 text-right">
                  <Link
                    to={`/students/${student.id}`}
                    className="inline-flex items-center gap-2 text-sm font-bold text-primary-500 hover:text-primary-600 transition-colors"
                  >
                    View Profile <FaArrowRight size={10} />
                  </Link>
                </td>
              </motion.tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};

export default HighestRiskStudentsTable;
