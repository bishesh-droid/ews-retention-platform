import pandas as pd
from typing import List, Dict, Any
from io import BytesIO
from fpdf import FPDF
from backend.database import AuditLog
from sqlalchemy.orm import Session
from datetime import datetime


class ExportService:
    @staticmethod
    def to_csv(data: List[Dict[str, Any]]) -> str:
        df = pd.DataFrame(data)
        return df.to_csv(index=False)

    @staticmethod
    def to_excel(data: List[Dict[str, Any]]) -> BytesIO:
        df = pd.DataFrame(data)
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        output.seek(0)
        return output

    @staticmethod
    def to_pdf(data: List[Dict[str, Any]], title: str) -> BytesIO:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, text=title, align='C')
        pdf.ln()

        for row in data:
            pdf.ln(10)
            for key, value in row.items():
                pdf.cell(100, 10, text=f"{key}: {value}")
                pdf.ln()

        output = BytesIO()
        pdf.output(output)
        output.seek(0)
        return output

    @staticmethod
    def log_export(db: Session, user_id: int, user_role: str, report_type: str):
        audit = AuditLog(
            user_id=user_id,
            user_role=user_role,
            action_type="export",
            details={"report_type": report_type},
            timestamp=datetime.utcnow()
        )
        db.add(audit)
        # Caller commits the transaction.
        db.flush()
