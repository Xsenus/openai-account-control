"""Heuristic UI probe for ChatGPT account/workspace state.

Important design note:
This service intentionally does not rely on undocumented internal JSON APIs.
Instead it:
- opens an authenticated ChatGPT session,
- navigates by visible text such as Settings/Billing/Usage,
- parses the visible page text,
- stores screenshots and raw text to simplify future selector maintenance.

Because ChatGPT UI changes, this probe is best-effort and built to degrade
gracefully: if one section cannot be opened, the scan still saves partial data.
"""

from __future__ import annotations

import asyncio
import json
import re
from contextlib import suppress
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator, Page

from ..config import settings
from ..enums import LimitUnit, WorkspaceKind, WorkspaceState
from ..selectors.phrases import (
    ADMIN_PATTERNS,
    BILLING_PATTERNS,
    LOCKED_PATTERNS,
    MEMBER_PATTERNS,
    OWNER_PATTERNS,
    PROFILE_BUTTON_PATTERNS,
    SETTINGS_PATTERNS,
    USAGE_PATTERNS,
    WORKSPACE_PATTERNS,
    ci_pattern,
    matches_any,
)
from .evidence_service import EvidenceService
from .exceptions import AuthExpiredError, ProbeError
from .parser_service import ParserService
from .playwright_session_service import PlaywrightSessionService
from .types import ProbeAccountResult, ProbeWorkspaceResult


class OpenAIProbeService:
    """Collect workspace data from one authenticated ChatGPT account session."""

    def __init__(
        self,
        session_service: PlaywrightSessionService | None = None,
        parser: ParserService | None = None,
        evidence_service: EvidenceService | None = None,
    ) -> None:
        """Create the probe with explicit dependencies or defaults."""
        self.session_service = session_service or PlaywrightSessionService()
        self.parser = parser or ParserService()
        self.evidence_service = evidence_service or EvidenceService()

    async def scan_account(self, *, storage_state: dict, account_id: str, account_label: str, run_id: str) -> ProbeAccountResult:
        """Open the account, discover workspaces, and read status data."""
        try:
            async with self.session_service.open_with_storage_state(storage_state=storage_state) as session:
                await self.session_service.assert_logged_in(session.page)
                return await self.scan_authenticated_page(
                    page=session.page,
                    account_id=account_id,
                    account_label=account_label,
                    run_id=run_id,
                    source="storage_state",
                )
        except AuthExpiredError as first_error:
            if not settings.playwright_allow_local_profile_fallback:
                raise first_error

            profile_dir = self.session_service.build_local_auth_profile_dir(account_id)
            if not profile_dir.exists():
                raise first_error

            async with self.session_service.open_with_local_profile(
                account_id=account_id,
                headless=settings.playwright_headless,
            ) as session:
                await self.session_service.assert_logged_in(session.page)
                return await self.scan_authenticated_page(
                    page=session.page,
                    account_id=account_id,
                    account_label=account_label,
                    run_id=run_id,
                    source="local_profile",
                )

    async def scan_authenticated_page(
        self,
        *,
        page: Page,
        account_id: str,
        account_label: str,
        run_id: str,
        source: str,
    ) -> ProbeAccountResult:
        """Discover workspaces and collect details from an already authenticated page."""
        await page.goto(settings.chatgpt_base_url, wait_until="domcontentloaded")
        # Codex often triggers Cloudflare if we first open account/workspace menus.
        # Read the primary account view first; workspace discovery can be added back
        # after Codex quota capture is stable for real accounts.
        result = await self.collect_workspace_details(
            page=page,
            account_id=account_id,
            run_id=run_id,
            workspace_name=account_label,
            predeclared_state=WorkspaceState.UNKNOWN,
        )
        result.raw_payload["scan_session_source"] = source

        return ProbeAccountResult(
            workspaces=[result],
            account_level_payload={
                "discovered_workspaces": [
                    {
                        "name": account_label,
                        "state": WorkspaceState.UNKNOWN,
                        "kind": None,
                    }
                ]
            },
        )

    async def discover_workspaces(self, page: Page) -> list[dict[str, Any]]:
        """Read the profile menu and infer visible workspaces.

        The logic uses DOM order and text heuristics, because workspace names are
        arbitrary and therefore cannot be predicted in advance.
        """
        if not await self.open_profile_menu(page):
            return []

        items = await self.collect_visible_clickables(page)
        header_index = None
        for idx, item in enumerate(items):
            if matches_any(WORKSPACE_PATTERNS, item["text"]):
                header_index = idx
                break

        if header_index is None:
            # Fallback: return nothing and let caller create a synthetic workspace.
            await self.try_close_overlays(page)
            return []

        results: list[dict[str, Any]] = []
        stop_regex = ci_pattern(
            "Settings",
            "Billing",
            "Help",
            "Keyboard shortcuts",
            "Log out",
            "Logout",
            "Sign out",
            "Profile",
        )

        for item in items[header_index + 1 :]:
            text = item["text"].strip()
            if not text:
                continue
            if stop_regex.search(text):
                break
            if len(text) < 2 or len(text) > 120:
                continue

            # Some menus may duplicate the currently active workspace; dedupe by text.
            if any(existing["name"] == text for existing in results):
                continue

            state = WorkspaceState.DEACTIVATED if matches_any(LOCKED_PATTERNS, text) or item["disabled"] else WorkspaceState.ACTIVE
            results.append({"name": text, "state": state, "kind": None})

        await self.try_close_overlays(page)
        return results

    async def switch_workspace(self, page: Page, workspace_name: str) -> None:
        """Switch to another workspace through the profile menu."""
        opened = await self.open_profile_menu(page)
        if not opened:
            raise ProbeError(f"Не удалось открыть меню профиля для переключения на workspace '{workspace_name}'.")

        if not await self.try_click_visible_text(page, workspace_name):
            await self.try_close_overlays(page)
            raise ProbeError(f"Не удалось выбрать workspace '{workspace_name}' в меню профиля.")

        await page.wait_for_timeout(1500)

    async def collect_workspace_details(
        self,
        *,
        page: Page,
        account_id: str,
        run_id: str,
        workspace_name: str,
        predeclared_state: WorkspaceState,
    ) -> ProbeWorkspaceResult:
        """Collect visible state, billing signals, and evidence for one workspace."""
        checked_at = datetime.now(timezone.utc)
        evidence_dir = self.evidence_service.build_workspace_dir(account_id, run_id, workspace_name)

        if predeclared_state == WorkspaceState.DEACTIVATED:
            await self.save_basic_evidence(page, evidence_dir, workspace_name)
            return ProbeWorkspaceResult(
                workspace_name=workspace_name,
                workspace_kind=WorkspaceKind.BUSINESS,
                workspace_state=WorkspaceState.DEACTIVATED,
                source="workspace_picker",
                raw_payload={"reason": "Workspace shown as locked/deactivated in profile picker."},
                evidence_dir=str(evidence_dir),
                checked_at=checked_at,
            )

        codex_usage_api = await self.fetch_codex_usage_api(page)
        codex_text = await self.read_page_text(page)
        await page.goto(settings.chatgpt_base_url, wait_until="domcontentloaded")
        home_text = await self.read_page_text(page)
        settings_text, billing_text, usage_text = await self.read_settings_areas(page)

        combined_text = "\n\n".join([part for part in [home_text, codex_text, settings_text, billing_text, usage_text] if part])
        lower = combined_text.lower()

        workspace_kind = self.detect_workspace_kind(combined_text)
        workspace_state = predeclared_state

        if any(marker in lower for marker in ["owner only", "contact your admin", "insufficient permissions", "permission"]):
            workspace_state = WorkspaceState.PARTIAL_VISIBILITY
        if any(
            marker in lower
            for marker in [
                "failed to load subscription",
                "не удалось загрузить подписку",
                "something went wrong",
            ]
        ):
            workspace_state = WorkspaceState.PARTIAL_VISIBILITY

        role = self.detect_role(combined_text)
        seat_type = self.parser.detect_seat_type(combined_text)
        personal_plan = self.parser.detect_plan(combined_text)
        limit_unit = self.parser.detect_limit_unit(combined_text)

        included_limit_text = self.parser.extract_included_limit_line(combined_text)
        included_percent = self.parser.extract_percent_remaining(combined_text)
        included_usage_details = self.parser.extract_included_usage_details(combined_text)
        codex_usage = self.extract_codex_usage_from_api(codex_usage_api)
        if not codex_usage:
            codex_usage = self.parser.extract_codex_usage_periods(combined_text)
        team_invitation = self.parser.detect_team_invitation(combined_text)
        credits_balance = self.parser.extract_credits_balance(combined_text)
        auto_topup_enabled = self.parser.detect_auto_topup(combined_text)
        spend_limit = self.parser.extract_spend_limit(combined_text)

        codex_usage_payload = {
            period: self.serialize_codex_period(details)
            for period, details in codex_usage.items()
        }
        payload = {
            "home_text_excerpt": home_text[:4000],
            "codex_text_excerpt": codex_text[:4000],
            "settings_text_excerpt": settings_text[:4000],
            "billing_text_excerpt": billing_text[:4000],
            "usage_text_excerpt": usage_text[:4000],
            "usage_summary": {
                "used": str(included_usage_details.used) if included_usage_details.used is not None else None,
                "total": str(included_usage_details.total) if included_usage_details.total is not None else None,
                "remaining": str(included_usage_details.remaining) if included_usage_details.remaining is not None else None,
                "refresh_text": included_usage_details.refresh_text,
            },
            "codex_usage": codex_usage_payload,
            "codex_usage_api": codex_usage_api,
            "team_invitation": asdict(team_invitation) if team_invitation else None,
        }
        self.evidence_service.write_json(evidence_dir, "text-excerpts.json", payload)
        self.evidence_service.write_text(evidence_dir, "combined.txt", combined_text[:20000])

        await self.capture_screenshot(page, evidence_dir / "workspace.png")

        return ProbeWorkspaceResult(
            workspace_name=workspace_name,
            workspace_kind=workspace_kind,
            workspace_state=workspace_state,
            role=role,
            seat_type=seat_type.value if seat_type else None,
            personal_plan=personal_plan.value if personal_plan else None,
            codex_limit_unit=limit_unit or LimitUnit.UNKNOWN,
            included_limit_text=included_limit_text,
            included_usage_percent_remaining=included_percent,
            included_usage_total=included_usage_details.total,
            included_usage_used=included_usage_details.used,
            included_usage_remaining=included_usage_details.remaining,
            included_usage_refresh_text=included_usage_details.refresh_text,
            codex_usage=codex_usage,
            team_invitation=team_invitation,
            credits_balance=credits_balance,
            auto_topup_enabled=auto_topup_enabled,
            spend_limit=spend_limit,
            source="ui_probe",
            raw_payload=payload,
            evidence_dir=str(evidence_dir),
            checked_at=checked_at,
        )

    async def read_codex_area(self, page: Page) -> str:
        """Open the Codex cloud page and return visible quota/status text."""
        try:
            await page.goto("https://chatgpt.com/codex/cloud", wait_until="domcontentloaded")
        except Exception:
            # The app may keep streaming or fail a subrequest; inspect whatever rendered.
            pass

        await page.wait_for_timeout(8000)
        return await self.read_page_text(page)

    async def fetch_codex_usage_api(self, page: Page) -> dict[str, Any] | None:
        """Read Codex usage from the internal JSON endpoint used by the Codex UI."""
        captured: dict[str, Any] | None = None
        captured_event = asyncio.Event()

        async def capture_response(response: Any) -> None:
            nonlocal captured
            if "/backend-api/wham/usage" not in response.url:
                return
            try:
                text = await response.text()
                if not response.ok:
                    captured = {"ok": False, "status": response.status, "body": text[:1000]}
                else:
                    captured = {"ok": True, "status": response.status, "body": json.loads(text)}
            except Exception as exc:
                captured = {"ok": False, "error": str(exc)}
            finally:
                captured_event.set()

        def on_response(response: Any) -> None:
            asyncio.create_task(capture_response(response))

        page.on("response", on_response)
        try:
            await page.goto("https://chatgpt.com/codex/cloud", wait_until="domcontentloaded")
            try:
                await asyncio.wait_for(captured_event.wait(), timeout=20000)
            except TimeoutError:
                return {"ok": False, "error": "Timed out waiting for /backend-api/wham/usage."}
            return captured
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        finally:
            with suppress(Exception):
                page.remove_listener("response", on_response)

    async def read_settings_areas(self, page: Page) -> tuple[str, str, str]:
        """Attempt to open Settings, Billing, and Usage areas and return collected text.

        Each step is optional. Failures are swallowed because the UI can differ by
        account type, workspace role, or future layout changes.
        """
        settings_text = ""
        billing_text = ""
        usage_text = ""

        if not await self.open_profile_menu(page):
            return settings_text, billing_text, usage_text

        if await self.try_click_patterns(page, SETTINGS_PATTERNS):
            await page.wait_for_timeout(1200)
            settings_text = await self.read_page_text(page)

            # Billing is usually present for Business owners or when personal credits exist.
            if await self.try_click_patterns(page, BILLING_PATTERNS):
                await page.wait_for_timeout(1200)
                billing_text = await self.read_page_text(page)

            # Usage page can exist as a tab or a subsection.
            if await self.try_click_patterns(page, USAGE_PATTERNS):
                await page.wait_for_timeout(1200)
                usage_text = await self.read_page_text(page)

        await self.try_close_overlays(page)
        return settings_text, billing_text, usage_text

    async def open_profile_menu(self, page: Page) -> bool:
        """Open the account/workspace menu using semantic fallbacks."""
        for pattern in PROFILE_BUTTON_PATTERNS:
            try:
                locator = page.get_by_role("button", name=pattern).first
                if await locator.count():
                    await locator.click(timeout=3000)
                    await page.wait_for_timeout(500)
                    return True
            except Exception:
                continue

        fallback_selectors = [
            "[aria-haspopup='menu']",
            "button[aria-expanded]",
            "button:has(svg)",
        ]
        for selector in fallback_selectors:
            try:
                locator = page.locator(selector).first
                if await locator.count():
                    await locator.click(timeout=3000)
                    await page.wait_for_timeout(500)
                    return True
            except Exception:
                continue

        return False

    async def try_click_patterns(self, page: Page, patterns: list[re.Pattern[str]]) -> bool:
        """Try clicking the first visible element whose text matches one of the patterns."""
        for pattern in patterns:
            if await self.try_click_regex(page, pattern):
                return True
        return False

    async def try_click_visible_text(self, page: Page, text: str) -> bool:
        """Click visible text by exact-ish matching across common interactive roles."""
        escaped = re.escape(text)
        return await self.try_click_regex(page, re.compile(escaped, re.IGNORECASE))

    async def try_click_regex(self, page: Page, pattern: re.Pattern[str]) -> bool:
        """Click the first visible UI element that matches the given regex pattern."""
        role_candidates = [
            ("button", page.get_by_role("button", name=pattern)),
            ("link", page.get_by_role("link", name=pattern)),
            ("menuitem", page.get_by_role("menuitem", name=pattern)),
            ("generic_text", page.get_by_text(pattern)),
        ]

        for _role_name, locator in role_candidates:
            try:
                candidate = locator.first
                if await candidate.count():
                    await candidate.click(timeout=3000)
                    return True
            except Exception:
                continue

        return False

    async def read_page_text(self, page: Page) -> str:
        """Read page body text, returning an empty string on transient UI failures."""
        try:
            text = await page.locator("body").inner_text(timeout=5000)
        except Exception:
            try:
                text = await page.evaluate("() => document.body ? (document.body.innerText || document.body.textContent || '') : ''")
            except Exception:
                return ""
        return self.compact_text(text)

    async def collect_visible_clickables(self, page: Page) -> list[dict[str, Any]]:
        """Collect visible text-bearing elements to support workspace discovery."""
        script = """
        () => {
          const isVisible = (el) => {
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style && style.visibility !== 'hidden' &&
                   style.display !== 'none' &&
                   rect.width > 0 && rect.height > 0;
          };

          const selectors = [
            'button',
            '[role="button"]',
            '[role="menuitem"]',
            'a',
            'div',
            'span'
          ];

          const seen = new Set();
          const items = [];

          document.querySelectorAll(selectors.join(',')).forEach((el) => {
            if (!isVisible(el)) return;
            const text = (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim();
            if (!text) return;
            const key = `${el.tagName}|${text}`;
            if (seen.has(key)) return;
            seen.add(key);
            items.push({
              tag: el.tagName.toLowerCase(),
              text,
              role: el.getAttribute('role') || '',
              disabled: el.getAttribute('aria-disabled') === 'true' || el.hasAttribute('disabled')
            });
          });

          return items;
        }
        """
        try:
            return await page.evaluate(script)
        except Exception:
            return []

    def detect_workspace_kind(self, text: str) -> WorkspaceKind:
        """Infer whether the current workspace is personal or business-like."""
        lowered = text.lower()
        business_markers = [
            "business",
            "workspace",
            "members",
            "seat",
            "owner",
            "admin",
            "credits",
        ]
        if any(marker in lowered for marker in business_markers):
            return WorkspaceKind.BUSINESS
        return WorkspaceKind.PERSONAL

    def detect_role(self, text: str) -> str | None:
        """Infer the user's role within a business workspace."""
        if matches_any(OWNER_PATTERNS, text):
            return "owner"
        if matches_any(ADMIN_PATTERNS, text):
            return "admin"
        if matches_any(MEMBER_PATTERNS, text):
            return "member"
        return None

    def serialize_codex_period(self, details: Any) -> dict[str, Any]:
        """Convert a CodexUsagePeriod dataclass into JSON-safe payload."""
        payload = asdict(details)
        for field_name in ("percent_remaining", "total", "used", "remaining"):
            value = payload.get(field_name)
            if isinstance(value, Decimal):
                payload[field_name] = str(value)
        return payload

    def extract_codex_usage_from_api(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        """Normalize the Codex WHAM usage endpoint into period cards."""
        if not payload or payload.get("ok") is not True:
            return {}

        body = payload.get("body")
        if not isinstance(body, dict):
            return {}

        rate_limit = body.get("rate_limit")
        if not isinstance(rate_limit, dict):
            return {}

        periods: dict[str, Any] = {}
        for api_key, period_name in (("primary_window", "primary"), ("secondary_window", "weekly")):
            window = rate_limit.get(api_key)
            if not isinstance(window, dict):
                continue

            used_percent = self.decimal_from_number(window.get("used_percent"))
            remaining_percent = Decimal("100") - used_percent if used_percent is not None else None
            reset_after_seconds = window.get("reset_after_seconds")
            limit_window_seconds = window.get("limit_window_seconds")
            reset_at = window.get("reset_at")
            reset_at_iso = self.timestamp_to_iso(reset_at)

            periods[period_name] = self.parser_period(
                period=period_name,
                percent_remaining=remaining_percent,
                refresh_text=self.format_reset_text(reset_after_seconds, reset_at_iso),
                reset_at=reset_at_iso,
                source_text=f"{api_key}: {window}",
                confidence="high",
            )

            # Keep the old daily slot populated for existing UI wording when the
            # short Codex window is what the account actually has.
            if period_name == "primary":
                periods["daily"] = periods[period_name]

        return periods

    def parser_period(
        self,
        *,
        period: str,
        percent_remaining: Decimal | None,
        refresh_text: str | None,
        reset_at: str | None,
        source_text: str,
        confidence: str,
    ) -> Any:
        """Create a CodexUsagePeriod without importing the dataclass into call sites."""
        from .types import CodexUsagePeriod

        return CodexUsagePeriod(
            period=period,
            percent_remaining=percent_remaining,
            refresh_text=refresh_text,
            reset_at=reset_at,
            source_text=source_text[:1000],
            confidence=confidence,
        )

    def decimal_from_number(self, value: Any) -> Decimal | None:
        """Convert JSON numeric values to Decimal."""
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except Exception:
            return None

    def timestamp_to_iso(self, value: Any) -> str | None:
        """Convert a Unix timestamp in seconds into an ISO UTC string."""
        try:
            timestamp = int(value)
        except (TypeError, ValueError):
            return None
        return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()

    def format_reset_text(self, reset_after_seconds: Any, reset_at_iso: str | None) -> str | None:
        """Format a human-readable reset hint from WHAM usage fields."""
        try:
            seconds = int(reset_after_seconds)
        except (TypeError, ValueError):
            seconds = 0

        parts: list[str] = []
        if seconds > 0:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            parts.append(f"resets in {hours}h {minutes}m")

        if reset_at_iso is not None:
            parts.append(f"reset_at={reset_at_iso}")

        return " | ".join(parts) if parts else None

    async def try_close_overlays(self, page: Page) -> None:
        """Attempt to close menus/modals without failing the whole scan."""
        try:
            await page.keyboard.press("Escape")
            await page.wait_for_timeout(300)
        except Exception:
            return

    async def save_basic_evidence(self, page: Page, evidence_dir: Path, workspace_name: str) -> None:
        """Save a basic screenshot and body text when deeper probing is not possible."""
        text = await self.read_page_text(page)
        self.evidence_service.write_text(evidence_dir, "body.txt", text[:20000])
        self.evidence_service.write_json(evidence_dir, "meta.json", {"workspace_name": workspace_name})
        await self.capture_screenshot(page, evidence_dir / "workspace.png")

    async def capture_screenshot(self, page: Page, path: Path) -> None:
        """Capture a full-page screenshot if the page is renderable."""
        try:
            await page.screenshot(path=str(path), full_page=True)
        except PlaywrightError:
            # A screenshot failure should not abort the scan.
            return

    def compact_text(self, text: str) -> str:
        """Normalize whitespace without losing line structure entirely."""
        lines = []
        for line in text.splitlines():
            cleaned = re.sub(r"\s+", " ", line).strip()
            if cleaned:
                lines.append(cleaned)
        return "\n".join(lines)
