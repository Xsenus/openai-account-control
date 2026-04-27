"""CRUD operations for managed OpenAI accounts."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Account
from ..schemas import AccountCreate, AccountUpdate
from .encryption_service import EncryptionService
from .storage_state_service import StorageStateService


class AccountService:
    """Encapsulate account CRUD and session-state management."""

    def __init__(
        self,
        session: AsyncSession,
        encryption: EncryptionService | None = None,
        storage_state_service: StorageStateService | None = None,
    ) -> None:
        """Remember DB session and encryption helper."""
        self.session = session
        self.encryption = encryption or EncryptionService()
        self.storage_state_service = storage_state_service or StorageStateService()

    async def list_accounts(self) -> list[Account]:
        """Return all accounts ordered by user-facing label."""
        query = select(Account).order_by(Account.label.asc())
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_account(self, account_id: str) -> Account | None:
        """Load one account by primary key."""
        return await self.session.get(Account, account_id)

    async def create_account(self, payload: AccountCreate) -> Account:
        """Create a new managed account record."""
        account = Account(**payload.model_dump())
        self.session.add(account)
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def update_account(self, account: Account, payload: AccountUpdate) -> Account:
        """Apply a partial update to an account."""
        for field_name, value in payload.model_dump(exclude_none=True).items():
            setattr(account, field_name, value)
        await self.session.commit()
        await self.session.refresh(account)
        return account

    async def delete_account(self, account: Account) -> None:
        """Delete an account and all dependent snapshots/runs."""
        await self.session.delete(account)
        await self.session.commit()

    async def import_storage_state(self, account: Account, storage_state: dict) -> Account:
        """Encrypt and store Playwright storage_state JSON for the account."""
        normalized_state = self.storage_state_service.normalize(storage_state)
        account.encrypted_storage_state = self.encryption.encrypt_json(normalized_state)
        account.last_auth_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(account)
        return account

    def get_storage_state(self, account: Account) -> dict | None:
        """Decrypt account storage_state JSON, returning None when absent."""
        if not account.encrypted_storage_state:
            return None
        decrypted = self.encryption.decrypt_json(account.encrypted_storage_state)
        return self.storage_state_service.normalize(decrypted)

    async def set_last_scan_at(self, account: Account) -> None:
        """Update last-scan timestamp after a successful probe."""
        account.last_scan_at = datetime.now(timezone.utc)
        await self.session.commit()
