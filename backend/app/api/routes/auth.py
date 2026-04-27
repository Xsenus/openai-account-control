"""Authentication routes for the self-hosted admin panel."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from ...config import settings
from ...schemas import AuthSessionRead, LoginRequest
from ...services.admin_auth_service import AdminSession

router = APIRouter(prefix="/api/auth", tags=["auth"])


def to_auth_session_read(session: AdminSession | None) -> AuthSessionRead:
    """Serialize a panel session for the frontend."""
    if not settings.auth_enabled:
        return AuthSessionRead(
            auth_enabled=False,
            authenticated=True,
            user_id=None,
            username=None,
            issued_at=None,
            expires_at=None,
        )

    if session is None:
        return AuthSessionRead(
            auth_enabled=True,
            authenticated=False,
            user_id=None,
            username=None,
            issued_at=None,
            expires_at=None,
        )

    return AuthSessionRead(
        auth_enabled=True,
        authenticated=True,
        user_id=session.user_id,
        username=session.username,
        issued_at=session.issued_at,
        expires_at=session.expires_at,
    )


@router.get("/session", response_model=AuthSessionRead)
async def get_panel_session(request: Request) -> AuthSessionRead:
    """Return whether the browser currently holds a valid control-panel session."""
    if not settings.auth_enabled:
        return to_auth_session_read(None)

    auth_service = request.app.state.admin_auth_service
    token = request.cookies.get(settings.session_cookie_name)
    session = await auth_service.get_session(token)
    return to_auth_session_read(session)


@router.post("/login", response_model=AuthSessionRead)
async def login(payload: LoginRequest, request: Request, response: Response) -> AuthSessionRead:
    """Validate configured credentials and issue a secure cookie session."""
    if not settings.auth_enabled:
        return to_auth_session_read(None)

    auth_service = request.app.state.admin_auth_service
    session = await auth_service.login(payload.username, payload.password)
    if session is None:
        raise HTTPException(status_code=401, detail="Invalid panel username or password.")

    ttl_seconds = settings.session_ttl_hours * 60 * 60
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session.token,
        max_age=ttl_seconds,
        expires=ttl_seconds,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite="lax",
    )
    return to_auth_session_read(session)


@router.post("/logout", response_model=AuthSessionRead)
async def logout(request: Request, response: Response) -> AuthSessionRead:
    """Invalidate the current session cookie."""
    if settings.auth_enabled:
        auth_service = request.app.state.admin_auth_service
        token = request.cookies.get(settings.session_cookie_name)
        await auth_service.logout(token)
        response.delete_cookie(
            key=settings.session_cookie_name,
            httponly=True,
            secure=settings.session_cookie_secure,
            samesite="lax",
        )

    return AuthSessionRead(
        auth_enabled=settings.auth_enabled,
        authenticated=not settings.auth_enabled,
        user_id=None,
        username=None,
        issued_at=None,
        expires_at=None,
    )
