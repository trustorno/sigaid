"""Ed25519 key generation and management."""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

from sigaid.constants import (
    ED25519_PRIVATE_KEY_SIZE,
    ED25519_PUBLIC_KEY_SIZE,
    KEYFILE_ALGORITHM,
    KEYFILE_VERSION,
    SCRYPT_N,
    SCRYPT_P,
    SCRYPT_R,
)
from sigaid.exceptions import CryptoError, InvalidKey, KeyDerivationError

if TYPE_CHECKING:
    from sigaid.identity.agent_id import AgentID


class KeyPair:
    """
    Ed25519 keypair for agent identity.
    
    This class manages cryptographic keys for agent identity, providing
    methods for key generation, signing, and secure storage.
    
    Example:
        # Generate new keypair
        keypair = KeyPair.generate()
        
        # Sign a message
        signature = keypair.sign(b"hello world")
        
        # Get agent ID
        agent_id = keypair.to_agent_id()
        
        # Save to encrypted file
        keypair.to_encrypted_file(Path("agent.key"), "password123")
        
        # Load from encrypted file
        keypair = KeyPair.from_encrypted_file(Path("agent.key"), "password123")
    """

    def __init__(self, private_key: Ed25519PrivateKey):
        """
        Initialize KeyPair from Ed25519 private key.
        
        Args:
            private_key: Ed25519 private key instance
        """
        self._private_key = private_key
        self._public_key = private_key.public_key()

    @classmethod
    def generate(cls) -> KeyPair:
        """
        Generate new random keypair using cryptographically secure randomness.
        
        Returns:
            New KeyPair instance with fresh keys
        """
        private_key = Ed25519PrivateKey.generate()
        return cls(private_key)

    @classmethod
    def from_seed(cls, seed: bytes) -> KeyPair:
        """
        Derive keypair from 32-byte seed (deterministic).
        
        This allows recreating the same keypair from a seed value.
        
        Args:
            seed: 32-byte seed value
            
        Returns:
            KeyPair derived from seed
            
        Raises:
            InvalidKey: If seed is not 32 bytes
        """
        if len(seed) != ED25519_PRIVATE_KEY_SIZE:
            raise InvalidKey(f"Seed must be {ED25519_PRIVATE_KEY_SIZE} bytes, got {len(seed)}")
        private_key = Ed25519PrivateKey.from_private_bytes(seed)
        return cls(private_key)

    @classmethod
    def from_private_bytes(cls, data: bytes) -> KeyPair:
        """
        Load keypair from raw private key bytes.
        
        Args:
            data: 32-byte raw private key
            
        Returns:
            KeyPair instance
            
        Raises:
            InvalidKey: If data is invalid
        """
        if len(data) != ED25519_PRIVATE_KEY_SIZE:
            raise InvalidKey(f"Private key must be {ED25519_PRIVATE_KEY_SIZE} bytes, got {len(data)}")
        try:
            private_key = Ed25519PrivateKey.from_private_bytes(data)
            return cls(private_key)
        except Exception as e:
            raise InvalidKey(f"Invalid private key bytes: {e}") from e

    def sign(self, message: bytes) -> bytes:
        """
        Sign message using Ed25519.
        
        Args:
            message: Message bytes to sign
            
        Returns:
            64-byte signature
        """
        return self._private_key.sign(message)

    def sign_with_domain(self, message: bytes, domain: str) -> bytes:
        """
        Sign message with domain separation.
        
        Domain separation prevents cross-protocol attacks by ensuring
        signatures from one context cannot be replayed in another.
        
        Args:
            message: Message bytes to sign
            domain: Domain string (e.g., "sigaid.identity.v1")
            
        Returns:
            64-byte signature
        """
        domain_bytes = domain.encode("utf-8")
        tagged_message = (
            len(domain_bytes).to_bytes(2, "big") + domain_bytes + message
        )
        return self._private_key.sign(tagged_message)

    def verify(self, signature: bytes, message: bytes) -> bool:
        """
        Verify signature against message.
        
        Args:
            signature: 64-byte signature to verify
            message: Original message bytes
            
        Returns:
            True if valid, False otherwise
        """
        try:
            self._public_key.verify(signature, message)
            return True
        except Exception:
            return False

    def verify_with_domain(self, signature: bytes, message: bytes, domain: str) -> bool:
        """
        Verify domain-separated signature.
        
        Args:
            signature: 64-byte signature to verify
            message: Original message bytes
            domain: Domain string used during signing
            
        Returns:
            True if valid, False otherwise
        """
        domain_bytes = domain.encode("utf-8")
        tagged_message = (
            len(domain_bytes).to_bytes(2, "big") + domain_bytes + message
        )
        try:
            self._public_key.verify(signature, tagged_message)
            return True
        except Exception:
            return False

    def public_key_bytes(self) -> bytes:
        """
        Get raw public key bytes (32 bytes).
        
        Returns:
            32-byte public key
        """
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def private_key_bytes(self) -> bytes:
        """
        Get raw private key bytes (32 bytes).
        
        WARNING: Handle with care! This exposes the secret key.
        
        Returns:
            32-byte private key
        """
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def derive_session_key(self, session_id: bytes, purpose: str = "session") -> bytes:
        """
        Derive a session-specific key using HKDF.
        
        Args:
            session_id: Unique session identifier
            purpose: Key purpose string for domain separation
            
        Returns:
            32-byte derived key
        """
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=session_id,
            info=purpose.encode("utf-8"),
        )
        return hkdf.derive(self.private_key_bytes())

    def to_agent_id(self) -> AgentID:
        """
        Derive AgentID from public key.
        
        Returns:
            AgentID instance
        """
        from sigaid.identity.agent_id import AgentID
        return AgentID.from_public_key(self.public_key_bytes())

    def to_encrypted_file(self, path: Path, password: str) -> None:
        """
        Save keypair to encrypted file.
        
        Uses scrypt for key derivation and ChaCha20-Poly1305 for encryption.
        
        Args:
            path: File path to save to
            password: Password for encryption
        """
        # Generate salt and derive encryption key
        salt = secrets.token_bytes(32)
        kdf = Scrypt(
            salt=salt,
            length=32,
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
        )
        encryption_key = kdf.derive(password.encode("utf-8"))

        # Encrypt private key
        nonce = secrets.token_bytes(12)  # ChaCha20-Poly1305 uses 12-byte nonce
        cipher = ChaCha20Poly1305(encryption_key)
        ciphertext = cipher.encrypt(nonce, self.private_key_bytes(), None)

        # Build keyfile
        keyfile = {
            "version": KEYFILE_VERSION,
            "algorithm": KEYFILE_ALGORITHM,
            "scrypt_params": {
                "n": SCRYPT_N,
                "r": SCRYPT_R,
                "p": SCRYPT_P,
            },
            "salt": salt.hex(),
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
        }

        # Write atomically
        temp_path = path.with_suffix(".tmp")
        with open(temp_path, "w") as f:
            json.dump(keyfile, f, indent=2)
        temp_path.rename(path)

    @classmethod
    def from_encrypted_file(cls, path: Path, password: str) -> KeyPair:
        """
        Load keypair from encrypted file.
        
        Args:
            path: File path to load from
            password: Password for decryption
            
        Returns:
            KeyPair instance
            
        Raises:
            CryptoError: If decryption fails
            InvalidKey: If key format is invalid
        """
        with open(path) as f:
            keyfile = json.load(f)

        if keyfile.get("version") != KEYFILE_VERSION:
            raise InvalidKey(f"Unsupported keyfile version: {keyfile.get('version')}")

        if keyfile.get("algorithm") != KEYFILE_ALGORITHM:
            raise InvalidKey(f"Unsupported algorithm: {keyfile.get('algorithm')}")

        # Derive decryption key
        params = keyfile["scrypt_params"]
        salt = bytes.fromhex(keyfile["salt"])
        kdf = Scrypt(
            salt=salt,
            length=32,
            n=params["n"],
            r=params["r"],
            p=params["p"],
        )
        
        try:
            decryption_key = kdf.derive(password.encode("utf-8"))
        except Exception as e:
            raise KeyDerivationError(f"Failed to derive key: {e}") from e

        # Decrypt private key
        nonce = bytes.fromhex(keyfile["nonce"])
        ciphertext = bytes.fromhex(keyfile["ciphertext"])
        cipher = ChaCha20Poly1305(decryption_key)
        
        try:
            private_key_bytes = cipher.decrypt(nonce, ciphertext, None)
        except Exception as e:
            raise CryptoError(f"Decryption failed (wrong password?): {e}") from e

        return cls.from_private_bytes(private_key_bytes)

    def __repr__(self) -> str:
        return f"KeyPair(agent_id={self.to_agent_id()})"


def verify_signature_with_public_key(
    public_key: bytes, signature: bytes, message: bytes
) -> bool:
    """
    Verify signature using raw public key bytes.
    
    Args:
        public_key: 32-byte Ed25519 public key
        signature: 64-byte signature
        message: Original message
        
    Returns:
        True if valid, False otherwise
    """
    if len(public_key) != ED25519_PUBLIC_KEY_SIZE:
        return False
    try:
        pk = Ed25519PublicKey.from_public_bytes(public_key)
        pk.verify(signature, message)
        return True
    except Exception:
        return False


def verify_signature_with_public_key_and_domain(
    public_key: bytes, signature: bytes, message: bytes, domain: str
) -> bool:
    """
    Verify domain-separated signature using raw public key bytes.
    
    Args:
        public_key: 32-byte Ed25519 public key
        signature: 64-byte signature
        message: Original message
        domain: Domain string used during signing
        
    Returns:
        True if valid, False otherwise
    """
    if len(public_key) != ED25519_PUBLIC_KEY_SIZE:
        return False
    domain_bytes = domain.encode("utf-8")
    tagged_message = (
        len(domain_bytes).to_bytes(2, "big") + domain_bytes + message
    )
    try:
        pk = Ed25519PublicKey.from_public_bytes(public_key)
        pk.verify(signature, tagged_message)
        return True
    except Exception:
        return False
