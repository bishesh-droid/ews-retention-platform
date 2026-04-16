"""
Presentation serializers for student APIs.
"""

from typing import Dict, List


def build_weekly_summary_response(
    student: Dict, enrollments: List[Dict], engagement_improvement: float
) -> Dict:
    total_study_minutes = int(
        round(sum((e.get("total_time_spent_seconds") or 0) for e in enrollments) / 60)
    )
    resources_viewed = int(sum((e.get("content_completed") or 0) for e in enrollments))
    assignments_completed = int(
        sum((e.get("num_assignment_submissions") or 0) for e in enrollments)
    )
    attendance_rate_pct = float(student.get("exam_attendance_rate") or 0)
    attendance_rate = max(0.0, min(1.0, attendance_rate_pct / 100.0))
    return {
        "assignmentsCompleted": assignments_completed,
        "attendanceRate": round(attendance_rate, 4),
        "engagementImprovement": engagement_improvement,
        "missedAssignments": 0,
        "lowEngagementDays": 0,
        "totalStudyTimeMinutes": total_study_minutes,
        "facultyInteractions": 0,
        "resourcesViewed": resources_viewed,
    }
