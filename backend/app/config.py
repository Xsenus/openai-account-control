"""Application configuration loaded from environment variables.

The project is intentionally self-hosted. The app stores Playwright session
state encrypted in the local database and evidence files on disk. No OpenAI
passwords are stored by this project.
"""

from pathlib import Path

from cryptography.fernet import Fernet
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Typed settings model for FastAPI, scheduler, and collectors."""

    app_name: str = Field(default="OpenAI Account Control Center", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    frontend_public_url: str = Field(default="http://localhost:8000", alias="FRONTEND_PUBLIC_URL")
    auth_enabled: bool = Field(default=False, alias="AUTH_ENABLED")
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="CHANGE_ME_ADMIN_PASSWORD", alias="ADMIN_PASSWORD")
    session_cookie_name: str = Field(default="control_center_session", alias="SESSION_COOKIE_NAME")
    session_ttl_hours: int = Field(default=24, alias="SESSION_TTL_HOURS")
    session_cookie_secure: bool = Field(default=False, alias="SESSION_COOKIE_SECURE")

    database_url: str = Field(default="sqlite+aiosqlite:///./data/app.db", alias="DATABASE_URL")
    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")
    evidence_dir: Path = Field(default=Path("./data/evidence"), alias="EVIDENCE_DIR")

    encryption_key: str = Field(alias="ENCRYPTION_KEY")

    scheduler_enabled: bool = Field(default=True, alias="SCHEDULER_ENABLED")
    scan_interval_minutes: int = Field(default=30, alias="SCAN_INTERVAL_MINUTES")
    low_credits_threshold: float = Field(default=15.0, alias="LOW_CREDITS_THRESHOLD")
    low_usage_percent_threshold: float = Field(default=20.0, alias="LOW_USAGE_PERCENT_THRESHOLD")

    playwright_headless: bool = Field(default=True, alias="PLAYWRIGHT_HEADLESS")
    playwright_allow_local_profile_fallback: bool = Field(default=False, alias="PLAYWRIGHT_ALLOW_LOCAL_PROFILE_FALLBACK")
    playwright_timeout_ms: int = Field(default=45000, alias="PLAYWRIGHT_TIMEOUT_MS")
    playwright_locale: str = Field(default="ru-RU", alias="PLAYWRIGHT_LOCALE")
    playwright_timezone_id: str | None = Field(default=None, alias="PLAYWRIGHT_TIMEZONE_ID")
    playwright_local_auth_profile_dir: Path = Field(
        default=Path("./data/playwright-local-auth"),
        alias="PLAYWRIGHT_LOCAL_AUTH_PROFILE_DIR",
    )
    playwright_local_browser_executable: str = Field(default="", alias="PLAYWRIGHT_LOCAL_BROWSER_EXECUTABLE")
    playwright_local_browser_channel: str = Field(default="", alias="PLAYWRIGHT_LOCAL_BROWSER_CHANNEL")
    chatgpt_base_url: str = Field(default="https://chatgpt.com", alias="CHATGPT_BASE_URL")

    @field_validator("encryption_key")
    @classmethod
    def validate_encryption_key(cls, value: str) -> str:
        """Fail fast when the encryption key is missing or malformed."""
        normalized = value.strip()
        if not normalized or normalized == "CHANGE_ME":
            raise ValueError(
                "ENCRYPTION_KEY is not configured. Copy .env.example to .env and generate a Fernet key first."
            )
        try:
            Fernet(normalized.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - pydantic should surface the reason cleanly.
            raise ValueError(
                "ENCRYPTION_KEY must be a valid Fernet key. Generate one with "
                "`python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"`."
            ) from exc
        return normalized

    @field_validator("admin_username")
    @classmethod
    def validate_admin_username(cls, value: str) -> str:
        """Normalize the panel admin username."""
        return value.strip()

    @field_validator("session_cookie_name")
    @classmethod
    def validate_session_cookie_name(cls, value: str) -> str:
        """Reject blank cookie names because browsers ignore them."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("SESSION_COOKIE_NAME must not be empty.")
        return normalized

    @model_validator(mode="after")
    def validate_auth_settings(self) -> "Settings":
        """Ensure panel auth has usable credentials when enabled."""
        if not self.auth_enabled:
            return self

        if not self.admin_username:
            raise ValueError("ADMIN_USERNAME must be configured when AUTH_ENABLED=true.")

        password = self.admin_password.strip()
        if not password or password == "CHANGE_ME_ADMIN_PASSWORD":
            raise ValueError("ADMIN_PASSWORD must be configured when AUTH_ENABLED=true.")

        if self.session_ttl_hours < 1:
            raise ValueError("SESSION_TTL_HOURS must be at least 1.")

        return self

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
        extra="ignore",
    )


settings = Settings()
