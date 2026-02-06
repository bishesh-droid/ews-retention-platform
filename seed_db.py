import sys
import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add project root to path
sys.path.append(os.getcwd())

from backend.app.database import SessionLocal, init_db, engine
from backend.app.models import Student

def seed_data():
    print("Initializing database...")
    init_db()
    
    db = SessionLocal()
    try:
        if db.query(Student).count() > 0:
            print(f"Database already has {db.query(Student).count()} students. Skipping seed.")
            return

        csv_path = "backend/data/simulated_data.csv"
        print(f"Reading data from {csv_path}...")
        
        if not os.path.exists(csv_path):
            print(f"Error: {csv_path} not found!")
            return

        df = pd.read_csv(csv_path)
        df = df.fillna(0)
        
        print(f"Found {len(df)} records. Inserting...")
        
        students = []
        for _, row in df.iterrows():
            student_data = row.to_dict()
            students.append(Student(**student_data))
            
        db.bulk_save_objects(students)
        db.commit()
        print("Data seeding completed successfully!")
        
    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
