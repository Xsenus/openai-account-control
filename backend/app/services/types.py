"""Internal dataclasses exchanged between probe, parser, and scanner services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from ..enums import LimitUnit, WorkspaceKind, WorkspaceState


@dataclass(slots=True)
class CodexUsagePeriod:
    """Structured Codex usage details for one refresh period."""

    period: str
    percent_remaining: Decimal | None = None
    total: Decimal | None = None
    used: Decimal | None = None
    remaining: Decimal | None = None
    refresh_text: str | None = None
    reset_at: str | None = None
    source_text: str | None = None
    confidence: str = "low"


@dataclass(slots=True)
class TeamInvitationSignal:
    """Best-effort signal that the account sees a team/workspace invitation."""

    status: str
    label: str | None = None
    source_text: str | None = None
    confidence: str = "low"


@dataclass(slots=True)
class ProbeWorkspaceResult:
    """Unnormalized raw result extracted from ChatGPT UI or billing screens."""

    workspace_name: str
    workspace_kind: WorkspaceKind
    workspace_state: WorkspaceState
    role: str | None = None
    seat_type: str | None = None
    personal_plan: str | None = None
    codex_limit_unit: LimitUnit | None = None
    included_limit_text: str | None = None
    included_usage_percent_remaining: Decimal | None = None
    included_usage_total: Decimal | None = None
    included_usage_used: Decimal | None = None
    included_usage_remaining: Decimal | None = None
    included_usage_refresh_text: str | None = None
    codex_usage: dict[str, CodexUsagePeriod] = field(default_factory=dict)
    team_invitation: TeamInvitationSignal | None = None
    credits_balance: Decimal | None = None
    auto_topup_enabled: bool | None = None
    spend_limit: Decimal | None = None
    source: str = "ui_probe"
    raw_payload: dict[str, Any] = field(default_factory=dict)
    evidence_dir: str | None = None
    checked_at: datetime | None = None


@dataclass(slots=True)
class ProbeAccountResult:
    """Collection of workspaces discovered under one account session."""

    workspaces: list[ProbeWorkspaceResult]
    account_level_payload: dict[str, Any] = field(default_factory=dict)
