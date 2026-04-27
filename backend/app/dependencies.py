"""Reusable FastAPI dependencies and convenience helpers."""

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .db import get_db_session
from .models import PanelUser
from .services.admin_auth_service import AdminSession


async def db_session(session: AsyncSession = Depends(get_db_session)) -> AsyncSession:
    """Alias dependency so route signatures read clearly."""
    return session


async def panel_session(request: Request) -> AdminSession:
    """Return the authenticated panel session from middleware state."""
    if not settings.auth_enabled:
        raise HTTPException(status_code=400, detail="Panel auth is disabled.")

    session = getattr(request.state, "admin_session", None)
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required.")

    return session


async def current_panel_user(
    admin_session: AdminSession = Depends(panel_session),
    session: AsyncSession = Depends(db_session),
) -> PanelUser:
    """Load the current operator account from the database."""
    user = await session.get(PanelUser, admin_session.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user
