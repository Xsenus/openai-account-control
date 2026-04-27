"""Regex patterns for extracting numeric values from page text."""

from __future__ import annotations

import re

NUMBER_RE = r"[0-9]+(?:[.,][0-9]{1,2})?"
QUOTA_UNIT_RE = r"(?:messages?|tokens?|credits?|сообщени(?:е|й|я)|токен(?:ы|ов|а)?|кредит(?:ы|ов|а)?)"

CREDITS_BALANCE_RE = re.compile(
    r"(?:credits balance|remaining credits|available credits)\s*[:\-]?\s*\$?\s*([0-9]+(?:[.,][0-9]{1,2})?)",
    re.IGNORECASE,
)

SPEND_LIMIT_RE = re.compile(
    r"(?:spend limit|workspace limit|budget)\s*[:\-]?\s*\$?\s*([0-9]+(?:[.,][0-9]{1,2})?)",
    re.IGNORECASE,
)

PERCENT_REMAINING_RE = re.compile(
    r"([0-9]{1,3}(?:[.,][0-9]{1,2})?)\s*%\s*(?:remaining|left|остал|доступно)",
    re.IGNORECASE,
)

ANY_PERCENT_RE = re.compile(
    r"([0-9]{1,3}(?:[.,][0-9]{1,2})?)\s*%",
    re.IGNORECASE,
)

INCLUDED_LIMIT_LINE_RE = re.compile(
    r".{0,40}(included|remaining|limit|usage|messages|tokens|credits|"
    r"лимит|использован|сообщени|токен|кредит|подписк).{0,160}",
    re.IGNORECASE,
)

USAGE_REMAINING_OF_TOTAL_RE = re.compile(
    rf"(?P<remaining>{NUMBER_RE})\s*(?P<unit>{QUOTA_UNIT_RE})?\s*"
    rf"(?:remaining|left|available|осталось|доступно)?\s*(?:out of|of|из|/)\s*"
    rf"(?P<total>{NUMBER_RE})\s*(?P<unit_tail>{QUOTA_UNIT_RE})?"
    rf"(?:\s*(?:remaining|left|available|осталось|доступно))?",
    re.IGNORECASE,
)

USAGE_USED_OF_TOTAL_RE = re.compile(
    rf"(?P<used>{NUMBER_RE})\s*(?P<unit>{QUOTA_UNIT_RE})?\s*"
    rf"(?:used|spent|consumed|использовано|потрачено)?\s*(?:out of|of|из|/)\s*"
    rf"(?P<total>{NUMBER_RE})\s*(?P<unit_tail>{QUOTA_UNIT_RE})?"
    rf"(?:\s*(?:used|spent|consumed|использовано|потрачено))?",
    re.IGNORECASE,
)

USAGE_SLASH_TOTAL_RE = re.compile(
    rf"(?P<used>{NUMBER_RE})\s*/\s*(?P<total>{NUMBER_RE})\s*(?P<unit>{QUOTA_UNIT_RE})",
    re.IGNORECASE,
)

USAGE_REMAINING_RE = re.compile(
    rf"(?P<remaining>{NUMBER_RE})\s*(?P<unit>{QUOTA_UNIT_RE})\s*"
    rf"(?:remaining|left|available|осталось|доступно)",
    re.IGNORECASE,
)

USAGE_USED_RE = re.compile(
    rf"(?P<used>{NUMBER_RE})\s*(?P<unit>{QUOTA_UNIT_RE})\s*"
    rf"(?:used|spent|consumed|использовано|потрачено)",
    re.IGNORECASE,
)

USAGE_TOTAL_RE = re.compile(
    rf"(?:limit|included|allowance|quota|total|лимит|всего|доступно всего)\s*[:\-]?\s*"
    rf"(?P<total>{NUMBER_RE})\s*(?P<unit>{QUOTA_UNIT_RE})",
    re.IGNORECASE,
)

USAGE_REFRESH_LINE_RE = re.compile(
    r".{0,40}(?:resets?|reset at|next reset|renews?|renewal|refresh(?:es)?|updates? on|"
    r"обнов(?:ится|ление|ляется)|сброс|следующ(?:ее|ий)\s+обновление|продлен[иео]|продлится).{0,140}",
    re.IGNORECASE,
)

CODEX_DAILY_RE = re.compile(
    r"(?:daily|per\s+day|24\s*hours?|today|дневн|сут(?:ки|ок)|за\s+день|24\s*час)",
    re.IGNORECASE,
)

CODEX_WEEKLY_RE = re.compile(
    r"(?:weekly|per\s+week|7\s*days?|this\s+week|недельн|за\s+недел|7\s*дн)",
    re.IGNORECASE,
)

CODEX_CONTEXT_RE = re.compile(
    r"(?:codex|code\s+agent|coding\s+agent|кодекс|usage|limit|лимит|использован)",
    re.IGNORECASE,
)

TEAM_INVITATION_RE = re.compile(
    r".{0,60}(?:invited?|invitation|join\s+(?:team|workspace)|pending\s+invite|"
    r"приглашен(?:ие|ы)?|пригласили|присоединиться\s+к\s+(?:команде|workspace|рабоч)).{0,160}",
    re.IGNORECASE,
)
