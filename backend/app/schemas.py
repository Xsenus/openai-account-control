"""Pydantic schemas used by FastAPI routes and service layers."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Simple health endpoint response."""

    status: str
    app: str
    now_utc: datetime


class LoginRequest(BaseModel):
    """Credentials used to unlock the control panel."""

    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=500)


class AuthSessionRead(BaseModel):
    """Frontend-facing view of the current panel session."""

    auth_enabled: bool
    authenticated: bool
    user_id: str | None
    username: str | None
    issued_at: datetime | None = None
    expires_at: datetime | None = None


class AccountBase(BaseModel):
    """Editable account fields."""

    label: str = Field(min_length=1, max_length=200)
    email_hint: str | None = Field(default=None, max_length=255)
    notes: str = Field(default="", max_length=5000)
    is_enabled: bool = True


class AccountCreate(AccountBase):
    """Payload used to create a new account entry."""


class AccountUpdate(BaseModel):
    """Patch payload for account updates."""

    label: str | None = Field(default=None, min_length=1, max_length=200)
    email_hint: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=5000)
    is_enabled: bool | None = None


class AccountRead(AccountBase):
    """Account DTO returned to frontend."""

    id: str
    auth_method: str
    has_session_state: bool
    last_auth_at: datetime | None
    last_scan_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SessionImportRequest(BaseModel):
    """Storage state JSON payload for importing an authenticated Playwright session."""

    storage_state: dict[str, Any]


class BrowserLoginStartRequest(BaseModel):
    """Parameters for interactive local Playwright login job."""

    timeout_seconds: int = Field(default=600, ge=60, le=1800)
    headless: bool = False


class AuthJobRead(BaseModel):
    """Public view of a local-browser auth job."""

    job_id: str
    account_id: str
    status: str
    message: str
    started_at: datetime | None = None
    finished_at: datetime | None = None


class CodexUsagePeriodRead(BaseModel):
    """Structured Codex quota details for one reset period."""

    period: str
    percent_remaining: Decimal | None = None
    total: Decimal | None = None
    used: Decimal | None = None
    remaining: Decimal | None = None
    refresh_text: str | None = None
    reset_at: str | None = None
    source_text: str | None = None
    confidence: str = "low"


class TeamInvitationRead(BaseModel):
    """Best-effort signal for pending team/workspace invitations."""

    status: str
    label: str | None = None
    source_text: str | None = None
    confidence: str = "low"


class WorkspaceSnapshotRead(BaseModel):
    """Normalized workspace snapshot for tables and history views."""

    id: str
    account_id: str
    workspace_name: str
    workspace_kind: str
    workspace_state: str
    overall_status: str
    role: str | None
    seat_type: str | None
    personal_plan: str | None
    codex_limit_unit: str | None
    included_limit_text: str | None
    included_usage_percent_remaining: Decimal | None
    included_usage_total: Decimal | None
    included_usage_used: Decimal | None
    included_usage_remaining: Decimal | None
    included_usage_refresh_text: str | None
    codex_usage: dict[str, CodexUsagePeriodRead]
    team_invitation: TeamInvitationRead | None
    credits_balance: Decimal | None
    auto_topup_enabled: bool | None
    spend_limit: Decimal | None
    source: str
    checked_at: datetime
    evidence_dir: str | None
    raw_payload: dict[str, Any]

    model_config = {"from_attributes": True}


class ScanRunRead(BaseModel):
    """Scan job history row."""

    id: str
    account_id: str | None
    scope: str
    status: str
    manual: bool
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    metrics: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DashboardCounters(BaseModel):
    """Top summary cards for the dashboard."""

    total_accounts: int
    active_accounts: int
    with_valid_session: int
    workspaces_ok: int
    workspaces_low: int
    workspaces_blocked: int
    workspaces_deactivated: int
    workspaces_partial: int
    last_scan_at: datetime | None


class DashboardSummaryResponse(BaseModel):
    """Combined dashboard response with counters and latest snapshots."""

    counters: DashboardCounters
    latest_snapshots: list[WorkspaceSnapshotRead]
    latest_runs: list[ScanRunRead]


class SettingsRead(BaseModel):
    """Editable runtime settings."""

    scan_interval_minutes: int = Field(ge=15, le=1440)
    low_credits_threshold: float = Field(ge=0, le=1000000)
    low_usage_percent_threshold: float = Field(ge=0, le=100)


class SettingsUpdate(SettingsRead):
    """Same schema as SettingsRead, but semantically used for updates."""


class PanelUserRead(BaseModel):
    """Operator account returned to the settings UI."""

    id: str
    username: str
    is_active: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PanelUserCreate(BaseModel):
    """Payload for creating a new operator."""

    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=500)
    is_active: bool = True


class PanelUserUpdate(BaseModel):
    """Patch payload for operator activity changes."""

    is_active: bool | None = None


class ChangePasswordRequest(BaseModel):
    """Payload for changing the current operator password."""

    current_password: str = Field(min_length=1, max_length=500)
    new_password: str = Field(min_length=8, max_length=500)


class MessageResponse(BaseModel):
    """Generic one-line response payload."""

    message: str
