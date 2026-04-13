from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime
import uuid

from backend.database import User, Prediction, Student
from backend.api import deps
from backend.core.constants import Role
from backend.database import AuditLog
from backend.schemas.common import APIResponse
from backend.services.audit_service import AuditService
from backend.services.export_service import ExportService
from backend.services.student_service import StudentService
from backend.utils.api import success_response, error_response

router = APIRouter()

ROOT_DIR = Path(__file__).resolve().parents[2]
GENERATED_DIR = ROOT_DIR / "data" / "reports" / "generated"


def _ensure_dirs() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)


def _fmt_upper(fmt: str) -> str:
    v = (fmt or "").strip().lower()
    if v in ("pdf",):
        return "PDF"
    if v in ("excel", "xlsx", "xls"):
        return "Excel"
    if v in ("csv",):
        return "CSV"
    return fmt.strip() or "PDF"


def _ext_for_format(fmt_upper: str) -> str:
    if fmt_upper == "PDF":
        return "pdf"
    if fmt_upper == "Excel":
        return "xlsx"
    if fmt_upper == "CSV":
        return "csv"
    return "bin"


def _media_type_for_format(fmt_upper: str) -> str:
    if fmt_upper == "PDF":
        return "application/pdf"
    if fmt_upper == "Excel":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if fmt_upper == "CSV":
        return "text/csv"
    return "application/octet-stream"


REPORT_TEMPLATES: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "Monthly Risk Summary",
        "description": "Executive KPI overview with risk trends and cohort breakdowns.",
        "formats": ["PDF"],
        "audience": ["Executive", "Faculty"],
        "estimated_time": "~45s",
        "sections": ["Executive Summary", "Risk Trend", "Cohort Breakdown", "Top At-Risk List"],
    },
    {
        "id": 2,
        "name": "High-Risk Students Report",
        "description": "Detailed student list with risk scores and key indicators.",
        "formats": ["PDF", "Excel", "CSV"],
        "audience": ["Faculty", "Counselors"],
        "estimated_time": "~30s",
        "sections": ["Risk Score Table", "Top Drivers", "Contact Details"],
    },
    {
        "id": 3,
        "name": "Intervention Impact Report",
        "description": "Intervention effectiveness snapshot and ROI summary.",
        "formats": ["PDF"],
        "audience": ["Admin", "Faculty"],
        "estimated_time": "~60s",
        "sections": ["Effectiveness Summary", "ROI Summary", "Recommendations"],
    },
    {
        "id": 4,
        "name": "Department Performance Report",
        "description": "Department-level retention and risk comparison.",
        "formats": ["PDF", "Excel", "CSV"],
        "audience": ["Admin", "Marketing"],
        "estimated_time": "~50s",
        "sections": ["Department Overview", "Cohort Breakdown", "Key Risks"],
    },
]


class ReportGenerateRequest(BaseModel):
    template_id: int
    format: str = "PDF"
    options: Optional[Dict[str, Any]] = None


@router.get("/templates", response_model=APIResponse)
def list_report_templates(
    current_user: User = Depends(deps.require_role([Role.RETENTION_TEAM, Role.ADMIN, Role.FACULTY])),
):
    """
    List available downloadable report templates.
    """
    return success_response(REPORT_TEMPLATES, message="Report templates")


@router.get("/generated", response_model=APIResponse)
def list_generated_reports(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role([Role.RETENTION_TEAM, Role.ADMIN, Role.FACULTY])),
    limit: int = Query(50, ge=1, le=500),
):
    """
    List generated report metadata (most recent first).
    """
    _ensure_dirs()
    q = (
        db.query(AuditLog)
        .filter(AuditLog.action_type == "report_generated")
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )

    rows: List[Dict[str, Any]] = []
    for a in q.all():
        d: Dict[str, Any] = a.details or {}
        rows.append(
            {
                "id": a.id,
                "template_id": d.get("template_id"),
                "template_name": d.get("template_name"),
                "format": d.get("format"),
                "file_name": d.get("file_name"),
                "size_bytes": d.get("size_bytes"),
                "generated_at": a.timestamp.isoformat() if a.timestamp else None,
                "status": d.get("status", "ready"),
            }
        )

    return success_response(rows, message="Generated reports")


@router.post("/generate", response_model=APIResponse)
def generate_report(
    req: ReportGenerateRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role([Role.RETENTION_TEAM, Role.ADMIN, Role.FACULTY])),
):
    """
    Trigger report generation and return generated metadata.

    This implementation generates synchronously and stores a file in `data/reports/generated/`.
    """
    _ensure_dirs()

    template = next((t for t in REPORT_TEMPLATES if t["id"] == req.template_id), None)
    if not template:
        return error_response("Unknown template_id", {"template_id": req.template_id})

    fmt = _fmt_upper(req.format)
    if fmt not in template.get("formats", []):
        return error_response("Unsupported format for template", {"format": fmt, "supported": template.get("formats", [])})

    options = req.options or {}
    now = datetime.utcnow()
    safe_name = "".join(ch if ch.isalnum() else "_" for ch in template["name"]).strip("_")
    ext = _ext_for_format(fmt)
    token = uuid.uuid4().hex[:10]
    file_name = f"{safe_name}_{now.strftime('%Y%m%d_%H%M%S')}_{token}.{ext}"
    file_path = GENERATED_DIR / file_name

    # Build report rows
    rows: List[Dict[str, Any]] = []
    title = template["name"]

    if req.template_id == 2:
        # High risk students
        students = StudentService.get_all_students(db, skip=0, limit=200, sort_by="risk_score", order="desc")
        high = [s for s in students if float(s.get("risk_score") or 0) >= 70]
        rows = [
            {
                "student_id": s.get("id"),
                "name": f"{s.get('first_name') or ''} {s.get('last_name') or ''}".strip(),
                "department": s.get("department"),
                "risk_score": s.get("risk_score"),
                "attendance_rate": s.get("exam_attendance_rate"),
                "quiz_score": s.get("graded_quiz_score"),
            }
            for s in high[:200]
        ]
        if not rows:
            rows = [{"note": "No high-risk students found for the selected criteria."}]
    elif req.template_id == 4:
        analytics = StudentService.get_analytics_data(db) or {}
        dept_rows = analytics.get("department_summary", []) if isinstance(analytics, dict) else []
        rows = [
            {
                "department": d.get("department", "Unknown"),
                "student_count": d.get("student_count", 0),
                "avg_risk_score": d.get("avg_risk_score", 0),
            }
            for d in dept_rows
        ]
        if not rows:
            rows = [{"note": "No department analytics available."}]
    else:
        # Generic summary for other templates
        stats = StudentService.get_overview_stats(db) or {}
        rows = [
            {"metric": "total_students", "value": stats.get("total_students")},
            {"metric": "avg_risk_score", "value": stats.get("average_risk_score")},
            {"metric": "at_risk_students", "value": stats.get("at_risk_students")},
            {"metric": "high_risk_students", "value": stats.get("high_risk_students")},
        ]

    # Render file
    size_bytes = 0
    if fmt == "CSV":
        content_str = ExportService.to_csv(rows)
        data_bytes = content_str.encode("utf-8")
        file_path.write_bytes(data_bytes)
        size_bytes = len(data_bytes)
    elif fmt == "Excel":
        bio = ExportService.to_excel(rows)
        data_bytes = bio.getvalue()
        file_path.write_bytes(data_bytes)
        size_bytes = len(data_bytes)
    else:  # PDF
        bio = ExportService.to_pdf(rows, title)
        data_bytes = bio.getvalue()
        file_path.write_bytes(data_bytes)
        size_bytes = len(data_bytes)

    audit = AuditService.log_action(
        db,
        user_id=current_user.id,  # type: ignore[arg-type]
        user_role=current_user.role,  # type: ignore[arg-type]
        action_type="report_generated",
        affected_student_id=None,
        details={
            "template_id": template["id"],
            "template_name": template["name"],
            "format": fmt,
            "file_name": file_name,
            "file_path": str(file_path),
            "size_bytes": size_bytes,
            "status": "ready",
            "options": options,
        },
    )

    db.commit()

    return success_response(
        {
            "id": audit.id,
            "template_id": template["id"],
            "template_name": template["name"],
            "format": fmt,
            "file_name": file_name,
            "size_bytes": size_bytes,
            "generated_at": audit.timestamp.isoformat() if audit.timestamp else None,
            "status": "ready",
        },
        message="Report generated",
    )


@router.get("/download/{report_id}", response_model=None)  # Returns StreamingResponse
def download_generated_report(
    report_id: int,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role([Role.RETENTION_TEAM, Role.ADMIN, Role.FACULTY])),
):
    """
    Download a previously generated report file by audit log id.
    """
    _ensure_dirs()
    audit = db.query(AuditLog).filter(AuditLog.id == report_id, AuditLog.action_type == "report_generated").first()
    if not audit:
        return Response(status_code=404, content="Not found")

    d: Dict[str, Any] = audit.details or {}
    file_path = d.get("file_path")
    file_name = d.get("file_name") or "report.bin"
    fmt = d.get("format") or ""
    media_type = _media_type_for_format(_fmt_upper(fmt))

    if not file_path:
        return Response(status_code=404, content="Not found")

    path = Path(file_path)
    if not path.exists() or not path.is_file():
        return Response(status_code=404, content="Not found")

    def _iterfile():
        with path.open("rb") as f:
            while True:
                chunk = f.read(1024 * 1024)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        _iterfile(),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/export/students", response_model=None)  # Returns StreamingResponse
def export_students(
    format: str = Query("csv", enum=["csv", "excel", "pdf"]),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role([Role.RETENTION_TEAM, Role.ADMIN]))
):
    """
    Export all students list in specified format.
    """
    students = db.query(Student).all()
    data = [
        {"id": s.id, "name": f"{s.first_name} {s.last_name}", "department": s.parent_department_name}
        for s in students
    ]

    ExportService.log_export(db, int(current_user.id), str(current_user.role), f"students_{format}")  # type: ignore[arg-type]

    db.commit()

    if format == "csv":
        csv_content = ExportService.to_csv(data)
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=students.csv"},
        )
    elif format == "excel":
        excel_bio = ExportService.to_excel(data)
        return StreamingResponse(
            excel_bio,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment; filename=students.xlsx"},
        )
    elif format == "pdf":
        pdf_bio = ExportService.to_pdf(data, "Student List")
        return StreamingResponse(
            pdf_bio,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=students.pdf"},
        )


@router.get("/export/risk-summary", response_model=None)  # Returns StreamingResponse
def export_risk_summary(
    format: str = Query("csv", enum=["csv", "excel", "pdf"]),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role([Role.RETENTION_TEAM, Role.ADMIN]))
):
    """
    Export high-level risk summary.
    """
    predictions = db.query(Prediction).all()
    [
        {"student_id": p.student_id, "risk_score": p.risk_score, "likelihood": p.retention_likelihood}
        for p in predictions
    ]

    ExportService.log_export(
        db,
        int(current_user.id),  # type: ignore[arg-type]
        str(current_user.role),
        f"risk_summary_{format}",
    )

    db.commit()

    # ... logic similar to above ...
    return {"message": "Export initiated"}
