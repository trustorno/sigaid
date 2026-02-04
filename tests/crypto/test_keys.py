"""Tests for key generation and management."""

import tempfile
from pathlib import Path

import pytest

from sigaid.crypto.keys import KeyPair, public_key_from_bytes
from sigaid.exceptions import InvalidKey, CryptoError


class TestKeyPair:
    """Tests for KeyPair class."""

    def test_generate_creates_valid_keypair(self):
        """Test that generate() creates a valid keypair."""
        keypair = KeyPair.generate()
        assert keypair.public_key_bytes() is not None
        assert len(keypair.public_key_bytes()) == 32
        assert len(keypair.private_key_bytes()) == 32

    def test_generate_creates_unique_keypairs(self):
        """Test that each generate() call creates unique keypair."""
        keypair1 = KeyPair.generate()
        keypair2 = KeyPair.generate()
        assert keypair1.public_key_bytes() != keypair2.public_key_bytes()

    def test_from_seed_is_deterministic(self):
        """Test that from_seed() is deterministic."""
        seed = b"a" * 32
        keypair1 = KeyPair.from_seed(seed)
        keypair2 = KeyPair.from_seed(seed)
        assert keypair1.public_key_bytes() == keypair2.public_key_bytes()

    def test_from_seed_invalid_length(self):
        """Test that from_seed() rejects invalid seed length."""
        with pytest.raises(InvalidKey):
            KeyPair.from_seed(b"too_short")

    def test_sign_and_verify(self):
        """Test signing and verification."""
        keypair = KeyPair.generate()
        message = b"hello world"

        signature = keypair.sign(message)
        assert len(signature) == 64
        assert keypair.verify(signature, message)

    def test_sign_with_domain_separation(self):
        """Test signing with domain separation."""
        keypair = KeyPair.generate()
        message = b"hello world"
        domain = "test.domain.v1"

        signature = keypair.sign(message, domain=domain)

        # Verify with same domain succeeds
        assert keypair.verify(signature, message, domain=domain)

        # Verify with different domain fails
        assert not keypair.verify(signature, message, domain="other.domain")

        # Verify without domain fails
        assert not keypair.verify(signature, message)

    def test_from_private_bytes(self):
        """Test loading from private key bytes."""
        keypair1 = KeyPair.generate()
        private_bytes = keypair1.private_key_bytes()

        keypair2 = KeyPair.from_private_bytes(private_bytes)
        assert keypair1.public_key_bytes() == keypair2.public_key_bytes()

    def test_to_agent_id(self):
        """Test deriving agent ID from keypair."""
        keypair = KeyPair.generate()
        agent_id = keypair.to_agent_id()

        assert str(agent_id).startswith("aid_")
        # Verify we can recover public key from agent ID
        recovered_pk = agent_id.to_public_key_bytes()
        assert recovered_pk == keypair.public_key_bytes()

    def test_encrypted_file_roundtrip(self):
        """Test saving and loading encrypted keyfile."""
        keypair = KeyPair.generate()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.key"
            password = "test_password_123"

            # Save
            keypair.to_encrypted_file(path, password)
            assert path.exists()

            # Load
            loaded = KeyPair.from_encrypted_file(path, password)
            assert loaded.public_key_bytes() == keypair.public_key_bytes()

    def test_encrypted_file_wrong_password(self):
        """Test that wrong password fails."""
        keypair = KeyPair.generate()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.key"

            keypair.to_encrypted_file(path, "correct_password")

            with pytest.raises(CryptoError):
                KeyPair.from_encrypted_file(path, "wrong_password")

    def test_repr_is_safe(self):
        """Test that repr doesn't leak private key."""
        keypair = KeyPair.generate()
        repr_str = repr(keypair)

        assert "KeyPair" in repr_str
        assert "aid_" in repr_str
        # Private key should not be in repr
        private_hex = keypair.private_key_bytes().hex()
        assert private_hex not in repr_str


class TestPublicKeyFromBytes:
    """Tests for public_key_from_bytes function."""

    def test_valid_public_key(self):
        """Test loading valid public key."""
        keypair = KeyPair.generate()
        pk_bytes = keypair.public_key_bytes()

        pk = public_key_from_bytes(pk_bytes)
        assert pk is not None

    def test_invalid_length(self):
        """Test that invalid length is rejected."""
        with pytest.raises(InvalidKey):
            public_key_from_bytes(b"too_short")
