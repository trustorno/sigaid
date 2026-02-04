"""Software-based key provider implementation.

This is the default key provider that stores keys in memory.
Keys are protected with secure memory handling when available.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization

from .interface import KeyProvider, KeyInfo, KeyType, KeyUsage
from ..secure_memory import SecureBytes


class SoftwareKeyProvider(KeyProvider):
    """Software-based key management.

    Stores keys in memory with secure memory handling.
    Suitable for development and single-instance deployments.
    """

    def __init__(self):
        """Initialize the software key provider."""
        self._keys: dict[str, _SoftwareKey] = {}

    @property
    def provider_name(self) -> str:
        return "Software Key Provider"

    @property
    def is_hardware_backed(self) -> bool:
        return False

    def generate_key(
        self,
        key_type: KeyType = KeyType.ED25519,
        usage: KeyUsage = KeyUsage.SIGNING,
        label: Optional[str] = None,
        exportable: bool = True,
    ) -> str:
        """Generate a new Ed25519 key."""
        if key_type != KeyType.ED25519:
            raise ValueError(f"Unsupported key type: {key_type}")

        # Generate key ID
        key_id = f"sw_{secrets.token_hex(16)}"

        # Generate Ed25519 keypair
        private_key = Ed25519PrivateKey.generate()
        private_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # Store only in secure memory (no duplicate Ed25519PrivateKey object)
        secure_private = SecureBytes(private_bytes, lock_memory=True)

        self._keys[key_id] = _SoftwareKey(
            key_id=key_id,
            key_type=key_type,
            usage=usage,
            secure_private=secure_private,
            created_at=datetime.now(timezone.utc),
            label=label,
            exportable=exportable,
        )

        return key_id

    def import_key(
        self,
        private_key: bytes,
        key_type: KeyType = KeyType.ED25519,
        usage: KeyUsage = KeyUsage.SIGNING,
        label: Optional[str] = None,
    ) -> str:
        """Import an existing Ed25519 private key."""
        if key_type != KeyType.ED25519:
            raise ValueError(f"Unsupported key type: {key_type}")

        if len(private_key) != 32:
            raise ValueError("Ed25519 private key must be 32 bytes")

        # Validate key is valid Ed25519 before storing
        Ed25519PrivateKey.from_private_bytes(private_key)

        key_id = f"sw_{secrets.token_hex(16)}"
        secure_private = SecureBytes(private_key, lock_memory=True)

        self._keys[key_id] = _SoftwareKey(
            key_id=key_id,
            key_type=key_type,
            usage=usage,
            secure_private=secure_private,
            created_at=datetime.now(timezone.utc),
            label=label,
            exportable=True,
        )

        return key_id

    def export_private_key(self, key_id: str) -> bytes:
        """Export private key bytes."""
        key = self._get_key(key_id)
        if not key.exportable:
            raise PermissionError(f"Key {key_id} is not exportable")
        return key.secure_private.data

    def get_public_key(self, key_id: str) -> bytes:
        """Get public key bytes."""
        key = self._get_key(key_id)
        return key.get_public_key_bytes()

    def get_key_info(self, key_id: str) -> KeyInfo:
        """Get information about a key."""
        key = self._get_key(key_id)
        return KeyInfo(
            key_id=key.key_id,
            key_type=key.key_type,
            usage=key.usage,
            public_key=self.get_public_key(key_id),
            created_at=key.created_at,
            hardware_backed=False,
            label=key.label,
            exportable=key.exportable,
        )

    def list_keys(self) -> list[KeyInfo]:
        """List all managed keys."""
        return [self.get_key_info(key_id) for key_id in self._keys]

    def delete_key(self, key_id: str) -> bool:
        """Delete a key securely."""
        if key_id not in self._keys:
            return False

        key = self._keys[key_id]
        # Securely clear the key material
        key.secure_private.clear()
        del self._keys[key_id]
        return True

    def sign(
        self,
        key_id: str,
        data: bytes,
        domain: str = "",
    ) -> bytes:
        """Sign data with domain separation."""
        key = self._get_key(key_id)

        if key.usage != KeyUsage.SIGNING:
            raise ValueError(f"Key {key_id} is not for signing")

        # Apply domain separation
        if domain:
            domain_bytes = domain.encode("utf-8")
            data = len(domain_bytes).to_bytes(2, "big") + domain_bytes + data

        # Reconstruct private key for signing operation
        private_key = key.get_private_key()
        return private_key.sign(data)

    def verify(
        self,
        key_id: str,
        signature: bytes,
        data: bytes,
        domain: str = "",
    ) -> bool:
        """Verify a signature with domain separation."""
        key = self._get_key(key_id)

        # Apply domain separation
        if domain:
            domain_bytes = domain.encode("utf-8")
            data = len(domain_bytes).to_bytes(2, "big") + domain_bytes + data

        try:
            # Use cached public key for verification
            public_key = Ed25519PublicKey.from_public_bytes(key.get_public_key_bytes())
            public_key.verify(signature, data)
            return True
        except Exception:
            return False

    def _get_key(self, key_id: str) -> "_SoftwareKey":
        """Get a key by ID."""
        if key_id not in self._keys:
            raise KeyError(f"Key not found: {key_id}")
        return self._keys[key_id]


class _SoftwareKey:
    """Internal representation of a software key.

    Only stores the private key in SecureBytes to avoid duplicate key material.
    The Ed25519PrivateKey object is reconstructed on demand for operations.
    """

    def __init__(
        self,
        key_id: str,
        key_type: KeyType,
        usage: KeyUsage,
        secure_private: SecureBytes,
        created_at: datetime,
        label: Optional[str] = None,
        exportable: bool = True,
    ):
        self.key_id = key_id
        self.key_type = key_type
        self.usage = usage
        self.secure_private = secure_private
        self.created_at = created_at
        self.label = label
        self.exportable = exportable
        # Cache public key bytes (not sensitive)
        self._public_key_bytes: Optional[bytes] = None

    def get_private_key(self) -> Ed25519PrivateKey:
        """Reconstruct Ed25519PrivateKey from secure storage."""
        return Ed25519PrivateKey.from_private_bytes(self.secure_private.data)

    def get_public_key_bytes(self) -> bytes:
        """Get public key bytes (cached for performance)."""
        if self._public_key_bytes is None:
            pk = self.get_private_key()
            self._public_key_bytes = pk.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        return self._public_key_bytes
