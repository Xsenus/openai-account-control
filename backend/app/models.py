"""SQLAlchemy models for accounts, settings, operators, scan history, and workspace snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for database defaults."""
    return datetime.now(timezone.utc)


def decimal_from_payload(value: Any) -> Decimal | None:
    """Convert JSON payload fragments back into Decimal values."""
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


class TimestampMixin:
    """Reusable created/updated timestamp fields."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Account(TimestampMixin, Base):
    """Stored OpenAI login account.

    One account may expose a personal workspace, multiple Business workspaces,
    or both. The actual password is never stored. We only keep encrypted
    Playwright storage_state JSON.
    """

    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    label: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    email_hint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auth_method: Mapped[str] = mapped_column(String(50), default="storage_state", nullable=False)
    encrypted_storage_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_auth_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_scan_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    snapshots: Mapped[list["WorkspaceSnapshot"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    scan_runs: Mapped[list["ScanRun"]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class WorkspaceSnapshot(TimestampMixin, Base):
    """One normalized scan result for one visible workspace at one point in time."""

    __tablename__ = "workspace_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)

    workspace_name: Mapped[str] = mapped_column(String(255), nullable=False)
    workspace_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    workspace_state: Mapped[str] = mapped_column(String(50), nullable=False)
    overall_status: Mapped[str] = mapped_column(String(50), nullable=False)

    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    seat_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    personal_plan: Mapped[str | None] = mapped_column(String(50), nullable=True)
    codex_limit_unit: Mapped[str | None] = mapped_column(String(50), nullable=True)

    included_limit_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    included_usage_percent_remaining: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    credits_balance: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    auto_topup_enabled: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    spend_limit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    source: Mapped[str] = mapped_column(String(100), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    evidence_dir: Mapped[str | None] = mapped_column(String(500), nullable=True)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    account: Mapped[Account] = relationship(back_populates="snapshots")

    @property
    def usage_summary(self) -> dict[str, Any]:
        """Structured quota details extracted during the scan, if any."""
        raw_payload = self.raw_payload if isinstance(self.raw_payload, dict) else {}
        usage_summary = raw_payload.get("usage_summary")
        return usage_summary if isinstance(usage_summary, dict) else {}

    @property
    def included_usage_total(self) -> Decimal | None:
        """Total included quota visible in the UI."""
        return decimal_from_payload(self.usage_summary.get("total"))

    @property
    def included_usage_used(self) -> Decimal | None:
        """Used part of the included quota visible in the UI."""
        return decimal_from_payload(self.usage_summary.get("used"))

    @property
    def included_usage_remaining(self) -> Decimal | None:
        """Remaining part of the included quota visible in the UI."""
        return decimal_from_payload(self.usage_summary.get("remaining"))

    @property
    def included_usage_refresh_text(self) -> str | None:
        """Human-readable next refresh/reset text captured from the UI."""
        value = self.usage_summary.get("refresh_text")
        return value if isinstance(value, str) and value.strip() else None

    @property
    def codex_usage(self) -> dict[str, Any]:
        """Structured daily/weekly Codex quota details captured from raw evidence."""
        raw_payload = self.raw_payload if isinstance(self.raw_payload, dict) else {}
        codex_usage = raw_payload.get("codex_usage")
        return codex_usage if isinstance(codex_usage, dict) else {}

    @property
    def team_invitation(self) -> dict[str, Any] | None:
        """Best-effort team/workspace invitation signal captured during scan."""
        raw_payload = self.raw_payload if isinstance(self.raw_payload, dict) else {}
        signal = raw_payload.get("team_invitation")
        return signal if isinstance(signal, dict) else None


class ScanRun(TimestampMixin, Base):
    """History entry for asynchronous scan execution."""

    __tablename__ = "scan_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    account_id: Mapped[str | None] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True)
    scope: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    account: Mapped[Account | None] = relationship(back_populates="scan_runs")


class AppSetting(TimestampMixin, Base):
    """Key/value settings persisted in database so the UI can change thresholds."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class PanelUser(TimestampMixin, Base):
    """Operator account allowed to log into the control panel."""

    __tablename__ = "panel_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
