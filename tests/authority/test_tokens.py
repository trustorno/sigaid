"""Tests for authority token service with revocation and key rotation."""

import secrets
import time
from datetime import datetime, timezone

import pytest
from unittest.mock import MagicMock, patch

from authority.services.tokens import (
    TokenService,
    TokenExpiredError,
    TokenInvalidError,
    TokenRevokedError,
    get_token_service,
    reset_token_service,
)


class TestTokenServiceBasic:
    """Basic tests for TokenService."""

    @pytest.fixture
    def key(self):
        """Generate random 32-byte key."""
        return secrets.token_bytes(32)

    @pytest.fixture
    def service(self, key):
        """Create service with random key."""
        return TokenService(secret_key=key)

    def test_create_token(self, service):
        """Test creating a lease token."""
        token, jti, expires_at = service.create_lease_token(
            agent_id="aid_test123",
            session_id="sess_abc",
        )

        assert token is not None
        assert token.startswith("v4.local.")
        assert len(jti) == 32  # 16 bytes hex
        assert expires_at > datetime.now(timezone.utc)

    def test_verify_token(self, service):
        """Test verifying a valid token."""
        token, jti, _ = service.create_lease_token(
            agent_id="aid_test",
            session_id="session_123",
            sequence=42,
        )

        payload = service.verify_lease_token(token)

        assert payload["agent_id"] == "aid_test"
        assert payload["session_id"] == "session_123"
        assert payload["seq"] == 42
        assert payload["jti"] == jti
        assert "kid" in payload  # Key ID should be present
        assert payload["kid"] == service.key_id

    def test_expired_token(self, key):
        """Test that expired token raises TokenExpiredError."""
        service = TokenService(secret_key=key)

        token, _, _ = service.create_lease_token(
            agent_id="aid_test",
            session_id="session_123",
            ttl_seconds=1,
        )

        time.sleep(1.5)  # Wait for expiration

        with pytest.raises(TokenExpiredError):
            service.verify_lease_token(token)

    def test_invalid_token(self, service):
        """Test that invalid token raises TokenInvalidError."""
        with pytest.raises(TokenInvalidError):
            service.verify_lease_token("v4.local.invalid_token_data")

    def test_wrong_key_fails(self):
        """Test that wrong key fails verification."""
        service1 = TokenService(secret_key=secrets.token_bytes(32))
        service2 = TokenService(secret_key=secrets.token_bytes(32))

        token, _, _ = service1.create_lease_token(
            agent_id="aid_test",
            session_id="session_123",
        )

        with pytest.raises(TokenInvalidError):
            service2.verify_lease_token(token)

    def test_invalid_key_length(self):
        """Test that invalid key length raises ValueError."""
        with pytest.raises(ValueError, match="32 bytes"):
            TokenService(secret_key=b"too_short")

    def test_key_id_computed(self, service):
        """Test that key ID is computed."""
        assert service.key_id is not None
        assert len(service.key_id) == 16  # 8 bytes hex


class TestTokenServiceRevocation:
    """Tests for token revocation."""

    @pytest.fixture
    def key(self):
        """Generate random 32-byte key."""
        return secrets.token_bytes(32)

    @pytest.fixture
    def revoked_jtis(self):
        """Set of revoked JTIs."""
        return set()

    @pytest.fixture
    def service(self, key, revoked_jtis):
        """Create service with revocation checker."""

        def revocation_checker(jti: str) -> bool:
            return jti in revoked_jtis

        return TokenService(secret_key=key, revocation_checker=revocation_checker)

    def test_revoked_token_raises(self, service, revoked_jtis):
        """Test that revoked token raises TokenRevokedError."""
        token, jti, _ = service.create_lease_token(
            agent_id="aid_test",
            session_id="session_123",
        )

        # Verify token works first
        payload = service.verify_lease_token(token)
        assert payload["jti"] == jti

        # Revoke the token
        revoked_jtis.add(jti)

        # Now verification should fail
        with pytest.raises(TokenRevokedError) as exc_info:
            service.verify_lease_token(token)

        assert exc_info.value.jti == jti
        assert exc_info.value.agent_id == "aid_test"

    def test_skip_revocation_check(self, service, revoked_jtis):
        """Test that revocation check can be skipped."""
        token, jti, _ = service.create_lease_token(
            agent_id="aid_test",
            session_id="session_123",
        )

        # Revoke the token
        revoked_jtis.add(jti)

        # With check_revocation=False, should succeed
        payload = service.verify_lease_token(token, check_revocation=False)
        assert payload["jti"] == jti

    def test_set_revocation_checker(self, key):
        """Test setting revocation checker after creation."""
        service = TokenService(secret_key=key)

        token, jti, _ = service.create_lease_token(
            agent_id="aid_test",
            session_id="session_123",
        )

        # Initially no revocation checker
        payload = service.verify_lease_token(token)
        assert payload is not None

        # Set revocation checker that revokes everything
        service.set_revocation_checker(lambda x: True)

        with pytest.raises(TokenRevokedError):
            service.verify_lease_token(token)


class TestTokenServiceKeyRotation:
    """Tests for key rotation support."""

    @pytest.fixture
    def primary_key(self):
        """Primary key."""
        return secrets.token_bytes(32)

    @pytest.fixture
    def old_key(self):
        """Old key for rotation."""
        return secrets.token_bytes(32)

    def test_verify_with_old_key(self, primary_key, old_key):
        """Test that tokens signed with old key are still valid."""
        # Create service with only old key
        old_service = TokenService(secret_key=old_key)
        token, _, _ = old_service.create_lease_token(
            agent_id="aid_test",
            session_id="session_123",
        )

        # Create service with new primary key and old key as previous
        new_service = TokenService(
            secret_key=primary_key,
            previous_keys=[old_key],
        )

        # Should still verify token created with old key
        payload = new_service.verify_lease_token(token)
        assert payload["agent_id"] == "aid_test"

    def test_new_tokens_use_primary_key(self, primary_key, old_key):
        """Test that new tokens are created with primary key."""
        service = TokenService(
            secret_key=primary_key,
            previous_keys=[old_key],
        )

        token, _, _ = service.create_lease_token(
            agent_id="aid_test",
            session_id="session_123",
        )

        # Verify with only primary key (no previous keys)
        primary_only = TokenService(secret_key=primary_key)
        payload = primary_only.verify_lease_token(token)
        assert payload["kid"] == service.key_id

    def test_multiple_previous_keys(self, primary_key):
        """Test with multiple previous keys."""
        old_key1 = secrets.token_bytes(32)
        old_key2 = secrets.token_bytes(32)

        # Create tokens with each old key
        service1 = TokenService(secret_key=old_key1)
        token1, _, _ = service1.create_lease_token(
            agent_id="aid_test1",
            session_id="sess1",
        )

        service2 = TokenService(secret_key=old_key2)
        token2, _, _ = service2.create_lease_token(
            agent_id="aid_test2",
            session_id="sess2",
        )

        # New service with both old keys
        new_service = TokenService(
            secret_key=primary_key,
            previous_keys=[old_key1, old_key2],
        )

        # Both old tokens should verify
        payload1 = new_service.verify_lease_token(token1)
        assert payload1["agent_id"] == "aid_test1"

        payload2 = new_service.verify_lease_token(token2)
        assert payload2["agent_id"] == "aid_test2"

    def test_invalid_previous_key_length_ignored(self, primary_key):
        """Test that invalid previous key lengths are ignored."""
        # Should not raise, just skip invalid key
        service = TokenService(
            secret_key=primary_key,
            previous_keys=[b"short", secrets.token_bytes(32)],
        )

        # Service should work with valid keys
        token, _, _ = service.create_lease_token(
            agent_id="aid_test",
            session_id="sess",
        )
        payload = service.verify_lease_token(token)
        assert payload is not None


class TestTokenServiceRefresh:
    """Tests for token refresh."""

    @pytest.fixture
    def key(self):
        """Generate random 32-byte key."""
        return secrets.token_bytes(32)

    @pytest.fixture
    def service(self, key):
        """Create service with random key."""
        return TokenService(secret_key=key)

    def test_refresh_token(self, service):
        """Test refreshing a token."""
        original_token, original_jti, _ = service.create_lease_token(
            agent_id="aid_test",
            session_id="session_123",
            sequence=0,
        )

        refreshed_token, new_jti, _ = service.refresh_lease_token(original_token)

        # New token should have different JTI
        assert new_jti != original_jti

        # Verify new token
        payload = service.verify_lease_token(refreshed_token)
        assert payload["agent_id"] == "aid_test"
        assert payload["session_id"] == "session_123"
        assert payload["seq"] == 1  # Sequence incremented

    def test_refresh_with_custom_sequence(self, service):
        """Test refreshing with custom sequence."""
        original, _, _ = service.create_lease_token(
            agent_id="aid_test",
            session_id="sess",
            sequence=5,
        )

        refreshed, _, _ = service.refresh_lease_token(original, new_sequence=100)
        payload = service.verify_lease_token(refreshed)
        assert payload["seq"] == 100

    def test_refresh_revoked_token_fails(self, key):
        """Test that refreshing revoked token fails."""
        revoked = set()
        service = TokenService(
            secret_key=key,
            revocation_checker=lambda jti: jti in revoked,
        )

        token, jti, _ = service.create_lease_token(
            agent_id="aid_test",
            session_id="sess",
        )

        revoked.add(jti)

        with pytest.raises(TokenRevokedError):
            service.refresh_lease_token(token)


class TestTokenServiceSingleton:
    """Tests for singleton access."""

    def test_get_token_service(self):
        """Test getting singleton instance."""
        reset_token_service()

        with patch("authority.services.tokens.settings") as mock_settings:
            mock_settings.paseto_key_bytes = secrets.token_bytes(32)
            mock_settings.paseto_previous_keys = []

            service1 = get_token_service()
            service2 = get_token_service()

            assert service1 is service2

    def test_reset_token_service(self):
        """Test resetting singleton instance."""
        reset_token_service()

        with patch("authority.services.tokens.settings") as mock_settings:
            mock_settings.paseto_key_bytes = secrets.token_bytes(32)
            mock_settings.paseto_previous_keys = []

            service1 = get_token_service()
            reset_token_service()
            service2 = get_token_service()

            assert service1 is not service2


class TestTokenRevokedError:
    """Tests for TokenRevokedError exception."""

    def test_error_attributes(self):
        """Test error contains JTI and agent_id."""
        error = TokenRevokedError(
            "Token revoked",
            jti="abc123",
            agent_id="aid_test",
        )

        assert error.jti == "abc123"
        assert error.agent_id == "aid_test"
        assert "Token revoked" in str(error)

    def test_error_without_attributes(self):
        """Test error without optional attributes."""
        error = TokenRevokedError("Revoked")

        assert error.jti is None
        assert error.agent_id is None
