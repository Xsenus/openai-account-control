"""Runtime settings and access-management routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from ...dependencies import current_panel_user, db_session
from ...models import PanelUser
from ...schemas import (
    ChangePasswordRequest,
    MessageResponse,
    PanelUserCreate,
    PanelUserRead,
    PanelUserUpdate,
    SettingsRead,
    SettingsUpdate,
)
from ...services.panel_user_service import PanelUserService
from ...services.settings_service import SettingsService

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=SettingsRead)
async def get_settings(session: AsyncSession = Depends(db_session)) -> SettingsRead:
    """Return the current runtime settings."""
    service = SettingsService(session)
    return await service.get()


@router.put("", response_model=SettingsRead)
async def update_settings(
    payload: SettingsUpdate,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> SettingsRead:
    """Persist settings and reschedule the periodic scan job."""
    service = SettingsService(session)
    updated = await service.update(payload)

    scheduler_service = request.app.state.scheduler_service
    if scheduler_service is not None:
        scheduler_service.reschedule(updated.scan_interval_minutes)

    return updated


@router.get("/access/users", response_model=list[PanelUserRead])
async def list_panel_users(session: AsyncSession = Depends(db_session)) -> list[PanelUserRead]:
    """Return all control-panel operators."""
    service = PanelUserService(session)
    return [PanelUserRead.model_validate(user) for user in await service.list_users()]


@router.post("/access/users", response_model=PanelUserRead)
async def create_panel_user(
    payload: PanelUserCreate,
    session: AsyncSession = Depends(db_session),
) -> PanelUserRead:
    """Create a new operator account for panel access."""
    service = PanelUserService(session)
    try:
        user = await service.create_user(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PanelUserRead.model_validate(user)


@router.put("/access/users/{user_id}", response_model=PanelUserRead)
async def update_panel_user(
    user_id: str,
    payload: PanelUserUpdate,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> PanelUserRead:
    """Enable or disable an operator."""
    service = PanelUserService(session)
    user = await service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Operator not found.")

    try:
        updated = await service.update_user(user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if payload.is_active is False:
        await request.app.state.admin_auth_service.invalidate_user_sessions(updated.id)

    return PanelUserRead.model_validate(updated)


@router.post("/access/change-password", response_model=MessageResponse)
async def change_current_password(
    payload: ChangePasswordRequest,
    session: AsyncSession = Depends(db_session),
    current_user: PanelUser = Depends(current_panel_user),
) -> MessageResponse:
    """Change the password of the currently authenticated operator."""
    service = PanelUserService(session)
    db_user = await service.get_user(current_user.id)
    if not db_user:
        raise HTTPException(status_code=404, detail="Operator not found.")

    try:
        await service.change_password(db_user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return MessageResponse(message="Password updated.")
