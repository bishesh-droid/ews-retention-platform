"""
Feature Engineering Service
Aggregates raw events into engineered features organized by 5 signal categories:
1. Academic Performance
2. Engagement
3. Consistency
4. Intent
5. Responsiveness
"""

from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional
import json
import numpy as np

from backend.database import RawEvent, EngineeredFeatures, Student


def compute_academic_signals(student_id: str, db: Session, lookback_days: int = 90) -> Dict[str, float]:  # noqa: C901
    """
    Compute academic performance signals from LMS events

    Returns:
        - assignment_completion_rate
        - average_grade
        - deadline_adherence_score
        - grade_trend
    """
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

    # Get LMS assignment events
    events = db.query(RawEvent).filter(
        RawEvent.student_id == student_id,
        RawEvent.event_source == "lms",
        RawEvent.event_type.in_(["assignment_submit", "grade_posted"]),
        RawEvent.timestamp >= cutoff_date
    ).all()

    if not events:
        # Fallback to existing student data
        student = db.query(Student).filter(Student.id == student_id).first()
        if student:
            # Use existing absrate and GPA data as proxy
            avg_grade = getattr(student, 'q4mpa7', 0) * 20  # Scale 0-5 to 0-100
            return {
                # Assume absrate relates to completion
                "assignment_completion_rate": 1.0 - getattr(student, 'absrate7', 0.5),
                "average_grade": avg_grade,
                "deadline_adherence_score": 0.8,  # Default
                "grade_trend": 0.0
            }
        return {
            "assignment_completion_rate": 0.5,
            "average_grade": 50.0,
            "deadline_adherence_score": 0.5,
            "grade_trend": 0.0
        }

    # Parse events
    assignments = []
    grades = []
    on_time = 0
    total_assignments = 0

    for event in events:
        data = json.loads(str(event.event_data)) if event.event_data else {}

        if event.event_type == "assignment_submit":
            total_assignments += 1
            if not data.get("submitted_late", False):
                on_time += 1

            if "score" in data:
                assignments.append({
                    "score": data["score"],
                    "max_score": data.get("max_score", 100),
                    "timestamp": event.timestamp
                })

        if event.event_type == "grade_posted" and "grade" in data:
            grades.append({
                "grade": data["grade"],
                "timestamp": event.timestamp
            })

    # Calculate metrics
    completion_rate = len(assignments) / max(total_assignments, 1)

    avg_grade = 0.0
    if assignments:
        avg_grade = np.mean([a["score"] / a["max_score"] * 100 for a in assignments])
    elif grades:
        avg_grade = np.mean([g["grade"] for g in grades])

    deadline_adherence = on_time / max(total_assignments, 1)

    # Calculate grade trend (simple linear regression)
    grade_trend = 0.0
    if len(assignments) >= 3:
        sorted_assignments = sorted(assignments, key=lambda x: x["timestamp"])
        scores = [a["score"] / a["max_score"] * 100 for a in sorted_assignments]
        x = np.arange(len(scores))
        z = np.polyfit(x, scores, 1)
        grade_trend = z[0]  # Slope

    return {
        "assignment_completion_rate": min(completion_rate, 1.0),
        "average_grade": avg_grade,
        "deadline_adherence_score": deadline_adherence,
        "grade_trend": grade_trend / 100.0  # Normalize
    }


def compute_engagement_signals(student_id: str, db: Session, lookback_days: int = 30) -> Dict[str, float]:
    """
    Compute engagement signals from LMS logins and website activity

    Returns:
        - login_frequency (logins per week)
        - avg_session_duration (minutes)
        - video_completion_rate
        - platform_interaction_score
    """
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

    # Get login events
    login_events = db.query(RawEvent).filter(
        RawEvent.student_id == student_id,
        RawEvent.event_source == "lms",
        RawEvent.event_type == "login",
        RawEvent.timestamp >= cutoff_date
    ).all()

    # Get website events
    website_events = db.query(RawEvent).filter(
        RawEvent.student_id == student_id,
        RawEvent.event_source == "website",
        RawEvent.timestamp >= cutoff_date
    ).all()

    # Login frequency
    login_count = len(login_events)
    weeks = lookback_days / 7.0
    login_frequency = login_count / weeks

    # Session duration (placeholder - would need session tracking)
    avg_session_duration = 30.0  # Default 30 minutes

    # Video completion rate
    video_events = [
        e for e in website_events
        if json.loads(str(e.event_data) if e.event_data else "{}").get("event_type") == "video_watch"
    ]
    if video_events:
        completion_rates = []
        for event in video_events:
            data = json.loads(str(event.event_data) if event.event_data else "{}")
            completion_rates.append(data.get("watch_percentage", 0) / 100.0)
        video_completion_rate = np.mean(completion_rates)
    else:
        video_completion_rate = 0.5  # Default

    # Platform interaction score (clicks, page views)
    interaction_count = len(website_events)
    platform_interaction_score = min(interaction_count / 100.0, 1.0)  # Normalize to 0-1

    return {
        "login_frequency": login_frequency,
        "avg_session_duration": avg_session_duration,
        "video_completion_rate": video_completion_rate,
        "platform_interaction_score": platform_interaction_score
    }


def compute_consistency_signals(student_id: str, db: Session, lookback_days: int = 60) -> Dict[str, Any]:
    """
    Compute consistency signals from Zoom attendance

    Returns:
        - attendance_rate
        - activity_regularity_score
        - missed_classes_count
        - attendance_trend
    """
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

    # Get Zoom attendance events
    zoom_events = db.query(RawEvent).filter(
        RawEvent.student_id == student_id,
        RawEvent.event_source == "zoom",
        RawEvent.event_type == "class_attend",
        RawEvent.timestamp >= cutoff_date
    ).all()

    # Fallback to existing student data
    student = db.query(Student).filter(Student.id == student_id).first()

    if not zoom_events and student:
        absrate = getattr(student, 'absrate7', 0.3)
        return {
            "attendance_rate": 1.0 - absrate,
            "activity_regularity_score": 0.7,  # Default
            "missed_classes_count": int(absrate * 20),  # Estimate
            "attendance_trend": 0.0
        }

    # Calculate metrics
    total_classes = 20  # Expected number of classes in lookback period (placeholder)
    attended = len(zoom_events)
    missed = total_classes - attended

    attendance_rate = attended / max(total_classes, 1)

    # Activity regularity (variance in daily activity)
    # Low variance = high regularity
    activity_regularity_score = 0.7  # Placeholder

    # Attendance trend
    attendance_trend = 0.0
    if len(zoom_events) >= 5:
        sorted_events = sorted(zoom_events, key=lambda x: x.timestamp or datetime.min)  # type: ignore[arg-type]
        # Simple: compare first half vs second half
        mid = len(sorted_events) // 2
        first_half = len(sorted_events[:mid])
        second_half = len(sorted_events[mid:])
        attendance_trend = (second_half - first_half) / max(first_half, 1)

    return {
        "attendance_rate": min(attendance_rate, 1.0),
        "activity_regularity_score": activity_regularity_score,
        "missed_classes_count": missed,
        "attendance_trend": attendance_trend
    }


def compute_intent_signals(student_id: str, db: Session, lookback_days: int = 30) -> Dict[str, Any]:
    """
    Compute intent signals (declining trends, inactivity)

    Returns:
        - engagement_trend
        - days_inactive
        - declining_performance_flag
    """
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

    # Get all recent events
    all_events = db.query(RawEvent).filter(
        RawEvent.student_id == student_id,
        RawEvent.timestamp >= cutoff_date
    ).order_by(RawEvent.timestamp.desc()).all()

    # Days inactive
    days_inactive = 0
    if all_events:
        last_event = all_events[0]
        if last_event.timestamp:
            days_inactive = (datetime.utcnow() - last_event.timestamp).days  # type: ignore[operator]
    else:
        days_inactive = lookback_days

    # Engagement trend (compare first half vs second half of period)
    mid_date = cutoff_date + timedelta(days=lookback_days // 2)
    first_half = [e for e in all_events if e.timestamp and e.timestamp < mid_date]  # type: ignore[operator]
    second_half = [e for e in all_events if e.timestamp and e.timestamp >= mid_date]  # type: ignore[operator]

    engagement_trend = 0.0
    if first_half:
        engagement_trend = (len(second_half) - len(first_half)) / max(len(first_half), 1)

    # Declining performance flag
    # Get academic and engagement signals
    academic = compute_academic_signals(student_id, db, lookback_days)
    declining_performance_flag = (
        academic["grade_trend"] < -0.1 and engagement_trend < -0.2
    )

    return {
        "engagement_trend": engagement_trend,
        "days_inactive": days_inactive,
        "declining_performance_flag": declining_performance_flag
    }


def compute_responsiveness_signals(student_id: str, db: Session, lookback_days: int = 30) -> Dict[str, float]:
    """
    Compute responsiveness signals from communication events

    Returns:
        - email_open_rate
        - message_reply_rate
        - avg_response_time_hours
    """
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

    # Get communication events
    comm_events = db.query(RawEvent).filter(
        RawEvent.student_id == student_id,
        RawEvent.event_source == "communication",
        RawEvent.timestamp >= cutoff_date
    ).all()

    if not comm_events:
        return {
            "email_open_rate": 0.5,  # Default
            "message_reply_rate": 0.4,
            "avg_response_time_hours": 24.0
        }

    # Parse events
    emails_sent = 0
    emails_opened = 0
    messages_sent = 0
    messages_replied = 0
    response_times = []

    for event in comm_events:
        data = json.loads(str(event.event_data) if event.event_data else "{}")

        if event.event_type == "email_send":
            emails_sent += 1
        elif event.event_type == "email_open":
            emails_opened += 1
        elif event.event_type == "message_reply":
            messages_replied += 1
            messages_sent += 1  # Assume every reply had a message
            if "response_time_hours" in data:
                response_times.append(data["response_time_hours"])

    email_open_rate = emails_opened / max(emails_sent, 1)
    message_reply_rate = messages_replied / max(messages_sent, 1)
    avg_response_time = np.mean(response_times) if response_times else 24.0

    return {
        "email_open_rate": email_open_rate,
        "message_reply_rate": message_reply_rate,
        "avg_response_time_hours": avg_response_time
    }


def compute_all_features(student_id: str, db: Session) -> Optional[EngineeredFeatures]:
    """
    Orchestrate feature computation for all signal categories

    Returns:
        EngineeredFeatures object ready to be saved
    """
    try:
        # Compute all signal categories
        academic = compute_academic_signals(student_id, db)
        engagement = compute_engagement_signals(student_id, db)
        consistency = compute_consistency_signals(student_id, db)
        intent = compute_intent_signals(student_id, db)
        responsiveness = compute_responsiveness_signals(student_id, db)

        # Create EngineeredFeatures object
        features = EngineeredFeatures(  # type: ignore[arg-type]
            student_id=student_id,
            computation_date=date.today(),
            # Academic
            assignment_completion_rate=academic["assignment_completion_rate"],
            average_grade=academic["average_grade"],
            deadline_adherence_score=academic["deadline_adherence_score"],
            grade_trend=academic["grade_trend"],
            # Engagement
            login_frequency=engagement["login_frequency"],
            avg_session_duration=engagement["avg_session_duration"],
            video_completion_rate=engagement["video_completion_rate"],
            platform_interaction_score=engagement["platform_interaction_score"],
            # Consistency
            attendance_rate=consistency["attendance_rate"],
            activity_regularity_score=consistency["activity_regularity_score"],
            missed_classes_count=consistency["missed_classes_count"],
            attendance_trend=consistency["attendance_trend"],
            # Intent
            engagement_trend=intent["engagement_trend"],
            days_inactive=intent["days_inactive"],
            declining_performance_flag=intent["declining_performance_flag"],
            # Responsiveness
            email_open_rate=responsiveness["email_open_rate"],
            message_reply_rate=responsiveness["message_reply_rate"],
            avg_response_time_hours=responsiveness["avg_response_time_hours"]
        )

        return features

    except Exception as e:
        print(f"Error computing features for student {student_id}: {e}")
        return None
