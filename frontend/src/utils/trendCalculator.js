/**
 * Trend Calculator
 * Calculates trends, deltas, and changes for various metrics
 */

/**
 * Calculate trend for a metric
 * @param {number} current - Current value
 * @param {number} previous - Previous value
 * @returns {Object} Trend information
 */
export const calculateTrend = (current, previous) => {
    if (previous === null || previous === undefined || current === null || current === undefined) {
        return {
            direction: 'stable',
            delta: 0,
            deltaPercent: 0,
            arrow: '→',
            color: '#9E9E9E',
            message: 'No change'
        };
    }

    const delta = current - previous;
    const deltaPercent = previous !== 0 ? ((delta / previous) * 100) : 0;

    let direction = 'stable';
    let arrow = '→';
    let color = '#9E9E9E';
    let message = 'No change';

    if (Math.abs(delta) < 0.01 && Math.abs(deltaPercent) < 1) {
        // Stable - no significant change
        direction = 'stable';
        arrow = '→';
        color = '#9E9E9E';
        message = 'Stable';
    } else if (delta > 0) {
        direction = 'up';
        arrow = '↑';
        color = '#4CAF50';
        message = 'Increasing';
    } else {
        direction = 'down';
        arrow = '↓';
        color = '#E96666';
        message = 'Decreasing';
    }

    return {
        direction,
        delta: Math.abs(delta),
        deltaPercent: Math.abs(deltaPercent),
        deltaRaw: delta,
        arrow,
        color,
        message
    };
};

/**
 * Calculate risk trend (inverted logic - lower is better)
 * @param {number} current - Current risk score
 * @param {number} previous - Previous risk score
 * @returns {Object} Risk trend information
 */
export const calculateRiskTrend = (current, previous) => {
    const trend = calculateTrend(current, previous);

    // For risk scores, down is good (green), up is bad (red)
    if (trend.direction === 'down') {
        return {
            ...trend,
            color: '#4CAF50',
            message: 'Improving',
            isImproving: true
        };
    } else if (trend.direction === 'up') {
        return {
            ...trend,
            color: '#E96666',
            message: 'Deteriorating',
            isImproving: false
        };
    }

    return {
        ...trend,
        isImproving: null
    };
};

/**
 * Calculate attendance trend (higher is better)
 * @param {number} current - Current attendance
 * @param {number} previous - Previous attendance
 * @returns {Object} Attendance trend
 */
export const calculateAttendanceTrend = (current, previous) => {
    const trend = calculateTrend(current, previous);

    // For attendance, up is good (green), down is bad (red)
    if (trend.direction === 'up') {
        return {
            ...trend,
            color: '#4CAF50',
            message: 'Improving',
            isImproving: true
        };
    } else if (trend.direction === 'down') {
        return {
            ...trend,
            color: '#E96666',
            message: 'Declining',
            isImproving: false
        };
    }

    return {
        ...trend,
        isImproving: null
    };
};

/**
 * Format delta for display
 * @param {number} delta - Delta value
 * @param {boolean} showSign - Whether to show +/- sign
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted delta
 */
export const formatDelta = (delta, showSign = true, decimals = 1) => {
    const sign = delta > 0 ? '+' : '';
    return `${showSign ? sign : ''}${delta.toFixed(decimals)}`;
};

/**
 * Format delta percent for display
 * @param {number} deltaPercent - Delta percentage
 * @param {boolean} showSign - Whether to show +/- sign
 * @returns {string} Formatted percentage
 */
export const formatDeltaPercent = (deltaPercent, showSign = true) => {
    const sign = deltaPercent > 0 ? '+' : '';
    return `${showSign ? sign : ''}${deltaPercent.toFixed(1)}%`;
};

/**
 * Get trend icon based on direction and metric type
 * @param {string} direction - Trend direction (up/down/stable)
 * @param {boolean} invertLogic - Whether lower is better (for risk scores)
 * @returns {string} Icon
 */
export const getTrendIcon = (direction, invertLogic = false) => {
    if (direction === 'stable') return '→';

    if (invertLogic) {
        return direction === 'down' ? '↓' : '↑';
    }

    return direction === 'up' ? '↑' : '↓';
};

/**
 * Generate trend description
 * @param {Object} trend - Trend object
 * @param {string} metricName - Name of the metric
 * @param {string} unit - Unit of measurement
 * @returns {string} Description
 */
export const getTrendDescription = (trend, metricName, unit = 'pts') => {
    if (trend.direction === 'stable') {
        return `${metricName} stable (no significant change)`;
    }

    const deltaStr = formatDelta(trend.deltaRaw, true, 1);
    const percentStr = formatDeltaPercent(trend.deltaPercent, false);

    return `${metricName} ${trend.message.toLowerCase()} by ${deltaStr} ${unit} (${percentStr})`;
};

/**
 * Mock function to calculate previous week's risk score
 * In production, this would fetch from historical data
 * @param {Object} student - Student object
 * @returns {number} Previous risk score
 */
export const getPreviousRiskScore = (student) => {
    // Mock: Generate a previous score based on current score
    const variation = (Math.random() - 0.5) * 20; // ±10 points
    return Math.max(0, Math.min(100, student.risk_score + variation));
};

/**
 * Mock function to calculate previous attendance
 * @param {Object} student - Student object
 * @returns {number} Previous attendance
 */
export const getPreviousAttendance = (student) => {
    const current = student.attendance || 75;
    const variation = (Math.random() - 0.5) * 10; // ±5%
    return Math.max(0, Math.min(100, current + variation));
};
