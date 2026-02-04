"""SigAid Authority Service configuration."""

import os
import secrets
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator


class ConfigurationError(Exception):
    """Raised when configuration is invalid or insecure."""
    pass


class Settings(BaseSettings):
    """Application settings loaded from environment.

    Security: SECRET_KEY and PASETO_KEY are REQUIRED in production.
    The server will refuse to start with insecure defaults.
    """

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "webscrapinguser"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "sigaid"

    # Security - NO DEFAULTS for critical secrets
    SECRET_KEY: Optional[str] = None
    PASETO_KEY: Optional[str] = None  # 32-byte hex for PASETO tokens

    # Key rotation: comma-separated list of old PASETO keys (hex) for graceful rotation
    PASETO_KEY_PREVIOUS: Optional[str] = None

    # CORS configuration
    CORS_ORIGINS: str = ""  # Comma-separated list of allowed origins
    CORS_ALLOW_CREDENTIALS: bool = True

    # Redis for distributed rate limiting (optional)
    REDIS_URL: Optional[str] = None  # e.g., redis://localhost:6379/0

    # API
    API_PREFIX: str = "/v1"
    DEBUG: bool = False

    # Allow insecure defaults only in explicit development mode
    ALLOW_INSECURE_DEFAULTS: bool = False

    @field_validator("SECRET_KEY", mode="before")
    @classmethod
    def validate_secret_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate SECRET_KEY is not a known insecure value."""
        insecure_values = {
            "change-me-in-production",
            "secret",
            "changeme",
            "password",
            "dev",
            "development",
            "test",
            "",
        }
        if v and v.lower() in insecure_values:
            return None  # Treat as not set
        return v

    @field_validator("PASETO_KEY", mode="before")
    @classmethod
    def validate_paseto_key(cls, v: Optional[str]) -> Optional[str]:
        """Validate PASETO_KEY format if provided."""
        if not v:
            return None
        # Must be 64 hex characters (32 bytes)
        v = v.strip()
        if len(v) != 64:
            raise ValueError("PASETO_KEY must be exactly 64 hex characters (32 bytes)")
        try:
            bytes.fromhex(v)
        except ValueError:
            raise ValueError("PASETO_KEY must be valid hexadecimal")
        return v

    @model_validator(mode="after")
    def validate_security_config(self) -> "Settings":
        """Ensure security configuration is valid for production."""
        if self.DEBUG or self.ALLOW_INSECURE_DEFAULTS:
            # In debug/dev mode, generate random keys if not provided
            if not self.SECRET_KEY:
                self.SECRET_KEY = secrets.token_hex(32)
            if not self.PASETO_KEY:
                self.PASETO_KEY = secrets.token_hex(32)
            return self

        # Production mode: require explicit configuration
        errors = []

        if not self.SECRET_KEY:
            errors.append(
                "SECRET_KEY is required. Set a secure random value "
                "(e.g., python -c \"import secrets; print(secrets.token_hex(32))\")"
            )

        if not self.PASETO_KEY:
            errors.append(
                "PASETO_KEY is required. Set a 32-byte hex value "
                "(e.g., python -c \"import secrets; print(secrets.token_hex(32))\")"
            )

        if errors:
            raise ConfigurationError(
                "Insecure configuration detected. Fix the following:\n"
                + "\n".join(f"  - {e}" for e in errors)
                + "\n\nTo allow insecure defaults (DEVELOPMENT ONLY), set ALLOW_INSECURE_DEFAULTS=true"
            )

        return self

    @property
    def database_url(self) -> str:
        """Construct database URL."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def async_database_url(self) -> str:
        """Construct async database URL."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS_ORIGINS into a list."""
        if not self.CORS_ORIGINS:
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def paseto_key_bytes(self) -> bytes:
        """Get PASETO key as bytes."""
        if not self.PASETO_KEY:
            raise ConfigurationError("PASETO_KEY not configured")
        return bytes.fromhex(self.PASETO_KEY)

    @property
    def paseto_previous_keys(self) -> list[bytes]:
        """Get previous PASETO keys for rotation support."""
        if not self.PASETO_KEY_PREVIOUS:
            return []
        keys = []
        for key_hex in self.PASETO_KEY_PREVIOUS.split(","):
            key_hex = key_hex.strip()
            if key_hex and len(key_hex) == 64:
                try:
                    keys.append(bytes.fromhex(key_hex))
                except ValueError:
                    pass  # Skip invalid keys
        return keys

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Load settings with explicit path to .env
_env_file = os.path.join(os.path.dirname(__file__), ".env")
settings = Settings(_env_file=_env_file)
