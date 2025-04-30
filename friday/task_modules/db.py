# tasks.py

from invoke import task
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import AsyncEngine
from app.models.database import Base
from app.config import settings
import asyncio

DB_URL = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
engine: AsyncEngine = create_async_engine(DB_URL, echo=True)


@task
def init(c):
    """Drop and recreate all tables."""
    async def run():
        async with engine.begin() as conn:
            print("⚠️ Dropping all tables...")
            await conn.run_sync(Base.metadata.drop_all)
            print("✅ Creating all tables...")
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database initialized.")

    asyncio.run(run())


@task
def clear(c):
    """Truncate all major tables (does not drop schema)."""
    async def run():
        async with engine.begin() as conn:
            print("🧹 Truncating data from tables...")
            tables = [
                "steps",
                "scenario_tags",
                "scenarios",
                "features",
                "test_runs",
                "build_infos",
                "health_metrics",
                "projects"
            ]
            for table in tables:
                await conn.execute(text(f'TRUNCATE TABLE "{table}" CASCADE'))
        print("✅ All table data cleared.")

    asyncio.run(run())

