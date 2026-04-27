"""Tests for quota parsing heuristics used by the ChatGPT UI probe."""

from decimal import Decimal

from backend.app.services.parser_service import ParserService


def test_extract_included_usage_details_from_used_of_total_line() -> None:
    """The parser should capture used, total, derived remaining, and refresh text."""
    text = """
    35 of 100 messages used
    Renews on Apr 30 at 00:00 UTC
    """

    details = ParserService().extract_included_usage_details(text)

    assert details.used == Decimal("35")
    assert details.total == Decimal("100")
    assert details.remaining == Decimal("65")
    assert details.refresh_text == "Renews on Apr 30 at 00:00 UTC"


def test_extract_included_usage_details_from_remaining_of_total_line() -> None:
    """The parser should capture remaining and derive used from total."""
    text = """
    18 of 50 tokens remaining
    Next reset in 6 hours
    """

    details = ParserService().extract_included_usage_details(text)

    assert details.remaining == Decimal("18")
    assert details.total == Decimal("50")
    assert details.used == Decimal("32")
    assert details.refresh_text == "Next reset in 6 hours"


def test_extract_included_usage_details_from_slash_format() -> None:
    """Slash-separated quota strings should also be recognized."""
    text = "12/40 credits"

    details = ParserService().extract_included_usage_details(text)

    assert details.used == Decimal("12")
    assert details.total == Decimal("40")
    assert details.remaining == Decimal("28")
    assert details.refresh_text is None


def test_extract_codex_usage_periods_from_daily_and_weekly_blocks() -> None:
    """Codex daily and weekly limits should be exposed as separate periods."""
    text = """
    Codex usage
    Daily limit
    20% remaining
    80 of 100 messages used
    Resets in 6 hours
    Weekly limit
    75% remaining
    50 of 200 messages used
    Renews on Apr 30 at 00:00 UTC
    """

    periods = ParserService().extract_codex_usage_periods(text)

    assert periods["daily"].percent_remaining == Decimal("20")
    assert periods["daily"].used == Decimal("80")
    assert periods["daily"].total == Decimal("100")
    assert periods["daily"].remaining == Decimal("20")
    assert periods["daily"].refresh_text == "Resets in 6 hours"
    assert periods["weekly"].percent_remaining == Decimal("75")
    assert periods["weekly"].used == Decimal("50")
    assert periods["weekly"].total == Decimal("200")
    assert periods["weekly"].remaining == Decimal("150")
    assert periods["weekly"].refresh_text == "Renews on Apr 30 at 00:00 UTC"


def test_detect_team_invitation_signal() -> None:
    """Visible team invite text should become an operator-facing signal."""
    text = "You have been invited to join team ACME Workspace. Accept invitation to continue."

    signal = ParserService().detect_team_invitation(text)

    assert signal is not None
    assert signal.status == "pending"
    assert "invited" in (signal.source_text or "")
