"""Tests for snapshot schema fields derived from raw_payload."""

from datetime import datetime, timezone
from decimal import Decimal

from backend.app.models import WorkspaceSnapshot
from backend.app.schemas import WorkspaceSnapshotRead


def test_workspace_snapshot_schema_exposes_usage_summary_fields() -> None:
    """API schema should expose structured quota details stored inside raw_payload."""
    snapshot = WorkspaceSnapshot(
        id="snapshot-1",
        account_id="account-1",
        workspace_name="Personal",
        workspace_kind="personal",
        workspace_state="active",
        overall_status="ok",
        role=None,
        seat_type=None,
        personal_plan="plus",
        codex_limit_unit="messages",
        included_limit_text="65% remaining",
        included_usage_percent_remaining=Decimal("65"),
        credits_balance=Decimal("42.50"),
        auto_topup_enabled=True,
        spend_limit=Decimal("100.00"),
        source="ui_probe",
        checked_at=datetime.now(timezone.utc),
        evidence_dir=None,
        raw_payload={
            "usage_summary": {
                "used": "35",
                "total": "100",
                "remaining": "65",
                "refresh_text": "Resets on Apr 30 at 00:00 UTC",
            },
            "codex_usage": {
                "daily": {
                    "period": "daily",
                    "percent_remaining": "65",
                    "total": "100",
                    "used": "35",
                    "remaining": "65",
                    "refresh_text": "Resets on Apr 30 at 00:00 UTC",
                    "reset_at": None,
                    "source_text": "Daily limit 65% remaining",
                    "confidence": "high",
                }
            },
            "team_invitation": {
                "status": "pending",
                "label": "Invited to ACME",
                "source_text": "You have been invited to join ACME.",
                "confidence": "medium",
            },
        },
    )

    payload = WorkspaceSnapshotRead.model_validate(snapshot)

    assert payload.included_usage_used == Decimal("35")
    assert payload.included_usage_total == Decimal("100")
    assert payload.included_usage_remaining == Decimal("65")
    assert payload.included_usage_refresh_text == "Resets on Apr 30 at 00:00 UTC"
    assert payload.codex_usage["daily"].percent_remaining == Decimal("65")
    assert payload.team_invitation is not None
    assert payload.team_invitation.status == "pending"
