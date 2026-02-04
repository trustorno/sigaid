"""BLAKE3 hashing operations for SigAid protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING, Sequence
import struct

import blake3

from sigaid.constants import BLAKE3_HASH_SIZE

if TYPE_CHECKING:
    from sigaid.models.state import StateEntry


def hash_bytes(data: bytes) -> bytes:
    """
    BLAKE3 hash, returns 32 bytes.
    
    Args:
        data: Data to hash
        
    Returns:
        32-byte hash digest
    """
    return blake3.blake3(data).digest()


def hash_hex(data: bytes) -> str:
    """
    BLAKE3 hash, returns hex string.
    
    Args:
        data: Data to hash
        
    Returns:
        64-character hex string
    """
    return blake3.blake3(data).hexdigest()


def hash_multiple(*items: bytes) -> bytes:
    """
    Hash multiple items together.
    
    Items are concatenated with length prefixes to prevent ambiguity.
    
    Args:
        *items: Variable number of byte strings
        
    Returns:
        32-byte hash digest
    """
    hasher = blake3.blake3()
    for item in items:
        # Prefix each item with its 4-byte length
        hasher.update(len(item).to_bytes(4, "big"))
        hasher.update(item)
    return hasher.digest()


def hash_state_entry_fields(
    agent_id: str,
    sequence: int,
    prev_hash: bytes,
    timestamp_iso: str,
    action_type: str,
    action_summary: str,
    action_data_hash: bytes,
) -> bytes:
    """
    Hash state entry fields in canonical order.
    
    This creates the message that gets signed for a state entry.
    
    Args:
        agent_id: Agent identifier
        sequence: Entry sequence number
        prev_hash: Hash of previous entry (32 bytes)
        timestamp_iso: ISO 8601 timestamp string
        action_type: Type of action
        action_summary: Human-readable summary
        action_data_hash: Hash of action data (32 bytes)
        
    Returns:
        32-byte hash digest
    """
    hasher = blake3.blake3()
    
    # Hash fields in canonical order
    hasher.update(agent_id.encode("utf-8"))
    hasher.update(struct.pack(">Q", sequence))  # 8-byte big-endian
    hasher.update(prev_hash)
    hasher.update(timestamp_iso.encode("utf-8"))
    hasher.update(action_type.encode("utf-8"))
    hasher.update(action_summary.encode("utf-8"))
    hasher.update(action_data_hash)
    
    return hasher.digest()


def hash_state_entry(entry: StateEntry) -> bytes:
    """
    Hash a complete state entry including signature.
    
    This creates the entry_hash that links entries in the chain.
    
    Args:
        entry: StateEntry instance
        
    Returns:
        32-byte entry hash
    """
    # Hash all fields including signature
    hasher = blake3.blake3()
    hasher.update(entry.agent_id.encode("utf-8"))
    hasher.update(struct.pack(">Q", entry.sequence))
    hasher.update(entry.prev_hash)
    hasher.update(entry.timestamp.isoformat().encode("utf-8"))
    hasher.update(entry.action_type.value.encode("utf-8"))
    hasher.update(entry.action_summary.encode("utf-8"))
    hasher.update(entry.action_data_hash)
    hasher.update(entry.signature)
    
    return hasher.digest()


def verify_chain_integrity(entries: Sequence[StateEntry]) -> bool:
    """
    Verify state chain integrity.
    
    Checks that:
    1. Sequences are monotonically increasing starting from expected value
    2. Each entry's prev_hash matches the previous entry's entry_hash
    3. Each entry's entry_hash is correctly computed
    
    Args:
        entries: Sequence of StateEntry instances in order
        
    Returns:
        True if chain is valid, False otherwise
    """
    if not entries:
        return True
    
    for i, entry in enumerate(entries):
        # Check prev_hash linkage
        if i == 0:
            # First entry in this segment - prev_hash links to previous segment
            # or is zero hash for genesis
            pass
        else:
            expected_prev = hash_state_entry(entries[i - 1])
            if entry.prev_hash != expected_prev:
                return False
        
        # Verify entry_hash
        computed_hash = hash_state_entry(entry)
        if entry.entry_hash != computed_hash:
            return False
        
        # Verify sequence is monotonically increasing
        if i > 0 and entry.sequence != entries[i - 1].sequence + 1:
            return False
    
    return True


def compute_chain_head_hash(entries: Sequence[StateEntry]) -> bytes:
    """
    Compute the hash that represents the head of a chain.
    
    Args:
        entries: State chain entries
        
    Returns:
        32-byte hash of the chain head, or zero hash if empty
    """
    if not entries:
        return bytes(BLAKE3_HASH_SIZE)
    return hash_state_entry(entries[-1])


# Zero hash constant (for genesis entries)
ZERO_HASH = bytes(BLAKE3_HASH_SIZE)
