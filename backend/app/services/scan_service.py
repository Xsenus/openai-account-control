"""Asynchronous scan orchestration for one account or the entire inventory."""

from __future__ import annotations

import asyncio
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..db import AsyncSessionFactory
from ..enums import (
    LimitUnit,
    ScanRunScope,
    ScanRunStatus,
    WorkspaceKind,
    WorkspaceState,
)
from ..models import Account, ScanRun, WorkspaceSnapshot
from ..schemas import SettingsRead
from .account_service import AccountService
from .exceptions import AuthExpiredError
from .openai_probe_service import OpenAIProbeService
from .settings_service import SettingsService
from .status_service import StatusService
from .types import ProbeWorkspaceResult


class ScanService:
    """Queue scan jobs and persist their results."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        probe_service: OpenAIProbeService | None = None,
        status_service: StatusService | None = None,
    ) -> None:
        """Create the scan orchestrator."""
        self.session_factory = session_factory or AsyncSessionFactory
        self.probe_service = probe_service or OpenAIProbeService()
        self.status_service = status_service or StatusService()

    async def queue_single(self, account_id: str, manual: bool = True) -> ScanRun:
        """Create a single-account run and launch it in background."""
        async with self.session_factory() as session:
            run = ScanRun(
                account_id=account_id,
                scope=ScanRunScope.SINGLE.value,
                status=ScanRunStatus.QUEUED.value,
                manual=manual,
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)

        asyncio.create_task(self.execute_run(run.id))
        return run

    async def queue_all(self, manual: bool = True) -> ScanRun:
        """Create a full-inventory run and launch it in background."""
        async with self.session_factory() as session:
            run = ScanRun(
                account_id=None,
                scope=ScanRunScope.ALL.value,
                status=ScanRunStatus.QUEUED.value,
                manual=manual,
            )
            session.add(run)
            await session.commit()
            await session.refresh(run)

        asyncio.create_task(self.execute_run(run.id))
        return run

    async def execute_run(self, run_id: str) -> None:
        """Run one queued scan job to completion."""
        async with self.session_factory() as session:
            run = await session.get(ScanRun, run_id)
            if not run:
                return
            run.status = ScanRunStatus.RUNNING.value
            run.started_at = datetime.now(timezone.utc)
            await session.commit()

        failures: list[dict[str, str]] = []
        scanned_accounts = 0
        scanned_workspaces = 0

        try:
            target_account_ids = await self._resolve_target_account_ids(run_id)

            for account_id in target_account_ids:
                try:
                    scanned_workspaces += await self._scan_one_account(account_id=account_id, run_id=run_id)
                    scanned_accounts += 1
                except Exception as exc:  # noqa: BLE001 - keep the batch moving.
                    failures.append({"account_id": account_id, "error": str(exc)})

            final_status = ScanRunStatus.SUCCESS.value
            if failures and scanned_accounts:
                final_status = ScanRunStatus.PARTIAL_SUCCESS.value
            elif failures and not scanned_accounts:
                final_status = ScanRunStatus.FAILED.value

            await self._finish_run(
                run_id=run_id,
                status=final_status,
                metrics={
                    "scanned_accounts": scanned_accounts,
                    "scanned_workspaces": scanned_workspaces,
                    "failures": failures,
                },
                error_message=None if final_status != ScanRunStatus.FAILED.value else "Все проверки завершились ошибкой.",
            )
        except Exception as exc:  # noqa: BLE001 - persist unexpected batch-level errors.
            await self._finish_run(
                run_id=run_id,
                status=ScanRunStatus.FAILED.value,
                metrics={
                    "scanned_accounts": scanned_accounts,
                    "scanned_workspaces": scanned_workspaces,
                    "failures": failures,
                },
                error_message=str(exc),
            )

    async def _resolve_target_account_ids(self, run_id: str) -> list[str]:
        """Return account ids covered by the run."""
        async with self.session_factory() as session:
            run = await session.get(ScanRun, run_id)
            if not run:
                return []

            if run.scope == ScanRunScope.SINGLE.value and run.account_id:
                return [run.account_id]

            query = select(Account.id).where(Account.is_enabled.is_(True)).order_by(Account.label.asc())
            result = await session.execute(query)
            return list(result.scalars().all())

    async def _scan_one_account(self, account_id: str, run_id: str) -> int:
        """Scan one account and persist all resulting workspace snapshots."""
        async with self.session_factory() as session:
            account = await session.get(Account, account_id)
            if not account:
                raise ValueError(f"Аккаунт {account_id} не найден.")

            settings_service = SettingsService(session)
            runtime_settings = await settings_service.get()
            account_service = AccountService(session)

            try:
                storage_state = account_service.get_storage_state(account)
            except Exception as exc:  # noqa: BLE001
                storage_state = None
                decrypt_error = str(exc)
            else:
                decrypt_error = None

            label = account.label

        # If there is no valid session, we persist a synthetic auth-expired snapshot.
        if not storage_state:
            synthetic = ProbeWorkspaceResult(
                workspace_name=label,
                workspace_kind=WorkspaceKind.PERSONAL,
                workspace_state=WorkspaceState.AUTH_EXPIRED,
                source="session_store",
                codex_limit_unit=LimitUnit.UNKNOWN,
                raw_payload={"error": decrypt_error or "Session state is missing."},
                checked_at=datetime.now(timezone.utc),
            )
            await self._persist_snapshots(account_id=account_id, snapshots=[synthetic], runtime_settings=runtime_settings)
            return 1

        try:
            probe_result = await self.probe_service.scan_account(
                storage_state=storage_state,
                account_id=account_id,
                account_label=label,
                run_id=run_id,
            )
            await self._persist_snapshots(
                account_id=account_id,
                snapshots=probe_result.workspaces,
                runtime_settings=runtime_settings,
            )
            return len(probe_result.workspaces)
        except AuthExpiredError as exc:
            synthetic = ProbeWorkspaceResult(
                workspace_name=label,
                workspace_kind=WorkspaceKind.PERSONAL,
                workspace_state=WorkspaceState.AUTH_EXPIRED,
                source="ui_probe",
                codex_limit_unit=LimitUnit.UNKNOWN,
                raw_payload={"error": str(exc)},
                checked_at=datetime.now(timezone.utc),
            )
            await self._persist_snapshots(account_id=account_id, snapshots=[synthetic], runtime_settings=runtime_settings)
            return 1

    async def _persist_snapshots(
        self,
        *,
        account_id: str,
        snapshots: list[ProbeWorkspaceResult],
        runtime_settings: SettingsRead,
    ) -> None:
        """Save normalized snapshots to the database."""
        async with self.session_factory() as session:
            account = await session.get(Account, account_id)
            if not account:
                raise ValueError(f"Аккаунт {account_id} не найден при сохранении snapshots.")

            for item in snapshots:
                overall_status = self.status_service.decide(item, runtime_settings)
                model = WorkspaceSnapshot(
                    account_id=account_id,
                    workspace_name=item.workspace_name,
                    workspace_kind=item.workspace_kind.value,
                    workspace_state=item.workspace_state.value,
                    overall_status=overall_status.value,
                    role=item.role,
                    seat_type=item.seat_type,
                    personal_plan=item.personal_plan,
                    codex_limit_unit=item.codex_limit_unit.value if item.codex_limit_unit else LimitUnit.UNKNOWN.value,
                    included_limit_text=item.included_limit_text,
                    included_usage_percent_remaining=item.included_usage_percent_remaining,
                    credits_balance=item.credits_balance,
                    auto_topup_enabled=item.auto_topup_enabled,
                    spend_limit=item.spend_limit,
                    source=item.source,
                    checked_at=item.checked_at or datetime.now(timezone.utc),
                    evidence_dir=item.evidence_dir,
                    raw_payload=item.raw_payload,
                )
                session.add(model)

            account.last_scan_at = datetime.now(timezone.utc)
            await session.commit()

    async def _finish_run(self, *, run_id: str, status: str, metrics: dict, error_message: str | None) -> None:
        """Mark a run as finished and persist summary metrics."""
        async with self.session_factory() as session:
            run = await session.get(ScanRun, run_id)
            if not run:
                return
            run.status = status
            run.metrics = metrics
            run.error_message = error_message
            run.finished_at = datetime.now(timezone.utc)
            await session.commit()
