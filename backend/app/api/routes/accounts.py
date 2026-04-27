"""Account management and authentication onboarding routes."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...dependencies import db_session
from ...models import Account, WorkspaceSnapshot
from ...schemas import (
    AccountCreate,
    AccountRead,
    AccountUpdate,
    AuthJobRead,
    BrowserLoginStartRequest,
    MessageResponse,
    SessionImportRequest,
    WorkspaceSnapshotRead,
)
from ...services.account_service import AccountService

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


def to_account_read(account: Account) -> AccountRead:
    """Convert a SQLAlchemy model to a frontend DTO."""
    return AccountRead(
        id=account.id,
        label=account.label,
        email_hint=account.email_hint,
        notes=account.notes,
        is_enabled=account.is_enabled,
        auth_method=account.auth_method,
        has_session_state=bool(account.encrypted_storage_state),
        last_auth_at=account.last_auth_at,
        last_scan_at=account.last_scan_at,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


@router.get("", response_model=list[AccountRead])
async def list_accounts(session: AsyncSession = Depends(db_session)) -> list[AccountRead]:
    """Return all managed accounts."""
    service = AccountService(session)
    accounts = await service.list_accounts()
    return [to_account_read(item) for item in accounts]


@router.post("", response_model=AccountRead)
async def create_account(payload: AccountCreate, session: AsyncSession = Depends(db_session)) -> AccountRead:
    """Create a new account entry."""
    service = AccountService(session)
    account = await service.create_account(payload)
    return to_account_read(account)


@router.get("/{account_id}", response_model=AccountRead)
async def get_account(account_id: str, session: AsyncSession = Depends(db_session)) -> AccountRead:
    """Get one account by id."""
    service = AccountService(session)
    account = await service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден.")
    return to_account_read(account)


@router.put("/{account_id}", response_model=AccountRead)
async def update_account(account_id: str, payload: AccountUpdate, session: AsyncSession = Depends(db_session)) -> AccountRead:
    """Update account fields."""
    service = AccountService(session)
    account = await service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден.")
    account = await service.update_account(account, payload)
    return to_account_read(account)


@router.delete("/{account_id}", response_model=MessageResponse)
async def delete_account(account_id: str, session: AsyncSession = Depends(db_session)) -> MessageResponse:
    """Delete an account and all snapshots/history under it."""
    service = AccountService(session)
    account = await service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден.")
    await service.delete_account(account)
    return MessageResponse(message="Аккаунт удален.")


@router.post("/{account_id}/auth/import", response_model=AccountRead)
async def import_session_state(
    account_id: str,
    payload: SessionImportRequest,
    session: AsyncSession = Depends(db_session),
) -> AccountRead:
    """Import Playwright storage_state JSON for an account."""
    service = AccountService(session)
    account = await service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден.")
    try:
        account = await service.import_storage_state(account, payload.storage_state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return to_account_read(account)


@router.post("/{account_id}/auth/browser-login", response_model=AuthJobRead)
async def start_browser_login_job(
    account_id: str,
    payload: BrowserLoginStartRequest,
    request: Request,
    session: AsyncSession = Depends(db_session),
) -> AuthJobRead:
    """Start an interactive local-browser login capture job."""
    service = AccountService(session)
    account = await service.get_account(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден.")

    async def save_storage_state(storage_state: dict) -> None:
        """Persist the newly captured session state via a fresh DB session."""
        from ...db import AsyncSessionFactory

        async with AsyncSessionFactory() as inner_session:
            inner_service = AccountService(inner_session)
            inner_account = await inner_service.get_account(account_id)
            if not inner_account:
                raise RuntimeError("Аккаунт был удален во время авторизации.")
            await inner_service.import_storage_state(inner_account, storage_state)

    auth_job_service = request.app.state.auth_job_service
    job = await auth_job_service.start(
        account_id=account_id,
        timeout_seconds=payload.timeout_seconds,
        headless=payload.headless,
        on_success=save_storage_state,
    )
    return AuthJobRead.model_validate(asdict(job))


@router.get("/{account_id}/auth/browser-login/{job_id}", response_model=AuthJobRead)
async def get_browser_login_job(account_id: str, job_id: str, request: Request) -> AuthJobRead:
    """Return the current status of a browser login job."""
    auth_job_service = request.app.state.auth_job_service
    job = await auth_job_service.get(job_id)
    if not job or job.account_id != account_id:
        raise HTTPException(status_code=404, detail="Задача авторизации не найдена.")
    return AuthJobRead.model_validate(asdict(job))


@router.get("/snapshots/latest", response_model=list[WorkspaceSnapshotRead])
async def list_latest_snapshots(session: AsyncSession = Depends(db_session)) -> list[WorkspaceSnapshotRead]:
    """Return latest snapshot per account/workspace for the accounts page."""
    # SQLite-friendly fallback: fetch recent rows and dedupe in Python.
    query = select(WorkspaceSnapshot).order_by(WorkspaceSnapshot.checked_at.desc()).limit(1000)
    result = await session.execute(query)

    seen: set[tuple[str, str]] = set()
    latest: list[WorkspaceSnapshot] = []
    for snapshot in result.scalars().all():
        key = (snapshot.account_id, snapshot.workspace_name)
        if key in seen:
            continue
        seen.add(key)
        latest.append(snapshot)

    return [WorkspaceSnapshotRead.model_validate(item) for item in latest]


@router.get("/{account_id}/snapshots", response_model=list[WorkspaceSnapshotRead])
async def list_account_snapshots(account_id: str, session: AsyncSession = Depends(db_session)) -> list[WorkspaceSnapshotRead]:
    """List historical snapshots for one account."""
    account = await session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден.")

    query = (
        select(WorkspaceSnapshot)
        .where(WorkspaceSnapshot.account_id == account_id)
        .order_by(WorkspaceSnapshot.checked_at.desc())
        .limit(200)
    )
    result = await session.execute(query)
    return [WorkspaceSnapshotRead.model_validate(item) for item in result.scalars().all()]
