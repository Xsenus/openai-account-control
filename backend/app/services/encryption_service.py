"""Encryption helper for Playwright storage_state payloads.

Passwords are never stored. We keep only the authenticated browser state and
encrypt it before writing it to the database.
"""

from __future__ import annotations

import json

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings


class EncryptionService:
    """Encrypt and decrypt JSON payloads with Fernet symmetric encryption."""

    def __init__(self, key: str | None = None) -> None:
        """Create the service with the configured key or an explicit override."""
        active_key = key or settings.encryption_key
        self._fernet = Fernet(active_key.encode("utf-8"))

    def encrypt_json(self, payload: dict) -> str:
        """Serialize JSON and encrypt it for safe storage in the database."""
        plain = json.dumps(payload).encode("utf-8")
        return self._fernet.encrypt(plain).decode("utf-8")

    def decrypt_json(self, token: str) -> dict:
        """Decrypt and deserialize JSON.

        A dedicated error message makes operational troubleshooting easier.
        """
        try:
            plain = self._fernet.decrypt(token.encode("utf-8"))
        except InvalidToken as exc:
            raise ValueError("Не удалось расшифровать session-state. Проверьте ENCRYPTION_KEY.") from exc
        return json.loads(plain.decode("utf-8"))
