"""Edge case tests for SigAid SDK."""

import base64
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sigaid.crypto.keys import KeyPair
from sigaid.crypto.hashing import hash_bytes, verify_chain
from sigaid.crypto.tokens import LeaseTokenManager
from sigaid.identity.agent_id import AgentID
from sigaid.models.state import StateEntry, ActionType
from sigaid.models.lease import Lease, LeaseStatus
from sigaid.state.chain import StateChain
from sigaid.exceptions import (
    InvalidKey,
    InvalidAgentID,
    CryptoError,
    TokenExpired,
    TokenInvalid,
    StateChainError,
    ChainIntegrityError,
    ClientError,
)
from sigaid.constants import GENESIS_PREV_HASH, BLAKE3_HASH_SIZE


class TestKeyPairEdgeCases:
    """Edge case tests for KeyPair."""

    def test_from_seed_empty_bytes(self):
        """Empty seed raises InvalidKey."""
        with pytest.raises(InvalidKey):
            KeyPair.from_seed(b"")

    def test_from_seed_exactly_31_bytes(self):
        """31 bytes (one short) raises InvalidKey."""
        with pytest.raises(InvalidKey):
            KeyPair.from_seed(b"x" * 31)

    def test_from_seed_exactly_33_bytes(self):
        """33 bytes (one extra) raises InvalidKey."""
        with pytest.raises(InvalidKey):
            KeyPair.from_seed(b"x" * 33)

    def test_from_private_bytes_invalid(self):
        """Invalid private key bytes raises InvalidKey."""
        with pytest.raises(InvalidKey):
            KeyPair.from_private_bytes(b"not valid key bytes" + b"x" * 12)

    def test_sign_empty_message(self):
        """Signing empty message works."""
        keypair = KeyPair.generate()
        sig = keypair.sign(b"")
        assert len(sig) == 64
        assert keypair.verify(sig, b"")

    def test_sign_very_long_message(self):
        """Signing very long message works."""
        keypair = KeyPair.generate()
        message = b"x" * 1_000_000  # 1MB
        sig = keypair.sign(message)
        assert keypair.verify(sig, message)

    def test_sign_with_unicode_domain(self):
        """Domain with unicode characters works."""
        keypair = KeyPair.generate()
        message = b"test"
        domain = "sigaid.test.v1.日本語"
        sig = keypair.sign(message, domain=domain)
        assert keypair.verify(sig, message, domain=domain)

    def test_verify_truncated_signature(self):
        """Truncated signature returns False."""
        keypair = KeyPair.generate()
        message = b"test"
        sig = keypair.sign(message)
        assert not keypair.verify(sig[:32], message)

    def test_verify_extended_signature(self):
        """Extended signature returns False."""
        keypair = KeyPair.generate()
        message = b"test"
        sig = keypair.sign(message)
        assert not keypair.verify(sig + b"extra", message)

    def test_encrypted_file_empty_password(self):
        """Empty password works (not recommended but valid)."""
        keypair = KeyPair.generate()
        with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
            path = Path(f.name)
        try:
            keypair.to_encrypted_file(path, "")
            loaded = KeyPair.from_encrypted_file(path, "")
            assert loaded.public_key_bytes() == keypair.public_key_bytes()
        finally:
            path.unlink(missing_ok=True)

    def test_encrypted_file_unicode_password(self):
        """Unicode password works."""
        keypair = KeyPair.generate()
        password = "пароль_密码_🔑"
        with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
            path = Path(f.name)
        try:
            keypair.to_encrypted_file(path, password)
            loaded = KeyPair.from_encrypted_file(path, password)
            assert loaded.public_key_bytes() == keypair.public_key_bytes()
        finally:
            path.unlink(missing_ok=True)

    def test_encrypted_file_missing_file(self):
        """Loading from missing file raises error."""
        with pytest.raises(FileNotFoundError):
            KeyPair.from_encrypted_file(Path("/nonexistent/path.key"), "password")

    def test_encrypted_file_corrupt_json(self):
        """Corrupt JSON file raises error."""
        with tempfile.NamedTemporaryFile(suffix=".key", delete=False, mode="w") as f:
            f.write("not valid json {")
            path = Path(f.name)
        try:
            with pytest.raises(json.JSONDecodeError):
                KeyPair.from_encrypted_file(path, "password")
        finally:
            path.unlink(missing_ok=True)

    def test_encrypted_file_wrong_version(self):
        """Wrong keyfile version raises CryptoError."""
        keypair = KeyPair.generate()
        with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
            path = Path(f.name)
        try:
            keypair.to_encrypted_file(path, "password")
            # Modify version
            data = json.loads(path.read_text())
            data["version"] = 999
            path.write_text(json.dumps(data))

            with pytest.raises(CryptoError, match="Unsupported keyfile version"):
                KeyPair.from_encrypted_file(path, "password")
        finally:
            path.unlink(missing_ok=True)


class TestAgentIDEdgeCases:
    """Edge case tests for AgentID."""

    def test_validate_empty_string(self):
        """Empty string raises InvalidAgentID."""
        with pytest.raises(InvalidAgentID):
            AgentID.validate("")

    def test_validate_wrong_prefix(self):
        """Wrong prefix raises InvalidAgentID."""
        with pytest.raises(InvalidAgentID, match="must start with"):
            AgentID.validate("bad_prefix123")

    def test_validate_only_prefix(self):
        """Only prefix with no data raises InvalidAgentID."""
        with pytest.raises(InvalidAgentID):
            AgentID.validate("aid_")

    def test_validate_invalid_base58(self):
        """Invalid base58 characters raise InvalidAgentID."""
        with pytest.raises(InvalidAgentID, match="Invalid base58"):
            AgentID.validate("aid_invalid+chars!")

    def test_validate_wrong_length(self):
        """Wrong decoded length raises InvalidAgentID."""
        with pytest.raises(InvalidAgentID):
            AgentID.validate("aid_tooShort")

    def test_validate_bad_checksum(self):
        """Bad checksum raises InvalidAgentID."""
        keypair = KeyPair.generate()
        agent_id = keypair.to_agent_id()
        # Corrupt the last character
        corrupted = str(agent_id)[:-1] + ("A" if str(agent_id)[-1] != "A" else "B")
        with pytest.raises(InvalidAgentID, match="Checksum"):
            AgentID.validate(corrupted)

    def test_from_public_key_wrong_size(self):
        """Wrong public key size raises InvalidAgentID."""
        with pytest.raises(InvalidAgentID, match="must be 32 bytes"):
            AgentID.from_public_key(b"too short")

    def test_equality_with_string(self):
        """AgentID can be compared with string."""
        keypair = KeyPair.generate()
        agent_id = keypair.to_agent_id()
        assert agent_id == str(agent_id)
        assert agent_id != "different_string"

    def test_equality_with_other_agent_id(self):
        """AgentID equality with another AgentID."""
        keypair = KeyPair.generate()
        agent_id1 = keypair.to_agent_id()
        agent_id2 = keypair.to_agent_id()
        assert agent_id1 == agent_id2

    def test_hash_for_dict_key(self):
        """AgentID can be used as dict key."""
        keypair = KeyPair.generate()
        agent_id = keypair.to_agent_id()
        d = {agent_id: "value"}
        assert d[agent_id] == "value"


class TestLeaseTokenEdgeCases:
    """Edge case tests for LeaseTokenManager."""

    def test_init_wrong_key_size(self):
        """Wrong key size raises ValueError."""
        with pytest.raises(ValueError, match="must be 32 bytes"):
            LeaseTokenManager(b"too short")

    def test_verify_expired_token(self):
        """Expired token raises TokenExpired."""
        manager = LeaseTokenManager(b"x" * 32)
        token = manager.create_token(
            agent_id="aid_test",
            session_id="session123",
            ttl=timedelta(seconds=-1),  # Already expired
        )
        with pytest.raises(TokenExpired):
            manager.verify_token(token)

    def test_verify_invalid_token(self):
        """Invalid token raises TokenInvalid."""
        manager = LeaseTokenManager(b"x" * 32)
        with pytest.raises(TokenInvalid):
            manager.verify_token("not.a.valid.token")

    def test_verify_token_from_different_key(self):
        """Token from different key raises TokenInvalid."""
        manager1 = LeaseTokenManager(b"a" * 32)
        manager2 = LeaseTokenManager(b"b" * 32)
        token = manager1.create_token(
            agent_id="aid_test",
            session_id="session123",
        )
        with pytest.raises(TokenInvalid):
            manager2.verify_token(token)

    def test_decode_token_check_expiry(self):
        """decode_token with check_expiry=True raises on expired."""
        manager = LeaseTokenManager(b"x" * 32)
        token = manager.create_token(
            agent_id="aid_test",
            session_id="session123",
            ttl=timedelta(seconds=-1),
        )
        # Should work without expiry check
        payload = manager.decode_token(token, check_expiry=False)
        assert payload["agent_id"] == "aid_test"

        # Should fail with expiry check
        with pytest.raises(TokenExpired):
            manager.decode_token(token, check_expiry=True)

    def test_refresh_expired_token(self):
        """Refreshing expired token raises TokenExpired."""
        manager = LeaseTokenManager(b"x" * 32)
        token = manager.create_token(
            agent_id="aid_test",
            session_id="session123",
            ttl=timedelta(seconds=-1),
        )
        with pytest.raises(TokenExpired):
            manager.refresh_token(token)


class TestLeaseModelEdgeCases:
    """Edge case tests for Lease model."""

    def test_repr_short_session_id(self):
        """__repr__ works with short session_id."""
        now = datetime.now(timezone.utc)
        lease = Lease(
            agent_id="aid_test",
            session_id="short",  # Less than 8 chars
            token="token",
            acquired_at=now,
            expires_at=now + timedelta(minutes=10),
        )
        repr_str = repr(lease)
        assert "short" in repr_str  # Should show full session_id

    def test_is_active_with_released_status(self):
        """is_active returns False if status is released."""
        now = datetime.now(timezone.utc)
        lease = Lease(
            agent_id="aid_test",
            session_id="session123",
            token="token",
            acquired_at=now,
            expires_at=now + timedelta(minutes=10),
            status=LeaseStatus.RELEASED,
        )
        assert not lease.is_active

    def test_should_renew_when_expired(self):
        """should_renew returns False when expired."""
        now = datetime.now(timezone.utc)
        lease = Lease(
            agent_id="aid_test",
            session_id="session123",
            token="token",
            acquired_at=now - timedelta(minutes=20),
            expires_at=now - timedelta(minutes=10),  # Already expired
        )
        assert not lease.should_renew

    def test_time_remaining_negative(self):
        """time_remaining can be negative when expired."""
        now = datetime.now(timezone.utc)
        lease = Lease(
            agent_id="aid_test",
            session_id="session123",
            token="token",
            acquired_at=now - timedelta(minutes=20),
            expires_at=now - timedelta(minutes=10),
        )
        assert lease.time_remaining.total_seconds() < 0

    def test_to_dict_from_dict_roundtrip(self):
        """Lease serialization roundtrip."""
        now = datetime.now(timezone.utc)
        lease = Lease(
            agent_id="aid_test",
            session_id="session123",
            token="token",
            acquired_at=now,
            expires_at=now + timedelta(minutes=10),
            sequence=5,
        )
        data = lease.to_dict()
        restored = Lease.from_dict(data)
        assert restored.agent_id == lease.agent_id
        assert restored.sequence == lease.sequence


class TestStateEntryEdgeCases:
    """Edge case tests for StateEntry."""

    def test_create_with_string_action_type(self):
        """StateEntry.create accepts string action_type."""
        keypair = KeyPair.generate()
        entry = StateEntry.create(
            agent_id=str(keypair.to_agent_id()),
            sequence=0,
            prev_hash=GENESIS_PREV_HASH,
            action_type="transaction",  # String, not ActionType
            action_summary="Test",
            action_data=None,
            keypair=keypair,
        )
        assert entry.action_type == ActionType.TRANSACTION

    def test_create_with_invalid_string_action_type(self):
        """Invalid string action_type raises ValueError."""
        keypair = KeyPair.generate()
        with pytest.raises(ValueError):
            StateEntry.create(
                agent_id=str(keypair.to_agent_id()),
                sequence=0,
                prev_hash=GENESIS_PREV_HASH,
                action_type="not_valid_type",
                action_summary="Test",
                action_data=None,
                keypair=keypair,
            )

    def test_create_with_none_action_data(self):
        """None action_data uses zero hash."""
        keypair = KeyPair.generate()
        entry = StateEntry.create(
            agent_id=str(keypair.to_agent_id()),
            sequence=0,
            prev_hash=GENESIS_PREV_HASH,
            action_type=ActionType.TRANSACTION,
            action_summary="Test",
            action_data=None,
            keypair=keypair,
        )
        assert entry.action_data_hash == bytes(BLAKE3_HASH_SIZE)

    def test_create_with_empty_action_data(self):
        """Empty dict action_data is treated as None (zero hash).

        Note: Empty dict {} is falsy in Python, so it uses zero hash.
        """
        keypair = KeyPair.generate()
        entry = StateEntry.create(
            agent_id=str(keypair.to_agent_id()),
            sequence=0,
            prev_hash=GENESIS_PREV_HASH,
            action_type=ActionType.TRANSACTION,
            action_summary="Test",
            action_data={},
            keypair=keypair,
        )
        # Empty dict is falsy, so treated as None -> zero hash
        assert entry.action_data_hash == bytes(BLAKE3_HASH_SIZE)

    def test_wrong_prev_hash_size_raises(self):
        """Wrong prev_hash size raises ValueError."""
        keypair = KeyPair.generate()
        with pytest.raises(ValueError, match="prev_hash must be"):
            StateEntry(
                agent_id=str(keypair.to_agent_id()),
                sequence=0,
                prev_hash=b"too short",
                timestamp=datetime.now(timezone.utc),
                action_type=ActionType.TRANSACTION,
                action_summary="Test",
                action_data_hash=bytes(32),
                signature=bytes(64),
                entry_hash=bytes(32),
            )

    def test_verify_signature_wrong_key(self):
        """verify_signature returns False for wrong key."""
        keypair1 = KeyPair.generate()
        keypair2 = KeyPair.generate()
        entry = StateEntry.create(
            agent_id=str(keypair1.to_agent_id()),
            sequence=0,
            prev_hash=GENESIS_PREV_HASH,
            action_type=ActionType.TRANSACTION,
            action_summary="Test",
            action_data=None,
            keypair=keypair1,
        )
        # Verify with wrong key
        assert not entry.verify_signature(keypair2.public_key_bytes())


class TestStateChainEdgeCases:
    """Edge case tests for StateChain."""

    def test_load_corrupt_file(self):
        """Loading corrupt file raises StateChainError."""
        keypair = KeyPair.generate()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write("not valid json {")
            path = Path(f.name)
        try:
            chain = StateChain(
                agent_id=str(keypair.to_agent_id()),
                keypair=keypair,
                persistence_path=path,
            )
            with pytest.raises(StateChainError, match="Corrupt state file"):
                chain._load_from_file()
        finally:
            path.unlink(missing_ok=True)

    def test_load_file_missing_entries(self):
        """Loading file without entries key raises StateChainError."""
        keypair = KeyPair.generate()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            f.write('{"agent_id": "test"}')  # Missing "entries"
            path = Path(f.name)
        try:
            chain = StateChain(
                agent_id=str(keypair.to_agent_id()),
                keypair=keypair,
                persistence_path=path,
            )
            with pytest.raises(StateChainError, match="missing 'entries'"):
                chain._load_from_file()
        finally:
            path.unlink(missing_ok=True)

    def test_initialize_already_initialized(self):
        """Initializing already initialized chain raises StateChainError."""
        keypair = KeyPair.generate()
        chain = StateChain(
            agent_id=str(keypair.to_agent_id()),
            keypair=keypair,
        )
        chain.initialize("First")
        with pytest.raises(StateChainError, match="already initialized"):
            chain.initialize("Second")

    def test_verify_empty_chain(self):
        """Verifying empty chain returns True."""
        keypair = KeyPair.generate()
        chain = StateChain(
            agent_id=str(keypair.to_agent_id()),
            keypair=keypair,
        )
        assert chain.verify()

    def test_get_entries_since_empty(self):
        """get_entries_since on empty chain returns empty list."""
        keypair = KeyPair.generate()
        chain = StateChain(
            agent_id=str(keypair.to_agent_id()),
            keypair=keypair,
        )
        assert chain.get_entries_since(0) == []

    def test_get_entry_by_hash_not_found(self):
        """get_entry_by_hash returns None if not found."""
        keypair = KeyPair.generate()
        chain = StateChain(
            agent_id=str(keypair.to_agent_id()),
            keypair=keypair,
        )
        chain.initialize()
        assert chain.get_entry_by_hash(b"x" * 32) is None

    def test_sequence_empty_chain(self):
        """sequence returns -1 for empty chain."""
        keypair = KeyPair.generate()
        chain = StateChain(
            agent_id=str(keypair.to_agent_id()),
            keypair=keypair,
        )
        assert chain.sequence == -1

    def test_head_empty_chain(self):
        """head returns None for empty chain."""
        keypair = KeyPair.generate()
        chain = StateChain(
            agent_id=str(keypair.to_agent_id()),
            keypair=keypair,
        )
        assert chain.head is None


class TestChainVerificationEdgeCases:
    """Edge case tests for chain verification."""

    def test_verify_empty_list(self):
        """Verifying empty list returns True."""
        assert verify_chain([])

    def test_verify_genesis_non_zero_prev_hash(self):
        """Genesis with non-zero prev_hash raises ChainIntegrityError."""
        keypair = KeyPair.generate()
        # Manually create entry with wrong prev_hash
        entry = StateEntry.create(
            agent_id=str(keypair.to_agent_id()),
            sequence=0,
            prev_hash=b"x" * 32,  # Should be zeros for genesis
            action_type=ActionType.TRANSACTION,
            action_summary="Test",
            action_data=None,
            keypair=keypair,
        )
        with pytest.raises(ChainIntegrityError, match="non-zero prev_hash"):
            verify_chain([entry])


class TestHashingEdgeCases:
    """Edge case tests for hashing functions."""

    def test_hash_empty_bytes(self):
        """Hashing empty bytes works."""
        result = hash_bytes(b"")
        assert len(result) == 32

    def test_hash_is_deterministic(self):
        """Same input always produces same hash."""
        data = b"test data"
        h1 = hash_bytes(data)
        h2 = hash_bytes(data)
        assert h1 == h2

    def test_hash_collision_resistance(self):
        """Different inputs produce different hashes."""
        h1 = hash_bytes(b"input1")
        h2 = hash_bytes(b"input2")
        assert h1 != h2


class TestClientErrorHandling:
    """Edge case tests for client error handling."""

    def test_client_error_with_response_data(self):
        """ClientError preserves response data."""
        response_data = {"error": "test", "detail": "message"}
        error = ClientError(400, "Bad request", response_data=response_data)
        assert error.status_code == 400
        assert error.response_data == response_data
        assert "400" in str(error)

    def test_client_error_without_response_data(self):
        """ClientError works without response data."""
        error = ClientError(404, "Not found")
        assert error.status_code == 404
        assert error.response_data == {}
