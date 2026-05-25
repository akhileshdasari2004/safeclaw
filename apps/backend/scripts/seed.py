"""Seed development user and license."""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from app.database import AsyncSessionLocal, Base, engine
from app.models.license import License
from app.models.user import User
from app.utils.security import generate_license_key, hash_password


async def seed() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        email = "dev@safeclaw.local"
        from sqlalchemy import select

        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            print("Seed data already exists")
            return

        user = User(email=email, hashed_password=hash_password("devpassword123"))
        db.add(user)
        await db.flush()

        lic = License(
            key=generate_license_key(),
            tier="pro",
            active=True,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
        )
        db.add(lic)
        await db.commit()
        print(f"Seeded user: {email} / devpassword123")
        print(f"License key: {lic.key}")


if __name__ == "__main__":
    asyncio.run(seed())
