"""Tests for post-quantum hybrid signatures."""

import pytest

from sigaid.crypto.hybrid import (
    HybridKeyPair,
    HybridPublicKey,
    PostQuantumNotAvailableError,
    HYBRID_VERSION,
    ED25519_SIGNATURE_SIZE,
    is_hybrid_signature,
    verify_hybrid_signature,
    _check_pqcrypto_available,
    _check_liboqs_available,
)


# Check if PQ library is available for full tests
PQ_AVAILABLE = _check_pqcrypto_available() or _check_liboqs_available()


class TestHybridPublicKey:
    """Tests for HybridPublicKey class."""

    def test_to_bytes_from_bytes_roundtrip(self):
        """Test serialization roundtrip."""
        ed25519_pub = b"a" * 32
        dilithium_pub = b"b" * 1952

        original = HybridPublicKey(
            ed25519_public=ed25519_pub,
            dilithium_public=dilithium_pub,
        )

        serialized = original.to_bytes()
        restored = HybridPublicKey.from_bytes(serialized)

        assert restored.ed25519_public == ed25519_pub
        assert restored.dilithium_public == dilithium_pub

    def test_to_bytes_length(self):
        """Test serialized length."""
        pub = HybridPublicKey(
            ed25519_public=b"a" * 32,
            dilithium_public=b"b" * 1952,
        )

        serialized = pub.to_bytes()
        assert len(serialized) == 32 + 1952

    def test_from_bytes_wrong_length(self):
        """Test from_bytes with wrong length fails."""
        with pytest.raises(ValueError, match="Expected"):
            HybridPublicKey.from_bytes(b"too short")


@pytest.mark.skipif(not PQ_AVAILABLE, reason="Post-quantum library not available")
class TestHybridKeyPairWithPQ:
    """Tests for HybridKeyPair (requires PQ library)."""

    @pytest.fixture
    def keypair(self):
        """Create a test keypair."""
        return HybridKeyPair.generate()

    def test_generate(self):
        """Test generating hybrid keypair."""
        keypair = HybridKeyPair.generate()

        assert keypair is not None
        assert keypair.public_key is not None
        assert len(keypair.ed25519_public_bytes) == 32

    def test_public_key_structure(self, keypair):
        """Test public key has both components."""
        pub = keypair.public_key

        assert isinstance(pub, HybridPublicKey)
        assert len(pub.ed25519_public) == 32
        assert len(pub.dilithium_public) == 1952

    def test_sign_produces_hybrid_signature(self, keypair):
        """Test signing produces hybrid signature."""
        message = b"test message"
        signature = keypair.sign(message)

        # Should have version + ed25519 + dilithium
        assert signature[0] == HYBRID_VERSION
        assert len(signature) > ED25519_SIGNATURE_SIZE + 1

    def test_sign_verify_roundtrip(self, keypair):
        """Test sign/verify cycle."""
        message = b"important message"

        signature = keypair.sign(message)
        result = keypair.verify(signature, message)

        assert result is True

    def test_sign_verify_with_domain(self, keypair):
        """Test sign/verify with domain separation."""
        message = b"data"
        domain = "sigaid.test.v1"

        signature = keypair.sign(message, domain=domain)
        result = keypair.verify(signature, message, domain=domain)

        assert result is True

    def test_verify_wrong_domain_fails(self, keypair):
        """Test verification with wrong domain fails."""
        message = b"data"

        signature = keypair.sign(message, domain="correct")
        result = keypair.verify(signature, message, domain="wrong")

        assert result is False

    def test_verify_tampered_message_fails(self, keypair):
        """Test verification of tampered message fails."""
        signature = keypair.sign(b"original")
        result = keypair.verify(signature, b"tampered")

        assert result is False

    def test_verify_tampered_signature_fails(self, keypair):
        """Test verification of tampered signature fails."""
        message = b"message"
        signature = bytearray(keypair.sign(message))

        # Tamper with Ed25519 portion
        signature[10] ^= 0xFF

        result = keypair.verify(bytes(signature), message)
        assert result is False

    def test_sign_ed25519_only(self, keypair):
        """Test Ed25519-only signing."""
        message = b"ed25519 only"
        signature = keypair.sign_ed25519_only(message)

        assert len(signature) == 64  # Pure Ed25519 signature

    def test_verify_ed25519_only_hybrid_sig(self, keypair):
        """Test Ed25519-only verification of hybrid signature."""
        message = b"test"
        hybrid_sig = keypair.sign(message)

        result = keypair.verify_ed25519_only(hybrid_sig, message)
        assert result is True

    def test_verify_ed25519_only_raw_sig(self, keypair):
        """Test Ed25519-only verification of raw Ed25519 signature."""
        message = b"test"
        raw_sig = keypair.sign_ed25519_only(message)

        result = keypair.verify_ed25519_only(raw_sig, message)
        assert result is True

    def test_from_ed25519_only(self):
        """Test creating hybrid from existing Ed25519 key."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        ed25519_key = Ed25519PrivateKey.generate()
        hybrid = HybridKeyPair.from_ed25519_only(ed25519_key)

        assert hybrid is not None

        # Should be able to sign and verify
        message = b"test"
        sig = hybrid.sign(message)
        assert hybrid.verify(sig, message)


class TestHybridKeyPairWithoutPQ:
    """Tests that work without PQ library."""

    @pytest.mark.skipif(PQ_AVAILABLE, reason="Test requires PQ library to NOT be available")
    def test_generate_raises_without_pq(self):
        """Test generating keypair raises without PQ library."""
        with pytest.raises(PostQuantumNotAvailableError):
            HybridKeyPair.generate()


class TestIsHybridSignature:
    """Tests for is_hybrid_signature function."""

    def test_identifies_hybrid_signature(self):
        """Test identifies hybrid signature."""
        # Create fake hybrid signature
        sig = bytes([HYBRID_VERSION]) + b"x" * (ED25519_SIGNATURE_SIZE + 100)
        assert is_hybrid_signature(sig) is True

    def test_rejects_pure_ed25519(self):
        """Test rejects pure Ed25519 signature."""
        sig = b"x" * 64
        assert is_hybrid_signature(sig) is False

    def test_rejects_wrong_version(self):
        """Test rejects wrong version."""
        sig = bytes([99]) + b"x" * (ED25519_SIGNATURE_SIZE + 100)
        assert is_hybrid_signature(sig) is False

    def test_rejects_empty(self):
        """Test rejects empty data."""
        assert is_hybrid_signature(b"") is False

    def test_rejects_none(self):
        """Test rejects None (as falsy)."""
        assert is_hybrid_signature(None) is False  # type: ignore


@pytest.mark.skipif(not PQ_AVAILABLE, reason="Post-quantum library not available")
class TestVerifyHybridSignature:
    """Tests for verify_hybrid_signature function."""

    @pytest.fixture
    def keypair(self):
        """Create a test keypair."""
        return HybridKeyPair.generate()

    def test_verify_valid_signature(self, keypair):
        """Test verifying valid signature."""
        message = b"test message"
        signature = keypair.sign(message)
        public_key = keypair.public_key

        result = verify_hybrid_signature(public_key, signature, message)
        assert result is True

    def test_verify_with_domain(self, keypair):
        """Test verifying with domain."""
        message = b"data"
        domain = "test.v1"
        signature = keypair.sign(message, domain=domain)

        result = verify_hybrid_signature(
            keypair.public_key, signature, message, domain=domain
        )
        assert result is True

    def test_verify_tampered_fails(self, keypair):
        """Test verifying tampered signature fails."""
        message = b"original"
        signature = keypair.sign(message)

        result = verify_hybrid_signature(
            keypair.public_key, signature, b"tampered"
        )
        assert result is False

    def test_verify_wrong_key_fails(self, keypair):
        """Test verifying with wrong key fails."""
        message = b"test"
        signature = keypair.sign(message)

        # Generate different keypair
        other_keypair = HybridKeyPair.generate()

        result = verify_hybrid_signature(
            other_keypair.public_key, signature, message
        )
        assert result is False
