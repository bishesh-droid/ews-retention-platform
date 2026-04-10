"""
Retrospective evaluation of the rule-based risk scorer against T1 outcomes.
Run with: python -m backend.ml.training.evaluate

This script compares risk scores stored in RiskSnapshot against final_outcome
labels in Enrollment to measure how well the rule-based scorer predicts dropouts.
"""
from backend.database.models.goals_and_risks import RiskSnapshot
from backend.database.models.enrollment import Enrollment
from backend.database.connection import SessionLocal
import argparse
import sys
from contextlib import contextmanager
from typing import Dict, Any

import pandas as pd
from sklearn.metrics import roc_auc_score, confusion_matrix

# Add project root to path for imports
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))


@contextmanager
def get_session():
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def load_labeled_data(session) -> pd.DataFrame:
    """
    Join students + enrollments with final_outcome + latest RiskSnapshot.

    Returns DataFrame with columns:
    - org_id: student identifier
    - risk_score: latest risk score (0-100 scale)
    - final_outcome: actual outcome label
    - program: BS or MSc
    - old_new: old or new student
    - semester: semester name

    Filters to only rows where final_outcome is not None.
    """

    # Use SQLAlchemy ORM approach for better compatibility
    results = []

    # Get all enrollments with final outcomes
    enrollments_with_outcomes = (
        session.query(Enrollment)
        .filter(Enrollment.final_outcome.isnot(None))
        .all()
    )

    for enrollment in enrollments_with_outcomes:
        student = enrollment.student
        if not student:
            continue

        # Get latest RiskSnapshot for this student
        latest_snapshot = (
            session.query(RiskSnapshot)
            .filter(RiskSnapshot.student_id == student.id)
            .order_by(RiskSnapshot.timestamp.desc())
            .first()
        )

        if not latest_snapshot:
            continue

        # Normalize risk score to 0-100
        risk_val = latest_snapshot.risk_score or 0
        if risk_val <= 1.0:
            risk_val *= 100.0

        # Determine program (BS/MSc from department name)
        dept = (student.parent_department_name or "").lower()
        program = "MSc" if "msc" in dept else "BS"

        results.append({
            "org_id": student.org_defined_id or student.id,
            "risk_score": risk_val,
            "final_outcome": enrollment.final_outcome,
            "outcome_source": enrollment.outcome_source,
            "program": program,
            "old_new": student.old_new_student or "unknown",
            "semester": enrollment.course.semester_name if enrollment.course else None,
            "risk_timestamp": latest_snapshot.timestamp,
        })

    df = pd.DataFrame(results)
    return df


def run_evaluation(df: pd.DataFrame, threshold: float = 60.0) -> Dict[str, Any]:
    """
    Evaluate the rule-based risk scorer against actual outcomes.

    Args:
        df: DataFrame with risk_score and final_outcome columns
        threshold: Risk score threshold for "at risk" classification

    Returns:
        Dictionary with evaluation metrics
    """
    df = df.copy()

    # Create binary predictions based on threshold
    df["predicted_at_risk"] = df["risk_score"] >= threshold

    # Create binary ground truth: dropped or deferred = at risk
    df["actual_at_risk"] = df["final_outcome"].isin(["dropped", "deferred"])

    metrics = {
        "threshold": threshold,
        "total_students": len(df),
        "actual_at_risk": int(df["actual_at_risk"].sum()),
        "actual_at_risk_pct": round(df["actual_at_risk"].mean() * 100, 1),
        "predicted_at_risk": int(df["predicted_at_risk"].sum()),
        "predicted_at_risk_pct": round(df["predicted_at_risk"].mean() * 100, 1),
    }

    # Calculate classification metrics
    y_true = df["actual_at_risk"].astype(int).values
    y_pred = df["predicted_at_risk"].astype(int).values

    # Confusion matrix
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    metrics["confusion_matrix"] = {
        "true_negatives": int(tn),
        "false_positives": int(fp),
        "false_negatives": int(fn),
        "true_positives": int(tp),
    }

    # Calculate metrics manually for precision
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    metrics["precision"] = round(precision, 3)
    metrics["recall"] = round(recall, 3)
    metrics["specificity"] = round(specificity, 3)
    metrics["f1_score"] = round(f1, 3)

    # ROC-AUC if possible (need both classes)
    try:
        auc = roc_auc_score(df["actual_at_risk"], df["risk_score"])
        metrics["roc_auc"] = round(auc, 3)
    except ValueError:
        metrics["roc_auc"] = None

    # Outcome breakdown
    outcome_counts = df["final_outcome"].value_counts().to_dict()
    metrics["outcome_breakdown"] = {k: int(v) for k, v in outcome_counts.items()}

    return metrics


def print_evaluation_report(metrics: Dict[str, Any], df: pd.DataFrame, threshold: float):
    """Print a formatted evaluation report to console."""
    print(f"\n{'='*60}")
    print(f"  EWS Rule-Based Scorer Evaluation (threshold={threshold})")
    print(f"{'='*60}")
    print(f"Total students evaluated: {metrics['total_students']}")
    print(f"Actual at-risk: {metrics['actual_at_risk']} ({metrics['actual_at_risk_pct']}%)")
    print(f"Predicted at-risk: {metrics['predicted_at_risk']} ({metrics['predicted_at_risk_pct']}%)")

    print("\n--- Classification Metrics ---")
    print(f"Precision: {metrics['precision']:.3f} (of those flagged, how many were truly at-risk)")
    print(f"Recall:    {metrics['recall']:.3f} (of all at-risk, how many did we catch)")
    print(f"Specificity: {metrics['specificity']:.3f} (of not at-risk, how many did we correctly ignore)")
    print(f"F1 Score:  {metrics['f1_score']:.3f}")

    if metrics.get("roc_auc"):
        print(f"ROC-AUC:   {metrics['roc_auc']:.3f}")
    else:
        print("ROC-AUC:   could not compute (need both classes represented)")

    print("\n--- Confusion Matrix ---")
    cm = metrics["confusion_matrix"]
    print("                 Predicted")
    print("                 Not Risk    Risk")
    print(
        f"Actual Not Risk    {cm['true_negatives']:4d}      {cm['false_positives']:4d}"
        f"   (specificity: {metrics['specificity']:.3f})"
    )
    print(f"Actual At Risk     {cm['false_negatives']:4d}      {cm['true_positives']:4d}   (recall: {metrics['recall']:.3f})")

    print("\n--- Outcome Breakdown ---")
    for outcome, count in metrics["outcome_breakdown"].items():
        pct = count / metrics['total_students'] * 100
        print(f"  {outcome:12s}: {count:4d} ({pct:5.1f}%)")

    # By program breakdown
    print("\n--- Breakdown by Program ---")
    for program in df["program"].unique():
        sub = df[df["program"] == program]
        sub_actual = sub["actual_at_risk"].sum()
        sub_pred = sub["predicted_at_risk"].sum()
        print(f"{program}: {len(sub)} students, {sub_actual} at-risk, {sub_pred} predicted")

    print(f"\n{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate rule-based risk scorer against T1 outcomes"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=60.0,
        help="Risk score threshold for 'at risk' classification (default: 60.0)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of formatted report",
    )
    parser.add_argument(
        "--compare-thresholds",
        action="store_true",
        help="Run evaluation at multiple thresholds (50, 60, 70, 80)",
    )

    args = parser.parse_args()

    with get_session() as session:
        df = load_labeled_data(session)

        if len(df) == 0:
            print("No labeled outcomes found. Run data ingestion first to populate final_outcome fields.")
            print("The infer_outcomes_from_exam_data() function must be called during ingestion.")
            sys.exit(1)

        if args.compare_thresholds:
            thresholds = [50.0, 60.0, 70.0, 80.0]
            print(f"\n{'='*60}")
            print(f"  Comparing thresholds: {thresholds}")
            print(f"{'='*60}")

            for thresh in thresholds:
                metrics = run_evaluation(df, threshold=thresh)
                print(f"\nThreshold {thresh:4.1f}: Precision={metrics['precision']:.3f}, "
                      f"Recall={metrics['recall']:.3f}, F1={metrics['f1_score']:.3f}")
        else:
            metrics = run_evaluation(df, threshold=args.threshold)

            if args.json:
                import json
                print(json.dumps(metrics, indent=2))
            else:
                print_evaluation_report(metrics, df, args.threshold)

                # Show command for other thresholds
                print("\nTo test other thresholds, run:")
                print("  python -m backend.ml.training.evaluate --threshold 50")
                print("  python -m backend.ml.training.evaluate --compare-thresholds")


if __name__ == "__main__":
    main()
