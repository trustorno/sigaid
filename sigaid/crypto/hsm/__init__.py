"""Hardware Security Module (HSM) abstraction layer.

This module provides an abstraction for key operations that allows
swapping between software-based keys and hardware-backed keys.

Supported backends:
- SoftwareKeyProvider: Default, uses in-memory keys (current behavior)
- PKCS11KeyProvider: Hardware HSM via PKCS#11 interface

Usage:
    from sigaid.crypto.hsm import get_key_provider, KeyProvider

    # Get the configured provider (software by default)
    provider = get_key_provider()

    # Generate a new key
    key_id = provider.generate_key()

    # Sign data
    signature = provider.sign(key_id, data, domain="sigaid.lease.v1")

    # Verify signature
    valid = provider.verify(key_id, signature, data, domain="sigaid.lease.v1")
"""

from .interface import KeyProvider, KeyInfo
from .software import SoftwareKeyProvider

__all__ = [
    "KeyProvider",
    "KeyInfo",
    "SoftwareKeyProvider",
    "get_key_provider",
    "set_key_provider",
]

# Global key provider instance
_key_provider: KeyProvider | None = None


def get_key_provider() -> KeyProvider:
    """Get the current key provider.

    Returns the configured key provider, defaulting to SoftwareKeyProvider.

    Returns:
        The active KeyProvider instance
    """
    global _key_provider
    if _key_provider is None:
        _key_provider = SoftwareKeyProvider()
    return _key_provider


def set_key_provider(provider: KeyProvider) -> None:
    """Set the global key provider.

    Use this to switch to HSM-backed keys:

        from sigaid.crypto.hsm.pkcs11 import PKCS11KeyProvider
        set_key_provider(PKCS11KeyProvider(library_path="/usr/lib/softhsm/libsofthsm2.so"))

    Args:
        provider: KeyProvider implementation to use
    """
    global _key_provider
    _key_provider = provider
