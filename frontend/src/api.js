import { parseCSV } from './utils/csvParser';

// Cache for loaded CSV data
let cachedStudents = null;
let cachedPredictions = null;

// Helper: Calculate risk score from student data (simplified formula based on features)
const calculateRiskScore = (student) => {
  // Average absence rate (absrate1-7) - higher = more risk
  const absRates = [student.absrate1, student.absrate2, student.absrate3, student.absrate4,
                    student.absrate5, student.absrate6, student.absrate7].filter(v => v !== undefined);
  const avgAbsence = absRates.length > 0 ? absRates.reduce((a, b) => a + b, 0) / absRates.length : 10;

  // Average suspensions (nsusp1-7) - higher = more risk
  const suspensions = [student.nsusp1, student.nsusp2, student.nsusp3, student.nsusp4,
                       student.nsusp5, student.nsusp6, student.nsusp7].filter(v => v !== undefined);
  const avgSusp = suspensions.length > 0 ? suspensions.reduce((a, b) => a + b, 0) / suspensions.length : 0;

  // Average mobility (mobility1-7) - higher = more risk
  const mobilities = [student.mobility1, student.mobility2, student.mobility3, student.mobility4,
                      student.mobility5, student.mobility6, student.mobility7].filter(v => v !== undefined);
  const avgMobility = mobilities.length > 0 ? mobilities.reduce((a, b) => a + b, 0) / mobilities.length : 0;

  // Average GPA from quarter MPAs (q1mpa1-q4mpa7) - lower GPA = more risk
  const gpas = [];
  for (let year = 1; year <= 7; year++) {
    for (let q = 1; q <= 4; q++) {
      const key = `q${q}mpa${year}`;
      if (student[key] !== undefined) gpas.push(student[key]);
    }
  }
  const avgGPA = gpas.length > 0 ? gpas.reduce((a, b) => a + b, 0) / gpas.length : 75;

  // Calculate risk score (0-100)
  // Weighted formula: absence contributes most, then GPA, then suspensions, then mobility
  let riskScore = 0;
  riskScore += (avgAbsence / 30) * 40;        // Absence: 0-30 range -> 0-40 risk points
  riskScore += ((100 - avgGPA) / 50) * 35;    // GPA: 50-100 range -> 0-35 risk points (inverted)
  riskScore += (avgSusp / 5) * 15;            // Suspensions: 0-5 range -> 0-15 risk points
  riskScore += (avgMobility / 3) * 10;        // Mobility: 0-3 range -> 0-10 risk points

  // Clamp to 0-100
  return Math.round(Math.max(0, Math.min(100, riskScore)));
};

// Helper: Generate risk level from score
const getRiskLevel = (score) => {
  if (score >= 70) return 'critical';
  if (score >= 50) return 'high';
  if (score >= 30) return 'medium';
  return 'low';
};

// Helper: Generate signal breakdown from student data
const generateSignalBreakdown = (student) => {
  const absRates = [student.absrate7, student.absrate6, student.absrate5].filter(v => v !== undefined);
  const avgRecentAbs = absRates.length > 0 ? absRates.reduce((a, b) => a + b, 0) / absRates.length : 10;

  const recentGPAs = [];
  for (let q = 1; q <= 4; q++) {
    if (student[`q${q}mpa7`] !== undefined) recentGPAs.push(student[`q${q}mpa7`]);
  }
  const avgRecentGPA = recentGPAs.length > 0 ? recentGPAs.reduce((a, b) => a + b, 0) / recentGPAs.length : 75;

  return {
    academic_signal_score: Math.max(0, Math.min(1, avgRecentGPA / 100)),
    engagement_signal_score: Math.max(0, Math.min(1, 1 - (avgRecentAbs / 30))),
    consistency_signal_score: Math.max(0, Math.min(1, 0.5 + (Math.random() * 0.3 - 0.15))),
    intent_signal_score: Math.max(0, Math.min(1, 0.6 + (Math.random() * 0.3 - 0.15))),
    responsiveness_signal_score: Math.max(0, Math.min(1, 0.55 + (Math.random() * 0.3 - 0.15)))
  };
};

// Load and parse CSV data
const loadCSVData = async () => {
  if (cachedStudents && cachedPredictions) {
    return { students: cachedStudents, predictions: cachedPredictions };
  }

  try {
    const response = await fetch('/data/student_data_test.csv');
    const csvText = await response.text();
    const rawData = parseCSV(csvText);

    // Transform to student format with proper fields
    cachedStudents = rawData.map((row, index) => ({
      ...row,
      id: row.id || `S${String(index + 1).padStart(5, '0')}`,
      name: `Student ${row.id || index + 1}`,
      email: `student${index + 1}@university.edu`,
      enrolled_date: '2023-09-01',
      program: ['Computer Science', 'Business', 'Engineering', 'Arts', 'Sciences'][index % 5],
      year: Math.ceil((index % 4) + 1),
      nograd: row.nograd
    }));

    // Generate predictions for each student
    cachedPredictions = {};
    cachedStudents.forEach(student => {
      const riskScore = calculateRiskScore(student);
      const engagementScore = Math.round(Math.max(0, Math.min(100, 100 - (riskScore * 0.7) + (Math.random() * 20 - 10))));
      cachedPredictions[student.id] = {
        student_id: student.id,
        risk_score: riskScore,
        risk_score_raw: riskScore / 100,
        risk_level: getRiskLevel(riskScore),
        retention_prediction: riskScore < 50 ? 'Likely to Stay' : 'At Risk',
        retention_likelihood: Math.round(100 - riskScore),
        engagement_score: engagementScore,
        prediction_available: true,
        prediction_error: false,
        signal_breakdown: generateSignalBreakdown(student),
        confidence: 0.75 + (Math.random() * 0.2),
        predicted_at: new Date().toISOString()
      };
    });

    return { students: cachedStudents, predictions: cachedPredictions };
  } catch (error) {
    console.error('Error loading CSV data:', error);
    throw error;
  }
};

export const getStudents = async (limit = 1500) => {
  const { students } = await loadCSVData();
  return students.slice(0, limit);
};

export const getStudentCount = async () => {
  const { students } = await loadCSVData();
  return students.length;
};

export const getStudent = async (id) => {
  const { students } = await loadCSVData();
  const student = students.find(s => s.id === id);
  if (!student) {
    throw new Error(`Student with id ${id} not found`);
  }
  return student;
};

export const getStudentPrediction = async (id) => {
  const { predictions } = await loadCSVData();
  const prediction = predictions[id];
  if (!prediction) {
    throw new Error(`Prediction for student ${id} not found`);
  }
  return prediction;
};

export const getBatchPredictions = async (limit = 1500) => {
  const { predictions } = await loadCSVData();
  // Return as object keyed by student_id (limited)
  const keys = Object.keys(predictions).slice(0, limit);
  const result = {};
  keys.forEach(key => {
    result[key] = predictions[key];
  });
  return result;
};

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
    setTimeout(() => {
      resolve(history);
    }, 200);
  });
};

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
  // Mock AI advice based on prompt type
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

export const getInterventions = async (studentId) => {
  // Mock interventions data
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve([
        {
          id: 1,
          student_id: studentId,
          date: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
          user: 'Dr. Smith',
          action: 'Academic counseling session',
          ai_suggested: true,
          effectiveness_score: 0.75,
          status: 'completed'
        },
        {
          id: 2,
          student_id: studentId,
          date: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
          user: 'Prof. Johnson',
          action: 'Tutoring referral',
          ai_suggested: true,
          effectiveness_score: 0.65,
          status: 'in_progress'
        }
      ]);
    }, 200);
  });
};

export const createIntervention = async (studentId, interventionData) => {
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        id: Date.now(),
        student_id: studentId,
        ...interventionData,
        date: new Date().toISOString(),
        status: 'pending'
      });
    }, 200);
  });
};

export const generateReportNarrative = async (reportType, reportData) => {
  // Mock report narrative generation
  return new Promise((resolve) => {
    setTimeout(() => {
      resolve({
        narrative: `This ${reportType} report shows an overview of student retention metrics. The data indicates trends that require attention from the academic team.`,
        generated_at: new Date().toISOString()
      });
    }, 300);
  });
};
