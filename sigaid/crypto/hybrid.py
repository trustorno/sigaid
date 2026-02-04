"""Post-quantum hybrid signature scheme.

Combines Ed25519 (classical) with Dilithium-3 (post-quantum) for
signatures that are secure against both classical and quantum computers.

Why hybrid?
- Ed25519 is fast and has small signatures (64 bytes)
- Dilithium-3 provides post-quantum security
- Hybrid ensures security if either scheme is broken

Signature format:
    [1-byte version][64-byte Ed25519 sig][3293-byte Dilithium sig]

Total hybrid signature size: ~3358 bytes (vs 64 bytes for Ed25519 alone)

Requirements:
    pip install pqcrypto  # Or liboqs-python

Usage:
    from sigaid.crypto.hybrid import HybridKeyPair

    # Generate hybrid keypair
    keypair = HybridKeyPair.generate()

    # Sign with both algorithms
    signature = keypair.sign(b"message", domain="sigaid.state.v1")

    # Verify requires both signatures to be valid
    valid = keypair.verify(signature, b"message", domain="sigaid.state.v1")

    # Can also verify with just Ed25519 for backwards compatibility
    ed_valid = keypair.verify_ed25519_only(signature, b"message", domain="sigaid.state.v1")
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional, Tuple
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization

from sigaid.exceptions import CryptoError

# Hybrid signature version
HYBRID_VERSION = 1

# Ed25519 sizes
ED25519_PRIVATE_SIZE = 32
ED25519_PUBLIC_SIZE = 32
ED25519_SIGNATURE_SIZE = 64

# Dilithium-3 sizes (NIST Level 3)
DILITHIUM3_PUBLIC_SIZE = 1952
DILITHIUM3_PRIVATE_SIZE = 4000
DILITHIUM3_SIGNATURE_SIZE = 3293

# Total hybrid sizes
HYBRID_PUBLIC_SIZE = ED25519_PUBLIC_SIZE + DILITHIUM3_PUBLIC_SIZE
HYBRID_PRIVATE_SIZE = ED25519_PRIVATE_SIZE + DILITHIUM3_PRIVATE_SIZE
HYBRID_SIGNATURE_SIZE = 1 + ED25519_SIGNATURE_SIZE + DILITHIUM3_SIGNATURE_SIZE


def _check_pqcrypto_available() -> bool:
    """Check if post-quantum crypto library is available."""
    try:
        from pqcrypto.sign import dilithium3
        return True
    except ImportError:
        return False


def _check_liboqs_available() -> bool:
    """Check if liboqs is available."""
    try:
        import oqs
        return True
    except ImportError:
        return False


class PostQuantumNotAvailableError(Exception):
    """Post-quantum cryptography library not available."""
    pass


@dataclass
class HybridPublicKey:
    """Combined Ed25519 + Dilithium public key."""
    ed25519_public: bytes  # 32 bytes
    dilithium_public: bytes  # 1952 bytes

    def to_bytes(self) -> bytes:
        """Serialize to bytes."""
        return self.ed25519_public + self.dilithium_public

    @classmethod
    def from_bytes(cls, data: bytes) -> HybridPublicKey:
        """Deserialize from bytes."""
        if len(data) != HYBRID_PUBLIC_SIZE:
            raise ValueError(f"Expected {HYBRID_PUBLIC_SIZE} bytes, got {len(data)}")
        return cls(
            ed25519_public=data[:ED25519_PUBLIC_SIZE],
            dilithium_public=data[ED25519_PUBLIC_SIZE:],
        )


class HybridKeyPair:
    """Ed25519 + Dilithium-3 hybrid keypair.

    Provides post-quantum security while maintaining backwards
    compatibility with Ed25519-only verification.
    """

    def __init__(
        self,
        ed25519_private: Ed25519PrivateKey,
        dilithium_private: bytes,
        dilithium_public: bytes,
    ):
        """Initialize with both keypairs.

        Use HybridKeyPair.generate() to create a new keypair.
        """
        self._ed25519_private = ed25519_private
        self._ed25519_public = ed25519_private.public_key()
        self._dilithium_private = dilithium_private
        self._dilithium_public = dilithium_public

    @classmethod
    def generate(cls) -> HybridKeyPair:
        """Generate a new hybrid keypair.

        Raises:
            PostQuantumNotAvailableError: If PQ library not installed
        """
        # Generate Ed25519 keypair
        ed25519_private = Ed25519PrivateKey.generate()

        # Generate Dilithium-3 keypair
        if _check_pqcrypto_available():
            from pqcrypto.sign import dilithium3
            dilithium_public, dilithium_private = dilithium3.generate_keypair()
        elif _check_liboqs_available():
            import oqs
            signer = oqs.Signature("Dilithium3")
            dilithium_public = signer.generate_keypair()
            dilithium_private = signer.export_secret_key()
        else:
            raise PostQuantumNotAvailableError(
                "Post-quantum library required. Install with:\n"
                "  pip install pqcrypto\n"
                "or:\n"
                "  pip install liboqs-python"
            )

        return cls(ed25519_private, dilithium_private, dilithium_public)

    @classmethod
    def from_ed25519_only(cls, ed25519_private: Ed25519PrivateKey) -> HybridKeyPair:
        """Create a hybrid keypair from existing Ed25519 key.

        Generates a new Dilithium keypair. Use this for migrating
        existing agents to hybrid signatures.

        Args:
            ed25519_private: Existing Ed25519 private key

        Returns:
            HybridKeyPair with the same Ed25519 key
        """
        if _check_pqcrypto_available():
            from pqcrypto.sign import dilithium3
            dilithium_public, dilithium_private = dilithium3.generate_keypair()
        elif _check_liboqs_available():
            import oqs
            signer = oqs.Signature("Dilithium3")
            dilithium_public = signer.generate_keypair()
            dilithium_private = signer.export_secret_key()
        else:
            raise PostQuantumNotAvailableError(
                "Post-quantum library required for hybrid keypair"
            )

        return cls(ed25519_private, dilithium_private, dilithium_public)

    @property
    def public_key(self) -> HybridPublicKey:
        """Get the hybrid public key."""
        ed25519_public = self._ed25519_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return HybridPublicKey(
            ed25519_public=ed25519_public,
            dilithium_public=self._dilithium_public,
        )

    @property
    def ed25519_public_bytes(self) -> bytes:
        """Get just the Ed25519 public key (for backwards compatibility)."""
        return self._ed25519_public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def sign(self, message: bytes, domain: str = "") -> bytes:
        """Sign message with both Ed25519 and Dilithium.

        Args:
            message: Message to sign
            domain: Optional domain separation tag

        Returns:
            Hybrid signature (version + Ed25519 sig + Dilithium sig)
        """
        # Apply domain separation
        if domain:
            domain_bytes = domain.encode("utf-8")
            message = len(domain_bytes).to_bytes(2, "big") + domain_bytes + message

        # Sign with Ed25519
        ed25519_sig = self._ed25519_private.sign(message)

        # Sign with Dilithium
        if _check_pqcrypto_available():
            from pqcrypto.sign import dilithium3
            # pqcrypto API: sign(message, private_key) -> signature
            dilithium_sig = dilithium3.sign(message, self._dilithium_private)
        elif _check_liboqs_available():
            import oqs
            signer = oqs.Signature("Dilithium3", self._dilithium_private)
            dilithium_sig = signer.sign(message)
        else:
            raise PostQuantumNotAvailableError("PQ library required for signing")

        # Combine: version (1 byte) + Ed25519 (64 bytes) + Dilithium (~3293 bytes)
        return struct.pack("B", HYBRID_VERSION) + ed25519_sig + dilithium_sig

    def sign_ed25519_only(self, message: bytes, domain: str = "") -> bytes:
        """Sign with only Ed25519 (backwards compatible).

        Use this when communicating with systems that don't support
        post-quantum signatures yet.

        Args:
            message: Message to sign
            domain: Optional domain separation tag

        Returns:
            64-byte Ed25519 signature (no version prefix)
        """
        if domain:
            domain_bytes = domain.encode("utf-8")
            message = len(domain_bytes).to_bytes(2, "big") + domain_bytes + message

        return self._ed25519_private.sign(message)

    def verify(self, signature: bytes, message: bytes, domain: str = "") -> bool:
        """Verify a hybrid signature.

        Both Ed25519 and Dilithium signatures must be valid.

        Args:
            signature: Hybrid signature from sign()
            message: Original message
            domain: Domain separation tag used when signing

        Returns:
            True if BOTH signatures are valid
        """
        if len(signature) < 1 + ED25519_SIGNATURE_SIZE:
            return False

        version = signature[0]
        if version != HYBRID_VERSION:
            return False

        ed25519_sig = signature[1:1 + ED25519_SIGNATURE_SIZE]
        dilithium_sig = signature[1 + ED25519_SIGNATURE_SIZE:]

        # Apply domain separation
        if domain:
            domain_bytes = domain.encode("utf-8")
            message = len(domain_bytes).to_bytes(2, "big") + domain_bytes + message

        # Verify Ed25519
        try:
            self._ed25519_public.verify(ed25519_sig, message)
        except Exception:
            return False

        # Verify Dilithium
        try:
            if _check_pqcrypto_available():
                from pqcrypto.sign import dilithium3
                # pqcrypto API: verify(public_key, message, signature) -> raises on failure
                dilithium3.verify(self._dilithium_public, dilithium_sig, message)
            elif _check_liboqs_available():
                import oqs
                verifier = oqs.Signature("Dilithium3")
                if not verifier.verify(message, dilithium_sig, self._dilithium_public):
                    return False
            else:
                # Can't verify Dilithium without library
                return False
        except Exception:
            return False

        return True

    def verify_ed25519_only(self, signature: bytes, message: bytes, domain: str = "") -> bool:
        """Verify only the Ed25519 portion of a hybrid signature.

        Use this for backwards compatibility when the verifier
        doesn't have PQ library installed.

        Args:
            signature: Either a hybrid signature or raw Ed25519 signature
            message: Original message
            domain: Domain separation tag

        Returns:
            True if Ed25519 signature is valid
        """
        # Handle both hybrid and raw Ed25519 signatures
        if len(signature) > ED25519_SIGNATURE_SIZE and signature[0] == HYBRID_VERSION:
            # Hybrid signature
            ed25519_sig = signature[1:1 + ED25519_SIGNATURE_SIZE]
        elif len(signature) == ED25519_SIGNATURE_SIZE:
            # Raw Ed25519 signature
            ed25519_sig = signature
        else:
            return False

        # Apply domain separation
        if domain:
            domain_bytes = domain.encode("utf-8")
            message = len(domain_bytes).to_bytes(2, "big") + domain_bytes + message

        try:
            self._ed25519_public.verify(ed25519_sig, message)
            return True
        except Exception:
            return False


def verify_hybrid_signature(
    public_key: HybridPublicKey,
    signature: bytes,
    message: bytes,
    domain: str = "",
    require_pq: bool = True,
) -> bool:
    """Verify a hybrid signature with a public key.

    Standalone verification function that doesn't require
    the private key.

    Args:
        public_key: Hybrid public key
        signature: Hybrid signature
        message: Original message
        domain: Domain separation tag
        require_pq: If True, require Dilithium verification

    Returns:
        True if valid
    """
    if len(signature) < 1 + ED25519_SIGNATURE_SIZE:
        return False

    version = signature[0]
    if version != HYBRID_VERSION:
        return False

    ed25519_sig = signature[1:1 + ED25519_SIGNATURE_SIZE]
    dilithium_sig = signature[1 + ED25519_SIGNATURE_SIZE:]

    # Apply domain separation
    if domain:
        domain_bytes = domain.encode("utf-8")
        message = len(domain_bytes).to_bytes(2, "big") + domain_bytes + message

    # Verify Ed25519
    try:
        ed_public = Ed25519PublicKey.from_public_bytes(public_key.ed25519_public)
        ed_public.verify(ed25519_sig, message)
    except Exception:
        return False

    # Verify Dilithium if required or available
    if require_pq or _check_pqcrypto_available() or _check_liboqs_available():
        try:
            if _check_pqcrypto_available():
                from pqcrypto.sign import dilithium3
                # pqcrypto API: verify(public_key, signature, message) -> raises on failure
                dilithium3.verify(public_key.dilithium_public, dilithium_sig, message)
            elif _check_liboqs_available():
                import oqs
                verifier = oqs.Signature("Dilithium3")
                if not verifier.verify(message, dilithium_sig, public_key.dilithium_public):
                    return False
            elif require_pq:
                raise PostQuantumNotAvailableError("PQ library required for verification")
        except PostQuantumNotAvailableError:
            raise
        except Exception:
            return False

    return True


def is_hybrid_signature(signature: bytes) -> bool:
    """Check if a signature is a hybrid signature.

    Args:
        signature: Signature bytes

    Returns:
        True if this is a hybrid signature (has version prefix)
    """
    if not signature or len(signature) < 1:
        return False
    return signature[0] == HYBRID_VERSION and len(signature) > ED25519_SIGNATURE_SIZE
