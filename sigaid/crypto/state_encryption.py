"""State data encryption for protecting sensitive action data.

Provides optional encryption for sensitive fields in state chain entries:
- action_summary: Human-readable description (may contain PII)
- action_data: Full action payload (may contain sensitive details)

Encryption uses:
- ChaCha20-Poly1305 for authenticated encryption
- Key derived from agent's keypair using HKDF
- Unique nonce per encryption

This is optional - agents can choose whether to encrypt sensitive data.
The state chain signatures remain valid regardless of encryption status.
"""

from __future__ import annotations

import os
import struct
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes

from sigaid.exceptions import CryptoError

if TYPE_CHECKING:
    from sigaid.crypto.keys import KeyPair


# Domain separation for key derivation
STATE_ENCRYPTION_DOMAIN = b"sigaid.state.encryption.v1"

# Encryption header version (for future algorithm changes)
ENCRYPTION_VERSION = 1


class StateEncryptor:
    """Encrypts and decrypts state entry data.

    Uses a key derived from the agent's keypair, so only the agent
    (or someone with the agent's private key) can decrypt the data.

    Example:
        encryptor = StateEncryptor(keypair)

        # Encrypt sensitive data
        encrypted = encryptor.encrypt(b"sensitive action details")

        # Decrypt later
        decrypted = encryptor.decrypt(encrypted)

        # With salt for additional security
        encryptor_with_salt = StateEncryptor(keypair, salt=b"unique-per-context")
    """

    def __init__(self, keypair: KeyPair, salt: bytes | None = None):
        """Initialize with agent keypair.

        Args:
            keypair: Agent's Ed25519 keypair for key derivation
            salt: Optional salt for key derivation. Use a unique salt per
                  context (e.g., agent_id bytes) for better security.
                  If None, derivation is deterministic from the private key.
        """
        self._keypair = keypair
        self._salt = salt
        self._encryption_key = self._derive_encryption_key()

    def _derive_encryption_key(self) -> bytes:
        """Derive encryption key from agent's keypair using HKDF.

        Uses the private key as input key material.
        """
        private_key = self._keypair.private_key_bytes()

        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._salt,  # Optional salt for non-deterministic derivation
            info=STATE_ENCRYPTION_DOMAIN,
        )

        return hkdf.derive(private_key)

    def encrypt(self, plaintext: bytes) -> bytes:
        """Encrypt data with authenticated encryption.

        Format: [version:1][nonce:12][ciphertext+tag:N+16]

        Args:
            plaintext: Data to encrypt

        Returns:
            Encrypted data with version header and nonce
        """
        if not plaintext:
            return b""

        # Generate random nonce
        nonce = os.urandom(12)

        # Encrypt with ChaCha20-Poly1305
        cipher = ChaCha20Poly1305(self._encryption_key)
        ciphertext = cipher.encrypt(nonce, plaintext, None)

        # Pack: version (1 byte) + nonce (12 bytes) + ciphertext
        return struct.pack("B", ENCRYPTION_VERSION) + nonce + ciphertext

    def decrypt(self, encrypted: bytes) -> bytes:
        """Decrypt authenticated encrypted data.

        Args:
            encrypted: Data encrypted with encrypt()

        Returns:
            Original plaintext

        Raises:
            CryptoError: If decryption fails (wrong key, tampered data)
        """
        if not encrypted:
            return b""

        if len(encrypted) < 1 + 12 + 16:  # version + nonce + min ciphertext
            raise CryptoError("Encrypted data too short")

        # Unpack version
        version = encrypted[0]
        if version != ENCRYPTION_VERSION:
            raise CryptoError(f"Unsupported encryption version: {version}")

        # Extract nonce and ciphertext
        nonce = encrypted[1:13]
        ciphertext = encrypted[13:]

        # Decrypt
        try:
            cipher = ChaCha20Poly1305(self._encryption_key)
            return cipher.decrypt(nonce, ciphertext, None)
        except Exception as e:
            raise CryptoError(f"Decryption failed: {e}") from e


class StateEncryptionHelper:
    """Helper for encrypting/decrypting state entry fields.

    Provides convenient methods for working with state entries.
    """

    def __init__(self, keypair: KeyPair, salt: bytes | None = None):
        """Initialize with agent keypair.

        Args:
            keypair: Agent's keypair
            salt: Optional salt for key derivation
        """
        self._encryptor = StateEncryptor(keypair, salt=salt)

    def encrypt_summary(self, summary: str) -> bytes:
        """Encrypt action summary.

        Args:
            summary: Human-readable summary

        Returns:
            Encrypted summary bytes
        """
        return self._encryptor.encrypt(summary.encode("utf-8"))

    def decrypt_summary(self, encrypted: bytes) -> str:
        """Decrypt action summary.

        Args:
            encrypted: Encrypted summary from encrypt_summary()

        Returns:
            Original summary string
        """
        return self._encryptor.decrypt(encrypted).decode("utf-8")

    def encrypt_action_data(self, data: dict) -> bytes:
        """Encrypt action data dictionary.

        Args:
            data: Action data dictionary

        Returns:
            Encrypted JSON bytes
        """
        import json
        json_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
        return self._encryptor.encrypt(json_bytes)

    def decrypt_action_data(self, encrypted: bytes) -> dict:
        """Decrypt action data.

        Args:
            encrypted: Encrypted data from encrypt_action_data()

        Returns:
            Original action data dictionary
        """
        import json
        decrypted = self._encryptor.decrypt(encrypted)
        return json.loads(decrypted.decode("utf-8"))

    @staticmethod
    def is_encrypted(data: bytes) -> bool:
        """Check if data appears to be encrypted.

        Args:
            data: Bytes to check

        Returns:
            True if data has encryption header
        """
        if not data or len(data) < 1:
            return False
        return data[0] == ENCRYPTION_VERSION


def create_encryptor(keypair: KeyPair, salt: bytes | None = None) -> StateEncryptionHelper:
    """Create a state encryption helper for an agent.

    Args:
        keypair: Agent's keypair
        salt: Optional salt for key derivation. Recommended to use
              agent_id bytes or similar unique value.

    Returns:
        StateEncryptionHelper instance
    """
    return StateEncryptionHelper(keypair, salt=salt)
