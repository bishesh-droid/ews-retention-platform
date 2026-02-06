/**
 * Data Quality Calculator
 * Calculates data completeness and quality scores for student records
 */

/**
 * Calculate data quality score for a student
 * @param {Object} student - Student object with various data fields
 * @returns {Object} Quality metrics including score, level, and missing fields
 */
export const calculateDataQuality = (student) => {
    const requiredFields = [
        'attendance',
        'gpa',
        'absrate1', 'absrate2', 'absrate3', 'absrate4', 'absrate5', 'absrate6', 'absrate7',
        'q1mpa1', 'q2mpa1', 'q3mpa1', 'q4mpa1',
        'q1mpa2', 'q2mpa2', 'q3mpa2', 'q4mpa2',
        'nsusp1', 'nsusp2', 'nsusp3', 'nsusp4'
    ];

    let presentCount = 0;
    let totalCount = requiredFields.length;
    const missingFields = [];

    requiredFields.forEach(field => {
        if (student[field] !== null && student[field] !== undefined && student[field] !== '') {
            presentCount++;
        } else {
            missingFields.push(field);
        }
    });

    const completenessScore = Math.round((presentCount / totalCount) * 100);

    // Determine quality level
    let qualityLevel = 'low';
    let qualityColor = '#E96666';
    let qualityIcon = '🔴';

    if (completenessScore >= 90) {
        qualityLevel = 'high';
        qualityColor = '#4CAF50';
        qualityIcon = '🟢';
    } else if (completenessScore >= 70) {
        qualityLevel = 'moderate';
        qualityColor = '#EBA84B';
        qualityIcon = '🟡';
    }

    return {
        completenessScore,
        qualityLevel,
        qualityColor,
        qualityIcon,
        presentCount,
        totalCount,
        missingFields: missingFields.map(field => formatFieldName(field)),
        hasSufficientData: completenessScore >= 70
    };
};

/**
 * Calculate confidence score for risk prediction
 * @param {Object} student - Student object
 * @returns {Object} Confidence metrics
 */
export const calculateConfidenceScore = (student) => {
    const quality = calculateDataQuality(student);

    // Confidence is based on data quality
    let confidenceScore = quality.completenessScore;
    let confidenceLevel = 'low';
    let confidenceColor = '#E96666';
    let confidenceBadge = '! Low Confidence';

    if (confidenceScore >= 85) {
        confidenceLevel = 'high';
        confidenceColor = '#4CAF50';
        confidenceBadge = '✓ High Confidence';
    } else if (confidenceScore >= 60) {
        confidenceLevel = 'moderate';
        confidenceColor = '#EBA84B';
        confidenceBadge = '~ Moderate Confidence';
    }

    return {
        confidenceScore,
        confidenceLevel,
        confidenceColor,
        confidenceBadge,
        dataQuality: quality
    };
};

/**
 * Format field name to human-readable
 * @param {string} field - Field name
 * @returns {string} Formatted name
 */
const formatFieldName = (field) => {
    const fieldMap = {
        'attendance': 'Attendance Rate',
        'gpa': 'GPA',
        'absrate1': 'Absence Rate (Period 1)',
        'absrate2': 'Absence Rate (Period 2)',
        'absrate3': 'Absence Rate (Period 3)',
        'absrate4': 'Absence Rate (Period 4)',
        'absrate5': 'Absence Rate (Period 5)',
        'absrate6': 'Absence Rate (Period 6)',
        'absrate7': 'Absence Rate (Period 7)',
        'q1mpa1': 'Q1 Marks (Year 1)',
        'q2mpa1': 'Q2 Marks (Year 1)',
        'q3mpa1': 'Q3 Marks (Year 1)',
        'q4mpa1': 'Q4 Marks (Year 1)',
        'nsusp1': 'Suspensions (Period 1)',
        'nsusp2': 'Suspensions (Period 2)',
        'nsusp3': 'Suspensions (Period 3)',
        'nsusp4': 'Suspensions (Period 4)'
    };

    return fieldMap[field] || field;
};

/**
 * Get data quality summary for display
 * @param {Object} student - Student object
 * @returns {string} Summary text
 */
export const getDataQualitySummary = (student) => {
    const quality = calculateDataQuality(student);

    if (quality.qualityLevel === 'high') {
        return `${quality.qualityIcon} High quality data (${quality.completenessScore}% complete)`;
    } else if (quality.qualityLevel === 'moderate') {
        return `${quality.qualityIcon} Moderate quality data (${quality.completenessScore}% complete, ${quality.missingFields.length} missing fields)`;
    } else {
        return `${quality.qualityIcon} Low quality data (${quality.completenessScore}% complete, ${quality.missingFields.length} missing fields)`;
    }
};
