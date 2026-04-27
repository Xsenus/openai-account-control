"""Text and regex phrases used by the OpenAI UI probe.

ChatGPT's web UI changes over time. The strategy in this project is:
1. Prefer visible text and semantic roles over brittle CSS classes.
2. Keep phrases centralized so updates are easy when the UI changes.
3. Store evidence on every scan to make phrase tuning straightforward.
"""

from __future__ import annotations

import re
from collections.abc import Iterable


def ci_pattern(*phrases: str) -> re.Pattern[str]:
    """Build one case-insensitive regex pattern from multiple literal phrases."""
    escaped = [re.escape(item) for item in phrases]
    return re.compile("|".join(escaped), re.IGNORECASE)


PROFILE_BUTTON_PATTERNS = [
    ci_pattern("Profile", "Account", "Workspace", "Open profile", "Avatar"),
]

SETTINGS_PATTERNS = [
    ci_pattern("Settings", "Настройки"),
]

BILLING_PATTERNS = [
    ci_pattern("Billing", "Оплата", "Биллинг", "Credits", "Usage and billing"),
]

USAGE_PATTERNS = [
    ci_pattern("Usage", "Usage Dashboard", "Использование"),
]

WORKSPACE_PATTERNS = [
    ci_pattern("Workspaces", "Рабочие пространства", "Workspace"),
]

MEMBERS_PATTERNS = [
    ci_pattern("Members", "Участники", "People"),
]

LOCKED_PATTERNS = [
    ci_pattern("deactivated", "locked", "inactive", "отключ", "деактив"),
]

OWNER_PATTERNS = [
    ci_pattern("Owner", "Владелец"),
]

ADMIN_PATTERNS = [
    ci_pattern("Admin", "Администратор"),
]

MEMBER_PATTERNS = [
    ci_pattern("Member", "Участник"),
]

PLAN_PATTERNS = {
    "free": ci_pattern("Free"),
    "go": ci_pattern("Go"),
    "plus": ci_pattern("Plus"),
    "pro": ci_pattern("Pro"),
    "business": ci_pattern("Business"),
}

SEAT_PATTERNS = {
    "standard_chatgpt": ci_pattern("standard ChatGPT seat", "ChatGPT seat", "standard seat"),
    "codex": ci_pattern("Codex seat", "Codex seats", "usage-based Codex seat"),
}

UNIT_PATTERNS = {
    "messages": ci_pattern("messages"),
    "tokens": ci_pattern("tokens"),
    "credits": ci_pattern("credits"),
}

TOPUP_ON_PATTERNS = [
    ci_pattern("Auto top-up on", "Auto recharge on", "auto top-up enabled"),
]

TOPUP_OFF_PATTERNS = [
    ci_pattern("Auto top-up off", "Auto recharge off", "auto top-up disabled"),
]

INCLUDED_LIMIT_HINT_PATTERNS = [
    ci_pattern("included", "remaining", "limit", "usage"),
]


def matches_any(patterns: Iterable[re.Pattern[str]], text: str) -> bool:
    """Return True when at least one regex pattern matches the text."""
    return any(pattern.search(text) for pattern in patterns)
