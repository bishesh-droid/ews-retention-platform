/**
 * Timeline Data Generator
 * Generates formatted timeline events for student activity visualization
 */

/**
 * Generate timeline events for a student
 * @param {Object} student - Student object
 * @returns {Array} Array of timeline event objects
 */
export const generateTimelineEvents = (student) => {
    const events = [];
    const today = new Date();

    // Mock attendance events
    if (student.absrate1 !== undefined && student.absrate1 > 0.3) {
        events.push({
            id: `att-1`,
            type: 'attendance',
            category: 'Attendance',
            title: 'Absence Pattern Detected',
            description: `Absence rate: ${(student.absrate1 * 100).toFixed(1)}%`,
            date: new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000), // 7 days ago
            severity: 'warning',
            icon: '📅',
            color: '#EBA84B'
        });
    }

    // Mock grade events
    if (student.q1mpa1 !== undefined) {
        events.push({
            id: `grade-1`,
            type: 'grade',
            category: 'Academic',
            title: 'Q1 Grade Submitted',
            description: `Score: ${student.q1mpa1.toFixed(2)}`,
            date: new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
            severity: student.q1mpa1 < 2.0 ? 'danger' : 'success',
            icon: '📝',
            color: student.q1mpa1 < 2.0 ? '#E96666' : '#4CAF50'
        });
    }

    // Mock risk score changes
    events.push({
        id: `risk-1`,
        type: 'risk',
        category: 'Risk Assessment',
        title: 'Risk Score Updated',
        description: `New risk score: ${student.risk_score}`,
        date: new Date(today.getTime() - 1 * 24 * 60 * 60 * 1000), // 1 day ago
        severity: student.risk_score > 75 ? 'danger' : student.risk_score > 50 ? 'warning' : 'info',
        icon: '⚠️',
        color: student.risk_score > 75 ? '#E96666' : student.risk_score > 50 ? '#EBA84B' : '#64B5F6'
    });

    // Mock intervention events
    if (student.risk_score > 60) {
        events.push({
            id: `intervention-1`,
            type: 'intervention',
            category: 'Intervention',
            title: 'Intervention Recommended',
            description: 'Academic coaching suggested based on risk profile',
            date: new Date(today.getTime() - 2 * 24 * 60 * 60 * 1000), // 2 days ago
            severity: 'info',
            icon: '🎯',
            color: '#2B2B88'
        });
    }

    // Mock engagement events
    events.push({
        id: `engagement-1`,
        type: 'engagement',
        category: 'Engagement',
        title: 'LMS Login',
        description: 'Student accessed learning platform',
        date: new Date(today.getTime() - 0.5 * 24 * 60 * 60 * 1000), // 12 hours ago
        severity: 'success',
        icon: '💻',
        color: '#4CAF50'
    });

    // Mock behavioral events
    if (student.nsusp1 && student.nsusp1 > 0) {
        events.push({
            id: `behavioral-1`,
            type: 'behavioral',
            category: 'Behavioral',
            title: 'Disciplinary Incident',
            description: `Suspension recorded`,
            date: new Date(today.getTime() - 14 * 24 * 60 * 60 * 1000), // 14 days ago
            severity: 'danger',
            icon: '⚡',
            color: '#E96666'
        });
    }

    // Sort by date (newest first)
    return events.sort((a, b) => b.date - a.date);
};

/**
 * Filter timeline events by type
 * @param {Array} events - Array of events
 * @param {string} type - Event type filter
 * @returns {Array} Filtered events
 */
export const filterEventsByType = (events, type) => {
    if (!type || type === 'all') return events;
    return events.filter(event => event.type === type);
};

/**
 * Filter timeline events by date range
 * @param {Array} events - Array of events
 * @param {Date} startDate - Start date
 * @param {Date} endDate - End date
 * @returns {Array} Filtered events
 */
export const filterEventsByDateRange = (events, startDate, endDate) => {
    return events.filter(event => {
        const eventDate = new Date(event.date);
        return eventDate >= startDate && eventDate <= endDate;
    });
};

/**
 * Format date for display
 * @param {Date} date - Date object
 * @returns {string} Formatted date string
 */
export const formatEventDate = (date) => {
    const now = new Date();
    const diffMs = now - date;
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor(diffMs / (1000 * 60));

    if (diffMinutes < 60) {
        return `${diffMinutes} minute${diffMinutes !== 1 ? 's' : ''} ago`;
    } else if (diffHours < 24) {
        return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
    } else if (diffDays < 7) {
        return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    } else if (diffDays < 30) {
        const weeks = Math.floor(diffDays / 7);
        return `${weeks} week${weeks !== 1 ? 's' : ''} ago`;
    } else {
        return date.toLocaleDateString();
    }
};

/**
 * Get event type icon
 * @param {string} type - Event type
 * @returns {string} Icon emoji
 */
export const getEventTypeIcon = (type) => {
    const iconMap = {
        'attendance': '📅',
        'grade': '📝',
        'risk': '⚠️',
        'intervention': '🎯',
        'engagement': '💻',
        'behavioral': '⚡',
        'note': '📌'
    };
    return iconMap[type] || '•';
};

/**
 * Get severity color
 * @param {string} severity - Severity level
 * @returns {string} Color hex code
 */
export const getSeverityColor = (severity) => {
    const colorMap = {
        'danger': '#E96666',
        'warning': '#EBA84B',
        'info': '#64B5F6',
        'success': '#4CAF50'
    };
    return colorMap[severity] || '#9E9E9E';
};
