"""Utilities for opening Playwright sessions with saved authentication state."""

from __future__ import annotations

import asyncio
import json
import socket
import subprocess
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.error import URLError
from urllib.request import urlopen

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from ..config import settings
from .exceptions import AuthExpiredError


@dataclass(slots=True)
class BrowserSession:
    """Bundle of Playwright objects returned by the session manager."""

    browser: Browser
    context: BrowserContext
    page: Page


@dataclass(slots=True)
class InteractiveBrowserProcess:
    """Metadata for a locally launched browser that exposes a CDP endpoint."""

    process: subprocess.Popen[Any]
    debugging_port: int
    profile_dir: Path


class PlaywrightSessionService:
    """Factory for authenticated and interactive Playwright browser sessions."""

    WINDOWS_BROWSER_CANDIDATES = (
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    )

    CHATGPT_HOST_MARKERS = (
        "chatgpt.com",
        "chat.openai.com",
        "auth.openai.com",
    )

    AUTH_WALL_MARKERS = (
        "cloudflare",
        "verify you are human",
        "checking your browser",
        "cf-turnstile",
        "just a moment",
        "проверка браузера",
        "подтвердите, что вы человек",
        "log in",
        "login",
        "sign up",
        "continue with google",
        "continue with microsoft",
        "continue with apple",
        "войти",
        "войдите в систему",
        "зарегистрироваться",
        "зарегистрироваться бесплатно",
        "продолжить с google",
        "продолжить с microsoft",
        "продолжить с apple",
    )

    AUTHENTICATED_APP_MARKERS = (
        "new chat",
        "search chats",
        "projects",
        "library",
        "deep research",
        "settings",
        "billing",
        "workspace",
        "история чата",
        "новый чат",
        "поиск в чатах",
        "проекты",
        "библиотека",
        "настройки",
        "рабочее пространство",
    )

    @asynccontextmanager
    async def open_with_storage_state(self, storage_state: dict, headless: bool | None = None) -> AsyncIterator[BrowserSession]:
        """Open a Chromium context using previously saved storage_state JSON."""
        chosen_headless = settings.playwright_headless if headless is None else headless

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=chosen_headless)
            context = await browser.new_context(storage_state=storage_state)
            page = await context.new_page()
            page.set_default_timeout(settings.playwright_timeout_ms)

            try:
                yield BrowserSession(browser=browser, context=context, page=page)
            finally:
                await context.close()
                await browser.close()

    @asynccontextmanager
    async def open_with_local_profile(
        self,
        *,
        account_id: str,
        headless: bool = False,
        start_url: str | None = None,
    ) -> AsyncIterator[BrowserSession]:
        """Open the trusted local Chrome/Edge profile used during interactive auth."""
        async with async_playwright() as pw:
            async with self.open_interactive_browser_session(
                pw,
                account_id=account_id,
                headless=headless,
                start_url=start_url or settings.chatgpt_base_url,
            ) as session:
                yield session

    async def capture_storage_state_interactively(
        self,
        *,
        account_id: str,
        timeout_seconds: int = 600,
        headless: bool = False,
        start_url: str | None = None,
    ) -> dict:
        """Open ChatGPT in a browser and wait for a successful login."""
        async with async_playwright() as pw:
            async with self.open_interactive_browser_session(
                pw,
                account_id=account_id,
                headless=headless,
                start_url=start_url or settings.chatgpt_base_url,
            ) as session:
                await self.wait_until_logged_in(session.page, timeout_seconds=timeout_seconds)
                storage_state = await session.context.storage_state()
                if not self.has_chatgpt_auth_cookie(storage_state):
                    raise RuntimeError(
                        "ChatGPT открылся, но session cookie не найдена. "
                        "Дождитесь полного входа в ChatGPT и появления основного интерфейса чата."
                    )
                return storage_state

    @asynccontextmanager
    async def open_interactive_browser_session(
        self,
        pw: Playwright,
        *,
        account_id: str,
        headless: bool,
        start_url: str,
    ) -> AsyncIterator[BrowserSession]:
        """Launch a regular local browser and attach Playwright over CDP."""
        browser_process = self.launch_interactive_browser_process(
            account_id=account_id,
            start_url=start_url,
            headless=headless,
        )
        browser: Browser | None = None

        try:
            endpoint_url = await self.wait_for_cdp_endpoint(browser_process, timeout_seconds=30)
            browser = await pw.chromium.connect_over_cdp(endpoint_url)
            context = await self.wait_for_connected_context(browser)
            page = await self.select_interactive_page(context, start_url=start_url)
            page.set_default_timeout(settings.playwright_timeout_ms)
            yield BrowserSession(browser=browser, context=context, page=page)
        finally:
            if browser is not None:
                with suppress(Exception):
                    await browser.close()
            self.stop_interactive_browser_process(browser_process)

    def build_local_auth_profile_dir(self, account_id: str) -> Path:
        """Store manual-login browser state per account to retain browser trust signals."""
        safe_account_id = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in account_id)
        return settings.playwright_local_auth_profile_dir / safe_account_id

    def resolve_local_browser_executable(self) -> str | None:
        """Choose a system browser for interactive auth, preferring the configured executable."""
        explicit_path = settings.playwright_local_browser_executable.strip()
        if explicit_path:
            candidate = Path(explicit_path)
            if candidate.exists():
                return str(candidate)
            raise RuntimeError(
                f"Configured PLAYWRIGHT_LOCAL_BROWSER_EXECUTABLE was not found: {candidate}"
            )

        for candidate in self.WINDOWS_BROWSER_CANDIDATES:
            if candidate.exists():
                return str(candidate)

        return None

    def build_interactive_browser_command(
        self,
        *,
        executable_path: str,
        profile_dir: Path,
        remote_debugging_port: int,
        start_url: str,
        headless: bool,
    ) -> list[str]:
        """Build a normal browser command line without Playwright's launch-time automation flags."""
        command = [
            executable_path,
            f"--remote-debugging-port={remote_debugging_port}",
            f"--user-data-dir={profile_dir.resolve()}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-default-apps",
            "--start-maximized",
            f"--lang={settings.playwright_locale}",
            "--new-window",
        ]

        if headless:
            command.append("--headless=new")

        command.append(start_url)
        return command

    def launch_interactive_browser_process(
        self,
        *,
        account_id: str,
        start_url: str,
        headless: bool,
    ) -> InteractiveBrowserProcess:
        """Launch a local system browser that exposes a CDP debugging endpoint."""
        executable_path = self.resolve_local_browser_executable()
        if not executable_path:
            raise RuntimeError(
                "Не найден локальный Chrome/Edge для интерактивного входа. "
                "Установите браузер или задайте PLAYWRIGHT_LOCAL_BROWSER_EXECUTABLE."
            )

        profile_dir = self.build_local_auth_profile_dir(account_id)
        profile_dir.mkdir(parents=True, exist_ok=True)

        debugging_port = self.find_available_local_port()
        command = self.build_interactive_browser_command(
            executable_path=executable_path,
            profile_dir=profile_dir,
            remote_debugging_port=debugging_port,
            start_url=start_url,
            headless=headless,
        )

        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        return InteractiveBrowserProcess(
            process=process,
            debugging_port=debugging_port,
            profile_dir=profile_dir,
        )

    def find_available_local_port(self) -> int:
        """Reserve an ephemeral local TCP port for Chrome DevTools."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            sock.listen(1)
            return int(sock.getsockname()[1])

    async def wait_for_cdp_endpoint(self, browser_process: InteractiveBrowserProcess, timeout_seconds: int) -> str:
        """Wait until the launched browser exposes its DevTools endpoint."""
        deadline = asyncio.get_event_loop().time() + timeout_seconds
        endpoint_url = f"http://127.0.0.1:{browser_process.debugging_port}"

        while asyncio.get_event_loop().time() < deadline:
            if browser_process.process.poll() is not None:
                raise RuntimeError("Локальный браузер закрылся до завершения инициализации.")

            if await asyncio.to_thread(self.is_cdp_endpoint_ready, endpoint_url):
                return endpoint_url

            await asyncio.sleep(0.5)

        raise TimeoutError("Не удалось подключиться к локальному браузеру по CDP.")

    def is_cdp_endpoint_ready(self, endpoint_url: str) -> bool:
        """Check whether the browser already answers on the CDP version endpoint."""
        try:
            with urlopen(f"{endpoint_url}/json/version", timeout=2) as response:  # noqa: S310 - local-only URL
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, TimeoutError, URLError, json.JSONDecodeError):
            return False

        return bool(payload.get("Browser"))

    async def wait_for_connected_context(self, browser: Browser, timeout_seconds: int = 15) -> BrowserContext:
        """Wait until the attached browser exposes at least one context."""
        deadline = asyncio.get_event_loop().time() + timeout_seconds

        while asyncio.get_event_loop().time() < deadline:
            if browser.contexts:
                return browser.contexts[0]
            await asyncio.sleep(0.2)

        raise RuntimeError("Локальный браузер не создал доступный контекст для Playwright.")

    async def select_interactive_page(self, context: BrowserContext, *, start_url: str) -> Page:
        """Reuse an existing ChatGPT tab or create a new one inside the attached browser."""
        deadline = asyncio.get_event_loop().time() + 10

        while asyncio.get_event_loop().time() < deadline:
            for page in context.pages:
                if self.is_chatgpt_related_url(page.url):
                    return page

            if context.pages:
                candidate = context.pages[-1]
                if not self.is_chatgpt_related_url(candidate.url):
                    await candidate.goto(start_url, wait_until="domcontentloaded")
                return candidate

            await asyncio.sleep(0.2)

        page = await context.new_page()
        await page.goto(start_url, wait_until="domcontentloaded")
        return page

    def is_chatgpt_related_url(self, url: str) -> bool:
        """Detect ChatGPT/OpenAI login pages without reloading the tab repeatedly."""
        lowered = (url or "").lower()
        return any(marker in lowered for marker in self.CHATGPT_HOST_MARKERS)

    def stop_interactive_browser_process(self, browser_process: InteractiveBrowserProcess) -> None:
        """Terminate the locally launched browser if it is still alive."""
        process = browser_process.process
        if process.poll() is not None:
            return

        with suppress(Exception):
            process.terminate()
            process.wait(timeout=5)

        if process.poll() is None:
            with suppress(Exception):
                process.kill()
                process.wait(timeout=5)

    async def wait_until_logged_in(self, page: Page, timeout_seconds: int = 600) -> None:
        """Poll the current tab until login appears complete or timeout is reached."""
        deadline = asyncio.get_event_loop().time() + timeout_seconds

        while asyncio.get_event_loop().time() < deadline:
            if page.is_closed():
                raise RuntimeError("Окно браузера было закрыто до завершения входа.")

            if await self.is_logged_in(page, navigate=False):
                return
            await asyncio.sleep(2)

        raise TimeoutError("Не удалось дождаться успешного входа в ChatGPT в отведенное время.")

    async def assert_logged_in(self, page: Page) -> None:
        """Raise an explicit domain error when the session is invalid."""
        if await self.is_logged_in(page, navigate=True):
            return

        reason = await self.auth_block_reason(page)
        raise AuthExpiredError(reason)

    async def is_logged_in(self, page: Page, *, navigate: bool) -> bool:
        """Best-effort heuristic that the current page belongs to an authenticated ChatGPT session."""
        if navigate:
            try:
                await page.goto(settings.chatgpt_base_url, wait_until="domcontentloaded")
            except Exception:
                # Even if the navigation had a transient issue, we still inspect whatever
                # page content is currently available.
                pass

        try:
            body_text = await page.locator("body").inner_text(timeout=5000)
        except Exception:
            return False

        return self.is_logged_in_text(body_text)

    def is_logged_in_text(self, body_text: str) -> bool:
        """Evaluate visible page text without needing a live Playwright page in tests."""
        lowered = body_text.lower()

        if any(marker in lowered for marker in self.AUTH_WALL_MARKERS):
            return False

        return any(marker in lowered for marker in self.AUTHENTICATED_APP_MARKERS)

    async def auth_block_reason(self, page: Page) -> str:
        """Return a user-facing reason for failed automated auth checks."""
        try:
            body_text = await page.locator("body").inner_text(timeout=5000)
        except Exception:
            body_text = ""

        lowered = body_text.lower()
        cloudflare_markers = (
            "cloudflare",
            "verify you are human",
            "checking your browser",
            "cf-turnstile",
            "just a moment",
            "проверка браузера",
            "подтвердите, что вы человек",
        )
        if any(marker in lowered for marker in cloudflare_markers):
            return (
                "ChatGPT показал Cloudflare/human-check. Фоновый VPS scan не открывает интерактивный браузер "
                "и не может пройти такую проверку автоматически; обновите session-state вручную через отдельный login flow."
            )

        return "Сохраненная сессия устарела или требует повторного входа."

    def has_chatgpt_auth_cookie(self, storage_state: dict) -> bool:
        """Return whether storage_state contains a likely ChatGPT/OpenAI auth cookie."""
        cookies = storage_state.get("cookies")
        if not isinstance(cookies, list):
            return False

        auth_name_markers = ("session", "auth", "access", "token")
        for cookie in cookies:
            if not isinstance(cookie, dict):
                continue
            domain = str(cookie.get("domain") or "").lower()
            name = str(cookie.get("name") or "").lower()
            if ("chatgpt.com" in domain or "openai.com" in domain) and any(marker in name for marker in auth_name_markers):
                return True

        return False
