"""Pytest fixtures: an isolated, throwaway testcontainers Postgres.

Tests always run against a dedicated testcontainers Postgres so the developer's
local database is never touched. ``uv run`` loads ``.env`` into the process
environment (including ``DATABASE_URL``), so relying on an ambient
``DATABASE_URL`` here would make ``make test`` create and then *drop* tables in
the development database on teardown.
"""

from __future__ import annotations

import os

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker
from testcontainers.postgres import PostgresContainer

# Set DATABASE_URL before importing the app so the engine is created against
# the isolated test database, regardless of any ambient value.
_pg = PostgresContainer("postgres:16-alpine")
_pg.start()
os.environ["DATABASE_URL"] = _pg.get_connection_url().replace(
    "postgresql+psycopg2", "postgresql+asyncpg"
)

from app.db.models import Base  # noqa: E402
from app.db.session import engine  # noqa: E402

TestSession = async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _schema():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def session():
    async with TestSession() as s:
        yield s
        await s.rollback()


@pytest_asyncio.fixture
async def terminology():
    from app.domain.terminology.base import get_terminology_client

    return get_terminology_client()
