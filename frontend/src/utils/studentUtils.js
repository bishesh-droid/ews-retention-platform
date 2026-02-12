/**
 * Determines the primary risk factor for a student based on their scores.
 * Uses real backend engagement metrics from the EWS platform.
 * @param {object} student - The student object with engagement scores from the backend.
 * @returns {string} The primary risk factor.
 */
export const getPrimaryRiskFactor = (student) => {
  if (!student) {
    return 'Unknown';
  }

  // If backend already computed the dominant risk factor, use it directly
  if (student.dominant_risk_factor) {
    return student.dominant_risk_factor;
  }

  // Fallback: compute from available scores (lower score = higher risk)
  const factors = {
    'Graded Quiz Performance': student.graded_quiz_score ?? 50,
    'Content Completion': student.content_completion_score ?? 50,
    'Exam Performance': student.exam_score ?? 50,
    'Graded Assignment Performance': student.graded_assignment_score ?? 50,
    'Exam Attendance': student.exam_attendance_rate ?? 50,
  };

  return Object.keys(factors).reduce((a, b) => factors[a] < factors[b] ? a : b);
};
