"""
T1 Exam Outcome Calibration Script
----------------------------------
Standalone analysis tool for calibrating risk score thresholds against
actual T1 exam outcomes.

Requirements:
    pip install pandas matplotlib scikit-learn

Usage:
    cd /home/duffer/Gemini/Project_1(complete)/ews-retention-platform
    python -m backend.ml.training.calibrate

Outputs:
    - Console: Threshold analysis table and recommended config values
    - backend/ml/outputs/threshold_calibration.png: Precision-Recall curve
"""

from backend.services.risk_scoring import RiskScorer
from backend.services.feature_engineering import FeatureEngineer
from backend.database.models.goals_and_risks import RiskSnapshot
from backend.database.models.academic import ExamRecord
from backend.database.models.enrollment import Enrollment
from backend.database.models.student import Student
from backend.database.connection import SessionLocal
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt
import matplotlib
from sqlalchemy.orm import Session
from sqlalchemy import or_
import pandas as pd
import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


# Matplotlib setup (non-interactive backend for scripts)
matplotlib.use("Agg")

# Import sklearn metrics

# Database imports


def load_t1_outcomes(db_session: Session) -> pd.DataFrame:
    """
    Load T1 exam records and label outcomes based on performance.

    Returns DataFrame with columns:
        - org_id: Student's org_defined_id
        - course_name: Course name
        - score_pct: Normalized score percentage (obtained/total * 100)
        - present: Attendance boolean
        - outcome: "at_risk" if (score_pct < 40 OR present == False), else "passed"

    Also computes per-student aggregate where student_outcome = "at_risk"
    if AT LEAST ONE course outcome == "at_risk".
    """
    # Query all ExamRecord rows for T1
    records = (
        db_session.query(
            Student.org_defined_id,
            Student.id.label("student_id"),
            ExamRecord.course_name,
            ExamRecord.marks_obtained,
            ExamRecord.marks_total,
            ExamRecord.present,
        )
        .join(Student, ExamRecord.student_id == Student.id)
        .filter(
            or_(
                ExamRecord.course_name.ilike("%Trimester 1%"),
                ExamRecord.course_name.ilike("%T1%"),
            )
        )
        .all()
    )

    if not records:
        # Try broader search if no semester-specific matches
        records = (
            db_session.query(
                Student.org_defined_id,
                Student.id.label("student_id"),
                ExamRecord.course_name,
                ExamRecord.marks_obtained,
                ExamRecord.marks_total,
                ExamRecord.present,
            )
            .join(Student, ExamRecord.student_id == Student.id)
            .all()
        )

    data = []
    for rec in records:
        org_id = rec.org_defined_id
        course_name = rec.course_name
        obtained = rec.marks_obtained or 0
        total = rec.marks_total or 1  # Avoid div by zero
        present = rec.present if rec.present is not None else True

        # Normalize to percentage (handles varying total marks: 40, 35, 50, etc.)
        score_pct = (obtained / total) * 100 if total > 0 else 0

        # Label outcome
        outcome = "at_risk" if (score_pct < 40 or not present) else "passed"

        data.append(
            {
                "org_id": org_id,
                "student_id": rec.student_id,
                "course_name": course_name,
                "score_pct": round(score_pct, 2),
                "present": present,
                "outcome": outcome,
            }
        )

    df = pd.DataFrame(data)

    # Compute per-student aggregate outcome
    if not df.empty:
        # Group by student, check if any course is at_risk
        student_outcomes = (
            df.groupby(["org_id", "student_id"])
            .apply(
                lambda x: "at_risk" if (x["outcome"] == "at_risk").any() else "passed"
            )
            .reset_index(name="student_outcome")
        )
        # Merge back
        df = df.merge(student_outcomes, on=["org_id", "student_id"], how="left")
    else:
        df["student_outcome"] = pd.Series(dtype="object")

    return df


def load_t1_risk_features(db_session: Session) -> pd.DataFrame:
    """
    For each T1 student, retroactively compute feature vector using their
    T1 enrollment data.

    If RiskSnapshot records exist for T1 students, use those directly
    for the risk_score instead of recalculating.

    Returns DataFrame with columns:
        - org_id: Student's org_defined_id
        - content_completion_score
        - login_consistency_score
        - quiz_engagement_score
        - assignment_score
        - time_investment_score
        - discussion_engagement_score (discussion_score in output)
        - risk_score
    """
    # Get all students who have exam records (T1 cohort)
    student_ids = (
        db_session.query(Student.id, Student.org_defined_id)
        .join(ExamRecord, Student.id == ExamRecord.student_id)
        .distinct()
        .all()
    )

    if not student_ids:
        print("Warning: No students with exam records found")
        return pd.DataFrame()

    # Fetch all enrollments for these students
    student_id_list = [s.id for s in student_ids]
    enrollments = (
        db_session.query(Enrollment)
        .filter(Enrollment.student_id.in_(student_id_list))
        .all()
    )

    # Group enrollments by student_id
    enrollments_by_student: dict = {}
    for e in enrollments:
        if e.student_id not in enrollments_by_student:
            enrollments_by_student[e.student_id] = []
        enrollments_by_student[e.student_id].append(
            {
                "course_id": e.course_id,
                "course_name": (
                    e.course.student.name if hasattr(e, "course") and e.course else ""
                ),
                "content_completed": e.content_completed,
                "content_required": e.content_required,
                "content_required_w1w2": e.content_required_w1w2,
                "quiz_completed": e.quiz_completed,
                "total_quiz_attempts": e.total_quiz_attempts,
                "discussion_posts_created": e.discussion_posts_created,
                "discussion_post_replies": e.discussion_post_replies,
                "discussion_posts_read": e.discussion_posts_read,
                "num_assignment_submissions": e.num_assignment_submissions,
                "total_time_spent_seconds": e.total_time_spent_seconds,
                "num_logins": e.num_logins,
                "last_system_login": e.last_system_login,
                "last_visited_date": e.last_visited_date,
                "last_assignment_submission_date": e.last_assignment_submission_date,
                "last_quiz_attempt_date": e.last_quiz_attempt_date,
                "last_discussion_post_date": e.last_discussion_post_date,
                "last_scorm_visit_date": e.last_scorm_visit_date,
                "last_scorm_completion_date": e.last_scorm_completion_date,
            }
        )

    # Check for RiskSnapshot records
    snapshots = (
        db_session.query(RiskSnapshot)
        .filter(RiskSnapshot.student_id.in_(student_id_list))
        .all()
    )
    risk_by_student = {s.student_id: s.risk_score for s in snapshots}

    data = []
    for student in student_id_list:
        org_id = next((s.org_defined_id for s in student_ids if s.id == student), None)
        student_enrollments = enrollments_by_student.get(student, [])

        if not student_enrollments:
            # No enrollment data, skip or use defaults
            continue

        # Calculate features using FeatureEngineer
        features = FeatureEngineer.calculate_all_features(
            student_enrollments,
            graded_components=[],  # No graded components for retroactive T1 calculation
            exam_records=[],  # Don't include exam data in feature calc for calibration
            is_new_student=False,
            week_number=None,
        )

        # Use RiskSnapshot if available, otherwise calculate risk score
        if student in risk_by_student and risk_by_student[student] is not None:
            risk_score = RiskScorer.normalize_risk_to_0_100(risk_by_student[student])
            if risk_score is None:
                risk_score = 50.0
        else:
            risk_score = RiskScorer.calculate_risk_score(
                features,
                graded_components=[],
                program=None,
                current_week=None,
            )

        # Also add risk_score to features dict for engagement pattern calculation
        features["risk_score"] = risk_score
        # Recalculate engagement pattern with the risk score
        features["engagement_pattern"] = FeatureEngineer.classify_engagement_pattern(
            features
        )

        data.append(
            {
                "org_id": org_id,
                "student_id": student,
                "content_completion_score": features.get("content_completion_score", 0),
                "login_consistency_score": features.get("login_consistency_score", 0),
                "quiz_engagement_score": features.get("quiz_engagement_score", 0),
                "assignment_score": features.get("assignment_score", 0),
                "time_investment_score": features.get("time_investment_score", 0),
                "discussion_score": features.get("discussion_engagement_score", 0),
                "risk_score": risk_score,
                "engagement_pattern": features.get("engagement_pattern", "on_track"),
            }
        )

    return pd.DataFrame(data)


def run_threshold_analysis(
    features_df: pd.DataFrame, outcomes_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Run threshold analysis comparing predicted vs actual outcomes.

    For each threshold t in range(20, 90, 5):
        - predicted_at_risk = risk_score >= t
        - actual_at_risk = student_outcome == "at_risk"

    Computes: TP, FP, FN, TN, precision, recall, f1, fpr

    Returns DataFrame with metrics per threshold.
    """
    # Get unique students with their aggregate outcome
    student_outcomes = outcomes_df.drop_duplicates(subset=["org_id", "student_id"])[
        ["org_id", "student_id", "student_outcome"]
    ]

    # Join features with outcomes
    merged = features_df.merge(
        student_outcomes, left_on="student_id", right_on="student_id", how="inner"
    )

    if merged.empty:
        print("Error: No matching students between features and outcomes")
        return pd.DataFrame()

    # Ensure binary labels
    merged["actual_at_risk"] = (merged["student_outcome"] == "at_risk").astype(int)

    results = []
    thresholds = range(20, 90, 5)

    for t in thresholds:
        merged["predicted_at_risk"] = (merged["risk_score"] >= t).astype(int)

        y_true = merged["actual_at_risk"].values
        y_pred = merged["predicted_at_risk"].values

        # Compute confusion matrix components
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

        # Calculate metrics
        precision = precision_score(y_true, y_pred, zero_division=0)
        recall = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)

        # False Positive Rate = FP / (FP + TN)
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        results.append(
            {
                "threshold": t,
                "tp": int(tp),
                "fp": int(fp),
                "fn": int(fn),
                "tn": int(tn),
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1": round(f1, 4),
                "fpr": round(fpr, 4),
                "flagged_count": int(tp + fp),
                "flagged_pct": round((tp + fp) / len(merged) * 100, 1),
            }
        )

    metrics_df = pd.DataFrame(results)

    # Print clean summary table
    print("\n" + "=" * 80)
    print("THRESHOLD ANALYSIS RESULTS")
    print("=" * 80)
    print(
        f"{'Threshold':<12} {'TP':<6} {'FP':<6} {'FN':<6} {'TN':<6} "
        f"{'Precision':<10} {'Recall':<8} {'F1':<8} {'Flagged %':<10}"
    )
    print("-" * 80)
    for _, row in metrics_df.iterrows():
        print(
            f"{row['threshold']:<12} {row['tp']:<6} {row['fp']:<6} {row['fn']:<6} {row['tn']:<6} "
            f"{row['precision']:<10.2f} {row['recall']:<8.2f} {row['f1']:<8.2f} "
            f"{row['flagged_pct']:<10.1f}"
        )
    print("=" * 80)

    return metrics_df


def recommend_threshold(metrics_df: pd.DataFrame, min_recall: float = 0.75) -> float:
    """
    Find the highest-precision threshold where recall >= min_recall.

    Prints recommendation details and returns the threshold as float.
    """
    # Filter to thresholds meeting min_recall
    valid = metrics_df[metrics_df["recall"] >= min_recall]

    if valid.empty:
        print(f"\nWarning: No threshold achieves recall >= {min_recall}")
        # Fall back to highest recall threshold
        best_idx = metrics_df["recall"].idxmax()
        best = metrics_df.loc[best_idx]
    else:
        # Among valid thresholds, pick highest precision
        best_idx = valid["precision"].idxmax()
        best = metrics_df.loc[best_idx]

    t = int(best["threshold"])
    p = best["precision"]
    r = best["recall"]
    f = best["f1"]
    n_flagged = int(best["flagged_count"])
    total = n_flagged + int(best["tn"])
    pct = best["flagged_pct"]

    print("\n" + "=" * 80)
    print("RECOMMENDED THRESHOLD")
    print("=" * 80)
    print(
        f"Recommended threshold: {t} | Precision: {p:.2f} | Recall: {r:.2f} | F1: {f:.2f}"
    )
    print(
        f"At this threshold, {n_flagged} students flagged as at-risk out of {total} ({pct:.1f}%)"
    )
    print("=" * 80)

    return float(t)


def plot_precision_recall_curve(
    metrics_df: pd.DataFrame, recommended_t: float, output_path: str
):
    """
    Save a matplotlib precision-recall curve figure.

    X-axis: recall, Y-axis: precision
    Marks the recommended threshold point.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot PR curve
    ax.plot(
        metrics_df["recall"],
        metrics_df["precision"],
        "b-",
        linewidth=2,
        label="Precision-Recall Curve",
    )

    # Mark recommended threshold
    rec_row = metrics_df[metrics_df["threshold"] == recommended_t]
    if not rec_row.empty:
        ax.plot(
            rec_row["recall"].values[0],
            rec_row["precision"].values[0],
            "ro",
            markersize=10,
            label=f"Recommended Threshold ({int(recommended_t)})",
        )

    # Add threshold annotations
    for _, row in metrics_df.iterrows():
        if int(row["threshold"]) % 10 == 0:  # Annotate every 10th threshold
            ax.annotate(
                f"{int(row['threshold'])}",
                (row["recall"], row["precision"]),
                textcoords="offset points",
                xytext=(5, 5),
                fontsize=8,
                alpha=0.7,
            )

    ax.set_xlabel("Recall", fontsize=12)
    ax.set_ylabel("Precision", fontsize=12)
    ax.set_title("T1 Cohort — Risk Score Threshold Calibration", fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best")
    ax.set_xlim(0, 1.05)
    ax.set_ylim(0, 1.05)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"\nPlot saved to: {output_path}")
    plt.close(fig)


if __name__ == "__main__":
    print("=" * 80)
    print("T1 EXAM OUTCOME CALIBRATION")
    print("=" * 80)

    # Create database session
    db = SessionLocal()
    try:
        # 1. Load T1 outcomes
        print("\n[1/4] Loading T1 exam outcomes...")
        outcomes_df = load_t1_outcomes(db)
        if outcomes_df.empty:
            print("Error: No T1 exam outcome data found")
            sys.exit(1)
        print(f"  Loaded {len(outcomes_df)} exam records")
        unique_students = outcomes_df[["org_id", "student_id"]].drop_duplicates()
        print(f"  {len(unique_students)} unique students")
        at_risk_count = (outcomes_df["student_outcome"] == "at_risk").sum()
        print(f"  {at_risk_count} students labeled as at-risk")

        # 2. Load T1 risk features
        print("\n[2/4] Computing T1 risk features...")
        features_df = load_t1_risk_features(db)
        if features_df.empty:
            print("Error: No feature data computed")
            sys.exit(1)
        print(f"  Computed features for {len(features_df)} students")

        # 3. Run threshold analysis
        print("\n[3/4] Running threshold analysis...")
        metrics_df = run_threshold_analysis(features_df, outcomes_df)
        if metrics_df.empty:
            print("Error: Threshold analysis failed")
            sys.exit(1)

        # 4. Recommend threshold
        print("\n[4/4] Recommending optimal threshold...")
        recommended_t = recommend_threshold(metrics_df, min_recall=0.75)

        # 5. Generate plot
        output_path = str(
            project_root / "backend" / "ml" / "outputs" / "threshold_calibration.png"
        )
        plot_precision_recall_curve(metrics_df, recommended_t, output_path)

        # 6. Print config suggestions
        t1 = round(recommended_t * 0.4)
        t2 = round(recommended_t * 0.55)
        t3 = round(recommended_t * 0.75)
        t4 = round(recommended_t)

        print("\n" + "=" * 80)
        print("CONFIG UPDATE SUGGESTION")
        print("=" * 80)
        print("Suggested config update:")
        print(f"  THRESHOLD_NO_ACTION={t1}")
        print(f"  THRESHOLD_GENTLE={t2}")
        print(f"  THRESHOLD_MENTOR={t3}")
        print(f"  THRESHOLD_URGENT={t4}")
        print("=" * 80)

    finally:
        db.close()
        print("\nDatabase session closed.")
