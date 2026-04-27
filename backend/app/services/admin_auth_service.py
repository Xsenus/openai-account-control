"""Cookie-backed session management for the local control panel."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe

from sqlalchemy.ext.asyncio import async_sessionmaker

from ..config import settings
from ..models import PanelUser
from .panel_user_service import PanelUserService


@dataclass(slots=True)
class AdminSession:
    """Authenticated control-panel session stored server-side."""

    token: str
    user_id: str
    username: str
    issued_at: datetime
    expires_at: datetime


class AdminAuthService:
    """Validate operator credentials from the database and manage browser sessions."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        """Initialize in-memory session storage and the DB session factory."""
        self._session_factory = session_factory
        self._sessions: dict[str, AdminSession] = {}
        self._lock = asyncio.Lock()
        self._ttl = timedelta(hours=settings.session_ttl_hours)

    def _utcnow(self) -> datetime:
        """Return timezone-aware UTC now."""
        return datetime.now(timezone.utc)

    def _cleanup_expired_locked(self) -> None:
        """Drop expired sessions while the internal lock is held."""
        now = self._utcnow()
        expired_tokens = [token for token, session in self._sessions.items() if session.expires_at <= now]
        for token in expired_tokens:
            self._sessions.pop(token, None)

    async def _get_user(self, user_id: str) -> PanelUser | None:
        """Load an operator by id from the database."""
        async with self._session_factory() as session:
            return await session.get(PanelUser, user_id)

    async def login(self, username: str, password: str) -> AdminSession | None:
        """Create a new session when the supplied credentials match an active operator."""
        async with self._session_factory() as session:
            users = PanelUserService(session)
            user = await users.get_by_username(username)
            if not user or not user.is_active:
                return None
            if not users.passwords.verify_password(password, user.password_hash):
                return None

            await users.mark_logged_in(user)

            issued_at = self._utcnow()
            auth_session = AdminSession(
                token=token_urlsafe(32),
                user_id=user.id,
                username=user.username,
                issued_at=issued_at,
                expires_at=issued_at + self._ttl,
            )

        async with self._lock:
            self._cleanup_expired_locked()
            self._sessions[auth_session.token] = auth_session

        return auth_session

    async def get_session(self, token: str | None) -> AdminSession | None:
        """Return an active session by token, pruning expired or deactivated users lazily."""
        if not token:
            return None

        async with self._lock:
            self._cleanup_expired_locked()
            auth_session = self._sessions.get(token)

        if auth_session is None:
            return None

        user = await self._get_user(auth_session.user_id)
        if not user or not user.is_active:
            await self.logout(token)
            return None

        if user.username != auth_session.username:
            auth_session = AdminSession(
                token=auth_session.token,
                user_id=auth_session.user_id,
                username=user.username,
                issued_at=auth_session.issued_at,
                expires_at=auth_session.expires_at,
            )
            async with self._lock:
                self._sessions[token] = auth_session

        return auth_session

    async def logout(self, token: str | None) -> None:
        """Invalidate one session token."""
        if not token:
            return

        async with self._lock:
            self._sessions.pop(token, None)

    async def invalidate_user_sessions(self, user_id: str) -> None:
        """Drop every active browser session that belongs to one operator."""
        async with self._lock:
            tokens = [token for token, session in self._sessions.items() if session.user_id == user_id]
            for token in tokens:
                self._sessions.pop(token, None)
