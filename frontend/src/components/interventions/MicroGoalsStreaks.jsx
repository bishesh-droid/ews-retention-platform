import React, { useState, useEffect } from 'react';

/**
 * Micro-Goals and Streaks Component
 * 
 * BENEFIT: Gamified progress tracking for small wins
 * EXCLUSIVITY: Behavioral psychology-driven goal decomposition
 * USER TYPE: Students
 * LOCATION: Student Portal sidebar widget
 */

const MicroGoalsStreaks = ({ goals, streaks }) => {
    const [activeGoals, setActiveGoals] = useState([]);
    const [currentStreaks, setCurrentStreaks] = useState([]);
    const [celebrateAchievement, setCelebrateAchievement] = useState(null);

    useEffect(() => {
        if (goals) {
            setActiveGoals(goals);
        } else {
            // Default micro-goals
            setActiveGoals([
                { id: 1, text: 'Attend 3 classes this week', progress: 2, target: 3, completed: false },
                { id: 2, text: 'Complete 2 assignments', progress: 1, target: 2, completed: false },
                { id: 3, text: 'Watch 5 course videos', progress: 4, target: 5, completed: false },
                { id: 4, text: 'Join a study session', progress: 0, target: 1, completed: false }
            ]);
        }

        if (streaks) {
            setCurrentStreaks(streaks);
        } else {
            setCurrentStreaks([
                { type: 'daily_login', count: 7, emoji: '🔥' },
                { type: 'assignment_streak', count: 3, emoji: '📚' }
            ]);
        }
    }, [goals, streaks]);

    const handleGoalClick = (goalId) => {
        const goal = activeGoals.find(g => g.id === goalId);
        if (goal && goal.progress >= goal.target && !goal.completed) {
            setActiveGoals(activeGoals.map(g =>
                g.id === goalId ? { ...g, completed: true } : g
            ));
            setCelebrateAchievement(goal.text);
            setTimeout(() => setCelebrateAchievement(null), 3000);
        }
    };

    return (
        <div className="premium-card student-context" style={{ marginBottom: 'var(--space-lg)' }}>
            <div className="card-header" style={{ fontSize: 'var(--font-size-h3)', fontWeight: 'var(--font-weight-semibold)' }}>
                Your Goals & Streaks
            </div>

            {/* Streaks Section - Display typography, extrabold weight, vibrant color */}
            {currentStreaks.length > 0 && (
                <div style={{ marginBottom: 'var(--space-lg)', padding: 'var(--space-md)', background: 'linear-gradient(135deg, var(--student-primary), var(--student-success))', borderRadius: 'var(--radius-md)', color: 'white' }}>
                    {currentStreaks.map((streak, idx) => (
                        <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: idx < currentStreaks.length - 1 ? 'var(--space-sm)' : 0 }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                                <span style={{ fontSize: 'var(--font-size-h2)' }}>{streak.emoji}</span>
                                <span style={{ fontSize: 'var(--font-size-body)', fontWeight: 'var(--font-weight-medium)' }}>
                                    {getStreakName(streak.type)}
                                </span>
                            </div>
                            {/* Streak Counter - Display, extrabold weight, vibrant */}
                            <div style={{ fontSize: 'var(--font-size-display)', fontWeight: 'var(--font-weight-extrabold)', fontFamily: 'var(--font-family-mono)' }}>
                                {streak.count}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Micro-Goals - Body typography, regular weight */}
            <div>
                <div style={{ fontSize: 'var(--font-size-small)', fontWeight: 'var(--font-weight-semibold)', color: 'var(--gray-600)', marginBottom: 'var(--space-sm)', textTransform: 'uppercase', letterSpacing: 'var(--letter-spacing-wider)' }}>
                    This Week's Goals
                </div>

                {activeGoals.map((goal) => (
                    <GoalItem
                        key={goal.id}
                        goal={goal}
                        onClick={() => handleGoalClick(goal.id)}
                    />
                ))}
            </div>

            {/* Achievement Celebration */}
            {celebrateAchievement && (
                <div style={{
                    position: 'fixed',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    padding: 'var(--space-xl)',
                    background: 'var(--student-success)',
                    color: 'white',
                    borderRadius: 'var(--radius-lg)',
                    boxShadow: 'var(--shadow-xl)',
                    zIndex: 1000,
                    textAlign: 'center',
                    minWidth: '300px'
                }}>
                    <div style={{ fontSize: 'var(--font-size-display)' }}>🎉</div>
                    <div style={{ fontSize: 'var(--font-size-h2)', fontWeight: 'var(--font-weight-bold)', marginTop: 'var(--space-sm)' }}>
                        Goal Achieved!
                    </div>
                    <div style={{ fontSize: 'var(--font-size-body)', marginTop: 'var(--space-sm)', opacity: 0.9 }}>
                        {celebrateAchievement}
                    </div>
                </div>
            )}
        </div>
    );
};

const GoalItem = ({ goal, onClick }) => {
    const progressPercentage = (goal.progress / goal.target) * 100;
    const isComplete = goal.completed || goal.progress >= goal.target;

    return (
        <div
            onClick={onClick}
            style={{
                padding: 'var(--space-md)',
                background: isComplete ? 'var(--gray-100)' : 'white',
                border: `var(--border-width-thin) solid ${isComplete ? 'var(--student-success)' : 'var(--gray-200)'}`,
                borderRadius: 'var(--radius-md)',
                marginBottom: 'var(--space-sm)',
                cursor: isComplete && !goal.completed ? 'pointer' : 'default',
                transition: 'all var(--transition-fast)'
            }}
        >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 'var(--space-sm)' }}>
                {/* Goal Text - Body, regular weight */}
                <div style={{
                    fontSize: 'var(--font-size-body)',
                    fontWeight: 'var(--font-weight-regular)',
                    color: isComplete ? 'var(--gray-600)' : 'var(--gray-800)',
                    textDecoration: isComplete ? 'line-through' : 'none',
                    flex: 1
                }}>
                    {goal.text}
                </div>

                {/* Achievement Badge - Caption, semibold, uppercase */}
                {isComplete && (
                    <div style={{
                        fontSize: 'var(--font-size-caption)',
                        fontWeight: 'var(--font-weight-semibold)',
                        textTransform: 'uppercase',
                        color: 'var(--student-success)',
                        background: 'rgba(16, 185, 129, 0.1)',
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-sm)'
                    }}>
                        ✓ Done
                    </div>
                )}
            </div>

            {/* Progress Bar */}
            {!isComplete && (
                <>
                    <div style={{
                        width: '100%',
                        height: '6px',
                        background: 'var(--gray-200)',
                        borderRadius: 'var(--radius-full)',
                        overflow: 'hidden'
                    }}>
                        <div style={{
                            width: `${progressPercentage}%`,
                            height: '100%',
                            background: 'var(--student-primary)',
                            transition: 'width var(--transition-normal)'
                        }} />
                    </div>
                    <div style={{
                        fontSize: 'var(--font-size-caption)',
                        color: 'var(--gray-600)',
                        marginTop: 'var(--space-xs)',
                        fontFamily: 'var(--font-family-mono)'
                    }}>
                        {goal.progress} / {goal.target}
                    </div>
                </>
            )}
        </div>
    );
};

const getStreakName = (type) => {
    const names = {
        daily_login: 'Daily Login Streak',
        assignment_streak: 'Assignment Streak',
        attendance_streak: 'Perfect Attendance'
    };
    return names[type] || type;
};

export default MicroGoalsStreaks;
