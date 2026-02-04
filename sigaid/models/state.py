"""State chain entry model."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sigaid.constants import GENESIS_PREV_HASH, BLAKE3_HASH_SIZE, ED25519_SIGNATURE_SIZE


class ActionType(str, Enum):
    """Types of actions that can be recorded in the state chain."""

    TRANSACTION = "transaction"  # Financial or resource transaction
    ATTESTATION = "attestation"  # Third-party attestation
    UPGRADE = "upgrade"  # Agent capability upgrade
    RESET = "reset"  # State reset (with authority approval)
    CUSTOM = "custom"  # Custom action type


@dataclass(frozen=True)
class StateEntry:
    """Immutable state chain entry.

    Each entry in the state chain contains:
    - Link to previous entry (prev_hash)
    - Monotonic sequence number
    - Timestamp
    - Action details
    - Signature proving agent performed the action
    - Entry hash for integrity verification

    Example:
        entry = StateEntry.create(
            agent_id="aid_xxx",
            sequence=1,
            prev_hash=GENESIS_PREV_HASH,
            action_type=ActionType.TRANSACTION,
            action_summary="Booked hotel room",
            action_data={"hotel": "Hilton", "amount": 180},
            keypair=my_keypair,
        )
    """

    agent_id: str
    sequence: int
    prev_hash: bytes  # 32 bytes
    timestamp: datetime
    action_type: ActionType
    action_summary: str
    action_data_hash: bytes  # 32 bytes, hash of full data
    signature: bytes  # 64 bytes, Ed25519 signature
    entry_hash: bytes  # 32 bytes, hash of this entry

    def __post_init__(self) -> None:
        """Validate field sizes."""
        if len(self.prev_hash) != BLAKE3_HASH_SIZE:
            raise ValueError(f"prev_hash must be {BLAKE3_HASH_SIZE} bytes")
        if len(self.action_data_hash) != BLAKE3_HASH_SIZE:
            raise ValueError(f"action_data_hash must be {BLAKE3_HASH_SIZE} bytes")
        if len(self.signature) != ED25519_SIGNATURE_SIZE:
            raise ValueError(f"signature must be {ED25519_SIGNATURE_SIZE} bytes")
        if len(self.entry_hash) != BLAKE3_HASH_SIZE:
            raise ValueError(f"entry_hash must be {BLAKE3_HASH_SIZE} bytes")

    @classmethod
    def create(
        cls,
        agent_id: str,
        sequence: int,
        prev_hash: bytes,
        action_type: ActionType | str,
        action_summary: str,
        action_data: dict[str, Any] | None,
        keypair: Any,  # KeyPair
        timestamp: datetime | None = None,
    ) -> StateEntry:
        """Create a new state entry with automatic signing.

        Args:
            agent_id: Agent identifier
            sequence: Sequence number (must be prev + 1)
            prev_hash: Hash of previous entry (or GENESIS_PREV_HASH for first)
            action_type: Type of action
            action_summary: Human-readable summary
            action_data: Full action data (will be hashed)
            keypair: Agent's keypair for signing
            timestamp: Entry timestamp (defaults to now)

        Returns:
            Signed StateEntry
        """
        from sigaid.crypto.hashing import hash_bytes, compute_entry_hash
        from sigaid.constants import DOMAIN_STATE

        if isinstance(action_type, str):
            action_type = ActionType(action_type)

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        # Hash action data
        if action_data:
            action_data_bytes = json.dumps(action_data, sort_keys=True).encode("utf-8")
            action_data_hash = hash_bytes(action_data_bytes)
        else:
            action_data_hash = bytes(BLAKE3_HASH_SIZE)

        # Create signable content
        timestamp_iso = timestamp.isoformat()
        signable = cls._create_signable(
            agent_id=agent_id,
            sequence=sequence,
            prev_hash=prev_hash,
            timestamp_iso=timestamp_iso,
            action_type=action_type.value,
            action_summary=action_summary,
            action_data_hash=action_data_hash,
        )

        # Sign
        signature = keypair.sign(signable, domain=DOMAIN_STATE)

        # Compute entry hash
        entry_hash = compute_entry_hash(
            agent_id=agent_id,
            sequence=sequence,
            prev_hash=prev_hash,
            timestamp_iso=timestamp_iso,
            action_type=action_type.value,
            action_summary=action_summary,
            action_data_hash=action_data_hash,
            signature=signature,
        )

        return cls(
            agent_id=agent_id,
            sequence=sequence,
            prev_hash=prev_hash,
            timestamp=timestamp,
            action_type=action_type,
            action_summary=action_summary,
            action_data_hash=action_data_hash,
            signature=signature,
            entry_hash=entry_hash,
        )

    @staticmethod
    def _create_signable(
        agent_id: str,
        sequence: int,
        prev_hash: bytes,
        timestamp_iso: str,
        action_type: str,
        action_summary: str,
        action_data_hash: bytes,
    ) -> bytes:
        """Create signable bytes for an entry."""
        parts = [
            agent_id.encode("utf-8"),
            sequence.to_bytes(8, "big"),
            prev_hash,
            timestamp_iso.encode("utf-8"),
            action_type.encode("utf-8"),
            action_summary.encode("utf-8"),
            action_data_hash,
        ]
        return b"".join(parts)

    def to_signable_bytes(self) -> bytes:
        """Get canonical bytes for hashing/signing (excludes entry_hash).

        Returns:
            Canonical byte representation
        """
        parts = [
            self.agent_id.encode("utf-8"),
            self.sequence.to_bytes(8, "big"),
            self.prev_hash,
            self.timestamp.isoformat().encode("utf-8"),
            self.action_type.value.encode("utf-8"),
            self.action_summary.encode("utf-8"),
            self.action_data_hash,
            self.signature,
        ]
        return b"".join(parts)

    def to_bytes(self) -> bytes:
        """Serialize to bytes for storage/transmission.

        Returns:
            Complete serialized entry
        """
        return self.to_signable_bytes() + self.entry_hash

    def verify_signature(self, public_key: bytes) -> bool:
        """Verify entry signature against public key.

        Args:
            public_key: 32-byte Ed25519 public key

        Returns:
            True if signature is valid
        """
        from sigaid.crypto.keys import public_key_from_bytes
        from sigaid.crypto.signing import verify_with_domain_safe
        from sigaid.constants import DOMAIN_STATE

        pk = public_key_from_bytes(public_key)
        signable = self._create_signable(
            agent_id=self.agent_id,
            sequence=self.sequence,
            prev_hash=self.prev_hash,
            timestamp_iso=self.timestamp.isoformat(),
            action_type=self.action_type.value,
            action_summary=self.action_summary,
            action_data_hash=self.action_data_hash,
        )
        return verify_with_domain_safe(pk, self.signature, signable, DOMAIN_STATE)

    def verify_hash(self) -> bool:
        """Verify entry_hash matches computed hash.

        Returns:
            True if hash is valid
        """
        from sigaid.crypto.hashing import hash_state_entry

        computed = hash_state_entry(self)
        return self.entry_hash == computed

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization.

        Returns:
            Dictionary representation
        """
        import base64

        return {
            "agent_id": self.agent_id,
            "sequence": self.sequence,
            "prev_hash": base64.b64encode(self.prev_hash).decode("ascii"),
            "timestamp": self.timestamp.isoformat(),
            "action_type": self.action_type.value,
            "action_summary": self.action_summary,
            "action_data_hash": base64.b64encode(self.action_data_hash).decode("ascii"),
            "signature": base64.b64encode(self.signature).decode("ascii"),
            "entry_hash": base64.b64encode(self.entry_hash).decode("ascii"),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StateEntry:
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            StateEntry instance
        """
        import base64

        return cls(
            agent_id=data["agent_id"],
            sequence=data["sequence"],
            prev_hash=base64.b64decode(data["prev_hash"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            action_type=ActionType(data["action_type"]),
            action_summary=data["action_summary"],
            action_data_hash=base64.b64decode(data["action_data_hash"]),
            signature=base64.b64decode(data["signature"]),
            entry_hash=base64.b64decode(data["entry_hash"]),
        )


def create_genesis_entry(
    agent_id: str,
    keypair: Any,  # KeyPair
    action_summary: str = "Agent created",
) -> StateEntry:
    """Create the genesis (first) entry for an agent.

    Args:
        agent_id: Agent identifier
        keypair: Agent's keypair
        action_summary: Summary for genesis entry

    Returns:
        Genesis StateEntry with sequence 0
    """
    return StateEntry.create(
        agent_id=agent_id,
        sequence=0,
        prev_hash=GENESIS_PREV_HASH,
        action_type=ActionType.ATTESTATION,
        action_summary=action_summary,
        action_data={"event": "genesis"},
        keypair=keypair,
    )
