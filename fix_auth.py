#!/usr/bin/env python3
"""
Fix authentication by re-creating admin user with valid bcrypt password hash.
"""
import sys
sys.path.insert(0, '/home/duffer/Gemini/Project_1(complete)/ews-retention-platform')

import bcrypt
from sqlalchemy.orm import Session
from backend.database.connection import SessionLocal, engine
from backend.database.models import User

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def fix_users():
    db = SessionLocal()
    try:
        # Delete existing users to clear invalid hashes
        db.query(User).delete()
        db.commit()
        print("Cleared existing users")
        
        # Create fresh admin user with valid bcrypt hash
        admin_user = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin123"),
            role="admin",  # lowercase for consistency
            is_superuser=True,
            is_active=True
        )
        db.add(admin_user)
        
        # Create faculty user
        faculty_user = User(
            username="faculty1",
            email="faculty1@example.com",
            hashed_password=get_password_hash("faculty123"),
            role="faculty",
            is_active=True
        )
        db.add(faculty_user)
        
        db.commit()
        print("Created admin user (username: admin, password: admin123)")
        print("Created faculty user (username: faculty1, password: faculty123)")
        print("\nYou can now log in with these credentials.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_users()
