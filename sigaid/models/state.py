"""State chain data models."""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, TYPE_CHECKING

from sigaid.constants import BLAKE3_HASH_SIZE, DOMAIN_STATE, ED25519_SIGNATURE_SIZE

if TYPE_CHECKING:
    from sigaid.crypto.keys import KeyPair


class ActionType(str, Enum):
    """Types of actions that can be recorded in state chain."""
    TRANSACTION = "transaction"      # External transaction (payment, booking, etc.)
    ATTESTATION = "attestation"      # Third-party attestation
    UPGRADE = "upgrade"              # Agent upgrade/migration
    RESET = "reset"                  # State reset (with Authority approval)
    CUSTOM = "custom"                # Custom action type
    
    # Common agent actions
    TOOL_CALL = "tool_call"          # Tool/function invocation
    LLM_REQUEST = "llm_request"      # LLM API call
    DECISION = "decision"            # Agent decision point
    TASK_START = "task_start"        # Task started
    TASK_COMPLETE = "task_complete"  # Task completed
    ERROR = "error"                  # Error occurred


@dataclass(frozen=True)
class StateEntry:
    """
    Immutable state chain entry.
    
    Each entry is cryptographically linked to the previous entry,
    forming a tamper-evident chain of agent actions.
    
    Structure:
        prev_hash -> points to previous entry
        sequence -> monotonically increasing
        entry_hash -> hash of this entry (for next entry's prev_hash)
    """
    agent_id: str
    sequence: int
    prev_hash: bytes
    timestamp: datetime
    action_type: ActionType
    action_summary: str
    action_data_hash: bytes
    signature: bytes
    entry_hash: bytes
    
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
    
    def signable_bytes(self) -> bytes:
        """
        Get bytes that are signed for this entry.
        
        This is all fields except signature and entry_hash.
        """
        return (
            self.agent_id.encode("utf-8") +
            struct.pack(">Q", self.sequence) +
            self.prev_hash +
            self.timestamp.isoformat().encode("utf-8") +
            self.action_type.value.encode("utf-8") +
            self.action_summary.encode("utf-8") +
            self.action_data_hash
        )
    
    def verify_signature(self, public_key: bytes) -> bool:
        """
        Verify entry signature against public key.
        
        Args:
            public_key: 32-byte Ed25519 public key
            
        Returns:
            True if signature is valid
        """
        from sigaid.crypto.signing import verify_with_domain
        return verify_with_domain(
            public_key,
            self.signature,
            self.signable_bytes(),
            DOMAIN_STATE,
        )
    
    def verify_hash(self) -> bool:
        """
        Verify entry_hash is correctly computed.
        
        Returns:
            True if hash matches
        """
        from sigaid.crypto.hashing import hash_state_entry
        computed = hash_state_entry(self)
        return computed == self.entry_hash
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "sequence": self.sequence,
            "prev_hash": self.prev_hash.hex(),
            "timestamp": self.timestamp.isoformat(),
            "action_type": self.action_type.value,
            "action_summary": self.action_summary,
            "action_data_hash": self.action_data_hash.hex(),
            "signature": self.signature.hex(),
            "entry_hash": self.entry_hash.hex(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StateEntry:
        """Create from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            sequence=data["sequence"],
            prev_hash=bytes.fromhex(data["prev_hash"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            action_type=ActionType(data["action_type"]),
            action_summary=data["action_summary"],
            action_data_hash=bytes.fromhex(data["action_data_hash"]),
            signature=bytes.fromhex(data["signature"]),
            entry_hash=bytes.fromhex(data["entry_hash"]),
        )
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes for transmission."""
        return json.dumps(self.to_dict()).encode("utf-8")
    
    @classmethod
    def from_bytes(cls, data: bytes) -> StateEntry:
        """Deserialize from bytes."""
        return cls.from_dict(json.loads(data.decode("utf-8")))
    
    def __repr__(self) -> str:
        return (
            f"StateEntry(seq={self.sequence}, "
            f"action={self.action_type.value}, "
            f"hash={self.entry_hash.hex()[:16]}...)"
        )


@dataclass
class StateEntryBuilder:
    """
    Builder for creating new state entries.
    
    Example:
        builder = StateEntryBuilder(agent_id, keypair)
        entry = builder.build(
            prev_entry=last_entry,
            action_type=ActionType.TRANSACTION,
            action_summary="Booked hotel for $180",
            action_data={"hotel_id": "123", "amount": 180},
        )
    """
    agent_id: str
    keypair: KeyPair
    
    def build(
        self,
        prev_entry: StateEntry | None,
        action_type: ActionType,
        action_summary: str,
        action_data: dict[str, Any] | None = None,
    ) -> StateEntry:
        """
        Build and sign a new state entry.
        
        Args:
            prev_entry: Previous entry in chain (None for genesis)
            action_type: Type of action
            action_summary: Human-readable summary
            action_data: Optional action data (will be hashed)
            
        Returns:
            Signed StateEntry
        """
        from sigaid.crypto.hashing import hash_bytes, hash_state_entry, ZERO_HASH
        
        # Determine sequence and prev_hash
        if prev_entry is None:
            sequence = 0
            prev_hash = ZERO_HASH
        else:
            sequence = prev_entry.sequence + 1
            prev_hash = prev_entry.entry_hash
        
        # Hash action data
        if action_data:
            action_data_bytes = json.dumps(action_data, sort_keys=True).encode("utf-8")
            action_data_hash = hash_bytes(action_data_bytes)
        else:
            action_data_hash = ZERO_HASH
        
        timestamp = datetime.now(timezone.utc)
        
        # Create unsigned entry (with placeholder signature and hash)
        temp_signature = bytes(ED25519_SIGNATURE_SIZE)
        temp_hash = bytes(BLAKE3_HASH_SIZE)
        
        # Build signable content
        signable = (
            self.agent_id.encode("utf-8") +
            struct.pack(">Q", sequence) +
            prev_hash +
            timestamp.isoformat().encode("utf-8") +
            action_type.value.encode("utf-8") +
            action_summary.encode("utf-8") +
            action_data_hash
        )
        
        # Sign with domain separation
        signature = self.keypair.sign_with_domain(signable, DOMAIN_STATE)
        
        # Create entry with signature (but temp hash)
        entry_no_hash = StateEntry(
            agent_id=self.agent_id,
            sequence=sequence,
            prev_hash=prev_hash,
            timestamp=timestamp,
            action_type=action_type,
            action_summary=action_summary,
            action_data_hash=action_data_hash,
            signature=signature,
            entry_hash=temp_hash,  # Placeholder
        )
        
        # Compute final entry hash
        entry_hash = hash_state_entry(entry_no_hash)
        
        # Return final entry
        return StateEntry(
            agent_id=self.agent_id,
            sequence=sequence,
            prev_hash=prev_hash,
            timestamp=timestamp,
            action_type=action_type,
            action_summary=action_summary,
            action_data_hash=action_data_hash,
            signature=signature,
            entry_hash=entry_hash,
        )
