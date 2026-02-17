from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List

from backend.database import User, Prediction, Student
from backend.app.api import deps
from backend.services.export_service import ExportService

router = APIRouter()

@router.get("/export/students")
def export_students(
    format: str = Query("csv", enum=["csv", "excel", "pdf"]),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(["Retention Team", "Admin"]))
):
    """
    Export all students list in specified format.
    """
    students = db.query(Student).all()
    data = [
        {"id": s.id, "name": f"{s.first_name} {s.last_name}", "department": s.parent_department_name}
        for s in students
    ]
    
    ExportService.log_export(db, current_user.id, current_user.role, f"students_{format}")
    
    if format == "csv":
        content = ExportService.to_csv(data)
        return Response(content=content, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=students.csv"})
    elif format == "excel":
        content = ExportService.to_excel(data)
        return StreamingResponse(content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=students.xlsx"})
    elif format == "pdf":
        content = ExportService.to_pdf(data, "Student List")
        return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=students.pdf"})

@router.get("/export/risk-summary")
def export_risk_summary(
    format: str = Query("csv", enum=["csv", "excel", "pdf"]),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.require_role(["Retention Team", "Admin"]))
):
    """
    Export high-level risk summary.
    """
    predictions = db.query(Prediction).all()
    data = [
        {"student_id": p.student_id, "risk_score": p.risk_score, "likelihood": p.retention_likelihood}
        for p in predictions
    ]
    
    ExportService.log_export(db, current_user.id, current_user.role, f"risk_summary_{format}")
    
    # ... logic similar to above ...
    return {"message": "Export initiated"}
