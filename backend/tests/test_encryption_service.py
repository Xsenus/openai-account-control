"""Unit tests for storage-state encryption."""

from backend.app.services.encryption_service import EncryptionService


def test_encrypt_roundtrip() -> None:
    """Encrypted JSON should decrypt back to the exact same payload."""
    service = EncryptionService(key="4zrqM1E2z4_bfdxEusZT6X0hgqP-d9qbM9Q1E3L8qjk=")
    payload = {"cookies": [{"name": "session", "value": "abc"}], "origins": []}
    token = service.encrypt_json(payload)
    decoded = service.decrypt_json(token)
    assert decoded == payload
