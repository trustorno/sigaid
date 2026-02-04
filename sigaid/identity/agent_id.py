"""Agent ID generation and validation."""

from __future__ import annotations

import hmac
import base58

from sigaid.constants import AGENT_ID_PREFIX, ED25519_PUBLIC_KEY_SIZE
from sigaid.exceptions import InvalidAgentID


class AgentID:
    """Agent identifier derived from Ed25519 public key.

    Format: aid_<base58(public_key + checksum)>

    The AgentID is deterministically derived from the agent's public key,
    providing a human-readable identifier that can be verified cryptographically.

    Example:
        # From keypair
        keypair = KeyPair.generate()
        agent_id = keypair.to_agent_id()

        # Validate format
        AgentID.validate("aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1")

        # Get public key bytes
        public_key = agent_id.to_public_key_bytes()
    """

    def __init__(self, agent_id: str):
        """Initialize with an agent ID string.

        Args:
            agent_id: Agent ID string (aid_xxx format)

        Raises:
            InvalidAgentID: If format is invalid
        """
        self.validate(agent_id)
        self._id = agent_id

    @classmethod
    def from_public_key(cls, public_key: bytes) -> AgentID:
        """Create AgentID from public key bytes.

        Args:
            public_key: 32-byte Ed25519 public key

        Returns:
            AgentID instance

        Raises:
            InvalidAgentID: If public key is invalid
        """
        if len(public_key) != ED25519_PUBLIC_KEY_SIZE:
            raise InvalidAgentID(
                f"Public key must be {ED25519_PUBLIC_KEY_SIZE} bytes, got {len(public_key)}"
            )

        # Compute checksum (first 4 bytes of hash of public key)
        from sigaid.crypto.hashing import hash_bytes

        checksum = hash_bytes(public_key)[:4]

        # Encode public key + checksum
        data = public_key + checksum
        encoded = base58.b58encode(data).decode("ascii")

        return cls(f"{AGENT_ID_PREFIX}{encoded}")

    @classmethod
    def validate(cls, agent_id: str) -> bool:
        """Validate agent ID format and checksum.

        Args:
            agent_id: Agent ID string to validate

        Returns:
            True if valid

        Raises:
            InvalidAgentID: If format or checksum is invalid
        """
        if not agent_id.startswith(AGENT_ID_PREFIX):
            raise InvalidAgentID(f"Agent ID must start with '{AGENT_ID_PREFIX}'")

        encoded = agent_id[len(AGENT_ID_PREFIX) :]

        try:
            data = base58.b58decode(encoded)
        except Exception as e:
            raise InvalidAgentID(f"Invalid base58 encoding: {e}") from e

        if len(data) != ED25519_PUBLIC_KEY_SIZE + 4:
            raise InvalidAgentID(
                f"Decoded data must be {ED25519_PUBLIC_KEY_SIZE + 4} bytes, got {len(data)}"
            )

        # Verify checksum using constant-time comparison to prevent timing attacks
        public_key = data[:ED25519_PUBLIC_KEY_SIZE]
        checksum = data[ED25519_PUBLIC_KEY_SIZE:]

        from sigaid.crypto.hashing import hash_bytes

        expected_checksum = hash_bytes(public_key)[:4]

        # Use hmac.compare_digest for constant-time comparison
        # This prevents timing attacks that could leak checksum information
        if not hmac.compare_digest(checksum, expected_checksum):
            raise InvalidAgentID("Checksum verification failed")

        return True

    def to_public_key_bytes(self) -> bytes:
        """Extract public key bytes from agent ID.

        Returns:
            32-byte Ed25519 public key
        """
        encoded = self._id[len(AGENT_ID_PREFIX) :]
        data = base58.b58decode(encoded)
        return data[:ED25519_PUBLIC_KEY_SIZE]

    def to_public_key(self):
        """Get Ed25519 public key object.

        Returns:
            Ed25519PublicKey instance
        """
        from sigaid.crypto.keys import public_key_from_bytes

        return public_key_from_bytes(self.to_public_key_bytes())

    @property
    def short(self) -> str:
        """Short form of agent ID (first 8 chars after prefix).

        Returns:
            Shortened ID like "aid_7Xq9YkPz..."
        """
        encoded = self._id[len(AGENT_ID_PREFIX) :]
        return f"{AGENT_ID_PREFIX}{encoded[:8]}..."

    def __str__(self) -> str:
        """String representation."""
        return self._id

    def __repr__(self) -> str:
        """Debug representation."""
        return f"AgentID('{self._id}')"

    def __eq__(self, other: object) -> bool:
        """Equality comparison."""
        if isinstance(other, AgentID):
            return self._id == other._id
        if isinstance(other, str):
            return self._id == other
        return False

    def __hash__(self) -> int:
        """Hash for use in sets/dicts."""
        return hash(self._id)
