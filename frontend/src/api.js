const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

// ---- Student Data ----

let cachedStudents = null;

export const getStudents = async (limit = 2000) => {
  if (cachedStudents) return cachedStudents.slice(0, limit);

  const response = await fetch(`${API_BASE}/students/students?limit=${limit}&sort_by=risk_score&order=desc`);
  if (!response.ok) throw new Error('Failed to fetch students');
  const data = await response.json();

  // ✅ CRITICAL: Use backend data AS-IS, no transformations
  // Backend returns risk_score as 0-100 percentage
  // Backend returns signal_breakdown as probabilities 0-1
  cachedStudents = data.students.map(s => ({
    ...s,  // Keep all backend fields unchanged
    name: `${s.first_name || ''} ${s.last_name || ''}`.trim() || s.id,
    email: s.id,
    program: s.department || '',
    // Display fields only - no computation
    prediction_available: s.risk_score != null,
    prediction_error: s.risk_score == null,
  }));

  return cachedStudents.slice(0, limit);
};

export const getStudentCount = async () => {
  const response = await fetch(`${API_BASE}/students/overview`);
  if (!response.ok) throw new Error('Failed to fetch overview');
  const data = await response.json();
  return data.total_students;
};

export const getStudent = async (id) => {
  const response = await fetch(`${API_BASE}/students/students/${encodeURIComponent(id)}`);
  if (!response.ok) throw new Error(`Student ${id} not found`);
  const s = await response.json();

  // ✅ Use backend data AS-IS
  return {
    ...s,  // Keep all backend fields unchanged
    name: `${s.first_name || ''} ${s.last_name || ''}`.trim() || s.id,
    email: s.id,
    program: s.department || '',
    prediction_available: s.risk_score != null,
  };
};

export const getStudentPrediction = async (id) => {
  const student = await getStudent(id);

  // Backend now returns risk_score as 0-100 percentage
  return {
    student_id: student.id,
    risk_score: student.risk_score,  // Already 0-100 from backend
    risk_level: student.risk_level || student.risk_category,  // Use backend value
    retention_prediction: student.risk_score < 50 ? 'Likely to Stay' : 'At Risk',
    retention_likelihood: Math.round(100 - student.risk_score),  // Inverse of risk
    engagement_score: student.engagement_score,  // Already 0-100 from backend
    prediction_available: student.prediction_available,
    prediction_error: student.prediction_error || false,
    signal_breakdown: student.signal_breakdown,  // Already present from backend (0-1 scale)
    confidence: student.confidence || 0.85,
    predicted_at: new Date().toISOString(),
  };
};

export const getStudentMLPrediction = async (id) => {
  const response = await fetch(`${API_BASE}/ml/predict/${encodeURIComponent(id)}`);
  if (!response.ok) {
    if (response.status === 404) return null; // No ML prediction yet
    throw new Error('Failed to fetch ML prediction');
  }
  return await response.json();
};

export const getBatchPredictions = async (limit = 2000) => {
  const students = await getStudents(limit);
  const predictions = {};
  students.forEach(student => {
    predictions[student.id] = {
      student_id: student.id,
      risk_score: student.risk_score,
      risk_level: student.risk_level,
      retention_prediction: student.risk_score < 50 ? 'Likely to Stay' : 'At Risk',
      retention_likelihood: Math.round(100 - student.risk_score),
      engagement_score: student.engagement_score,
      prediction_available: true,
      prediction_error: false,
      signal_breakdown: student.signal_breakdown,
      confidence: 0.85,
      predicted_at: new Date().toISOString(),
    };
  });
  return predictions;
};

// ---- Risk History (generated) ----

const generateRiskHistory = (studentId, finalRiskScore) => {
  const history = [];
  const numPoints = 6;
  let currentRisk = finalRiskScore;

  for (let i = numPoints; i > 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - (i * 7));
    currentRisk = Math.max(0, Math.min(100, currentRisk));
    history.push({
      date: date.toISOString().split('T')[0],
      risk_score: Math.round(currentRisk),
    });
    const fluctuation = (Math.random() - 0.5) * 20;
    const trend = (Math.random() - 0.5) * 5;
    currentRisk -= (trend + fluctuation);
  }
  history[history.length - 1].risk_score = Math.round(finalRiskScore);
  return history;
};

export const getStudentRiskHistory = async (studentId, finalRiskScore) => {
  return new Promise((resolve) => {
    const history = generateRiskHistory(studentId, finalRiskScore);
    setTimeout(() => resolve(history), 200);
  });
};

// ---- Recommendations ----

export const getRecommendations = async (role, riskProfile) => {
  const advice = {
    faculty: {
      high: "A significant number of students are at high risk. Focus on personalized outreach, offer tutoring, and connect them with academic advisors immediately.",
      medium: "Students in the medium-risk category could benefit from proactive engagement. Consider sending encouraging emails and reminding them of available resources.",
      low: "The student population appears healthy. Continue to foster a positive learning environment and monitor engagement levels.",
      default: "Select a risk category to see specific recommendations."
    },
    sales: {
      high: "High-risk students may be questioning the value of their investment. Reach out to discuss their career goals and reinforce the program's benefits.",
      medium: "Medium-risk students might need a nudge. Share success stories and testimonials from alumni to boost their confidence.",
      low: "This is a great opportunity to gather positive testimonials and identify potential brand ambassadors.",
      default: "Select a risk category to see specific recommendations."
    },
    marketing: {
      high: "The high-risk segment is a retention concern. Launch a targeted campaign highlighting support services and academic success workshops.",
      medium: "Engage medium-risk students with content about campus life, student clubs, and extracurricular activities to improve their sense of belonging.",
      low: "Showcase the success of low-risk students in marketing materials to attract prospective students.",
      default: "Select a risk category to see specific recommendations."
    }
  };
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({ advice: advice[role]?.[riskProfile] || advice[role]?.['default'] || "No recommendations available." });
    }, 200);
  });
};

export const getAIAdvice = async (studentId, promptType) => {
  const adviceTemplates = {
    faculty: `Based on this student's profile, consider scheduling a one-on-one meeting to discuss their academic progress. Focus on understanding any challenges they may be facing and connect them with appropriate support services.`,
    sales: `This student may benefit from learning about career opportunities and success stories from program alumni. Consider sharing information about internship placements and job outcomes.`,
    marketing: `Engage this student with personalized content about campus events and student communities that align with their interests. Building a sense of belonging can improve retention.`,
    student: `Focus on maintaining consistent study habits and don't hesitate to reach out to your academic advisor if you're facing challenges. Take advantage of tutoring services and study groups.`
  };
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve(adviceTemplates[promptType] || adviceTemplates.faculty);
    }, 300);
  });
};

// ---- Interventions ----

export const getInterventions = async (studentId) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve([
        {
          id: 1, student_id: studentId,
          date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
          user: 'Dr. Smith', action: 'Academic counseling session',
          ai_suggested: true, effectiveness_score: 0.75, status: 'completed'
        },
        {
          id: 2, student_id: studentId,
          date: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
          user: 'Prof. Johnson', action: 'Tutoring referral',
          ai_suggested: true, effectiveness_score: 0.65, status: 'in_progress'
        }
      ]);
    }, 200);
  });
};

export const createIntervention = async (studentId, interventionData) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({ id: Date.now(), student_id: studentId, ...interventionData, date: new Date().toISOString(), status: 'pending' });
    }, 200);
  });
};

export const generateReportNarrative = async (reportType, reportData) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        narrative: `This ${reportType} report shows an overview of student retention metrics. The data indicates trends that require attention from the academic team.`,
        generated_at: new Date().toISOString()
      });
    }, 300);
  });
};
