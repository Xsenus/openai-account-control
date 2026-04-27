"""Create demo accounts and synthetic snapshots for local UI exploration.

This script is optional. It does not touch real OpenAI accounts; it only writes
sample data into the database so you can inspect the dashboard immediately.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import delete, select

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db import AsyncSessionFactory, init_db
from backend.app.models import Account, WorkspaceSnapshot

DEMO_ACCOUNTS = [
    {
        "label": "Личная учетка",
        "email_hint": "me@example.com",
        "notes": "Демо-профиль",
        "snapshot": {
            "workspace_name": "Personal",
            "workspace_kind": "personal",
            "workspace_state": "active",
            "overall_status": "ok",
            "personal_plan": "plus",
            "codex_limit_unit": "credits",
            "included_limit_text": "Included usage available",
            "included_usage_percent_remaining": Decimal("65"),
            "credits_balance": Decimal("42.50"),
            "auto_topup_enabled": True,
            "spend_limit": Decimal("100.00"),
            "raw_payload": {
                "demo": True,
                "usage_summary": {
                    "used": "35",
                    "total": "100",
                    "remaining": "65",
                    "refresh_text": "Resets on Apr 30 at 00:00 UTC",
                },
            },
        },
    },
    {
        "label": "Рабочая учетка",
        "email_hint": "work@example.com",
        "notes": "Демо-профиль",
        "snapshot": {
            "workspace_name": "Acme Business",
            "workspace_kind": "business",
            "workspace_state": "deactivated",
            "overall_status": "deactivated",
            "role": "member",
            "seat_type": "standard_chatgpt",
            "codex_limit_unit": "credits",
            "credits_balance": Decimal("0"),
            "auto_topup_enabled": False,
            "raw_payload": {
                "demo": True,
                "usage_summary": {
                    "used": "100",
                    "total": "100",
                    "remaining": "0",
                    "refresh_text": "Renews tomorrow",
                },
            },
        },
    },
]


async def main() -> None:
    """Seed the database with synthetic data.

    The script is idempotent: rerunning it refreshes demo snapshots instead of
    creating duplicate accounts.
    """
    await init_db()
    now = datetime.now(timezone.utc)

    async with AsyncSessionFactory() as session:
        labels = [item["label"] for item in DEMO_ACCOUNTS]
        result = await session.execute(select(Account).where(Account.label.in_(labels)))
        accounts_by_label = {account.label: account for account in result.scalars().all()}

        demo_accounts: list[Account] = []
        for item in DEMO_ACCOUNTS:
            account = accounts_by_label.get(item["label"])
            if account is None:
                account = Account(
                    label=item["label"],
                    email_hint=item["email_hint"],
                    notes=item["notes"],
                )
                session.add(account)
                await session.flush()
            else:
                account.email_hint = item["email_hint"]
                account.notes = item["notes"]
                account.is_enabled = True

            account.last_scan_at = now
            demo_accounts.append(account)

        await session.execute(
            delete(WorkspaceSnapshot).where(WorkspaceSnapshot.account_id.in_([account.id for account in demo_accounts]))
        )

        for account, item in zip(demo_accounts, DEMO_ACCOUNTS, strict=True):
            snapshot_payload = dict(item["snapshot"])
            raw_payload = snapshot_payload.pop("raw_payload", {"demo": True})
            session.add(
                WorkspaceSnapshot(
                    account_id=account.id,
                    source="demo",
                    checked_at=now,
                    raw_payload=raw_payload,
                    **snapshot_payload,
                )
            )

        await session.commit()

    print("Demo data loaded or refreshed.")


if __name__ == "__main__":
    asyncio.run(main())
