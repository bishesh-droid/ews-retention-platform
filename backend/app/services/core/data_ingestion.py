import pandas as pd
from sqlalchemy.orm import Session
from backend.database import Student

def ingest_data(db: Session):
    # Check if data is already in the database
    if db.query(Student).count() == 0:
        print("No student data found in the database. Ingesting from CSV...")
        try:
            # The CSV is in the root of the project
            df = pd.read_csv('simulated_data.csv')
            
            # fill nan values with 0
            df = df.fillna(0)

            for _, row in df.iterrows():
                student_data = row.to_dict()
                student = Student(**student_data)
                db.add(student)
            
            db.commit()
            print("Data ingestion complete.")
        except FileNotFoundError:
            print("Error: simulated_data.csv not found. Make sure the file is in the root of the project.")
        except Exception as e:
            db.rollback()
            print(f"An error occurred during data ingestion: {e}")
    else:
        print("Student data already exists in the database. Skipping ingestion.")

