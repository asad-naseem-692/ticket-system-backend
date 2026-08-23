import sys
import os
from datetime import datetime, timedelta, timezone

# Ensure root backend dir is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, engine, Base
from app.core.security import get_password_hash
from app.core.config import settings
from app.models.user import User
from app.models.ticket import Ticket

def seed_database():
    """
    Creates database schema and seeds initial users and tickets.
    """
    print("Connecting to database and creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Database tables verified.")

    db = SessionLocal()
    try:
        # 1. Seed Admin User
        admin_email = "admin@example.com"
        admin = db.query(User).filter(User.email == admin_email).first()
        if not admin:
            admin = User(
                name="System Administrator",
                email=admin_email,
                hashed_password=get_password_hash("AdminPass123!"),
                role="admin",
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            print(f"Created Admin user: {admin.email}")
        else:
            print(f"Admin user already exists: {admin.email}")

        # 2. Seed Agent Users
        agent1_email = "agent1@example.com"
        agent1 = db.query(User).filter(User.email == agent1_email).first()
        if not agent1:
            agent1 = User(
                name="Agent Jane",
                email=agent1_email,
                hashed_password=get_password_hash("AgentPass123!"),
                role="agent",
            )
            db.add(agent1)
            db.commit()
            db.refresh(agent1)
            print(f"Created Agent user: {agent1.email}")
        else:
            print(f"Agent user already exists: {agent1.email}")

        agent2_email = "agent2@example.com"
        agent2 = db.query(User).filter(User.email == agent2_email).first()
        if not agent2:
            agent2 = User(
                name="Agent Bob",
                email=agent2_email,
                hashed_password=get_password_hash("AgentPass123!"),
                role="agent",
            )
            db.add(agent2)
            db.commit()
            db.refresh(agent2)
            print(f"Created Agent user: {agent2.email}")

        # 3. Seed Demo Customer User
        customer_email = "seed-customer@example.com"
        customer = db.query(User).filter(User.email == customer_email).first()
        if not customer:
            customer = User(
                name="Demo Customer",
                email=customer_email,
                hashed_password=get_password_hash("CustomerPass123!"),
                role="customer",
            )
            db.add(customer)
            db.commit()
            db.refresh(customer)
            print(f"Created Customer user: {customer.email}")
        else:
            print(f"Customer user already exists: {customer.email}")

        # 4. Seed Sample Tickets for Demo Customer
        existing_tickets = db.query(Ticket).filter(Ticket.customer_id == customer.id).all()
        if not existing_tickets:
            now = datetime.now(timezone.utc)

            # Ticket 1: Critical (2h SLA)
            ticket1 = Ticket(
                title="Critical database connection timeout in EU cluster",
                description="Our production cluster is intermittently dropping connection pools.",
                category="Emergency",
                status="open",
                priority="critical",
                customer_id=customer.id,
                assigned_agent_id=agent1.id,
                created_at=now,
                deadline_at=now + timedelta(hours=settings.SLA_HOURS["critical"]),
                sla_breached=False,
            )
            db.add(ticket1)

            # Ticket 2: Medium (24h SLA)
            ticket2 = Ticket(
                title="Billing invoice missing VAT registration number",
                description="The exported monthly statement for August does not display our EU VAT ID.",
                category="Billing",
                status="in_progress",
                priority="medium",
                customer_id=customer.id,
                assigned_agent_id=agent1.id,
                created_at=now - timedelta(hours=2),
                deadline_at=now - timedelta(hours=2) + timedelta(hours=settings.SLA_HOURS["medium"]),
                sla_breached=False,
            )
            db.add(ticket2)

            db.commit()
            print("Created sample seed tickets.")
        else:
            print(f"Seed tickets already exist ({len(existing_tickets)} found).")

        print("Database seeding completed successfully.")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
