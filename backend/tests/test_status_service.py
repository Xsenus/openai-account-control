"""Unit tests for status calculation rules."""

from decimal import Decimal

from backend.app.enums import LimitUnit, WorkspaceKind, WorkspaceOverallStatus, WorkspaceState
from backend.app.schemas import SettingsRead
from backend.app.services.status_service import StatusService
from backend.app.services.types import ProbeWorkspaceResult


def test_status_low_when_credits_below_threshold() -> None:
    """Credits at or below threshold should produce LOW status."""
    service = StatusService()
    result = ProbeWorkspaceResult(
        workspace_name="A",
        workspace_kind=WorkspaceKind.BUSINESS,
        workspace_state=WorkspaceState.ACTIVE,
        credits_balance=Decimal("10"),
        codex_limit_unit=LimitUnit.CREDITS,
    )
    settings = SettingsRead(
        scan_interval_minutes=180,
        low_credits_threshold=15.0,
        low_usage_percent_threshold=20.0,
    )
    assert service.decide(result, settings) == WorkspaceOverallStatus.LOW


def test_status_deactivated_when_workspace_locked() -> None:
    """Deactivated workspace should map to DEACTIVATED top-level status."""
    service = StatusService()
    result = ProbeWorkspaceResult(
        workspace_name="B",
        workspace_kind=WorkspaceKind.BUSINESS,
        workspace_state=WorkspaceState.DEACTIVATED,
        codex_limit_unit=LimitUnit.UNKNOWN,
    )
    settings = SettingsRead(
        scan_interval_minutes=180,
        low_credits_threshold=15.0,
        low_usage_percent_threshold=20.0,
    )
    assert service.decide(result, settings) == WorkspaceOverallStatus.DEACTIVATED
