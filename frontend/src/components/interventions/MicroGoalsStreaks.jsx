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
        <div style={{ backgroundColor: '#130D23', border: '1px solid rgba(139,92,246,0.18)', borderRadius: '16px', padding: '20px', marginBottom: '20px' }}>
            <div style={{ fontSize: '16px', fontWeight: 700, color: '#EDE9FE', marginBottom: '16px' }}>
                Your Goals &amp; Streaks
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

            {/* Micro-Goals */}
            <div>
                <div style={{ fontSize: '11px', fontWeight: 700, color: '#8B7DB8', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.12em' }}>
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
                padding: '12px 14px',
                backgroundColor: isComplete ? 'rgba(16,185,129,0.08)' : '#1A1035',
                border: `1px solid ${isComplete ? 'rgba(16,185,129,0.35)' : 'rgba(139,92,246,0.2)'}`,
                borderRadius: '12px',
                marginBottom: '8px',
                cursor: isComplete && !goal.completed ? 'pointer' : 'default',
                transition: 'all 0.2s ease'
            }}
        >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{
                    fontSize: '13px',
                    fontWeight: 500,
                    color: isComplete ? '#6B7280' : '#DDD6FE',
                    textDecoration: isComplete ? 'line-through' : 'none',
                    flex: 1
                }}>
                    {goal.text}
                </div>
                {isComplete && (
                    <div style={{
                        fontSize: '10px', fontWeight: 700, textTransform: 'uppercase',
                        color: '#10B981', background: 'rgba(16,185,129,0.15)',
                        padding: '2px 8px', borderRadius: '6px', marginLeft: '8px', flexShrink: 0
                    }}>
                        ✓ Done
                    </div>
                )}
            </div>

            {!isComplete && (
                <>
                    <div style={{ width: '100%', height: '5px', backgroundColor: 'rgba(139,92,246,0.15)', borderRadius: '99px', overflow: 'hidden' }}>
                        <div style={{
                            width: `${progressPercentage}%`, height: '100%',
                            background: 'linear-gradient(90deg, #7C3AED, #A78BFA)',
                            borderRadius: '99px', transition: 'width 0.4s ease'
                        }} />
                    </div>
                    <div style={{ fontSize: '11px', color: '#8B7DB8', marginTop: '5px', fontFamily: 'monospace' }}>
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
