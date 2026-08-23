import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal
from app.models.user import User
from app.core.security import verify_password

def check():
    db = SessionLocal()
    users = db.query(User).all()
    print(f"Total users in DB: {len(users)}")
    for u in users:
        admin_check = verify_password("AdminPass123!", u.hashed_password)
        agent_check = verify_password("AgentPass123!", u.hashed_password)
        cust_check = verify_password("CustomerPass123!", u.hashed_password)
        print(f"Email: '{u.email}' | Role: '{u.role}' | AdminPass: {admin_check} | AgentPass: {agent_check} | CustPass: {cust_check}")
    db.close()

if __name__ == "__main__":
    check()
