"""Routes for starting and inspecting scan jobs."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...dependencies import db_session
from ...models import Account, ScanRun
from ...schemas import MessageResponse, ScanRunRead
from ...services.scan_service import ScanService

router = APIRouter(prefix="/api", tags=["scans"])


@router.post("/accounts/{account_id}/scan", response_model=ScanRunRead)
async def start_account_scan(account_id: str, request: Request, session: AsyncSession = Depends(db_session)) -> ScanRunRead:
    """Queue a scan for one specific account."""
    account = await session.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Аккаунт не найден.")
    scan_service: ScanService = request.app.state.scan_service
    run = await scan_service.queue_single(account_id=account_id, manual=True)
    return ScanRunRead.model_validate(run)


@router.post("/scans/run-all", response_model=ScanRunRead)
async def start_inventory_scan(request: Request) -> ScanRunRead:
    """Queue a full inventory scan for all enabled accounts."""
    scan_service: ScanService = request.app.state.scan_service
    run = await scan_service.queue_all(manual=True)
    return ScanRunRead.model_validate(run)


@router.get("/scans", response_model=list[ScanRunRead])
async def list_scan_runs(session: AsyncSession = Depends(db_session)) -> list[ScanRunRead]:
    """Return latest scan runs for progress/history view."""
    query = select(ScanRun).order_by(ScanRun.created_at.desc()).limit(100)
    result = await session.execute(query)
    return [ScanRunRead.model_validate(item) for item in result.scalars().all()]


@router.get("/scans/{run_id}", response_model=ScanRunRead)
async def get_scan_run(run_id: str, session: AsyncSession = Depends(db_session)) -> ScanRunRead:
    """Return one scan run by id."""
    run = await session.get(ScanRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Проверка не найдена.")
    return ScanRunRead.model_validate(run)
