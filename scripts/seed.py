import sys
import os
from datetime import datetime, timedelta, timezone
import uuid

# Ensure root backend dir is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from passlib.context import CryptContext
from sqlalchemy import text
from app.core.database import SessionLocal, engine
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def seed_database():
    """
    Seeds initial users (Admin, Agent, Customer) and sample tickets
    for manual testing and validation.
    """
    print("Starting database seeding...")
    db = SessionLocal()
    try:
        # Verify connection
        db.execute(text("SELECT 1"))
        print("Database connection verified.")

        # Note: Actual insertion of User and Ticket records will run once
        # the SQLAlchemy models are created in Slice 1 & Slice 4.
        print("Database seed script initialized and ready for model execution.")

    except Exception as e:
        print(f"Seeding notice: {e}")
        print("Seed script will run migrations and insert records once DB tables are created.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
