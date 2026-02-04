"""BLAKE3 hashing operations for SigAid."""

from __future__ import annotations

from typing import TYPE_CHECKING

import blake3

if TYPE_CHECKING:
    from sigaid.models.state import StateEntry


def hash_bytes(data: bytes) -> bytes:
    """BLAKE3 hash, returns 32 bytes.

    Args:
        data: Data to hash

    Returns:
        32-byte hash digest
    """
    return blake3.blake3(data).digest()


def hash_hex(data: bytes) -> str:
    """BLAKE3 hash, returns hex string.

    Args:
        data: Data to hash

    Returns:
        64-character hex string
    """
    return blake3.blake3(data).hexdigest()


def hash_multiple(*parts: bytes) -> bytes:
    """Hash multiple byte strings together.

    Args:
        *parts: Byte strings to hash together

    Returns:
        32-byte hash digest
    """
    hasher = blake3.blake3()
    for part in parts:
        hasher.update(part)
    return hasher.digest()


def hash_state_entry(entry: StateEntry) -> bytes:
    """Hash state entry in canonical form.

    The canonical form includes all fields except the entry_hash itself.

    Args:
        entry: StateEntry to hash

    Returns:
        32-byte hash of the entry
    """
    canonical = entry.to_signable_bytes()
    return hash_bytes(canonical)


def verify_chain(entries: list[StateEntry]) -> bool:
    """Verify state chain integrity.

    Checks that:
    1. Each entry's prev_hash matches the previous entry's entry_hash
    2. Each entry's entry_hash is correctly computed
    3. Genesis entry has zero prev_hash

    Args:
        entries: List of state entries in sequence order

    Returns:
        True if chain is valid

    Raises:
        ChainIntegrityError: If chain verification fails
    """
    from sigaid.constants import GENESIS_PREV_HASH
    from sigaid.exceptions import ChainIntegrityError

    if not entries:
        return True

    for i, entry in enumerate(entries):
        # Check genesis has zero prev_hash
        if i == 0:
            if entry.prev_hash != GENESIS_PREV_HASH:
                raise ChainIntegrityError(
                    f"Genesis entry has non-zero prev_hash: {entry.prev_hash.hex()}"
                )
        else:
            # Check prev_hash links to previous entry
            expected_prev = entries[i - 1].entry_hash
            if entry.prev_hash != expected_prev:
                raise ChainIntegrityError(
                    f"Entry {i} prev_hash mismatch: expected {expected_prev.hex()}, "
                    f"got {entry.prev_hash.hex()}"
                )

        # Verify entry's own hash
        computed_hash = hash_state_entry(entry)
        if entry.entry_hash != computed_hash:
            raise ChainIntegrityError(
                f"Entry {i} hash mismatch: expected {computed_hash.hex()}, "
                f"got {entry.entry_hash.hex()}"
            )

    return True


def compute_entry_hash(
    agent_id: str,
    sequence: int,
    prev_hash: bytes,
    timestamp_iso: str,
    action_type: str,
    action_summary: str,
    action_data_hash: bytes,
    signature: bytes,
) -> bytes:
    """Compute hash for a state entry from its components.

    Args:
        agent_id: Agent identifier
        sequence: Sequence number
        prev_hash: Previous entry hash (32 bytes)
        timestamp_iso: ISO 8601 timestamp
        action_type: Action type string
        action_summary: Action summary
        action_data_hash: Hash of action data (32 bytes)
        signature: Entry signature (64 bytes)

    Returns:
        32-byte entry hash
    """
    parts = [
        agent_id.encode("utf-8"),
        sequence.to_bytes(8, "big"),
        prev_hash,
        timestamp_iso.encode("utf-8"),
        action_type.encode("utf-8"),
        action_summary.encode("utf-8"),
        action_data_hash,
        signature,
    ]
    return hash_multiple(*parts)
