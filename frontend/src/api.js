// In a real application, you would fetch this data from a server.
// For this example, we'll use mock data.

const students = [
    { id: 1, name: 'John Doe', email: 'john.doe@example.com' },
    { id: 2, name: 'Jane Smith', email: 'jane.smith@example.com' },
    { id: 3, name: 'Peter Jones', email: 'peter.jones@example.com' },
    { id: 4, name: 'Mary Williams', email: 'mary.williams@example.com' },
    { id: 5, name: 'David Brown', email: 'david.brown@example.com' },
  ];
  
  const predictions = [
    { student_id: 1, risk_score: 85, engagement_score: 40, retention_likelihood: 'Low', attendance: 70, assignments: 60, grades: 55 },
    { student_id: 2, risk_score: 45, engagement_score: 75, retention_likelihood: 'Medium', attendance: 90, assignments: 80, grades: 70 },
    { student_id: 3, risk_score: 20, engagement_score: 90, retention_likelihood: 'High', attendance: 95, assignments: 95, grades: 85 },
    { student_id: 4, risk_score: 95, engagement_score: 30, retention_likelihood: 'Low', attendance: 60, assignments: 50, grades: 40 },
    { student_id: 5, risk_score: 60, engagement_score: 60, retention_likelihood: 'Medium', attendance: 80, assignments: 70, grades: 65 },
  ];
  
  export const getStudents = async () => {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(students);
      }, 500);
    });
  };

  export const getStudent = async (id) => {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        const student = students.find(s => s.id === parseInt(id));
        if (student) {
          const prediction = predictions.find(p => p.student_id === parseInt(id));
          resolve({ ...student, ...prediction });
        } else {
          reject(new Error('Student not found'));
        }
      }, 500);
    });
  };
  
  export const getPredictions = async () => {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(predictions);
      }, 500);
    });
  };

  const generateRiskHistory = (studentId, finalRiskScore) => {
    const history = [];
    const numPoints = 6; // Generate 6 data points
    let currentRisk = finalRiskScore;
  
    for (let i = numPoints - 1; i >= 0; i--) {
      const date = new Date();
      date.setDate(date.getDate() - (i * 7)); // Go back i weeks
      
      history.unshift({
        date: date.toISOString().split('T')[0],
        risk_score: Math.max(0, Math.min(100, currentRisk)),
      });
      
      // Make the next risk score fluctuate, but trend towards the start
      const fluctuation = (Math.random() - 0.5) * 20; // Fluctuate by +/- 10
      const trend = (Math.random() - 0.5) * 10; // Add a slight trend
      currentRisk = currentRisk - trend + fluctuation;
    }
    
    // Ensure the last point is the actual final risk score
    history[history.length - 1].risk_score = finalRiskScore;
    
    return history;
  };

  export const getStudentRiskHistory = async (studentId) => {
    return new Promise((resolve) => {
      const prediction = predictions.find(p => p.student_id === parseInt(studentId));
      const history = generateRiskHistory(studentId, prediction.risk_score);
      setTimeout(() => {
        resolve(history);
      }, 400);
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
        resolve({ advice: advice[role][riskProfile] || advice[role]['default'] });
      }, 300);
    });
  };