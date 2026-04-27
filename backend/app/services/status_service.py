"""Convert raw workspace probe results into dashboard statuses."""

from __future__ import annotations

from decimal import Decimal

from ..enums import WorkspaceOverallStatus, WorkspaceState
from ..schemas import SettingsRead
from .types import ProbeWorkspaceResult


class StatusService:
    """Apply business rules to determine the top-level health status of a workspace."""

    def decide(self, item: ProbeWorkspaceResult, runtime_settings: SettingsRead) -> WorkspaceOverallStatus:
        """Map raw fields to a stable dashboard status.

        The goal is operational clarity:
        - BLOCKED means the workspace cannot currently be used.
        - DEACTIVATED means the workspace exists but is intentionally inactive.
        - PARTIAL means data is incomplete due to permissions/visibility.
        - LOW means usage or credit levels are approaching a problem.
        - OK means no known problem was detected.
        """
        if item.workspace_state == WorkspaceState.AUTH_EXPIRED:
            return WorkspaceOverallStatus.BLOCKED

        if item.workspace_state in {WorkspaceState.DEACTIVATED, WorkspaceState.MERGED}:
            return WorkspaceOverallStatus.DEACTIVATED

        if item.workspace_state == WorkspaceState.PARTIAL_VISIBILITY:
            return WorkspaceOverallStatus.PARTIAL

        if item.credits_balance is not None and item.credits_balance <= Decimal(str(runtime_settings.low_credits_threshold)):
            return WorkspaceOverallStatus.LOW

        codex_periods = list(item.codex_usage.values())
        if any(self._period_is_exhausted(period) for period in codex_periods):
            return WorkspaceOverallStatus.BLOCKED

        if any(
            period.percent_remaining is not None
            and period.percent_remaining <= Decimal(str(runtime_settings.low_usage_percent_threshold))
            for period in codex_periods
        ):
            return WorkspaceOverallStatus.LOW

        if (
            item.included_usage_percent_remaining is not None
            and item.included_usage_percent_remaining <= Decimal(str(runtime_settings.low_usage_percent_threshold))
        ):
            return WorkspaceOverallStatus.LOW

        if item.auto_topup_enabled is False and item.credits_balance is not None and item.credits_balance <= Decimal("0"):
            return WorkspaceOverallStatus.BLOCKED

        if item.workspace_state == WorkspaceState.UNKNOWN:
            return WorkspaceOverallStatus.UNKNOWN

        return WorkspaceOverallStatus.OK

    def _period_is_exhausted(self, period: object) -> bool:
        """Return whether a structured Codex period is fully depleted."""
        percent_remaining = getattr(period, "percent_remaining", None)
        if percent_remaining is not None and percent_remaining <= Decimal("0"):
            return True

        remaining = getattr(period, "remaining", None)
        total = getattr(period, "total", None)
        return remaining is not None and total is not None and total > Decimal("0") and remaining <= Decimal("0")
