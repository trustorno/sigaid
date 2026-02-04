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


class TestKeyPairSecureMemory:
    """Tests for KeyPair secure memory handling."""

    def test_clear_method(self):
        """Test clear() method zeros key material."""
        keypair = KeyPair.generate()
        assert not keypair._cleared

        keypair.clear()

        assert keypair._cleared
        assert keypair._secure_seed is None

    def test_clear_multiple_times_safe(self):
        """Test clear() can be called multiple times safely."""
        keypair = KeyPair.generate()
        keypair.clear()
        keypair.clear()  # Should not raise
        assert keypair._cleared

    def test_sign_after_clear_raises(self):
        """Test signing after clear raises CryptoError."""
        keypair = KeyPair.generate()
        keypair.clear()

        with pytest.raises(CryptoError, match="cleared"):
            keypair.sign(b"message")

    def test_private_key_bytes_after_clear_raises(self):
        """Test getting private key bytes after clear raises."""
        keypair = KeyPair.generate()
        keypair.clear()

        with pytest.raises(CryptoError, match="cleared"):
            keypair.private_key_bytes()

    def test_to_encrypted_file_after_clear_raises(self):
        """Test encrypting to file after clear raises."""
        keypair = KeyPair.generate()
        keypair.clear()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test.key"
            with pytest.raises(CryptoError, match="cleared"):
                keypair.to_encrypted_file(path, "password")

    def test_context_manager(self):
        """Test KeyPair as context manager."""
        with KeyPair.generate() as keypair:
            # Can use keypair inside context
            assert len(keypair.public_key_bytes()) == 32
            assert not keypair._cleared

        # Automatically cleared after exiting
        assert keypair._cleared

    def test_context_manager_clears_on_exception(self):
        """Test context manager clears even on exception."""
        keypair = None
        try:
            with KeyPair.generate() as kp:
                keypair = kp
                raise ValueError("test error")
        except ValueError:
            pass

        assert keypair._cleared

    def test_destructor_clears(self):
        """Test __del__ clears key material."""
        keypair = KeyPair.generate()
        assert not keypair._cleared

        keypair.__del__()

        assert keypair._cleared

    def test_repr_shows_cleared_status(self):
        """Test repr shows cleared status."""
        keypair = KeyPair.generate()
        keypair.clear()

        repr_str = repr(keypair)
        assert "cleared" in repr_str

    def test_from_seed_uses_secure_memory(self):
        """Test from_seed uses secure memory."""
        seed = b"a" * 32
        keypair = KeyPair.from_seed(seed)

        # Should have secure seed storage
        assert keypair._secure_seed is not None
        assert not keypair._secure_seed.is_cleared

        keypair.clear()
        assert keypair._secure_seed is None

    def test_from_private_bytes_uses_secure_memory(self):
        """Test from_private_bytes uses secure memory."""
        seed = b"b" * 32
        keypair = KeyPair.from_private_bytes(seed)

        assert keypair._secure_seed is not None
        assert not keypair._secure_seed.is_cleared

        keypair.clear()

    def test_from_encrypted_file_uses_secure_memory(self):
        """Test loaded keypair uses secure memory."""
        with KeyPair.generate() as original:
            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir) / "test.key"
                original.to_encrypted_file(path, "password")

                loaded = KeyPair.from_encrypted_file(path, password="password")

                # Loaded keypair should have secure storage
                assert loaded._secure_seed is not None
                assert not loaded._secure_seed.is_cleared

                loaded.clear()

    def test_verify_still_works_after_clear(self):
        """Test verify works after clear (uses public key only)."""
        keypair = KeyPair.generate()
        message = b"hello"
        signature = keypair.sign(message)

        keypair.clear()

        # Verify should still work - only needs public key
        assert keypair.verify(signature, message)

    def test_public_key_bytes_works_after_clear(self):
        """Test getting public key bytes works after clear."""
        keypair = KeyPair.generate()
        pk_before = keypair.public_key_bytes()

        keypair.clear()

        pk_after = keypair.public_key_bytes()
        assert pk_before == pk_after

    def test_to_agent_id_works_after_clear(self):
        """Test to_agent_id works after clear."""
        keypair = KeyPair.generate()
        agent_id_before = keypair.to_agent_id()

        keypair.clear()

        agent_id_after = keypair.to_agent_id()
        assert str(agent_id_before) == str(agent_id_after)
