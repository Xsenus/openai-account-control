"""Unit tests for Playwright login heuristics and local-browser launch config."""

from __future__ import annotations

import asyncio
from pathlib import Path

from backend.app.config import settings
from backend.app.services.playwright_session_service import PlaywrightSessionService


class FakeLocator:
    """Small async locator stub for unit tests."""

    def __init__(self, text: str) -> None:
        self.text = text

    async def inner_text(self, timeout: int) -> str:  # noqa: ARG002 - mirrors Playwright signature.
        return self.text


class FakePage:
    """Minimal async page stub used to verify navigation behavior."""

    def __init__(self, text: str, url: str = "https://chatgpt.com") -> None:
        self.text = text
        self.url = url
        self.goto_calls = 0

    async def goto(self, url: str, wait_until: str = "domcontentloaded") -> None:  # noqa: ARG002
        self.goto_calls += 1
        self.url = url

    def locator(self, selector: str) -> FakeLocator:  # noqa: ARG002 - mirrors Playwright signature.
        return FakeLocator(self.text)


def test_public_chatgpt_shell_with_login_prompt_is_not_treated_as_authenticated() -> None:
    """The public landing page exposes app-like words, so auth-wall text must take priority."""
    body_text = """
    Новый чат
    История чата
    Настройки
    Войдите в систему, чтобы получать ответы на основе сохраненных чатов.
    Войти
    Зарегистрироваться бесплатно
    """

    service = PlaywrightSessionService()
    assert service.is_logged_in_text(body_text) is False


def test_authenticated_shell_markers_are_accepted_without_login_prompt() -> None:
    """Once the sign-in wall disappears, app-shell text should count as a live session."""
    body_text = """
    Новый чат
    Поиск в чатах
    Проекты
    Настройки
    """

    service = PlaywrightSessionService()
    assert service.is_logged_in_text(body_text) is True


def test_is_logged_in_without_navigation_does_not_reload_the_tab() -> None:
    """Interactive login polling must not restart Cloudflare or the login page."""
    page = FakePage("Идет проверка...")
    service = PlaywrightSessionService()

    result = asyncio.run(service.is_logged_in(page, navigate=False))

    assert result is False
    assert page.goto_calls == 0


def test_build_local_auth_profile_dir_is_account_scoped() -> None:
    """Each account should get its own persistent local browser profile directory."""
    service = PlaywrightSessionService()

    path = service.build_local_auth_profile_dir("account:with/odd*chars")

    assert path == settings.playwright_local_auth_profile_dir / "account_with_odd_chars"


def test_resolve_local_browser_executable_prefers_configured_path(monkeypatch, tmp_path) -> None:
    """An explicit executable path from config should win over auto-detection."""
    executable = tmp_path / "chrome.exe"
    executable.write_text("stub", encoding="utf-8")
    monkeypatch.setattr(settings, "playwright_local_browser_executable", str(executable))

    service = PlaywrightSessionService()
    assert service.resolve_local_browser_executable() == str(executable)

    monkeypatch.setattr(settings, "playwright_local_browser_executable", "")


def test_resolve_local_browser_executable_uses_windows_candidates(monkeypatch) -> None:
    """When no explicit path is configured, Windows browser candidates should be auto-detected."""
    target = PlaywrightSessionService.WINDOWS_BROWSER_CANDIDATES[1]
    original_exists = Path.exists

    def fake_exists(path: Path) -> bool:
        return path == target

    monkeypatch.setattr(settings, "playwright_local_browser_executable", "")
    monkeypatch.setattr(Path, "exists", fake_exists)

    service = PlaywrightSessionService()
    assert service.resolve_local_browser_executable() == str(target)

    monkeypatch.setattr(Path, "exists", original_exists)


def test_build_interactive_browser_command_avoids_problematic_playwright_flags(tmp_path) -> None:
    """The local browser should not be launched with --no-sandbox or --enable-automation."""
    service = PlaywrightSessionService()

    command = service.build_interactive_browser_command(
        executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        profile_dir=tmp_path / "profile",
        remote_debugging_port=9222,
        start_url="https://chatgpt.com",
        headless=False,
    )

    assert "--no-sandbox" not in command
    assert "--enable-automation" not in command
    assert "--remote-debugging-port=9222" in command
