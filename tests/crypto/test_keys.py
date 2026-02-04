"""Tests for crypto/keys.py - Key generation and management."""

import pytest
from pathlib import Path

from sigaid.crypto.keys import KeyPair, verify_signature_with_public_key
from sigaid.constants import ED25519_PRIVATE_KEY_SIZE, ED25519_PUBLIC_KEY_SIZE, ED25519_SIGNATURE_SIZE
from sigaid.exceptions import InvalidKey, CryptoError


class TestKeyPair:
    """Tests for KeyPair class."""
    
    def test_generate_creates_valid_keypair(self):
        """generate() should create a valid keypair."""
        keypair = KeyPair.generate()
        
        assert len(keypair.public_key_bytes()) == ED25519_PUBLIC_KEY_SIZE
        assert len(keypair.private_key_bytes()) == ED25519_PRIVATE_KEY_SIZE
    
    def test_generate_creates_unique_keypairs(self):
        """Each generate() call should produce unique keys."""
        kp1 = KeyPair.generate()
        kp2 = KeyPair.generate()
        
        assert kp1.public_key_bytes() != kp2.public_key_bytes()
        assert kp1.private_key_bytes() != kp2.private_key_bytes()
    
    def test_from_seed_is_deterministic(self):
        """from_seed() should produce same keypair from same seed."""
        seed = b"x" * 32
        
        kp1 = KeyPair.from_seed(seed)
        kp2 = KeyPair.from_seed(seed)
        
        assert kp1.public_key_bytes() == kp2.public_key_bytes()
        assert kp1.private_key_bytes() == kp2.private_key_bytes()
    
    def test_from_seed_rejects_wrong_size(self):
        """from_seed() should reject seeds that aren't 32 bytes."""
        with pytest.raises(InvalidKey):
            KeyPair.from_seed(b"too short")
        
        with pytest.raises(InvalidKey):
            KeyPair.from_seed(b"x" * 64)
    
    def test_from_private_bytes_roundtrip(self):
        """from_private_bytes() should restore keypair."""
        original = KeyPair.generate()
        private_bytes = original.private_key_bytes()
        
        restored = KeyPair.from_private_bytes(private_bytes)
        
        assert restored.public_key_bytes() == original.public_key_bytes()
        assert restored.private_key_bytes() == original.private_key_bytes()
    
    def test_sign_produces_valid_signature(self):
        """sign() should produce a verifiable signature."""
        keypair = KeyPair.generate()
        message = b"Hello, World!"
        
        signature = keypair.sign(message)
        
        assert len(signature) == ED25519_SIGNATURE_SIZE
        assert keypair.verify(signature, message)
    
    def test_sign_with_domain_produces_unique_signature(self):
        """sign_with_domain() should produce different signature than sign()."""
        keypair = KeyPair.generate()
        message = b"Hello, World!"
        
        sig_plain = keypair.sign(message)
        sig_domain = keypair.sign_with_domain(message, "test.domain.v1")
        
        assert sig_plain != sig_domain
    
    def test_verify_with_domain_requires_same_domain(self):
        """verify_with_domain() should fail with wrong domain."""
        keypair = KeyPair.generate()
        message = b"Hello, World!"
        
        signature = keypair.sign_with_domain(message, "correct.domain")
        
        assert keypair.verify_with_domain(signature, message, "correct.domain")
        assert not keypair.verify_with_domain(signature, message, "wrong.domain")
    
    def test_verify_rejects_tampered_message(self):
        """verify() should reject signatures for tampered messages."""
        keypair = KeyPair.generate()
        message = b"Original message"
        
        signature = keypair.sign(message)
        
        assert keypair.verify(signature, message)
        assert not keypair.verify(signature, b"Tampered message")
    
    def test_verify_rejects_wrong_keypair(self):
        """verify() should reject signatures from different keypair."""
        kp1 = KeyPair.generate()
        kp2 = KeyPair.generate()
        message = b"Hello, World!"
        
        signature = kp1.sign(message)
        
        assert kp1.verify(signature, message)
        assert not kp2.verify(signature, message)
    
    def test_to_agent_id_is_deterministic(self):
        """to_agent_id() should always return same ID."""
        keypair = KeyPair.generate()
        
        id1 = keypair.to_agent_id()
        id2 = keypair.to_agent_id()
        
        assert str(id1) == str(id2)
    
    def test_encrypted_file_roundtrip(self, temp_dir):
        """Keypair should survive encryption/decryption cycle."""
        original = KeyPair.generate()
        path = temp_dir / "test.key"
        password = "test_password_123"
        
        original.to_encrypted_file(path, password)
        restored = KeyPair.from_encrypted_file(path, password)
        
        assert restored.public_key_bytes() == original.public_key_bytes()
        assert restored.private_key_bytes() == original.private_key_bytes()
    
    def test_encrypted_file_wrong_password_fails(self, temp_dir):
        """Decryption with wrong password should fail."""
        keypair = KeyPair.generate()
        path = temp_dir / "test.key"
        
        keypair.to_encrypted_file(path, "correct_password")
        
        with pytest.raises(CryptoError):
            KeyPair.from_encrypted_file(path, "wrong_password")
    
    def test_derive_session_key_is_deterministic(self):
        """derive_session_key() should be deterministic."""
        keypair = KeyPair.generate()
        session_id = b"session_12345"
        
        key1 = keypair.derive_session_key(session_id)
        key2 = keypair.derive_session_key(session_id)
        
        assert key1 == key2
        assert len(key1) == 32
    
    def test_derive_session_key_varies_with_session(self):
        """derive_session_key() should vary with session ID."""
        keypair = KeyPair.generate()
        
        key1 = keypair.derive_session_key(b"session_1")
        key2 = keypair.derive_session_key(b"session_2")
        
        assert key1 != key2


class TestVerifySignatureWithPublicKey:
    """Tests for standalone signature verification."""
    
    def test_verifies_valid_signature(self):
        """Should verify valid signature."""
        keypair = KeyPair.generate()
        message = b"Test message"
        signature = keypair.sign(message)
        
        assert verify_signature_with_public_key(
            keypair.public_key_bytes(),
            signature,
            message,
        )
    
    def test_rejects_wrong_public_key(self):
        """Should reject signature with wrong public key."""
        kp1 = KeyPair.generate()
        kp2 = KeyPair.generate()
        message = b"Test message"
        signature = kp1.sign(message)
        
        assert not verify_signature_with_public_key(
            kp2.public_key_bytes(),
            signature,
            message,
        )
    
    def test_rejects_invalid_public_key(self):
        """Should reject invalid public key bytes."""
        keypair = KeyPair.generate()
        message = b"Test message"
        signature = keypair.sign(message)
        
        assert not verify_signature_with_public_key(
            b"invalid_key",
            signature,
            message,
        )
