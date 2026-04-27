"""Text parsing helpers used by the UI probe.

The parser is deliberately heuristic because ChatGPT's UI is not a stable,
public API for account/workspace billing details. Every scan stores evidence so
you can adjust these rules when OpenAI changes labels or wording.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from ..enums import LimitUnit, PersonalPlan, SeatType
from ..selectors.parser_patterns import (
    ANY_PERCENT_RE,
    CODEX_CONTEXT_RE,
    CODEX_DAILY_RE,
    CODEX_WEEKLY_RE,
    CREDITS_BALANCE_RE,
    INCLUDED_LIMIT_LINE_RE,
    PERCENT_REMAINING_RE,
    SPEND_LIMIT_RE,
    TEAM_INVITATION_RE,
    USAGE_REFRESH_LINE_RE,
    USAGE_REMAINING_OF_TOTAL_RE,
    USAGE_REMAINING_RE,
    USAGE_SLASH_TOTAL_RE,
    USAGE_TOTAL_RE,
    USAGE_USED_OF_TOTAL_RE,
    USAGE_USED_RE,
)
from ..selectors.phrases import (
    INCLUDED_LIMIT_HINT_PATTERNS,
    PLAN_PATTERNS,
    SEAT_PATTERNS,
    TOPUP_OFF_PATTERNS,
    TOPUP_ON_PATTERNS,
    UNIT_PATTERNS,
    matches_any,
)
from .types import CodexUsagePeriod, TeamInvitationSignal


def _to_decimal(raw: str | None) -> Decimal | None:
    """Convert strings like '12.50' or '12,50' to Decimal."""
    if not raw:
        return None
    try:
        return Decimal(raw.replace(",", "."))
    except InvalidOperation:
        return None


@dataclass(slots=True)
class IncludedUsageDetails:
    """Structured quota details extracted from visible ChatGPT billing text."""

    used: Decimal | None = None
    total: Decimal | None = None
    remaining: Decimal | None = None
    refresh_text: str | None = None


class ParserService:
    """Convert large page text blobs into structured signals."""

    REMAINING_KEYWORDS = ("remaining", "left", "available", "осталось", "доступно")
    USED_KEYWORDS = ("used", "spent", "consumed", "использовано", "потрачено")
    PERIOD_WINDOW_LINES = 3

    def detect_plan(self, text: str) -> PersonalPlan | None:
        """Infer personal plan name from visible text."""
        for plan_name, pattern in PLAN_PATTERNS.items():
            if pattern.search(text):
                if plan_name in PersonalPlan.__members__.values():
                    # This branch is never hit because __members__ keys differ from values,
                    # but it documents the intent and keeps the loop readable.
                    pass
        if PLAN_PATTERNS["pro"].search(text):
            return PersonalPlan.PRO
        if PLAN_PATTERNS["plus"].search(text):
            return PersonalPlan.PLUS
        if PLAN_PATTERNS["go"].search(text):
            return PersonalPlan.GO
        if PLAN_PATTERNS["free"].search(text):
            return PersonalPlan.FREE
        return None

    def detect_seat_type(self, text: str) -> SeatType | None:
        """Infer Business seat type from visible text."""
        if SEAT_PATTERNS["codex"].search(text):
            return SeatType.CODEX
        if SEAT_PATTERNS["standard_chatgpt"].search(text):
            return SeatType.STANDARD_CHATGPT
        return None

    def detect_limit_unit(self, text: str) -> LimitUnit | None:
        """Infer whether the page describes messages, tokens, or credits."""
        if UNIT_PATTERNS["tokens"].search(text):
            return LimitUnit.TOKENS
        if UNIT_PATTERNS["messages"].search(text):
            return LimitUnit.MESSAGES
        if UNIT_PATTERNS["credits"].search(text):
            return LimitUnit.CREDITS
        return None

    def detect_auto_topup(self, text: str) -> bool | None:
        """Infer the current auto top-up state from page labels."""
        if matches_any(TOPUP_ON_PATTERNS, text):
            return True
        if matches_any(TOPUP_OFF_PATTERNS, text):
            return False
        return None

    def extract_credits_balance(self, text: str) -> Decimal | None:
        """Find a credits-balance number in the page text."""
        match = CREDITS_BALANCE_RE.search(text)
        return _to_decimal(match.group(1)) if match else None

    def extract_spend_limit(self, text: str) -> Decimal | None:
        """Find a spend-limit value in the page text."""
        match = SPEND_LIMIT_RE.search(text)
        return _to_decimal(match.group(1)) if match else None

    def extract_percent_remaining(self, text: str) -> Decimal | None:
        """Find a percentage-remaining signal in page text."""
        match = PERCENT_REMAINING_RE.search(text)
        return _to_decimal(match.group(1)) if match else None

    def extract_included_limit_line(self, text: str) -> str | None:
        """Return the most promising line describing included usage or remaining quota."""
        for line in text.splitlines():
            cleaned = line.strip()
            if not cleaned:
                continue
            if INCLUDED_LIMIT_LINE_RE.match(cleaned):
                return cleaned[:500]
        if matches_any(INCLUDED_LIMIT_HINT_PATTERNS, text):
            return text[:500]
        return None

    def extract_included_usage_details(self, text: str) -> IncludedUsageDetails:
        """Return numeric quota details plus the nearest reset/renewal line."""
        details = IncludedUsageDetails()

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            lowered = line.lower()
            has_remaining_keyword = any(keyword in lowered for keyword in self.REMAINING_KEYWORDS)
            has_used_keyword = any(keyword in lowered for keyword in self.USED_KEYWORDS)

            if details.refresh_text is None and USAGE_REFRESH_LINE_RE.search(line):
                details.refresh_text = line[:500]

            if has_remaining_keyword and (details.remaining is None or details.total is None):
                remaining_of_total = USAGE_REMAINING_OF_TOTAL_RE.search(line)
                if remaining_of_total:
                    details.remaining = details.remaining or _to_decimal(remaining_of_total.group("remaining"))
                    details.total = details.total or _to_decimal(remaining_of_total.group("total"))
                    continue

            if has_used_keyword and (details.used is None or details.total is None):
                used_of_total = USAGE_USED_OF_TOTAL_RE.search(line)
                if used_of_total:
                    details.used = details.used or _to_decimal(used_of_total.group("used"))
                    details.total = details.total or _to_decimal(used_of_total.group("total"))
                    continue

            if details.used is None or details.total is None:
                slash_total = USAGE_SLASH_TOTAL_RE.search(line)
                if slash_total:
                    details.used = details.used or _to_decimal(slash_total.group("used"))
                    details.total = details.total or _to_decimal(slash_total.group("total"))
                    continue

            if has_remaining_keyword and details.remaining is None:
                remaining_only = USAGE_REMAINING_RE.search(line)
                if remaining_only:
                    details.remaining = _to_decimal(remaining_only.group("remaining"))
                    continue

            if has_used_keyword and details.used is None:
                used_only = USAGE_USED_RE.search(line)
                if used_only:
                    details.used = _to_decimal(used_only.group("used"))
                    continue

            if details.total is None:
                total_only = USAGE_TOTAL_RE.search(line)
                if total_only:
                    details.total = _to_decimal(total_only.group("total"))

        if details.total is not None and details.used is not None and details.remaining is None and details.total >= details.used:
            details.remaining = details.total - details.used

        if (
            details.total is not None
            and details.remaining is not None
            and details.used is None
            and details.total >= details.remaining
        ):
            details.used = details.total - details.remaining

        return details

    def extract_codex_usage_periods(self, text: str) -> dict[str, CodexUsagePeriod]:
        """Extract separate daily and weekly Codex quota blocks from visible UI text."""
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        periods: dict[str, CodexUsagePeriod] = {}

        for period, marker in (("daily", CODEX_DAILY_RE), ("weekly", CODEX_WEEKLY_RE)):
            block = self._build_period_block(lines, marker)
            if not block:
                continue

            block_text = "\n".join(block)
            usage = self.extract_included_usage_details(block_text)
            percent_remaining = self.extract_percent_remaining(block_text)
            if percent_remaining is None:
                percent_match = ANY_PERCENT_RE.search(block_text)
                percent_remaining = _to_decimal(percent_match.group(1)) if percent_match else None

            has_usage_signal = any(
                value is not None
                for value in (
                    percent_remaining,
                    usage.total,
                    usage.used,
                    usage.remaining,
                    usage.refresh_text,
                )
            )
            if not has_usage_signal:
                continue

            confidence = "high" if CODEX_CONTEXT_RE.search(block_text) and usage.refresh_text else "medium"
            periods[period] = CodexUsagePeriod(
                period=period,
                percent_remaining=percent_remaining,
                total=usage.total,
                used=usage.used,
                remaining=usage.remaining,
                refresh_text=usage.refresh_text,
                source_text=block_text[:1000],
                confidence=confidence,
            )

        return periods

    def detect_team_invitation(self, text: str) -> TeamInvitationSignal | None:
        """Return a best-effort signal when visible UI text mentions a team invite."""
        match = TEAM_INVITATION_RE.search(text)
        if not match:
            return None

        source_text = " ".join(match.group(0).split())
        label = source_text[:120] if source_text else None
        return TeamInvitationSignal(
            status="pending",
            label=label,
            source_text=source_text[:500] if source_text else None,
            confidence="medium",
        )

    def _build_period_block(self, lines: list[str], marker: re.Pattern[str]) -> list[str]:
        """Collect nearby lines around every daily/weekly marker."""
        block: list[str] = []
        for index, line in enumerate(lines):
            if not marker.search(line):
                continue

            candidates: list[str] = []
            if index > 0 and CODEX_CONTEXT_RE.search(lines[index - 1]):
                candidates.append(lines[index - 1])

            for candidate in lines[index : min(len(lines), index + self.PERIOD_WINDOW_LINES + 2)]:
                if candidate != line and (CODEX_DAILY_RE.search(candidate) or CODEX_WEEKLY_RE.search(candidate)):
                    break
                candidates.append(candidate)

            for candidate in candidates:
                if candidate not in block:
                    block.append(candidate)

        return block
