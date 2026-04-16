"""Seed the initial Higher Authority admin account.

Run once: python scripts/seed_admin.py
"""

import sys
import os
import uuid

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.auth import hash_password
from db.connection import get_db_session
from db.models import Base, UserModel
from db.connection import get_engine


def seed():
    """Create the initial admin account if it doesn't exist."""
    # Create tables
    engine = get_engine()
    Base.metadata.create_all(engine)

    session = get_db_session()
    try:
        existing = session.query(UserModel).filter_by(username="admin").first()
        if existing:
            print(f"Admin account already exists (id={existing.id}, role={existing.role})")
            return

        admin = UserModel(
            id=str(uuid.uuid4()),
            username="admin",
            email="admin@company.com",
            password_hash=hash_password("admin123"),
            full_name="System Administrator",
            role="higher_authority",
            is_active=True,
            created_by=None,
        )
        session.add(admin)
        session.commit()
        print(f"Admin account created successfully!")
        print(f"  Username: admin")
        print(f"  Password: admin123")
        print(f"  Role:     higher_authority")
        print(f"  ID:       {admin.id}")
        print(f"\n  *** Change this password after first login! ***")

    finally:
        session.close()


if __name__ == "__main__":
    seed()
