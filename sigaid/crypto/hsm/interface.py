"""Abstract interface for key providers.

Defines the contract for key management operations that can be
implemented by different backends (software, HSM, cloud KMS, etc.).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class KeyType(str, Enum):
    """Supported key types."""
    ED25519 = "ed25519"
    # Future: ED448, DILITHIUM3, etc.


class KeyUsage(str, Enum):
    """Intended key usage."""
    SIGNING = "signing"
    ENCRYPTION = "encryption"
    KEY_AGREEMENT = "key_agreement"


@dataclass
class KeyInfo:
    """Information about a managed key."""

    key_id: str
    key_type: KeyType
    usage: KeyUsage
    public_key: bytes  # Raw public key bytes
    created_at: datetime
    hardware_backed: bool = False
    label: Optional[str] = None
    exportable: bool = True  # Whether private key can be exported


class KeyProvider(ABC):
    """Abstract base class for key management.

    Implementations can use:
    - Software keys (in-memory or file-based)
    - Hardware Security Modules (HSM) via PKCS#11
    - Cloud KMS (AWS KMS, Google Cloud KMS, Azure Key Vault)
    - Secure enclaves (SGX, TrustZone)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider name."""
        pass

    @property
    @abstractmethod
    def is_hardware_backed(self) -> bool:
        """Whether keys are stored in hardware."""
        pass

    @abstractmethod
    def generate_key(
        self,
        key_type: KeyType = KeyType.ED25519,
        usage: KeyUsage = KeyUsage.SIGNING,
        label: Optional[str] = None,
        exportable: bool = True,
    ) -> str:
        """Generate a new key.

        Args:
            key_type: Type of key to generate
            usage: Intended usage for the key
            label: Optional human-readable label
            exportable: Whether private key can be exported (HSM only)

        Returns:
            Unique key identifier
        """
        pass

    @abstractmethod
    def import_key(
        self,
        private_key: bytes,
        key_type: KeyType = KeyType.ED25519,
        usage: KeyUsage = KeyUsage.SIGNING,
        label: Optional[str] = None,
    ) -> str:
        """Import an existing private key.

        Args:
            private_key: Raw private key bytes
            key_type: Type of the key
            usage: Intended usage
            label: Optional label

        Returns:
            Unique key identifier
        """
        pass

    @abstractmethod
    def export_private_key(self, key_id: str) -> bytes:
        """Export private key bytes.

        Args:
            key_id: Key identifier

        Returns:
            Raw private key bytes

        Raises:
            KeyError: If key not found
            PermissionError: If key is not exportable
        """
        pass

    @abstractmethod
    def get_public_key(self, key_id: str) -> bytes:
        """Get public key bytes.

        Args:
            key_id: Key identifier

        Returns:
            Raw public key bytes (32 bytes for Ed25519)

        Raises:
            KeyError: If key not found
        """
        pass

    @abstractmethod
    def get_key_info(self, key_id: str) -> KeyInfo:
        """Get information about a key.

        Args:
            key_id: Key identifier

        Returns:
            KeyInfo with key metadata

        Raises:
            KeyError: If key not found
        """
        pass

    @abstractmethod
    def list_keys(self) -> list[KeyInfo]:
        """List all managed keys.

        Returns:
            List of KeyInfo for all keys
        """
        pass

    @abstractmethod
    def delete_key(self, key_id: str) -> bool:
        """Delete a key.

        Args:
            key_id: Key identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def sign(
        self,
        key_id: str,
        data: bytes,
        domain: str = "",
    ) -> bytes:
        """Sign data with a key.

        Args:
            key_id: Key identifier
            data: Data to sign
            domain: Optional domain separation tag

        Returns:
            Signature bytes (64 bytes for Ed25519)

        Raises:
            KeyError: If key not found
            ValueError: If key cannot be used for signing
        """
        pass

    @abstractmethod
    def verify(
        self,
        key_id: str,
        signature: bytes,
        data: bytes,
        domain: str = "",
    ) -> bool:
        """Verify a signature.

        Args:
            key_id: Key identifier
            signature: Signature to verify
            data: Original data
            domain: Domain separation tag used when signing

        Returns:
            True if signature is valid

        Raises:
            KeyError: If key not found
        """
        pass

    def verify_with_public_key(
        self,
        public_key: bytes,
        signature: bytes,
        data: bytes,
        domain: str = "",
    ) -> bool:
        """Verify a signature using raw public key bytes.

        This is a convenience method for verifying signatures
        without needing to import the key first.

        Args:
            public_key: Raw public key bytes
            signature: Signature to verify
            data: Original data
            domain: Domain separation tag

        Returns:
            True if signature is valid
        """
        # Default implementation using cryptography library
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        if domain:
            domain_bytes = domain.encode("utf-8")
            data = len(domain_bytes).to_bytes(2, "big") + domain_bytes + data

        try:
            pk = Ed25519PublicKey.from_public_bytes(public_key)
            pk.verify(signature, data)
            return True
        except Exception:
            return False
