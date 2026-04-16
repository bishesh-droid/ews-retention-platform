"""
Run once during local development setup: python -m backend.scripts.seed_dev_data
Creates a hashed admin user for local testing. Never runs automatically.
"""

import asyncio
from backend.database.session import get_session
from backend.core.security import get_password_hash
from backend.database.models.user import User


async def seed():
    async with get_session() as session:
        existing = session.query(User).filter(User.username == "dev_admin").first()
        if existing:
            print("Dev admin already exists — skipping")
            return
        user = User(
            username="dev_admin",
            hashed_password=get_password_hash("changeme_local_only"),
            role="admin",
            is_superuser=True,
        )
        session.add(user)
        session.commit()
        print("Dev admin created: dev_admin / changeme_local_only")


if __name__ == "__main__":
    asyncio.run(seed())
