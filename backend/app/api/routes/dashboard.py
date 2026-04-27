"""Dashboard routes with counters and latest workspace state."""

from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...dependencies import db_session
from ...models import Account, ScanRun, WorkspaceSnapshot
from ...schemas import DashboardCounters, DashboardSummaryResponse, ScanRunRead, WorkspaceSnapshotRead

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


async def get_latest_workspace_snapshots(session: AsyncSession) -> list[WorkspaceSnapshot]:
    """Return the newest snapshot per (account_id, workspace_name) pair."""
    subquery = (
        select(
            WorkspaceSnapshot.account_id.label("account_id"),
            WorkspaceSnapshot.workspace_name.label("workspace_name"),
            func.max(WorkspaceSnapshot.checked_at).label("max_checked_at"),
        )
        .group_by(WorkspaceSnapshot.account_id, WorkspaceSnapshot.workspace_name)
        .subquery()
    )

    query = (
        select(WorkspaceSnapshot)
        .join(
            subquery,
            and_(
                WorkspaceSnapshot.account_id == subquery.c.account_id,
                WorkspaceSnapshot.workspace_name == subquery.c.workspace_name,
                WorkspaceSnapshot.checked_at == subquery.c.max_checked_at,
            ),
        )
        .order_by(WorkspaceSnapshot.checked_at.desc())
        .limit(100)
    )
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get("/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(session: AsyncSession = Depends(db_session)) -> DashboardSummaryResponse:
    """Return summary counters, latest snapshots, and latest runs."""
    latest_snapshots = await get_latest_workspace_snapshots(session)

    accounts_count = await session.scalar(select(func.count()).select_from(Account))
    active_accounts_count = await session.scalar(select(func.count()).select_from(Account).where(Account.is_enabled.is_(True)))
    accounts_with_session = await session.scalar(
        select(func.count()).select_from(Account).where(Account.encrypted_storage_state.is_not(None))
    )

    counter = Counter(snapshot.overall_status for snapshot in latest_snapshots)
    last_scan_at = max((snapshot.checked_at for snapshot in latest_snapshots), default=None)

    runs_query = select(ScanRun).order_by(ScanRun.created_at.desc()).limit(10)
    runs_result = await session.execute(runs_query)
    latest_runs = list(runs_result.scalars().all())

    return DashboardSummaryResponse(
        counters=DashboardCounters(
            total_accounts=int(accounts_count or 0),
            active_accounts=int(active_accounts_count or 0),
            with_valid_session=int(accounts_with_session or 0),
            workspaces_ok=int(counter.get("ok", 0)),
            workspaces_low=int(counter.get("low", 0)),
            workspaces_blocked=int(counter.get("blocked", 0)),
            workspaces_deactivated=int(counter.get("deactivated", 0)),
            workspaces_partial=int(counter.get("partial", 0)),
            last_scan_at=last_scan_at,
        ),
        latest_snapshots=[WorkspaceSnapshotRead.model_validate(item) for item in latest_snapshots],
        latest_runs=[ScanRunRead.model_validate(item) for item in latest_runs],
    )
