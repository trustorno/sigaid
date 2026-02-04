"""Tests for token and key revocation."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from authority.services.revocation import RevocationService, create_revocation_checker
from authority.models.revocation import SigAidRevokedToken, SigAidKeyRevocation


class TestRevocationService:
    """Tests for RevocationService."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create service with mock db."""
        return RevocationService(mock_db)

    def test_revoke_token(self, service, mock_db):
        """Test revoking a token."""
        mock_db.refresh = MagicMock()

        result = service.revoke_token(
            token_jti="abc123",
            agent_id="aid_xxx",
            original_expiry=datetime.now(timezone.utc) + timedelta(hours=1),
            revoked_by="admin",
            reason="Compromised",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        # Check the created object
        created = mock_db.add.call_args[0][0]
        assert created.token_jti == "abc123"
        assert created.agent_id == "aid_xxx"
        assert created.revoked_by == "admin"
        assert created.revocation_reason == "Compromised"

    def test_is_token_revoked_true(self, service, mock_db):
        """Test checking revoked token returns True."""
        # Setup mock to return a revocation record
        mock_revocation = SigAidRevokedToken()
        mock_revocation.token_jti = "revoked_jti"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_revocation

        result = service.is_token_revoked("revoked_jti")

        assert result is True

    def test_is_token_revoked_false(self, service, mock_db):
        """Test checking non-revoked token returns False."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.is_token_revoked("valid_jti")

        assert result is False

    def test_get_token_revocation(self, service, mock_db):
        """Test getting revocation details."""
        mock_revocation = SigAidRevokedToken()
        mock_revocation.token_jti = "test_jti"
        mock_revocation.revocation_reason = "Test reason"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_revocation

        result = service.get_token_revocation("test_jti")

        assert result is not None
        assert result.token_jti == "test_jti"
        assert result.revocation_reason == "Test reason"

    def test_get_token_revocation_not_found(self, service, mock_db):
        """Test getting non-existent revocation returns None."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.get_token_revocation("nonexistent")

        assert result is None

    def test_revoke_key(self, service, mock_db):
        """Test revoking a PASETO key."""
        mock_db.refresh = MagicMock()
        grace_end = datetime.now(timezone.utc) + timedelta(hours=24)

        result = service.revoke_key(
            key_id="abcd1234",
            revoked_by="system",
            reason="Key rotation",
            grace_period_end=grace_end,
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        created = mock_db.add.call_args[0][0]
        assert created.key_id == "abcd1234"
        assert created.revoked_by == "system"
        assert created.grace_period_end == grace_end

    def test_is_key_revoked_true(self, service, mock_db):
        """Test checking revoked key returns True."""
        mock_revocation = SigAidKeyRevocation()
        mock_revocation.key_id = "revoked_key"
        mock_revocation.grace_period_end = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_revocation

        result = service.is_key_revoked("revoked_key")

        assert result is True

    def test_is_key_revoked_false(self, service, mock_db):
        """Test checking non-revoked key returns False."""
        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = service.is_key_revoked("valid_key")

        assert result is False

    def test_is_key_revoked_in_grace_period(self, service, mock_db):
        """Test key in grace period is not considered revoked."""
        mock_revocation = SigAidKeyRevocation()
        mock_revocation.key_id = "grace_key"
        mock_revocation.grace_period_end = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_revocation

        result = service.is_key_revoked("grace_key", check_grace_period=True)

        assert result is False

    def test_is_key_revoked_past_grace_period(self, service, mock_db):
        """Test key past grace period is revoked."""
        mock_revocation = SigAidKeyRevocation()
        mock_revocation.key_id = "expired_grace"
        mock_revocation.grace_period_end = datetime.now(timezone.utc) - timedelta(hours=1)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_revocation

        result = service.is_key_revoked("expired_grace", check_grace_period=True)

        assert result is True

    def test_cleanup_expired_revocations(self, service, mock_db):
        """Test cleanup of expired revocations."""
        mock_db.query.return_value.filter.return_value.delete.return_value = 5

        result = service.cleanup_expired_revocations(retention_hours=24)

        assert result == 5
        mock_db.commit.assert_called_once()


class TestCreateRevocationChecker:
    """Tests for create_revocation_checker factory."""

    def test_creates_callable(self):
        """Test creates a callable function."""
        def mock_session_factory():
            return MagicMock()

        checker = create_revocation_checker(mock_session_factory)

        assert callable(checker)

    def test_checker_returns_bool(self):
        """Test checker function returns boolean."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        def mock_session_factory():
            return mock_db

        checker = create_revocation_checker(mock_session_factory)
        result = checker("test_jti")

        assert isinstance(result, bool)

    def test_checker_closes_session(self):
        """Test checker closes database session."""
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None

        def mock_session_factory():
            return mock_db

        checker = create_revocation_checker(mock_session_factory)
        checker("test_jti")

        mock_db.close.assert_called_once()
