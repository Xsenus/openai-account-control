"""Interactive helper to capture a ChatGPT Playwright session state.

Typical usage:
    python backend/scripts/capture_session.py \
        --account-id <UUID> \
        --backend-url http://localhost:8000

The script opens a local browser profile for the selected account, waits until
ChatGPT is really logged in, then uploads the resulting storage_state to the
backend API.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.services.playwright_session_service import PlaywrightSessionService


async def main() -> None:
    """Parse arguments, capture storage_state, and upload or save it."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-url", required=False, default="http://localhost:8000")
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--output", required=False, default="")
    parser.add_argument("--chatgpt-url", required=False, default="https://chatgpt.com")
    parser.add_argument("--panel-username", required=False, default="")
    parser.add_argument("--panel-password", required=False, default="")
    args = parser.parse_args()

    print("Открывается локальный браузер для выбранной учетки.")
    print("1) Выполните вход в нужную учетную запись OpenAI.")
    print("2) Если появится Cloudflare, дождитесь завершения проверки в этом же окне.")
    print("3) Окно закроется после того, как панель увидит успешный вход.")

    service = PlaywrightSessionService()
    state = await service.capture_storage_state_interactively(
        account_id=args.account_id,
        timeout_seconds=900,
        headless=False,
        start_url=args.chatgpt_url,
    )

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"storage_state сохранен в файл: {out_path}")

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
            json={"storage_state": state},
        )
        response.raise_for_status()
        print("storage_state успешно отправлен на backend.")


if __name__ == "__main__":
    asyncio.run(main())
