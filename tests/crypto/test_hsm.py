"""Tests for HSM abstraction layer."""

import pytest

from sigaid.crypto.hsm import (
    KeyProvider,
    KeyInfo,
    SoftwareKeyProvider,
    get_key_provider,
    set_key_provider,
)
from sigaid.crypto.hsm.interface import KeyType, KeyUsage
from sigaid.crypto.hsm.software import _SoftwareKey


class TestSoftwareKeyProvider:
    """Tests for SoftwareKeyProvider."""

    @pytest.fixture
    def provider(self):
        """Create a fresh provider for each test."""
        return SoftwareKeyProvider()

    def test_provider_name(self, provider):
        """Test provider name."""
        assert provider.provider_name == "Software Key Provider"

    def test_not_hardware_backed(self, provider):
        """Test is_hardware_backed returns False."""
        assert provider.is_hardware_backed is False

    def test_generate_key(self, provider):
        """Test generating a new key."""
        key_id = provider.generate_key()

        assert key_id is not None
        assert key_id.startswith("sw_")
        assert len(key_id) > 3

    def test_generate_key_with_label(self, provider):
        """Test generating key with custom label."""
        key_id = provider.generate_key(label="my-agent-key")
        info = provider.get_key_info(key_id)

        assert info.label == "my-agent-key"

    def test_generate_key_non_exportable(self, provider):
        """Test generating non-exportable key."""
        key_id = provider.generate_key(exportable=False)
        info = provider.get_key_info(key_id)

        assert info.exportable is False

    def test_generate_unsupported_key_type(self, provider):
        """Test generating unsupported key type raises."""
        with pytest.raises(ValueError, match="Unsupported key type"):
            provider.generate_key(key_type="rsa")  # type: ignore

    def test_import_key(self, provider):
        """Test importing an existing key."""
        # Generate a key and export it
        original_id = provider.generate_key()
        private_bytes = provider.export_private_key(original_id)

        # Import the key
        imported_id = provider.import_key(private_bytes)

        # Public keys should match
        assert provider.get_public_key(original_id) == provider.get_public_key(imported_id)

    def test_import_invalid_key_length(self, provider):
        """Test importing key with wrong length fails."""
        with pytest.raises(ValueError, match="32 bytes"):
            provider.import_key(b"too short")

    def test_export_private_key(self, provider):
        """Test exporting private key."""
        key_id = provider.generate_key()
        private_bytes = provider.export_private_key(key_id)

        assert len(private_bytes) == 32  # Ed25519 private key size

    def test_export_non_exportable_key_fails(self, provider):
        """Test exporting non-exportable key fails."""
        key_id = provider.generate_key(exportable=False)

        with pytest.raises(PermissionError):
            provider.export_private_key(key_id)

    def test_export_nonexistent_key_fails(self, provider):
        """Test exporting nonexistent key fails."""
        with pytest.raises(KeyError):
            provider.export_private_key("sw_nonexistent")

    def test_get_public_key(self, provider):
        """Test getting public key bytes."""
        key_id = provider.generate_key()
        public_bytes = provider.get_public_key(key_id)

        assert len(public_bytes) == 32  # Ed25519 public key size

    def test_get_key_info(self, provider):
        """Test getting key info."""
        key_id = provider.generate_key(
            key_type=KeyType.ED25519,
            usage=KeyUsage.SIGNING,
            label="test-key",
        )

        info = provider.get_key_info(key_id)

        assert isinstance(info, KeyInfo)
        assert info.key_id == key_id
        assert info.key_type == KeyType.ED25519
        assert info.usage == KeyUsage.SIGNING
        assert info.label == "test-key"
        assert info.hardware_backed is False
        assert len(info.public_key) == 32

    def test_list_keys_empty(self, provider):
        """Test listing keys when empty."""
        keys = provider.list_keys()
        assert keys == []

    def test_list_keys_multiple(self, provider):
        """Test listing multiple keys."""
        id1 = provider.generate_key(label="key1")
        id2 = provider.generate_key(label="key2")
        id3 = provider.generate_key(label="key3")

        keys = provider.list_keys()

        assert len(keys) == 3
        key_ids = {k.key_id for k in keys}
        assert id1 in key_ids
        assert id2 in key_ids
        assert id3 in key_ids

    def test_delete_key(self, provider):
        """Test deleting a key."""
        key_id = provider.generate_key()

        result = provider.delete_key(key_id)

        assert result is True
        with pytest.raises(KeyError):
            provider.get_key_info(key_id)

    def test_delete_nonexistent_key(self, provider):
        """Test deleting nonexistent key returns False."""
        result = provider.delete_key("sw_nonexistent")
        assert result is False

    def test_sign_basic(self, provider):
        """Test signing data."""
        key_id = provider.generate_key()
        data = b"data to sign"

        signature = provider.sign(key_id, data)

        assert len(signature) == 64  # Ed25519 signature size

    def test_sign_with_domain(self, provider):
        """Test signing with domain separation."""
        key_id = provider.generate_key()
        data = b"data"

        sig1 = provider.sign(key_id, data, domain="domain1")
        sig2 = provider.sign(key_id, data, domain="domain2")
        sig3 = provider.sign(key_id, data, domain="")

        # Different domains should produce different signatures
        assert sig1 != sig2
        assert sig1 != sig3
        assert sig2 != sig3

    def test_sign_wrong_usage_fails(self, provider):
        """Test signing with wrong key usage fails."""
        key_id = provider.generate_key(usage=KeyUsage.ENCRYPTION)

        with pytest.raises(ValueError, match="not for signing"):
            provider.sign(key_id, b"data")

    def test_verify_valid_signature(self, provider):
        """Test verifying valid signature."""
        key_id = provider.generate_key()
        data = b"verified data"

        signature = provider.sign(key_id, data)
        result = provider.verify(key_id, signature, data)

        assert result is True

    def test_verify_with_domain(self, provider):
        """Test verifying with domain separation."""
        key_id = provider.generate_key()
        data = b"data"
        domain = "test.domain.v1"

        signature = provider.sign(key_id, data, domain=domain)
        result = provider.verify(key_id, signature, data, domain=domain)

        assert result is True

    def test_verify_wrong_domain_fails(self, provider):
        """Test verifying with wrong domain fails."""
        key_id = provider.generate_key()
        data = b"data"

        signature = provider.sign(key_id, data, domain="correct")
        result = provider.verify(key_id, signature, data, domain="wrong")

        assert result is False

    def test_verify_tampered_data_fails(self, provider):
        """Test verifying tampered data fails."""
        key_id = provider.generate_key()
        data = b"original data"

        signature = provider.sign(key_id, data)
        result = provider.verify(key_id, signature, b"tampered data")

        assert result is False

    def test_verify_invalid_signature_fails(self, provider):
        """Test verifying invalid signature fails."""
        key_id = provider.generate_key()
        data = b"data"

        result = provider.verify(key_id, b"x" * 64, data)

        assert result is False

    def test_verify_with_public_key(self, provider):
        """Test verifying with raw public key bytes."""
        key_id = provider.generate_key()
        public_key = provider.get_public_key(key_id)
        data = b"test data"
        domain = "test.v1"

        signature = provider.sign(key_id, data, domain=domain)
        result = provider.verify_with_public_key(public_key, signature, data, domain=domain)

        assert result is True


class TestGlobalKeyProvider:
    """Tests for global key provider management."""

    def test_get_default_provider(self):
        """Test getting default provider."""
        # Reset global state
        import sigaid.crypto.hsm as hsm_module
        hsm_module._key_provider = None

        provider = get_key_provider()

        assert isinstance(provider, SoftwareKeyProvider)

    def test_set_custom_provider(self):
        """Test setting custom provider."""
        custom_provider = SoftwareKeyProvider()
        set_key_provider(custom_provider)

        assert get_key_provider() is custom_provider

    def test_provider_persists(self):
        """Test provider instance persists."""
        provider1 = get_key_provider()
        provider2 = get_key_provider()

        assert provider1 is provider2


class TestSoftwareKey:
    """Tests for internal _SoftwareKey class."""

    def test_get_private_key(self):
        """Test reconstructing private key."""
        from sigaid.crypto.secure_memory import SecureBytes
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        # Create a valid Ed25519 private key
        original = Ed25519PrivateKey.generate()
        from cryptography.hazmat.primitives import serialization
        private_bytes = original.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )

        secure = SecureBytes(private_bytes, lock_memory=False)
        from datetime import datetime, timezone

        key = _SoftwareKey(
            key_id="test",
            key_type=KeyType.ED25519,
            usage=KeyUsage.SIGNING,
            secure_private=secure,
            created_at=datetime.now(timezone.utc),
        )

        reconstructed = key.get_private_key()
        assert isinstance(reconstructed, Ed25519PrivateKey)

    def test_get_public_key_bytes_cached(self):
        """Test public key bytes are cached."""
        from sigaid.crypto.secure_memory import SecureBytes
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives import serialization
        from datetime import datetime, timezone

        original = Ed25519PrivateKey.generate()
        private_bytes = original.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )

        secure = SecureBytes(private_bytes, lock_memory=False)

        key = _SoftwareKey(
            key_id="test",
            key_type=KeyType.ED25519,
            usage=KeyUsage.SIGNING,
            secure_private=secure,
            created_at=datetime.now(timezone.utc),
        )

        # First call computes
        pub1 = key.get_public_key_bytes()
        # Second call uses cache
        pub2 = key.get_public_key_bytes()

        assert pub1 == pub2
        assert key._public_key_bytes is not None
