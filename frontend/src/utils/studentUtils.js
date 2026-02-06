/**
 * Determines the primary risk factor for a student based on their scores.
 * In a real-world application, this logic could be significantly more complex,
 * potentially involving weighted factors or machine learning model outputs.
 * @param {object} student - The student object, containing attendance, assignments, and grades.
 * @returns {string} The primary risk factor.
 */
export const getPrimaryRiskFactor = (student) => {
  if (!student) {
    return 'Unknown';
  }

  // Derive the scores from the student object properties
  const attendance = Math.round(student.absrate7 ? 100 - (student.absrate7 * 100) : 0);
  // Assuming assignments and grades are both represented by q4mpa7
  // This might need clarification if there are separate fields for assignments vs grades
  const assignments = student.q4mpa7 ? student.q4mpa7 : 0;
  const grades = student.q4mpa7 ? student.q4mpa7 : 0;

  const factors = {
    'Attendance': attendance,
    'Assignments': assignments,
    'Grades': grades
  };

  // Find the factor with the lowest score, as lower scores indicate higher risk.
  // Add a check for factors array to not be empty
  if (Object.keys(factors).length === 0) {
      return 'Unknown';
  }

  return Object.keys(factors).reduce((a, b) => factors[a] < factors[b] ? a : b);
};
