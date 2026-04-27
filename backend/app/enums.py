"""Centralized enums to keep API payloads and database values consistent."""

from enum import StrEnum


class WorkspaceKind(StrEnum):
    """Supported workspace types that can exist under one ChatGPT login."""

    PERSONAL = "personal"
    BUSINESS = "business"


class WorkspaceState(StrEnum):
    """Lifecycle and access state of a workspace."""

    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    MERGED = "merged"
    AUTH_EXPIRED = "auth_expired"
    PARTIAL_VISIBILITY = "partial_visibility"
    UNKNOWN = "unknown"


class WorkspaceOverallStatus(StrEnum):
    """Top-level traffic-light status for the dashboard."""

    OK = "ok"
    LOW = "low"
    BLOCKED = "blocked"
    PARTIAL = "partial"
    DEACTIVATED = "deactivated"
    UNKNOWN = "unknown"


class SeatType(StrEnum):
    """Known Business seat types as of the current OpenAI help center model."""

    STANDARD_CHATGPT = "standard_chatgpt"
    CODEX = "codex"
    UNKNOWN = "unknown"


class PersonalPlan(StrEnum):
    """Known personal plan labels."""

    FREE = "free"
    GO = "go"
    PLUS = "plus"
    PRO = "pro"
    UNKNOWN = "unknown"


class LimitUnit(StrEnum):
    """Unit in which Codex access/usage may be expressed."""

    MESSAGES = "messages"
    TOKENS = "tokens"
    CREDITS = "credits"
    UNKNOWN = "unknown"


class ScanRunScope(StrEnum):
    """Whether a scan covers one account or the entire inventory."""

    SINGLE = "single"
    ALL = "all"


class ScanRunStatus(StrEnum):
    """State of an asynchronous scan job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class AuthJobStatus(StrEnum):
    """State of an asynchronous local-browser authentication capture job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
