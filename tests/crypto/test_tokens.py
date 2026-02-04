"""Tests for PASETO token management."""

import secrets
from datetime import timedelta
import time

import pytest

from sigaid.crypto.tokens import LeaseTokenManager
from sigaid.exceptions import TokenExpired, TokenInvalid


class TestLeaseTokenManager:
    """Tests for LeaseTokenManager class."""

    @pytest.fixture
    def manager(self):
        """Create token manager with random key."""
        return LeaseTokenManager(secrets.token_bytes(32))

    def test_create_token(self, manager):
        """Test creating a token."""
        token = manager.create_token(
            agent_id="aid_test",
            session_id="session_123",
        )
        assert token is not None
        assert isinstance(token, str)
        assert token.startswith("v4.local.")

    def test_verify_token(self, manager):
        """Test verifying a valid token."""
        token = manager.create_token(
            agent_id="aid_test",
            session_id="session_123",
            sequence=42,
        )

        payload = manager.verify_token(token)

        assert payload["agent_id"] == "aid_test"
        assert payload["session_id"] == "session_123"
        assert payload["seq"] == 42
        assert "iat" in payload
        assert "exp" in payload
        assert "jti" in payload

    def test_expired_token(self, manager):
        """Test that expired token raises TokenExpired."""
        token = manager.create_token(
            agent_id="aid_test",
            session_id="session_123",
            ttl=timedelta(milliseconds=1),  # Expires almost immediately
        )

        time.sleep(0.01)  # Wait for expiration

        with pytest.raises(TokenExpired):
            manager.verify_token(token)

    def test_invalid_token(self, manager):
        """Test that invalid token raises TokenInvalid."""
        with pytest.raises(TokenInvalid):
            manager.verify_token("v4.local.invalid_token")

    def test_wrong_key_fails(self):
        """Test that wrong key fails verification."""
        manager1 = LeaseTokenManager(secrets.token_bytes(32))
        manager2 = LeaseTokenManager(secrets.token_bytes(32))

        token = manager1.create_token(
            agent_id="aid_test",
            session_id="session_123",
        )

        with pytest.raises(TokenInvalid):
            manager2.verify_token(token)

    def test_refresh_token(self, manager):
        """Test refreshing a token."""
        original = manager.create_token(
            agent_id="aid_test",
            session_id="session_123",
            sequence=0,
        )

        refreshed = manager.refresh_token(original)

        # Verify refreshed token
        payload = manager.verify_token(refreshed)
        assert payload["agent_id"] == "aid_test"
        assert payload["seq"] == 1  # Sequence incremented

    def test_extra_claims(self, manager):
        """Test adding extra claims to token."""
        token = manager.create_token(
            agent_id="aid_test",
            session_id="session_123",
            extra_claims={"custom_field": "custom_value"},
        )

        payload = manager.verify_token(token)
        assert payload["custom_field"] == "custom_value"

    def test_invalid_key_length(self):
        """Test that invalid key length raises error."""
        with pytest.raises(ValueError):
            LeaseTokenManager(b"too_short")
