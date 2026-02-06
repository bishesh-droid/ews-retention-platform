"""
Student Model
------------
Database model for student entity and all academic metrics.
"""

from sqlalchemy import Column, String, Float, Integer
from sqlalchemy.orm import relationship
from backend.app.database.connection import Base


class Student(Base):
    """
    Student model containing all baseline academic performance metrics
    across multiple years (1-7) including absence rates, suspensions,
    mobility, and GPA/MPA scores by quarter.
    """
    __tablename__ = "students"
    
    # Primary Key
    id = Column(String, primary_key=True, index=True)
    
    # Absence rates (years 1-7)
    absrate1 = Column(Float)
    absrate2 = Column(Float)
    absrate3 = Column(Float)
    absrate4 = Column(Float)
    absrate5 = Column(Float)
    absrate6 = Column(Float)
    absrate7 = Column(Float)
    
    # Suspension counts (years 1-7)
    nsusp1 = Column(Float)
    nsusp2 = Column(Float)
    nsusp3 = Column(Float)
    nsusp4 = Column(Float)
    nsusp5 = Column(Float)
    nsusp6 = Column(Float)
    nsusp7 = Column(Float)
    
    # Mobility/transfers (years 1-7)
    mobility1 = Column(Float)
    mobility2 = Column(Float)
    mobility3 = Column(Float)
    mobility4 = Column(Float)
    mobility5 = Column(Float)
    mobility6 = Column(Float)
    mobility7 = Column(Float)
    
    # MPA (academic performance) by quarter and year
    # Year 1
    q1mpa1 = Column(Float)
    q2mpa1 = Column(Float)
    q3mpa1 = Column(Float)
    q4mpa1 = Column(Float)
    
    # Year 2
    q1mpa2 = Column(Float)
    q2mpa2 = Column(Float)
    q3mpa2 = Column(Float)
    q4mpa2 = Column(Float)
    
    # Year 3
    q1mpa3 = Column(Float)
    q2mpa3 = Column(Float)
    q3mpa3 = Column(Float)
    q4mpa3 = Column(Float)
    
    # Year 4
    q1mpa4 = Column(Float)
    q2mpa4 = Column(Float)
    q3mpa4 = Column(Float)
    q4mpa4 = Column(Float)
    
    # Year 5
    q1mpa5 = Column(Float)
    q2mpa5 = Column(Float)
    q3mpa5 = Column(Float)
    q4mpa5 = Column(Float)
    
    # Year 6
    q1mpa6 = Column(Float)
    q2mpa6 = Column(Float)
    q3mpa6 = Column(Float)
    q4mpa6 = Column(Float)
    
    # Year 7
    q1mpa7 = Column(Float)
    q2mpa7 = Column(Float)
    q3mpa7 = Column(Float)
    q4mpa7 = Column(Float)
    
    # Graduation status
    nograd = Column(Integer)  # 0 = graduated, 1 = did not graduate (dropout)
    
    # Relationships
    predictions = relationship("Prediction", back_populates="student")
    interventions = relationship("Intervention", back_populates="student")
