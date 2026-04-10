from sqlalchemy import Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from ..connection import Base  # Assuming Base is defined here or in a common file


class GradedComponent(Base):
    __tablename__ = "graded_components"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    course_code = Column(String)
    course_name = Column(String)
    component_type = Column(String)  # "quiz" or "assignment"
    component_number = Column(Integer)
    score = Column(Float, nullable=True)  # null = missed/absent
    max_score = Column(Float)
    missed = Column(Boolean, default=False)
    student = relationship("Student", back_populates="graded_components")


class ExamRecord(Base):
    __tablename__ = "exam_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    course_code = Column(String)
    course_name = Column(String)
    slot = Column(String)  # "slot-1", "slot-2"
    marks_obtained = Column(Float, nullable=True)
    marks_total = Column(Float)
    present = Column(Boolean, default=True)
    mode = Column(String, nullable=True)  # "Online" or "Onsite"
    # High-signal academic flags
    ufm_flagged = Column(Boolean, default=False, nullable=False)  # Unfair Means (academic misconduct)
    defaulter_reason = Column(String, nullable=True)  # Mapped reason from FINAL_REMARKS
    student = relationship("Student", back_populates="exam_records")
