"""In-memory orchestrator for interactive local-browser login jobs.

This service is intentionally lightweight:
- It is enough for a self-hosted single-instance deployment.
- A future multi-instance deployment can replace it with Redis or a DB queue.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from .playwright_session_service import PlaywrightSessionService


@dataclass(slots=True)
class AuthJob:
    """State snapshot for one local-browser authentication capture job."""

    job_id: str
    account_id: str
    status: str
    message: str
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AuthJobService:
    """Start and track browser-based login capture jobs."""

    def __init__(self, playwright_service: PlaywrightSessionService | None = None) -> None:
        """Create an empty in-memory registry."""
        self.playwright_service = playwright_service or PlaywrightSessionService()
        self.jobs: dict[str, AuthJob] = {}
        self._lock = asyncio.Lock()

    async def start(
        self,
        *,
        account_id: str,
        timeout_seconds: int,
        headless: bool,
        on_success: Callable[[dict], "asyncio.Future[None] | None"],
    ) -> AuthJob:
        """Create and launch a new auth capture job."""
        job = AuthJob(
            job_id=str(uuid4()),
            account_id=account_id,
            status="queued",
            message="Задача создана. Ожидается запуск локального браузера.",
        )
        async with self._lock:
            self.jobs[job.job_id] = job

        asyncio.create_task(
            self._run_job(
                job_id=job.job_id,
                timeout_seconds=timeout_seconds,
                headless=headless,
                on_success=on_success,
            )
        )
        return job

    async def get(self, job_id: str) -> AuthJob | None:
        """Read a job by its identifier."""
        return self.jobs.get(job_id)

    async def _run_job(
        self,
        *,
        job_id: str,
        timeout_seconds: int,
        headless: bool,
        on_success: Callable[[dict], "asyncio.Future[None] | None"],
    ) -> None:
        """Execute the interactive browser login flow."""
        job = self.jobs[job_id]
        job.status = "running"
        job.message = (
            "Открыт локальный браузер. Выполните вход в ChatGPT и дождитесь завершения "
            "Cloudflare-проверки, если она появилась."
        )
        job.started_at = datetime.now(timezone.utc)

        try:
            storage_state = await self.playwright_service.capture_storage_state_interactively(
                account_id=job.account_id,
                timeout_seconds=timeout_seconds,
                headless=headless,
            )

            result = on_success(storage_state)
            if asyncio.iscoroutine(result):
                await result

            job.status = "success"
            job.message = "Сессия успешно сохранена."
            job.finished_at = datetime.now(timezone.utc)
        except Exception as exc:
            job.status = "failed"
            job.message = f"Ошибка во время авторизации: {exc}"
            job.finished_at = datetime.now(timezone.utc)
