"""PKCS#11 HSM key provider implementation.

Requires the python-pkcs11 package:
    pip install python-pkcs11

Tested with:
- SoftHSM2 (software HSM for testing)
- Thales Luna HSM
- AWS CloudHSM

Example usage:
    from sigaid.crypto.hsm.pkcs11 import PKCS11KeyProvider

    provider = PKCS11KeyProvider(
        library_path="/usr/lib/softhsm/libsofthsm2.so",
        token_label="sigaid-keys",
        pin="1234",
    )

    key_id = provider.generate_key(label="agent-001")
    signature = provider.sign(key_id, b"data", domain="sigaid.lease.v1")
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Optional

from .interface import KeyProvider, KeyInfo, KeyType, KeyUsage


class PKCS11NotAvailableError(Exception):
    """PKCS#11 library is not available."""
    pass


class PKCS11KeyProvider(KeyProvider):
    """PKCS#11 HSM-backed key provider.

    Stores keys in a hardware security module via the PKCS#11 interface.
    Provides hardware-level protection for private keys.
    """

    def __init__(
        self,
        library_path: str,
        token_label: str,
        pin: str,
        slot_index: int = 0,
    ):
        """Initialize PKCS#11 key provider.

        Args:
            library_path: Path to PKCS#11 library (.so/.dylib/.dll)
            token_label: Token/partition label
            pin: User PIN for the token
            slot_index: Slot index (default 0)

        Raises:
            PKCS11NotAvailableError: If python-pkcs11 is not installed
            RuntimeError: If connection to HSM fails
        """
        try:
            import pkcs11
            from pkcs11 import Mechanism, ObjectClass, KeyType as P11KeyType
        except ImportError:
            raise PKCS11NotAvailableError(
                "python-pkcs11 package required. Install with: pip install python-pkcs11"
            )

        self._pkcs11 = pkcs11
        self._Mechanism = Mechanism
        self._ObjectClass = ObjectClass
        self._P11KeyType = P11KeyType

        # Load library and open session
        try:
            lib = pkcs11.lib(library_path)
            token = lib.get_token(token_label=token_label)
            self._session = token.open(user_pin=pin)
        except Exception as e:
            raise RuntimeError(f"Failed to connect to HSM: {e}")

        self._token_label = token_label
        self._key_cache: dict[str, KeyInfo] = {}

    @property
    def provider_name(self) -> str:
        return f"PKCS#11 HSM ({self._token_label})"

    @property
    def is_hardware_backed(self) -> bool:
        return True

    def generate_key(
        self,
        key_type: KeyType = KeyType.ED25519,
        usage: KeyUsage = KeyUsage.SIGNING,
        label: Optional[str] = None,
        exportable: bool = False,  # Default to non-exportable for HSM
    ) -> str:
        """Generate a new Ed25519 key in the HSM."""
        if key_type != KeyType.ED25519:
            raise ValueError(f"Unsupported key type: {key_type}")

        # Generate unique key ID
        import secrets
        key_id = f"hsm_{secrets.token_hex(8)}"

        # HSM key attributes
        key_label = label or key_id

        try:
            # Generate Ed25519 keypair in HSM
            # Note: Ed25519 support varies by HSM vendor
            public_key, private_key = self._session.generate_keypair(
                self._P11KeyType.EC_EDWARDS,
                mechanism=self._Mechanism.EC_EDWARDS_KEY_PAIR_GEN,
                store=True,
                label=key_label,
                id=key_id.encode(),
            )

            # Get public key bytes
            public_bytes = bytes(public_key[self._pkcs11.Attribute.EC_POINT])

            # Cache key info
            self._key_cache[key_id] = KeyInfo(
                key_id=key_id,
                key_type=key_type,
                usage=usage,
                public_key=public_bytes,
                created_at=datetime.now(timezone.utc),
                hardware_backed=True,
                label=key_label,
                exportable=exportable,
            )

            return key_id

        except Exception as e:
            raise RuntimeError(f"Failed to generate key in HSM: {e}")

    def import_key(
        self,
        private_key: bytes,
        key_type: KeyType = KeyType.ED25519,
        usage: KeyUsage = KeyUsage.SIGNING,
        label: Optional[str] = None,
    ) -> str:
        """Import a private key into the HSM."""
        if key_type != KeyType.ED25519:
            raise ValueError(f"Unsupported key type: {key_type}")

        import secrets
        key_id = f"hsm_{secrets.token_hex(8)}"
        key_label = label or key_id

        try:
            # Import private key into HSM
            # Implementation depends on HSM vendor
            raise NotImplementedError(
                "Key import is HSM-specific. Please generate keys directly in the HSM."
            )
        except Exception as e:
            raise RuntimeError(f"Failed to import key to HSM: {e}")

    def export_private_key(self, key_id: str) -> bytes:
        """Export private key - usually not allowed for HSM keys."""
        info = self.get_key_info(key_id)
        if not info.exportable:
            raise PermissionError(
                f"Key {key_id} is stored in HSM and cannot be exported"
            )
        # If somehow marked as exportable, attempt export
        raise NotImplementedError("HSM key export not implemented")

    def get_public_key(self, key_id: str) -> bytes:
        """Get public key bytes."""
        if key_id in self._key_cache:
            return self._key_cache[key_id].public_key

        # Look up in HSM
        try:
            public_key = self._session.get_key(
                object_class=self._ObjectClass.PUBLIC_KEY,
                id=key_id.encode(),
            )
            return bytes(public_key[self._pkcs11.Attribute.EC_POINT])
        except Exception as e:
            raise KeyError(f"Key not found: {key_id}") from e

    def get_key_info(self, key_id: str) -> KeyInfo:
        """Get information about a key."""
        if key_id in self._key_cache:
            return self._key_cache[key_id]

        # Look up in HSM
        public_bytes = self.get_public_key(key_id)
        info = KeyInfo(
            key_id=key_id,
            key_type=KeyType.ED25519,
            usage=KeyUsage.SIGNING,
            public_key=public_bytes,
            created_at=datetime.now(timezone.utc),  # HSM may not track this
            hardware_backed=True,
            exportable=False,
        )
        self._key_cache[key_id] = info
        return info

    def list_keys(self) -> list[KeyInfo]:
        """List all Ed25519 keys in the HSM."""
        import logging
        logger = logging.getLogger(__name__)

        keys = []
        try:
            for key in self._session.get_objects({
                self._pkcs11.Attribute.CLASS: self._ObjectClass.PRIVATE_KEY,
                self._pkcs11.Attribute.KEY_TYPE: self._P11KeyType.EC_EDWARDS,
            }):
                try:
                    key_id = key[self._pkcs11.Attribute.ID].decode()
                    keys.append(self.get_key_info(key_id))
                except Exception as e:
                    logger.warning(f"Failed to get info for HSM key: {e}")
        except Exception as e:
            logger.error(f"Failed to list HSM keys: {e}")
            raise RuntimeError(f"Failed to list HSM keys: {e}") from e
        return keys

    def delete_key(self, key_id: str) -> bool:
        """Delete a key from the HSM."""
        try:
            # Delete private key
            private_key = self._session.get_key(
                object_class=self._ObjectClass.PRIVATE_KEY,
                id=key_id.encode(),
            )
            private_key.destroy()

            # Delete public key
            try:
                public_key = self._session.get_key(
                    object_class=self._ObjectClass.PUBLIC_KEY,
                    id=key_id.encode(),
                )
                public_key.destroy()
            except Exception:
                pass  # Public key may not exist separately

            # Remove from cache
            self._key_cache.pop(key_id, None)
            return True

        except Exception:
            return False

    def sign(
        self,
        key_id: str,
        data: bytes,
        domain: str = "",
    ) -> bytes:
        """Sign data using HSM key."""
        # Apply domain separation
        if domain:
            domain_bytes = domain.encode("utf-8")
            data = len(domain_bytes).to_bytes(2, "big") + domain_bytes + data

        try:
            private_key = self._session.get_key(
                object_class=self._ObjectClass.PRIVATE_KEY,
                id=key_id.encode(),
            )
            return private_key.sign(data, mechanism=self._Mechanism.EDDSA)
        except Exception as e:
            raise RuntimeError(f"HSM signing failed: {e}")

    def verify(
        self,
        key_id: str,
        signature: bytes,
        data: bytes,
        domain: str = "",
    ) -> bool:
        """Verify signature using HSM key."""
        # Apply domain separation
        if domain:
            domain_bytes = domain.encode("utf-8")
            data = len(domain_bytes).to_bytes(2, "big") + domain_bytes + data

        try:
            public_key = self._session.get_key(
                object_class=self._ObjectClass.PUBLIC_KEY,
                id=key_id.encode(),
            )
            public_key.verify(data, signature, mechanism=self._Mechanism.EDDSA)
            return True
        except Exception:
            return False

    def __del__(self):
        """Close HSM session on cleanup."""
        if hasattr(self, "_session"):
            try:
                self._session.close()
            except Exception:
                pass
