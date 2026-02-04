"""Tests for state data encryption."""

import json
import pytest

from sigaid.crypto.keys import KeyPair
from sigaid.crypto.state_encryption import (
    StateEncryptor,
    StateEncryptionHelper,
    create_encryptor,
    ENCRYPTION_VERSION,
)
from sigaid.exceptions import CryptoError


class TestStateEncryptor:
    """Tests for StateEncryptor class."""

    @pytest.fixture
    def keypair(self):
        """Create a test keypair."""
        kp = KeyPair.generate()
        yield kp
        kp.clear()

    @pytest.fixture
    def encryptor(self, keypair):
        """Create a test encryptor."""
        return StateEncryptor(keypair)

    def test_encrypt_decrypt_roundtrip(self, encryptor):
        """Test basic encrypt/decrypt cycle."""
        plaintext = b"sensitive data to encrypt"

        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_empty_data(self, encryptor):
        """Test encrypting empty data."""
        encrypted = encryptor.encrypt(b"")
        assert encrypted == b""

        decrypted = encryptor.decrypt(encrypted)
        assert decrypted == b""

    def test_encrypted_format(self, encryptor):
        """Test encrypted data has correct format."""
        plaintext = b"test data"
        encrypted = encryptor.encrypt(plaintext)

        # Should have version byte + nonce + ciphertext
        assert len(encrypted) >= 1 + 12 + 16  # version + nonce + min ciphertext
        assert encrypted[0] == ENCRYPTION_VERSION

    def test_different_plaintexts_different_ciphertexts(self, encryptor):
        """Test different plaintexts produce different ciphertexts."""
        e1 = encryptor.encrypt(b"data one")
        e2 = encryptor.encrypt(b"data two")

        assert e1 != e2

    def test_same_plaintext_different_ciphertexts(self, encryptor):
        """Test same plaintext produces different ciphertexts (random nonce)."""
        plaintext = b"same data"
        e1 = encryptor.encrypt(plaintext)
        e2 = encryptor.encrypt(plaintext)

        # Ciphertexts should differ due to random nonces
        assert e1 != e2

        # But both should decrypt to same plaintext
        assert encryptor.decrypt(e1) == plaintext
        assert encryptor.decrypt(e2) == plaintext

    def test_decrypt_wrong_key_fails(self, keypair):
        """Test decryption with wrong key fails."""
        encryptor1 = StateEncryptor(keypair)
        keypair2 = KeyPair.generate()
        encryptor2 = StateEncryptor(keypair2)

        encrypted = encryptor1.encrypt(b"secret")

        with pytest.raises(CryptoError, match="Decryption failed"):
            encryptor2.decrypt(encrypted)

        keypair2.clear()

    def test_decrypt_tampered_data_fails(self, encryptor):
        """Test decryption of tampered data fails."""
        encrypted = bytearray(encryptor.encrypt(b"original"))

        # Tamper with ciphertext
        encrypted[-1] ^= 0xFF

        with pytest.raises(CryptoError, match="Decryption failed"):
            encryptor.decrypt(bytes(encrypted))

    def test_decrypt_too_short_fails(self, encryptor):
        """Test decryption of too-short data fails."""
        with pytest.raises(CryptoError, match="too short"):
            encryptor.decrypt(b"short")

    def test_decrypt_wrong_version_fails(self, encryptor):
        """Test decryption with wrong version fails."""
        encrypted = bytearray(encryptor.encrypt(b"data"))
        encrypted[0] = 99  # Invalid version

        with pytest.raises(CryptoError, match="Unsupported encryption version"):
            encryptor.decrypt(bytes(encrypted))

    def test_encryptor_with_salt(self, keypair):
        """Test encryptor with salt produces different keys."""
        enc1 = StateEncryptor(keypair, salt=b"salt1")
        enc2 = StateEncryptor(keypair, salt=b"salt2")

        # Different salts should produce different encryption keys
        encrypted1 = enc1.encrypt(b"test")
        encrypted2 = enc2.encrypt(b"test")

        # enc1 can decrypt its own data
        assert enc1.decrypt(encrypted1) == b"test"

        # enc2 cannot decrypt enc1's data
        with pytest.raises(CryptoError):
            enc2.decrypt(encrypted1)

    def test_encryptor_same_salt_same_key(self, keypair):
        """Test same salt produces same key."""
        enc1 = StateEncryptor(keypair, salt=b"same")
        enc2 = StateEncryptor(keypair, salt=b"same")

        encrypted = enc1.encrypt(b"data")
        decrypted = enc2.decrypt(encrypted)

        assert decrypted == b"data"


class TestStateEncryptionHelper:
    """Tests for StateEncryptionHelper class."""

    @pytest.fixture
    def keypair(self):
        """Create a test keypair."""
        kp = KeyPair.generate()
        yield kp
        kp.clear()

    @pytest.fixture
    def helper(self, keypair):
        """Create a test helper."""
        return StateEncryptionHelper(keypair)

    def test_encrypt_decrypt_summary(self, helper):
        """Test encrypting/decrypting action summary."""
        summary = "User booked hotel room at Hilton"

        encrypted = helper.encrypt_summary(summary)
        decrypted = helper.decrypt_summary(encrypted)

        assert decrypted == summary

    def test_encrypt_decrypt_action_data(self, helper):
        """Test encrypting/decrypting action data dict."""
        data = {
            "hotel": "Hilton",
            "room_type": "suite",
            "price": 299.99,
            "guest_name": "John Doe",
        }

        encrypted = helper.encrypt_action_data(data)
        decrypted = helper.decrypt_action_data(encrypted)

        assert decrypted == data

    def test_is_encrypted_true(self, helper):
        """Test is_encrypted returns True for encrypted data."""
        encrypted = helper.encrypt_summary("test")
        assert StateEncryptionHelper.is_encrypted(encrypted) is True

    def test_is_encrypted_false_plain_data(self):
        """Test is_encrypted returns False for plain data."""
        assert StateEncryptionHelper.is_encrypted(b"plain text") is False

    def test_is_encrypted_false_empty(self):
        """Test is_encrypted returns False for empty data."""
        assert StateEncryptionHelper.is_encrypted(b"") is False
        assert StateEncryptionHelper.is_encrypted(None) is False

    def test_encrypt_unicode_summary(self, helper):
        """Test encrypting Unicode summary."""
        summary = "Hotel buchen: Hilton Zurich"

        encrypted = helper.encrypt_summary(summary)
        decrypted = helper.decrypt_summary(encrypted)

        assert decrypted == summary

    def test_encrypt_complex_action_data(self, helper):
        """Test encrypting complex nested data."""
        data = {
            "items": [
                {"name": "item1", "qty": 2},
                {"name": "item2", "qty": 1},
            ],
            "metadata": {
                "timestamp": "2024-01-01T00:00:00Z",
                "source": "api",
            },
        }

        encrypted = helper.encrypt_action_data(data)
        decrypted = helper.decrypt_action_data(encrypted)

        assert decrypted == data

    def test_helper_with_salt(self, keypair):
        """Test helper with salt parameter."""
        helper = StateEncryptionHelper(keypair, salt=b"agent123")

        summary = "Test summary"
        encrypted = helper.encrypt_summary(summary)
        decrypted = helper.decrypt_summary(encrypted)

        assert decrypted == summary


class TestCreateEncryptor:
    """Tests for create_encryptor factory function."""

    def test_creates_helper(self):
        """Test creates StateEncryptionHelper instance."""
        keypair = KeyPair.generate()
        helper = create_encryptor(keypair)

        assert isinstance(helper, StateEncryptionHelper)

        keypair.clear()

    def test_creates_helper_with_salt(self):
        """Test creates helper with salt."""
        keypair = KeyPair.generate()
        helper = create_encryptor(keypair, salt=b"mysalt")

        # Verify it works
        encrypted = helper.encrypt_summary("test")
        decrypted = helper.decrypt_summary(encrypted)
        assert decrypted == "test"

        keypair.clear()
