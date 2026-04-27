"""Shared pytest setup for backend tests."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

TEST_ROOT = Path(__file__).resolve().parent / ".runtime"
TEST_DB = TEST_ROOT / "app.db"

# Tests should not depend on a local .env file or the operator's real data directory.
os.environ.setdefault("ENCRYPTION_KEY", "4zrqM1E2z4_bfdxEusZT6X0hgqP-d9qbM9Q1E3L8qjk=")
os.environ.setdefault("SCHEDULER_ENABLED", "false")
os.environ.setdefault("AUTH_ENABLED", "true")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "ChangeMe123!")
os.environ.setdefault("DATA_DIR", TEST_ROOT.as_posix())
os.environ.setdefault("EVIDENCE_DIR", (TEST_ROOT / "evidence").as_posix())
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DB.resolve().as_posix()}")

TEST_ROOT.mkdir(parents=True, exist_ok=True)
(TEST_ROOT / "evidence").mkdir(parents=True, exist_ok=True)


@pytest.fixture(autouse=True)
def reset_database() -> None:
    """Isolate route tests by recreating the SQLite schema for every test."""
    from backend.app.db import engine
    from backend.app.models import Base

    async def _reset() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_reset())
