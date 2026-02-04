"""Tests for Authority Service configuration."""

import os
import pytest
from unittest.mock import patch

# Import the config module, but we'll test Settings class directly
from authority.config import Settings, ConfigurationError


class TestSettingsValidation:
    """Tests for Settings validation."""

    def test_insecure_secret_key_rejected(self):
        """Test known insecure SECRET_KEYs are rejected."""
        insecure_values = [
            "change-me-in-production",
            "secret",
            "changeme",
            "password",
            "dev",
            "development",
            "test",
            "",
        ]

        for value in insecure_values:
            with patch.dict(os.environ, {
                "SECRET_KEY": value,
                "PASETO_KEY": "a" * 64,
                "DEBUG": "false",
                "ALLOW_INSECURE_DEFAULTS": "false",
            }, clear=True):
                with pytest.raises(ConfigurationError, match="SECRET_KEY"):
                    Settings(
                        _env_file=None,
                        SECRET_KEY=value,
                        PASETO_KEY="a" * 64,
                        DEBUG=False,
                        ALLOW_INSECURE_DEFAULTS=False,
                    )

    def test_valid_secret_key_accepted(self):
        """Test valid SECRET_KEY is accepted."""
        valid_key = "a" * 64  # 64 hex chars = 32 bytes

        settings = Settings(
            _env_file=None,
            SECRET_KEY=valid_key,
            PASETO_KEY="b" * 64,
            DEBUG=False,
            ALLOW_INSECURE_DEFAULTS=False,
        )

        assert settings.SECRET_KEY == valid_key

    def test_paseto_key_length_validation(self):
        """Test PASETO_KEY must be 64 hex chars."""
        with pytest.raises(ValueError, match="64 hex"):
            Settings(
                _env_file=None,
                SECRET_KEY="a" * 64,
                PASETO_KEY="tooshort",
                DEBUG=False,
                ALLOW_INSECURE_DEFAULTS=False,
            )

    def test_paseto_key_hex_validation(self):
        """Test PASETO_KEY must be valid hex."""
        with pytest.raises(ValueError, match="hexadecimal"):
            Settings(
                _env_file=None,
                SECRET_KEY="a" * 64,
                PASETO_KEY="g" * 64,  # 'g' is not hex
                DEBUG=False,
                ALLOW_INSECURE_DEFAULTS=False,
            )

    def test_valid_paseto_key_accepted(self):
        """Test valid PASETO_KEY is accepted."""
        valid_key = "abcdef0123456789" * 4  # 64 hex chars

        settings = Settings(
            _env_file=None,
            SECRET_KEY="a" * 64,
            PASETO_KEY=valid_key,
            DEBUG=False,
            ALLOW_INSECURE_DEFAULTS=False,
        )

        assert settings.PASETO_KEY == valid_key


class TestDebugModeDefaults:
    """Tests for DEBUG mode behavior."""

    def test_debug_mode_generates_keys(self):
        """Test DEBUG mode generates random keys if not set."""
        settings = Settings(
            _env_file=None,
            DEBUG=True,
            ALLOW_INSECURE_DEFAULTS=False,
        )

        assert settings.SECRET_KEY is not None
        assert len(settings.SECRET_KEY) == 64
        assert settings.PASETO_KEY is not None
        assert len(settings.PASETO_KEY) == 64

    def test_allow_insecure_generates_keys(self):
        """Test ALLOW_INSECURE_DEFAULTS generates random keys."""
        settings = Settings(
            _env_file=None,
            DEBUG=False,
            ALLOW_INSECURE_DEFAULTS=True,
        )

        assert settings.SECRET_KEY is not None
        assert settings.PASETO_KEY is not None


class TestProductionModeEnforcement:
    """Tests for production mode security enforcement."""

    def test_production_requires_secret_key(self):
        """Test production mode requires SECRET_KEY."""
        with pytest.raises(ConfigurationError, match="SECRET_KEY"):
            Settings(
                _env_file=None,
                PASETO_KEY="a" * 64,
                DEBUG=False,
                ALLOW_INSECURE_DEFAULTS=False,
            )

    def test_production_requires_paseto_key(self):
        """Test production mode requires PASETO_KEY."""
        with pytest.raises(ConfigurationError, match="PASETO_KEY"):
            Settings(
                _env_file=None,
                SECRET_KEY="a" * 64,
                DEBUG=False,
                ALLOW_INSECURE_DEFAULTS=False,
            )

    def test_production_requires_both_keys(self):
        """Test production mode requires both keys."""
        with pytest.raises(ConfigurationError) as exc_info:
            Settings(
                _env_file=None,
                DEBUG=False,
                ALLOW_INSECURE_DEFAULTS=False,
            )

        # Should mention both missing keys
        assert "SECRET_KEY" in str(exc_info.value)
        assert "PASETO_KEY" in str(exc_info.value)


class TestDatabaseUrl:
    """Tests for database URL construction."""

    def test_database_url_construction(self):
        """Test database URL is correctly constructed."""
        settings = Settings(
            _env_file=None,
            POSTGRES_HOST="localhost",
            POSTGRES_PORT=5432,
            POSTGRES_USER="testuser",
            POSTGRES_PASSWORD="testpass",
            POSTGRES_DB="testdb",
            DEBUG=True,
        )

        expected = "postgresql+psycopg2://testuser:testpass@localhost:5432/testdb"
        assert settings.database_url == expected

    def test_async_database_url_construction(self):
        """Test async database URL is correctly constructed."""
        settings = Settings(
            _env_file=None,
            POSTGRES_HOST="dbhost",
            POSTGRES_PORT=5433,
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_DB="db",
            DEBUG=True,
        )

        expected = "postgresql+asyncpg://user:pass@dbhost:5433/db"
        assert settings.async_database_url == expected


class TestCorsOrigins:
    """Tests for CORS origins configuration."""

    def test_empty_cors_origins(self):
        """Test empty CORS_ORIGINS returns empty list."""
        settings = Settings(
            _env_file=None,
            CORS_ORIGINS="",
            DEBUG=True,
        )

        assert settings.cors_origins_list == []

    def test_single_cors_origin(self):
        """Test single CORS origin."""
        settings = Settings(
            _env_file=None,
            CORS_ORIGINS="https://example.com",
            DEBUG=True,
        )

        assert settings.cors_origins_list == ["https://example.com"]

    def test_multiple_cors_origins(self):
        """Test multiple CORS origins."""
        settings = Settings(
            _env_file=None,
            CORS_ORIGINS="https://a.com,https://b.com,https://c.com",
            DEBUG=True,
        )

        assert settings.cors_origins_list == [
            "https://a.com",
            "https://b.com",
            "https://c.com",
        ]

    def test_cors_origins_strips_whitespace(self):
        """Test CORS origins strips whitespace."""
        settings = Settings(
            _env_file=None,
            CORS_ORIGINS=" https://a.com , https://b.com ",
            DEBUG=True,
        )

        assert settings.cors_origins_list == [
            "https://a.com",
            "https://b.com",
        ]


class TestPasetoKeyBytes:
    """Tests for PASETO key conversion."""

    def test_paseto_key_bytes_conversion(self):
        """Test PASETO key hex to bytes conversion."""
        hex_key = "00112233445566778899aabbccddeeff" * 2  # 64 hex chars

        settings = Settings(
            _env_file=None,
            SECRET_KEY="a" * 64,
            PASETO_KEY=hex_key,
            DEBUG=False,
            ALLOW_INSECURE_DEFAULTS=False,
        )

        key_bytes = settings.paseto_key_bytes
        assert len(key_bytes) == 32
        assert key_bytes == bytes.fromhex(hex_key)

    def test_paseto_key_bytes_not_configured(self):
        """Test paseto_key_bytes raises if not configured."""
        settings = Settings(
            _env_file=None,
            DEBUG=True,
            PASETO_KEY=None,  # Will be generated
        )

        # In debug mode a key is generated, so this should work
        assert len(settings.paseto_key_bytes) == 32


class TestPreviousPasetoKeys:
    """Tests for PASETO key rotation support."""

    def test_no_previous_keys(self):
        """Test empty previous keys."""
        settings = Settings(
            _env_file=None,
            PASETO_KEY_PREVIOUS="",
            DEBUG=True,
        )

        assert settings.paseto_previous_keys == []

    def test_single_previous_key(self):
        """Test single previous key."""
        old_key = "a" * 64

        settings = Settings(
            _env_file=None,
            PASETO_KEY_PREVIOUS=old_key,
            DEBUG=True,
        )

        assert len(settings.paseto_previous_keys) == 1
        assert settings.paseto_previous_keys[0] == bytes.fromhex(old_key)

    def test_multiple_previous_keys(self):
        """Test multiple previous keys."""
        key1 = "a" * 64
        key2 = "b" * 64

        settings = Settings(
            _env_file=None,
            PASETO_KEY_PREVIOUS=f"{key1},{key2}",
            DEBUG=True,
        )

        assert len(settings.paseto_previous_keys) == 2

    def test_invalid_previous_keys_skipped(self):
        """Test invalid previous keys are skipped."""
        valid_key = "a" * 64
        invalid_key = "tooshort"

        settings = Settings(
            _env_file=None,
            PASETO_KEY_PREVIOUS=f"{valid_key},{invalid_key}",
            DEBUG=True,
        )

        # Only the valid key should be included
        assert len(settings.paseto_previous_keys) == 1
