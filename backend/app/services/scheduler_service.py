"""Scheduler wrapper around APScheduler for periodic inventory scans."""

from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..config import settings
from .scan_service import ScanService


class SchedulerService:
    """Own the APScheduler instance and keep it aligned with DB settings."""

    def __init__(self, scan_service: ScanService) -> None:
        """Create a scheduler bound to the provided scan service."""
        self.scan_service = scan_service
        self.scheduler = AsyncIOScheduler()
        self.started = False

    async def start(self, interval_minutes: int) -> None:
        """Start or restart the periodic scan job."""
        self.reschedule(interval_minutes)
        if not self.started:
            self.scheduler.start()
            self.started = True

    def reschedule(self, interval_minutes: int) -> None:
        """Replace the existing periodic job with a new interval."""
        if self.scheduler.get_job("scheduled-inventory-scan"):
            self.scheduler.remove_job("scheduled-inventory-scan")

        self.scheduler.add_job(
            self._scheduled_scan,
            "interval",
            minutes=interval_minutes,
            id="scheduled-inventory-scan",
            replace_existing=True,
        )

    async def stop(self) -> None:
        """Shutdown APScheduler gracefully."""
        if self.started:
            self.scheduler.shutdown(wait=False)
            self.started = False

    async def _scheduled_scan(self) -> None:
        """Queue a non-manual full scan if scheduling is enabled."""
        await self.scan_service.queue_all(manual=False)
