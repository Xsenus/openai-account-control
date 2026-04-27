"""CRUD and password workflows for control-panel operators."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import PanelUser
from ..schemas import ChangePasswordRequest, PanelUserCreate, PanelUserUpdate
from .password_service import PasswordService


class PanelUserService:
    """Manage panel operators stored in the local database."""

    def __init__(self, session: AsyncSession, passwords: PasswordService | None = None) -> None:
        """Store the active DB session and password hashing helper."""
        self.session = session
        self.passwords = passwords or PasswordService()

    def _utcnow(self) -> datetime:
        """Return timezone-aware UTC now."""
        return datetime.now(timezone.utc)

    async def list_users(self) -> list[PanelUser]:
        """Return operators with active users first, then alphabetical username."""
        query = select(PanelUser).order_by(PanelUser.is_active.desc(), PanelUser.username.asc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def active_user_count(self) -> int:
        """Count active operators for guardrails around deactivation."""
        count = await self.session.scalar(
            select(func.count()).select_from(PanelUser).where(PanelUser.is_active.is_(True))
        )
        return int(count or 0)

    async def get_user(self, user_id: str) -> PanelUser | None:
        """Load one operator by primary key."""
        return await self.session.get(PanelUser, user_id)

    async def get_by_username(self, username: str) -> PanelUser | None:
        """Find an operator by exact username."""
        normalized = username.strip()
        if not normalized:
            return None

        query = select(PanelUser).where(PanelUser.username == normalized)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def ensure_bootstrap_user(self) -> PanelUser | None:
        """Create or reactivate the bootstrap operator if no active users remain."""
        if not settings.auth_enabled:
            return None

        if await self.active_user_count() > 0:
            return None

        existing = await self.get_by_username(settings.admin_username)
        if existing:
            existing.password_hash = self.passwords.hash_password(settings.admin_password)
            existing.is_active = True
            await self.session.commit()
            await self.session.refresh(existing)
            return existing

        user = PanelUser(
            username=settings.admin_username,
            password_hash=self.passwords.hash_password(settings.admin_password),
            is_active=True,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def create_user(self, payload: PanelUserCreate) -> PanelUser:
        """Create a new operator with a hashed password."""
        if await self.get_by_username(payload.username):
            raise ValueError("Operator with this username already exists.")

        user = PanelUser(
            username=payload.username.strip(),
            password_hash=self.passwords.hash_password(payload.password),
            is_active=payload.is_active,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user(self, user: PanelUser, payload: PanelUserUpdate) -> PanelUser:
        """Update operator activity without allowing all operators to disappear."""
        if payload.is_active is not None and payload.is_active is False and user.is_active:
            if await self.active_user_count() <= 1:
                raise ValueError("At least one active operator must remain.")

        if payload.is_active is not None:
            user.is_active = payload.is_active

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def change_password(self, user: PanelUser, payload: ChangePasswordRequest) -> None:
        """Validate the current password and store the replacement."""
        if not self.passwords.verify_password(payload.current_password, user.password_hash):
            raise ValueError("Current password is incorrect.")

        user.password_hash = self.passwords.hash_password(payload.new_password)
        await self.session.commit()

    async def mark_logged_in(self, user: PanelUser) -> None:
        """Persist the latest successful login timestamp."""
        user.last_login_at = self._utcnow()
        await self.session.commit()
