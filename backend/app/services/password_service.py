"""Password hashing helpers for operator accounts."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os


class PasswordService:
    """Hash and verify passwords using PBKDF2-HMAC-SHA256."""

    algorithm = "pbkdf2_sha256"
    iterations = 390000
    salt_bytes = 16

    def _urlsafe_b64encode(self, value: bytes) -> str:
        """Encode bytes without padding so hashes stay compact."""
        return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")

    def _urlsafe_b64decode(self, value: str) -> bytes:
        """Decode urlsafe base64 strings that may omit padding."""
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))

    def hash_password(self, password: str) -> str:
        """Return a versioned PBKDF2 hash string for storage."""
        salt = os.urandom(self.salt_bytes)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            self.iterations,
        )
        return "$".join(
            (
                self.algorithm,
                str(self.iterations),
                self._urlsafe_b64encode(salt),
                self._urlsafe_b64encode(digest),
            )
        )

    def verify_password(self, password: str, encoded_hash: str) -> bool:
        """Compare a clear-text password against a stored PBKDF2 hash."""
        try:
            algorithm, iterations_raw, salt_raw, digest_raw = encoded_hash.split("$", maxsplit=3)
        except ValueError:
            return False

        if algorithm != self.algorithm:
            return False

        try:
            iterations = int(iterations_raw)
            salt = self._urlsafe_b64decode(salt_raw)
            expected_digest = self._urlsafe_b64decode(digest_raw)
        except Exception:  # noqa: BLE001 - verification should fail closed.
            return False

        candidate_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(candidate_digest, expected_digest)
