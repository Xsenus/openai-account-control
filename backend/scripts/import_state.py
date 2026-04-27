"""Upload an existing Playwright storage_state JSON file to the backend."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import httpx


async def main() -> None:
    """Load a JSON file and send it to the backend."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-url", required=False, default="http://localhost:8000")
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--panel-username", required=False, default="")
    parser.add_argument("--panel-password", required=False, default="")
    args = parser.parse_args()

    payload = json.loads(Path(args.file).read_text(encoding="utf-8"))

    async with httpx.AsyncClient(timeout=60) as client:
        if args.panel_username and args.panel_password:
            login_response = await client.post(
                f"{args.backend_url.rstrip('/')}/api/auth/login",
                json={
                    "username": args.panel_username,
                    "password": args.panel_password,
                },
            )
            login_response.raise_for_status()

        response = await client.post(
            f"{args.backend_url.rstrip('/')}/api/accounts/{args.account_id}/auth/import",
            json={"storage_state": payload},
        )
        response.raise_for_status()
        print("storage_state успешно импортирован.")


if __name__ == "__main__":
    asyncio.run(main())
