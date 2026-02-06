/**
 * Risk Narrative Generator
 * Generates natural language explanations for student risk scores
 */

import { getPrimaryRiskFactor } from './studentUtils';

/**
 * Generate a comprehensive risk narrative for a student
 * @param {Object} student - Student object with risk data
 * @returns {string} Natural language explanation
 */
export const generateRiskNarrative = (student) => {
    const riskScore = student.risk_score;
    const riskLevel = getRiskLevel(riskScore);
    const primaryFactor = getPrimaryRiskFactor(student);
    const attendance = student.attendance || calculateAttendance(student);
    const gpa = student.gpa || 2.5;

    // Build narrative based on risk level and factors
    let narrative = '';

    // Opening statement
    if (riskLevel === 'Critical') {
        narrative = `Student ${student.id}'s risk score (${riskScore}) is at a critical level, requiring immediate intervention. `;
    } else if (riskLevel === 'High') {
        narrative = `Student ${student.id} is at high risk (${riskScore}) and intervention is recommended within 1 week. `;
    } else if (riskLevel === 'Medium') {
        narrative = `Student ${student.id} has a medium risk score (${riskScore}) and should be monitored closely. `;
    } else {
        narrative = `Student ${student.id} has a low risk score (${riskScore}) and appears stable. `;
    }

    // Add primary factor analysis
    if (primaryFactor === 'Attendance' && attendance < 70) {
        narrative += `The primary concern is poor attendance (${Math.round(attendance)}% attendance rate). `;
    } else if (primaryFactor === 'Academic' && gpa < 2.5) {
        narrative += `The main issue is academic performance (GPA: ${gpa.toFixed(2)}). `;
    } else if (primaryFactor === 'Engagement') {
        narrative += `Low engagement with learning platforms is the key concern. `;
    } else if (primaryFactor === 'Behavioral') {
        narrative += `Behavioral incidents are contributing significantly to the risk. `;
    }

    // Add secondary factors
    const secondaryFactors = [];
    if (attendance < 70 && primaryFactor !== 'Attendance') {
        secondaryFactors.push(`low attendance (${Math.round(attendance)}%)`);
    }
    if (gpa < 2.5 && primaryFactor !== 'Academic') {
        secondaryFactors.push(`declining GPA (${gpa.toFixed(2)})`);
    }

    if (secondaryFactors.length > 0) {
        narrative += `Additional concerns include ${secondaryFactors.join(' and ')}. `;
    }

    return narrative.trim();
};

/**
 * Generate a short risk summary (1 sentence)
 * @param {Object} student - Student object
 * @returns {string} Brief summary
 */
export const generateShortRiskSummary = (student) => {
    const riskScore = student.risk_score;
    const riskLevel = getRiskLevel(riskScore);
    const primaryFactor = getPrimaryRiskFactor(student);

    const factorText = primaryFactor.toLowerCase();

    if (riskLevel === 'Critical' || riskLevel === 'High') {
        return `High risk (${riskScore}) driven primarily by ${factorText} issues.`;
    } else if (riskLevel === 'Medium') {
        return `Medium risk (${riskScore}) with ${factorText} as the main factor.`;
    } else {
        return `Low risk (${riskScore}), student appears stable.`;
    }
};

/**
 * Get risk level classification
 * @param {number} score - Risk score
 * @returns {string} Risk level
 */
export const getRiskLevel = (score) => {
    if (score > 85) return 'Critical';
    if (score > 75) return 'High';
    if (score > 50) return 'Medium';
    if (score > 25) return 'Low';
    return 'Very Low';
};

/**
 * Get severity description
 * @param {number} score - Risk score
 * @returns {Object} Severity info
 */
export const getSeverityInfo = (score) => {
    const level = getRiskLevel(score);

    const severityMap = {
        'Critical': {
            label: 'Critical Risk',
            description: 'Immediate intervention required',
            action: 'Assign intervention and schedule meeting within 24 hours',
            color: '#E96666',
            icon: '🚨'
        },
        'High': {
            label: 'High Risk',
            description: 'Intervention recommended within 1 week',
            action: 'Review case and assign appropriate intervention',
            color: '#EBA84B',
            icon: '⚠️'
        },
        'Medium': {
            label: 'Medium Risk',
            description: 'Monitor closely',
            action: 'Check in with student, track progress weekly',
            color: '#FFD54F',
            icon: '⚡'
        },
        'Low': {
            label: 'Low Risk',
            description: 'Stable, no immediate action needed',
            action: 'Continue regular monitoring',
            color: '#81C784',
            icon: '✓'
        },
        'Very Low': {
            label: 'Very Low Risk',
            description: 'Performing well',
            action: 'No action required',
            color: '#4CAF50',
            icon: '✓✓'
        }
    };

    return severityMap[level];
};

/**
 * Generate factor-specific explanation
 * @param {string} factor - Risk factor name
 * @param {Object} student - Student object
 * @returns {string} Explanation text
 */
export const getFactorExplanation = (factor, student) => {
    const attendance = student.attendance || calculateAttendance(student);
    const gpa = student.gpa || 2.5;

    const explanations = {
        'Attendance': `Attendance rate of ${Math.round(attendance)}% is ${attendance < 70 ? 'below the healthy threshold of 85%' : 'within acceptable range'}.`,
        'Academic': `Current GPA of ${gpa.toFixed(2)} ${gpa < 2.5 ? 'indicates academic struggles' : 'shows satisfactory performance'}.`,
        'Engagement': `Learning platform engagement ${student.engagement_score ? 'score of ' + student.engagement_score : 'appears limited'}.`,
        'Behavioral': `Behavioral record ${student.nsusp1 > 0 ? 'shows disciplinary incidents' : 'is clean with no major incidents'}.`
    };

    return explanations[factor] || 'No specific data available.';
};

/**
 * Calculate attendance from absence rates
 * @param {Object} student - Student object
 * @returns {number} Attendance percentage
 */
const calculateAttendance = (student) => {
    const absenceRates = [
        student.absrate1, student.absrate2, student.absrate3,
        student.absrate4, student.absrate5, student.absrate6, student.absrate7
    ].filter(rate => rate !== null && rate !== undefined);

    if (absenceRates.length === 0) return 75; // Default

    const avgAbsence = absenceRates.reduce((sum, rate) => sum + rate, 0) / absenceRates.length;
    return Math.max(0, Math.min(100, 100 - (avgAbsence * 100)));
};
