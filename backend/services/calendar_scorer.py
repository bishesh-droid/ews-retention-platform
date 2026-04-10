"""
Calendar-based scoring utilities.

Hardcoded COURSE_CALENDAR for now (will be DB-backed later).
"""

from __future__ import annotations

from datetime import date
from statistics import mean
from typing import Dict, List, Optional, Tuple


COURSE_CALENDAR: Dict[Tuple[str, str], List[Dict]] = {
    ("BS", "Probability & Statistics"): [
        {"week": 3, "component": "Graded Quiz 1", "weight": 0.10},
        {"week": 6, "component": "Graded Quiz 2", "weight": 0.15},
        {"week": 10, "component": "Assignment I", "weight": 0.20},
        {"week": 11, "component": "Graded Quiz 3", "weight": 0.15},
        {"week": 13, "component": "End Exam", "weight": 0.40},
    ],
    ("BS", "Computer Programming"): [
        {"week": 3, "component": "Graded Quiz 1", "weight": 0.08},
        {"week": 5, "component": "Graded Quiz 2", "weight": 0.08},
        {"week": 7, "component": "Graded Quiz 3", "weight": 0.08},
        {"week": 9, "component": "Graded Quiz 4", "weight": 0.08},
        {"week": 12, "component": "Assignment I", "weight": 0.28},
        {"week": 13, "component": "End Exam", "weight": 0.40},
    ],
    ("BS", "Writing Practice"): [
        {"week": 2, "component": "Graded Quiz 1", "weight": 0.05},
        {"week": 4, "component": "Assignment I", "weight": 0.10},
        {"week": 6, "component": "Graded Quiz 2", "weight": 0.05},
        {"week": 8, "component": "Assignment II", "weight": 0.10},
        {"week": 13, "component": "End Exam", "weight": 0.50},
    ],
    ("BS", "Computing Systems"): [
        {"week": 4, "component": "Assignment I", "weight": 0.15},
        {"week": 6, "component": "Assignment II", "weight": 0.15},
        {"week": 7, "component": "Graded Quiz 1", "weight": 0.10},
        {"week": 10, "component": "Graded Quiz 2", "weight": 0.10},
        {"week": 13, "component": "Graded Quiz 3", "weight": 0.10},
        {"week": 15, "component": "End Exam", "weight": 0.40},
    ],
    ("MSc", "Statistical Modelling & Inferencing"): [
        {"week": 3, "component": "Quiz 1", "weight": 0.15},
        {"week": 6, "component": "Quiz 2", "weight": 0.15},
        {"week": 10, "component": "Assignment", "weight": 0.20},
        {"week": 11, "component": "Quiz 3", "weight": 0.15},
        {"week": 13, "component": "End Exam", "weight": 0.35},
    ],
    ("MSc", "Data Pre-processing"): [
        {"week": 2, "component": "Quiz 1", "weight": 0.10},
        {"week": 4, "component": "Quiz 2", "weight": 0.10},
        {"week": 5, "component": "Quiz 3", "weight": 0.10},
        {"week": 6, "component": "Quiz 4", "weight": 0.10},
        {"week": 7, "component": "Quiz 5", "weight": 0.10},
        {"week": 8, "component": "Quiz 6", "weight": 0.10},
        {"week": 13, "component": "Compre Exam", "weight": 0.40},
    ],
    ("MSc", "Feature Engineering"): [
        {"week": 4, "component": "Quiz", "weight": 0.20},
        {"week": 5, "component": "Assignment", "weight": 0.40},
        {"week": 13, "component": "Compre Exam", "weight": 0.40},
    ],
    ("MSc", "Data Visualization & Storytelling"): [
        {"week": 4, "component": "Quiz 1", "weight": 0.20},
        {"week": 8, "component": "Quiz 2", "weight": 0.20},
        {"week": 13, "component": "Assignment", "weight": 0.20},
        {"week": 13, "component": "Final Exam", "weight": 0.40},
    ],
    ("MSc", "Data Stores & Pipelines"): [
        {"week": 4, "component": "Quiz 1", "weight": 0.08},
        {"week": 6, "component": "Assignment 1", "weight": 0.20},
        {"week": 8, "component": "Quiz 2", "weight": 0.08},
        {"week": 9, "component": "Assignment 2", "weight": 0.20},
        {"week": 13, "component": "Quiz 3", "weight": 0.09},
        {"week": 13, "component": "Compre Exam", "weight": 0.35},
    ],
    ("MSc", "Basic Mathematics"): [
        {"week": 3, "component": "Graded Quiz 1", "weight": 0.20},
        {"week": 6, "component": "Graded Quiz 2", "weight": 0.20},
        {"week": 9, "component": "Graded Quiz 3", "weight": 0.20},
        {"week": 12, "component": "Graded Quiz 4", "weight": 0.20},
        {"week": 13, "component": "Final Quiz", "weight": 0.20},
    ],
}


def get_current_week(trimester_start: str) -> int | None:
    """
    Compute current trimester week number from today's date.

    Week 1 = days 1–7, week 2 = days 8–14, etc.
    Returns None if today is before trimester start (was returning 0).
    """
    start = date.fromisoformat(trimester_start)
    delta_days = (date.today() - start).days
    if delta_days < 0:
        return None  # Before trimester start — was returning 0
    week = (delta_days // 7) + 1
    return min(week, 13)  # cap at 13 — no week 14+


def _is_exam_component(name: str) -> bool:
    n = (name or "").lower()
    return ("exam" in n) or ("compre" in n)


def _infer_program_for_course(course_name: str) -> Optional[str]:
    if not course_name:
        return None
    programs = {prog for (prog, cname) in COURSE_CALENDAR.keys() if cname == course_name}
    if len(programs) == 1:
        return next(iter(programs))
    return None


def get_expected_completion_pct(program: str, course_name: str, current_week: int) -> float | None:
    """
    Baseline completion (0–1) expected by `current_week`, excluding exams.
    Returns None if course not found (was returning 0.0 which masked underperformance).
    """
    items = COURSE_CALENDAR.get((program, course_name))
    if not items:
        return None  # caller must handle — do not blend calendar risk for this course
    total = 0.0
    for it in items:
        due_week = int(it.get("week") or 0)
        component = str(it.get("component") or "")
        if due_week <= int(current_week) and not _is_exam_component(component):
            total += float(it.get("weight") or 0.0)
    return round(max(0.0, min(1.0, total)), 4)


def get_overdue_components(
    program: str,
    course_name: str,
    current_week: int,
    submitted_component_names: List[str],
) -> List[Dict]:
    """
    Return components past due and not submitted.
    """
    items = COURSE_CALENDAR.get((program, course_name))
    if not items:
        return []

    submitted = {str(s).strip().lower() for s in (submitted_component_names or []) if s}
    overdue: List[Dict] = []
    cw = int(current_week)

    for it in items:
        due_week = int(it.get("week") or 0)
        component = str(it.get("component") or "")
        weight = float(it.get("weight") or 0.0)
        if due_week <= 0:
            continue
        if due_week < cw and component.strip().lower() not in submitted:
            overdue.append(
                {
                    "component": component,
                    "due_week": due_week,
                    "weight": weight,
                    "weeks_overdue": cw - due_week,
                }
            )
    overdue.sort(key=lambda x: (x["weeks_overdue"], x["due_week"], x["component"]), reverse=True)
    return overdue


def _graded_component_pct(g: Dict) -> Optional[float]:
    """
    Normalize a graded component dict to a 0–100 percentage.
    Returns None if not scorable.
    """
    if not g:
        return None
    max_score = g.get("max_score")
    if max_score is None:
        return None
    try:
        max_score_f = float(max_score)
    except (TypeError, ValueError):
        return None
    if max_score_f <= 0:
        return None

    missed = bool(g.get("missed", False))
    score = 0.0 if missed else g.get("score")
    if score is None:
        return None
    try:
        score_f = float(score)
    except (TypeError, ValueError):
        return None
    pct = (score_f / max_score_f) * 100.0
    return max(0.0, min(100.0, pct))


def calculate_calendar_adjusted_risk(
    student_features: Dict,
    graded_components: List[Dict],
    program: Optional[str],
    current_week: int,
) -> Dict:
    per_course = student_features.get("per_course_breakdown") or []
    course_names = [c.get("course_name") for c in per_course if c and c.get("course_name")]

    # Map submissions by course: we only have component_type/number in DB output;
    # keep a best-effort component-name mapping for the schedule.
    submitted_by_course: Dict[str, List[str]] = {}
    pct_by_course: Dict[str, List[float]] = {}
    for g in (graded_components or []):
        cname = str(g.get("course_name") or "").strip()
        if not cname:
            continue
        ctype = str(g.get("component_type") or "").strip().lower()
        cnum = g.get("component_number")
        label = None
        if ctype == "quiz" and cnum is not None:
            label = f"Graded Quiz {cnum}"
        elif ctype == "assignment" and cnum is not None:
            # Matches "Assignment I/II" imperfectly; still useful for filtering overdue.
            label = "Assignment"
        if label:
            submitted_by_course.setdefault(cname, []).append(label)

        pct = _graded_component_pct(g)
        if pct is not None:
            pct_by_course.setdefault(cname, []).append(pct)

    deficits: List[float] = []
    expected_pcts: List[float] = []
    actual_pcts: List[float] = []
    overdue_all: List[Dict] = []

    for cname in course_names:
        prog = program or _infer_program_for_course(str(cname))
        if not prog:
            exp = None
            overdue = []
        else:
            exp = get_expected_completion_pct(prog, str(cname), current_week)
            overdue = get_overdue_components(
                prog,
                str(cname),
                current_week,
                submitted_by_course.get(str(cname), []),
            ) if exp is not None else []
        
        # Skip courses where expected_pct is None — no calendar data, don't distort risk
        if exp is None:
            continue
        
        overdue_all.extend(
            [{"course_name": str(cname), **o} for o in overdue]
        )

        actual = mean(pct_by_course.get(str(cname), [])) if pct_by_course.get(str(cname)) else 0.0
        deficit = max(0.0, float(exp) - (float(actual) / 100.0))

        expected_pcts.append(float(exp))
        actual_pcts.append(float(actual))
        deficits.append(deficit)

    mean_deficit = mean(deficits) if deficits else 0.0
    calendar_risk_score = min(100.0, (mean_deficit / 0.30) * 100.0) if mean_deficit > 0 else 0.0

    return {
        "calendar_risk_score": round(float(calendar_risk_score), 2),
        "overdue_components": overdue_all,
        "expected_pct": round(mean(expected_pcts), 4) if expected_pcts else 0.0,
        "actual_pct": round(mean(actual_pcts), 2) if actual_pcts else 0.0,
    }

