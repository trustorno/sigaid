"""Unit tests for cryptographic components."""

import base64
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from sigaid.crypto.keys import KeyPair, public_key_from_bytes
from sigaid.crypto.hashing import hash_bytes, hash_hex, hash_multiple, verify_chain, compute_entry_hash
from sigaid.crypto.signing import sign_with_domain, verify_with_domain, verify_with_domain_safe
from sigaid.constants import (
    DOMAIN_LEASE,
    DOMAIN_STATE,
    DOMAIN_VERIFY,
    ED25519_SEED_SIZE,
    ED25519_SIGNATURE_SIZE,
    BLAKE3_HASH_SIZE,
    GENESIS_PREV_HASH,
)
from sigaid.exceptions import InvalidKey, CryptoError


class TestKeyPair:
    """Tests for KeyPair class."""

    def test_generate_creates_valid_keypair(self):
        """Generate creates a valid keypair."""
        keypair = KeyPair.generate()

        assert keypair.public_key_bytes() is not None
        assert len(keypair.public_key_bytes()) == 32
        assert len(keypair.private_key_bytes()) == 32

    def test_from_seed_is_deterministic(self):
        """Same seed produces same keypair."""
        seed = b"x" * 32

        kp1 = KeyPair.from_seed(seed)
        kp2 = KeyPair.from_seed(seed)

        assert kp1.public_key_bytes() == kp2.public_key_bytes()
        assert kp1.private_key_bytes() == kp2.private_key_bytes()

    def test_from_seed_rejects_wrong_size(self):
        """Seed must be exactly 32 bytes."""
        with pytest.raises(InvalidKey):
            KeyPair.from_seed(b"too short")

        with pytest.raises(InvalidKey):
            KeyPair.from_seed(b"x" * 64)

    def test_sign_produces_valid_signature(self):
        """Sign produces a 64-byte signature."""
        keypair = KeyPair.generate()
        message = b"test message"

        signature = keypair.sign(message)

        assert len(signature) == ED25519_SIGNATURE_SIZE
        assert keypair.verify(signature, message)

    def test_sign_with_domain_separation(self):
        """Domain separation changes the signature."""
        keypair = KeyPair.generate()
        message = b"test message"

        sig_no_domain = keypair.sign(message)
        sig_with_domain = keypair.sign(message, domain="test.domain.v1")

        assert sig_no_domain != sig_with_domain
        assert keypair.verify(sig_no_domain, message)
        assert keypair.verify(sig_with_domain, message, domain="test.domain.v1")
        assert not keypair.verify(sig_with_domain, message)  # Wrong domain

    def test_verify_rejects_wrong_signature(self):
        """Verify rejects invalid signatures."""
        keypair = KeyPair.generate()
        message = b"test message"

        signature = keypair.sign(message)
        bad_signature = bytes(64)

        assert keypair.verify(signature, message)
        assert not keypair.verify(bad_signature, message)

    def test_verify_rejects_wrong_message(self):
        """Verify rejects tampered messages."""
        keypair = KeyPair.generate()
        message = b"test message"

        signature = keypair.sign(message)

        assert keypair.verify(signature, message)
        assert not keypair.verify(signature, b"different message")

    def test_to_agent_id(self):
        """KeyPair can derive AgentID."""
        keypair = KeyPair.generate()
        agent_id = keypair.to_agent_id()

        assert str(agent_id).startswith("aid_")
        assert agent_id.to_public_key_bytes() == keypair.public_key_bytes()

    def test_encrypted_file_roundtrip(self):
        """Keypair can be saved and loaded from encrypted file."""
        keypair = KeyPair.generate()
        password = "test-password-123"

        with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
            path = Path(f.name)

        try:
            keypair.to_encrypted_file(path, password)
            loaded = KeyPair.from_encrypted_file(path, password)

            assert loaded.public_key_bytes() == keypair.public_key_bytes()
            assert loaded.private_key_bytes() == keypair.private_key_bytes()
        finally:
            path.unlink(missing_ok=True)

    def test_encrypted_file_wrong_password(self):
        """Wrong password raises CryptoError."""
        keypair = KeyPair.generate()

        with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
            path = Path(f.name)

        try:
            keypair.to_encrypted_file(path, "correct-password")

            with pytest.raises(CryptoError):
                KeyPair.from_encrypted_file(path, "wrong-password")
        finally:
            path.unlink(missing_ok=True)

    def test_encrypted_file_format(self):
        """Encrypted file has expected format."""
        keypair = KeyPair.generate()

        with tempfile.NamedTemporaryFile(suffix=".key", delete=False) as f:
            path = Path(f.name)

        try:
            keypair.to_encrypted_file(path, "password")
            data = json.loads(path.read_text())

            assert data["version"] == 1
            assert data["algorithm"] == "scrypt-chacha20poly1305"
            assert "scrypt_params" in data
            assert "salt" in data
            assert "nonce" in data
            assert "ciphertext" in data
        finally:
            path.unlink(missing_ok=True)


class TestPublicKeyFromBytes:
    """Tests for public_key_from_bytes function."""

    def test_valid_public_key(self):
        """Valid 32-byte public key loads successfully."""
        keypair = KeyPair.generate()
        pk_bytes = keypair.public_key_bytes()

        pk = public_key_from_bytes(pk_bytes)
        assert pk is not None

    def test_rejects_wrong_size(self):
        """Wrong size public key raises InvalidKey."""
        with pytest.raises(InvalidKey):
            public_key_from_bytes(b"too short")


class TestHashing:
    """Tests for hashing functions."""

    def test_hash_bytes_produces_32_bytes(self):
        """hash_bytes produces 32-byte hash."""
        result = hash_bytes(b"test data")
        assert len(result) == BLAKE3_HASH_SIZE

    def test_hash_bytes_is_deterministic(self):
        """Same input produces same hash."""
        data = b"test data"
        assert hash_bytes(data) == hash_bytes(data)

    def test_hash_bytes_different_inputs(self):
        """Different inputs produce different hashes."""
        assert hash_bytes(b"data1") != hash_bytes(b"data2")

    def test_hash_hex_produces_64_chars(self):
        """hash_hex produces 64-character hex string."""
        result = hash_hex(b"test data")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_multiple_combines_inputs(self):
        """hash_multiple combines multiple inputs."""
        h1 = hash_multiple(b"part1", b"part2")
        h2 = hash_multiple(b"part1", b"part2")
        h3 = hash_multiple(b"part1part2")  # Different from concatenation

        assert h1 == h2
        assert len(h1) == BLAKE3_HASH_SIZE

    def test_genesis_prev_hash_is_zero(self):
        """Genesis prev_hash is 32 zero bytes."""
        assert len(GENESIS_PREV_HASH) == BLAKE3_HASH_SIZE
        assert GENESIS_PREV_HASH == bytes(32)


class TestSigning:
    """Tests for signing functions."""

    def test_sign_with_domain(self):
        """sign_with_domain creates valid signature."""
        keypair = KeyPair.generate()
        message = b"test message"

        signature = sign_with_domain(
            keypair._private_key, message, DOMAIN_LEASE
        )

        assert len(signature) == ED25519_SIGNATURE_SIZE

    def test_verify_with_domain(self):
        """verify_with_domain validates correct signature."""
        keypair = KeyPair.generate()
        message = b"test message"

        signature = sign_with_domain(
            keypair._private_key, message, DOMAIN_LEASE
        )

        # Should succeed
        verify_with_domain(keypair._public_key, signature, message, DOMAIN_LEASE)

    def test_verify_with_domain_wrong_domain_fails(self):
        """verify_with_domain fails with wrong domain."""
        keypair = KeyPair.generate()
        message = b"test message"

        signature = sign_with_domain(
            keypair._private_key, message, DOMAIN_LEASE
        )

        # Wrong domain should fail
        with pytest.raises(Exception):
            verify_with_domain(keypair._public_key, signature, message, DOMAIN_STATE)

    def test_verify_with_domain_safe_returns_bool(self):
        """verify_with_domain_safe returns bool instead of raising."""
        keypair = KeyPair.generate()
        message = b"test message"

        signature = sign_with_domain(
            keypair._private_key, message, DOMAIN_LEASE
        )

        assert verify_with_domain_safe(keypair._public_key, signature, message, DOMAIN_LEASE)
        assert not verify_with_domain_safe(keypair._public_key, signature, message, DOMAIN_STATE)


class TestStateEntry:
    """Tests for state entry creation and verification."""

    def test_create_state_entry(self):
        """StateEntry.create produces valid entry."""
        from sigaid.models.state import StateEntry, ActionType

        keypair = KeyPair.generate()
        agent_id = str(keypair.to_agent_id())

        entry = StateEntry.create(
            agent_id=agent_id,
            sequence=0,
            prev_hash=GENESIS_PREV_HASH,
            action_type=ActionType.TRANSACTION,
            action_summary="Test transaction",
            action_data={"amount": 100},
            keypair=keypair,
        )

        assert entry.agent_id == agent_id
        assert entry.sequence == 0
        assert entry.prev_hash == GENESIS_PREV_HASH
        assert entry.action_type == ActionType.TRANSACTION
        assert len(entry.signature) == ED25519_SIGNATURE_SIZE
        assert len(entry.entry_hash) == BLAKE3_HASH_SIZE

    def test_state_entry_verify_signature(self):
        """StateEntry signature verification works."""
        from sigaid.models.state import StateEntry, ActionType

        keypair = KeyPair.generate()
        agent_id = str(keypair.to_agent_id())

        entry = StateEntry.create(
            agent_id=agent_id,
            sequence=0,
            prev_hash=GENESIS_PREV_HASH,
            action_type=ActionType.TRANSACTION,
            action_summary="Test",
            action_data=None,
            keypair=keypair,
        )

        assert entry.verify_signature(keypair.public_key_bytes())

    def test_state_entry_verify_hash(self):
        """StateEntry hash verification works."""
        from sigaid.models.state import StateEntry, ActionType

        keypair = KeyPair.generate()
        agent_id = str(keypair.to_agent_id())

        entry = StateEntry.create(
            agent_id=agent_id,
            sequence=0,
            prev_hash=GENESIS_PREV_HASH,
            action_type=ActionType.TRANSACTION,
            action_summary="Test",
            action_data=None,
            keypair=keypair,
        )

        assert entry.verify_hash()

    def test_state_entry_to_dict_roundtrip(self):
        """StateEntry serializes and deserializes correctly."""
        from sigaid.models.state import StateEntry, ActionType

        keypair = KeyPair.generate()
        agent_id = str(keypair.to_agent_id())

        entry = StateEntry.create(
            agent_id=agent_id,
            sequence=0,
            prev_hash=GENESIS_PREV_HASH,
            action_type=ActionType.TRANSACTION,
            action_summary="Test",
            action_data={"key": "value"},
            keypair=keypair,
        )

        data = entry.to_dict()
        restored = StateEntry.from_dict(data)

        assert restored.agent_id == entry.agent_id
        assert restored.sequence == entry.sequence
        assert restored.entry_hash == entry.entry_hash
        assert restored.signature == entry.signature


class TestChainVerification:
    """Tests for state chain verification."""

    def test_verify_single_entry_chain(self):
        """Single entry chain verifies successfully."""
        from sigaid.models.state import StateEntry, ActionType

        keypair = KeyPair.generate()
        agent_id = str(keypair.to_agent_id())

        entry = StateEntry.create(
            agent_id=agent_id,
            sequence=0,
            prev_hash=GENESIS_PREV_HASH,
            action_type=ActionType.TRANSACTION,
            action_summary="Genesis",
            action_data=None,
            keypair=keypair,
        )

        assert verify_chain([entry])

    def test_verify_multi_entry_chain(self):
        """Multi-entry chain verifies successfully."""
        from sigaid.models.state import StateEntry, ActionType

        keypair = KeyPair.generate()
        agent_id = str(keypair.to_agent_id())

        entries = []

        # Genesis
        entry0 = StateEntry.create(
            agent_id=agent_id,
            sequence=0,
            prev_hash=GENESIS_PREV_HASH,
            action_type=ActionType.ATTESTATION,
            action_summary="Genesis",
            action_data=None,
            keypair=keypair,
        )
        entries.append(entry0)

        # Entry 1
        entry1 = StateEntry.create(
            agent_id=agent_id,
            sequence=1,
            prev_hash=entry0.entry_hash,
            action_type=ActionType.TRANSACTION,
            action_summary="Transaction 1",
            action_data={"amount": 100},
            keypair=keypair,
        )
        entries.append(entry1)

        # Entry 2
        entry2 = StateEntry.create(
            agent_id=agent_id,
            sequence=2,
            prev_hash=entry1.entry_hash,
            action_type=ActionType.TRANSACTION,
            action_summary="Transaction 2",
            action_data={"amount": 200},
            keypair=keypair,
        )
        entries.append(entry2)

        assert verify_chain(entries)

    def test_verify_chain_detects_broken_link(self):
        """Chain verification detects broken prev_hash link."""
        from sigaid.models.state import StateEntry, ActionType
        from sigaid.exceptions import ChainIntegrityError

        keypair = KeyPair.generate()
        agent_id = str(keypair.to_agent_id())

        entry0 = StateEntry.create(
            agent_id=agent_id,
            sequence=0,
            prev_hash=GENESIS_PREV_HASH,
            action_type=ActionType.ATTESTATION,
            action_summary="Genesis",
            action_data=None,
            keypair=keypair,
        )

        # Entry 1 with WRONG prev_hash
        entry1 = StateEntry.create(
            agent_id=agent_id,
            sequence=1,
            prev_hash=bytes(32),  # Wrong! Should be entry0.entry_hash
            action_type=ActionType.TRANSACTION,
            action_summary="Transaction",
            action_data=None,
            keypair=keypair,
        )

        with pytest.raises(ChainIntegrityError):
            verify_chain([entry0, entry1])


class TestForkDetection:
    """Tests for fork detection."""

    def test_fork_detection_same_sequence_different_hash(self):
        """Fork detected when same sequence has different hash."""
        from sigaid.models.state import StateEntry, ActionType
        from sigaid.state.verification import ChainVerifier
        from sigaid.exceptions import ForkDetected

        keypair = KeyPair.generate()
        agent_id = str(keypair.to_agent_id())

        verifier = ChainVerifier()

        # Create first entry
        entry1 = StateEntry.create(
            agent_id=agent_id,
            sequence=0,
            prev_hash=GENESIS_PREV_HASH,
            action_type=ActionType.TRANSACTION,
            action_summary="Version A",
            action_data={"version": "a"},
            keypair=keypair,
        )

        # Record it
        verifier.verify_head(agent_id, entry1)

        # Create DIFFERENT entry with same sequence (fork!)
        entry2 = StateEntry.create(
            agent_id=agent_id,
            sequence=0,
            prev_hash=GENESIS_PREV_HASH,
            action_type=ActionType.TRANSACTION,
            action_summary="Version B",  # Different!
            action_data={"version": "b"},
            keypair=keypair,
        )

        # Should detect fork
        with pytest.raises(ForkDetected):
            verifier.verify_head(agent_id, entry2)

    def test_fork_detection_sequence_behind(self):
        """Fork detected when claimed sequence is behind known."""
        from sigaid.models.state import StateEntry, ActionType
        from sigaid.state.verification import ChainVerifier
        from sigaid.exceptions import ForkDetected

        keypair = KeyPair.generate()
        agent_id = str(keypair.to_agent_id())

        verifier = ChainVerifier()

        # Create two entries
        entry0 = StateEntry.create(
            agent_id=agent_id,
            sequence=0,
            prev_hash=GENESIS_PREV_HASH,
            action_type=ActionType.ATTESTATION,
            action_summary="Genesis",
            action_data=None,
            keypair=keypair,
        )

        entry1 = StateEntry.create(
            agent_id=agent_id,
            sequence=1,
            prev_hash=entry0.entry_hash,
            action_type=ActionType.TRANSACTION,
            action_summary="Transaction",
            action_data=None,
            keypair=keypair,
        )

        # Record entry1 (sequence 1)
        verifier.record_head(agent_id, entry1)

        # Now try to claim entry0 (sequence 0) as head - should fail
        with pytest.raises(ForkDetected):
            verifier.verify_head(agent_id, entry0)
