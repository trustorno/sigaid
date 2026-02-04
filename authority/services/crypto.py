"""Cryptographic verification service."""

import base64
import hashlib
from datetime import datetime, timezone
from typing import Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
import blake3


# Domain separation prefixes (must match SDK)
DOMAIN_IDENTITY = "sigaid.identity.v1"
DOMAIN_LEASE = "sigaid.lease.v1"
DOMAIN_STATE = "sigaid.state.v1"
DOMAIN_VERIFY = "sigaid.verify.v1"


class CryptoService:
    """Service for cryptographic verification operations."""

    @staticmethod
    def verify_signature(
        public_key: bytes,
        message: bytes,
        signature: bytes,
        domain: str = "",
    ) -> bool:
        """
        Verify an Ed25519 signature.

        Args:
            public_key: 32-byte Ed25519 public key
            message: The message that was signed
            signature: 64-byte Ed25519 signature
            domain: Optional domain separation string

        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Apply domain separation if specified
            if domain:
                domain_bytes = domain.encode("utf-8")
                tagged_message = (
                    len(domain_bytes).to_bytes(2, "big") +
                    domain_bytes +
                    message
                )
            else:
                tagged_message = message

            # Load public key and verify
            key = Ed25519PublicKey.from_public_bytes(public_key)
            key.verify(signature, tagged_message)
            return True
        except (InvalidSignature, ValueError):
            return False

    @staticmethod
    def verify_lease_request(
        public_key: bytes,
        agent_id: str,
        session_id: str,
        timestamp: str,
        nonce: str,
        signature_hex: str,
    ) -> bool:
        """
        Verify a lease acquisition request signature.

        The message format is: agent_id:session_id:timestamp:nonce (colons, matching SDK)
        """
        try:
            # Validate timestamp is recent (within 5 minutes)
            ts = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age = abs((now - ts).total_seconds())
            if age > 300:  # 5 minutes
                return False

            # Construct message - SDK format uses colons as separator
            message = f"{agent_id}:{session_id}:{timestamp}:{nonce}".encode("utf-8")
            signature = bytes.fromhex(signature_hex)

            return CryptoService.verify_signature(
                public_key, message, signature, domain=DOMAIN_LEASE
            )
        except (ValueError, TypeError):
            return False

    @staticmethod
    def verify_state_entry(
        public_key: bytes,
        agent_id: str,
        sequence: int,
        prev_hash: bytes,
        timestamp: str,
        action_type: str,
        action_summary: str,
        action_data_hash: Optional[bytes],
        signature: bytes,
        entry_hash: bytes,
    ) -> bool:
        """
        Verify a state entry signature and hash.

        Returns True if both signature and entry_hash are valid.
        Uses SDK binary format for compatibility.
        """
        try:
            # Use zero hash if no action data hash provided
            if action_data_hash is None:
                action_data_hash = bytes(32)

            # Construct the canonical signable message (binary format matching SDK)
            # Format: binary concatenation of all fields
            signable = b"".join([
                agent_id.encode("utf-8"),
                sequence.to_bytes(8, "big"),  # 8-byte big-endian integer
                prev_hash,
                timestamp.encode("utf-8"),
                action_type.encode("utf-8"),
                action_summary.encode("utf-8"),
                action_data_hash,
            ])

            # Verify signature
            if not CryptoService.verify_signature(
                public_key, signable, signature, domain=DOMAIN_STATE
            ):
                return False

            # Verify entry_hash
            # Hash is computed over: signable content + signature
            hash_input = signable + signature
            computed_hash = blake3.blake3(hash_input).digest()

            return computed_hash == entry_hash
        except (ValueError, TypeError):
            return False

    @staticmethod
    def hash_bytes(data: bytes) -> bytes:
        """Compute BLAKE3 hash of data."""
        return blake3.blake3(data).digest()

    @staticmethod
    def hash_api_key(key: str) -> bytes:
        """Hash an API key for storage."""
        return blake3.blake3(key.encode("utf-8")).digest()
