"""Service for editable runtime settings stored in the database."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import AppSetting
from ..schemas import SettingsRead, SettingsUpdate

SETTINGS_KEY = "runtime"


class SettingsService:
    """Load and update DB-backed settings, with env-based defaults as fallback."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the current database session."""
        self.session = session

    async def ensure_defaults(self) -> None:
        """Create the settings row if it does not exist yet."""
        existing = await self.session.get(AppSetting, SETTINGS_KEY)
        if existing:
            return
        record = AppSetting(
            key=SETTINGS_KEY,
            value={
                "scan_interval_minutes": settings.scan_interval_minutes,
                "low_credits_threshold": settings.low_credits_threshold,
                "low_usage_percent_threshold": settings.low_usage_percent_threshold,
            },
        )
        self.session.add(record)
        await self.session.commit()

    async def get(self) -> SettingsRead:
        """Return current settings as a typed schema."""
        await self.ensure_defaults()
        record = await self.session.get(AppSetting, SETTINGS_KEY)
        return SettingsRead(**record.value)

    async def update(self, payload: SettingsUpdate) -> SettingsRead:
        """Persist updated settings."""
        await self.ensure_defaults()
        record = await self.session.get(AppSetting, SETTINGS_KEY)
        record.value = payload.model_dump()
        await self.session.commit()
        await self.session.refresh(record)
        return SettingsRead(**record.value)
