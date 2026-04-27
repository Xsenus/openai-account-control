"""Validation helpers for Playwright storage_state payloads."""

from __future__ import annotations

from typing import Any


class StorageStateService:
    """Normalize and validate imported Playwright session-state payloads."""

    SESSION_EXPORT_KEYS = {
        "accessToken",
        "sessionToken",
        "user",
        "account",
        "authProvider",
        "expires",
    }

    def normalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Return a safe Playwright storage_state dict or raise a clear error."""
        if not isinstance(payload, dict):
            raise ValueError("storage_state must be a JSON object.")

        if self._looks_like_openai_session_export(payload):
            raise ValueError(
                "Этот JSON похож на экспорт токенов OpenAI, а не на Playwright storage_state. "
                "Нужен файл с верхними полями 'cookies' и 'origins'. "
                "Создать его можно через backend/scripts/capture_session.py или scripts/capture-storage-state.ps1."
            )

        cookies = payload.get("cookies")
        if not isinstance(cookies, list):
            raise ValueError(
                "Импорт поддерживает только Playwright storage_state: верхнее поле 'cookies' должно быть массивом."
            )

        origins = payload.get("origins", [])
        if origins is None:
            origins = []
        if not isinstance(origins, list):
            raise ValueError(
                "Импорт поддерживает только Playwright storage_state: верхнее поле 'origins' должно быть массивом."
            )

        self._validate_cookie_items(cookies)
        self._validate_origin_items(origins)

        return {"cookies": cookies, "origins": origins}

    def _looks_like_openai_session_export(self, payload: dict[str, Any]) -> bool:
        """Detect common token/session dumps that users often confuse with storage_state."""
        return bool(self.SESSION_EXPORT_KEYS.intersection(payload.keys())) and "cookies" not in payload

    def _validate_cookie_items(self, cookies: list[Any]) -> None:
        """Validate cookie entries without over-constraining Playwright-compatible payloads."""
        for index, item in enumerate(cookies):
            if not isinstance(item, dict):
                raise ValueError(f"Cookie entry #{index + 1} must be an object.")

            missing_keys = [key for key in ("name", "value") if not item.get(key)]
            if missing_keys:
                missing = ", ".join(missing_keys)
                raise ValueError(f"Cookie entry #{index + 1} is missing required fields: {missing}.")

    def _validate_origin_items(self, origins: list[Any]) -> None:
        """Validate localStorage origin blocks."""
        for index, item in enumerate(origins):
            if not isinstance(item, dict):
                raise ValueError(f"Origin entry #{index + 1} must be an object.")

            origin = item.get("origin")
            local_storage = item.get("localStorage", [])
            if not isinstance(origin, str) or not origin.strip():
                raise ValueError(f"Origin entry #{index + 1} must contain a non-empty 'origin' string.")
            if not isinstance(local_storage, list):
                raise ValueError(f"Origin entry #{index + 1} must contain a 'localStorage' array.")

            for storage_index, storage_item in enumerate(local_storage):
                if not isinstance(storage_item, dict):
                    raise ValueError(
                        f"Origin entry #{index + 1}, localStorage item #{storage_index + 1} must be an object."
                    )
                missing_keys = [key for key in ("name", "value") if key not in storage_item]
                if missing_keys:
                    missing = ", ".join(missing_keys)
                    raise ValueError(
                        f"Origin entry #{index + 1}, localStorage item #{storage_index + 1} is missing: {missing}."
                    )
