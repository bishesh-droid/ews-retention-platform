/**
 * Determines the primary risk factor for a student based on their scores.
 * In a real-world application, this logic could be significantly more complex,
 * potentially involving weighted factors or machine learning model outputs.
 * @param {object} student - The student object, containing attendance, assignments, and grades.
 * @returns {string} The primary risk factor.
 */
export const getPrimaryRiskFactor = (student) => {
  // Ensure student and necessary properties exist to prevent errors
  if (!student || typeof student.attendance === 'undefined' || typeof student.assignments === 'undefined' || typeof student.grades === 'undefined') {
    return 'Unknown';
  }

  const factors = {
    'Attendance': student.attendance,
    'Assignments': student.assignments,
    'Grades': student.grades
  };

  // Find the factor with the lowest score, as lower scores indicate higher risk.
  return Object.keys(factors).reduce((a, b) => factors[a] < factors[b] ? a : b);
};
