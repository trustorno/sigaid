"""State chain verification utilities."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Sequence

from sigaid.crypto.hashing import ZERO_HASH, hash_state_entry, verify_chain_integrity
from sigaid.crypto.signing import verify_with_domain
from sigaid.constants import DOMAIN_STATE
from sigaid.exceptions import (
    ForkDetected,
    InvalidStateEntry,
    StateChainBroken,
    StateChainError,
)
from sigaid.models.state import StateEntry

if TYPE_CHECKING:
    pass


def verify_entry(
    entry: StateEntry,
    public_key: bytes,
    prev_entry: StateEntry | None = None,
) -> bool:
    """
    Verify a single state entry.
    
    Checks:
    - Signature is valid
    - Entry hash is correct
    - Links correctly to previous entry (if provided)
    
    Args:
        entry: Entry to verify
        public_key: Agent's public key
        prev_entry: Previous entry (optional)
        
    Returns:
        True if entry is valid
    """
    # Verify signature
    if not entry.verify_signature(public_key):
        return False
    
    # Verify hash
    if not entry.verify_hash():
        return False
    
    # Verify linkage to previous
    if prev_entry is not None:
        if entry.prev_hash != prev_entry.entry_hash:
            return False
        if entry.sequence != prev_entry.sequence + 1:
            return False
    elif entry.sequence == 0:
        # Genesis entry should have zero prev_hash
        if entry.prev_hash != ZERO_HASH:
            return False
    
    return True


def verify_chain(
    entries: Sequence[StateEntry],
    public_key: bytes,
) -> bool:
    """
    Verify an entire state chain.
    
    Args:
        entries: Sequence of entries in order
        public_key: Agent's public key
        
    Returns:
        True if entire chain is valid
    """
    if not entries:
        return True
    
    # Check first entry
    first = entries[0]
    if first.sequence == 0:
        if first.prev_hash != ZERO_HASH:
            return False
    
    # Verify each entry and linkage
    for i, entry in enumerate(entries):
        prev = entries[i - 1] if i > 0 else None
        if not verify_entry(entry, public_key, prev):
            return False
    
    return True


class StateVerifier:
    """
    Stateful verifier that tracks known state heads.
    
    Used by services to verify agents' state chains and detect forks.
    
    Example:
        verifier = StateVerifier()
        
        # First interaction - records head
        verifier.verify_head(agent_id, entry1, public_key)
        
        # Later interaction - checks for fork
        verifier.verify_head(agent_id, entry2, public_key)
    """
    
    def __init__(self):
        """Initialize verifier with empty state."""
        # agent_id -> (sequence, entry_hash)
        self._known_heads: dict[str, tuple[int, bytes]] = {}
    
    def verify_head(
        self,
        agent_id: str,
        claimed_head: StateEntry,
        public_key: bytes,
        *,
        max_age: timedelta | None = None,
    ) -> bool:
        """
        Verify a claimed state head against known state.
        
        Args:
            agent_id: Agent identifier
            claimed_head: Agent's claimed state head
            public_key: Agent's public key
            max_age: Optional maximum age for the entry
            
        Returns:
            True if valid and consistent
            
        Raises:
            ForkDetected: If state chain has forked
            InvalidStateEntry: If entry is invalid
        """
        # Verify the entry itself
        if not claimed_head.verify_signature(public_key):
            raise InvalidStateEntry("Invalid signature on state head")
        
        if not claimed_head.verify_hash():
            raise InvalidStateEntry("Invalid hash on state head")
        
        # Check age if specified
        if max_age is not None:
            age = datetime.now(timezone.utc) - claimed_head.timestamp
            if age > max_age:
                raise InvalidStateEntry(
                    f"State head is too old: {age.total_seconds():.0f}s > {max_age.total_seconds():.0f}s"
                )
        
        # Check against known head
        known = self._known_heads.get(agent_id)
        
        if known is None:
            # First interaction - record this head
            self._known_heads[agent_id] = (claimed_head.sequence, claimed_head.entry_hash)
            return True
        
        known_seq, known_hash = known
        
        # Same sequence - must have same hash
        if claimed_head.sequence == known_seq:
            if claimed_head.entry_hash != known_hash:
                raise ForkDetected(
                    agent_id,
                    expected_hash=known_hash,
                    actual_hash=claimed_head.entry_hash,
                    sequence=known_seq,
                )
            return True
        
        # Claimed is behind known - suspicious but not necessarily a fork
        if claimed_head.sequence < known_seq:
            # This could be legitimate (old cached state) or a fork
            # We can't tell without fetching the full chain
            # For now, reject as stale
            raise InvalidStateEntry(
                f"State head is behind known: {claimed_head.sequence} < {known_seq}"
            )
        
        # Claimed is ahead - update known head
        # (In a full implementation, we'd verify the chain extends properly)
        self._known_heads[agent_id] = (claimed_head.sequence, claimed_head.entry_hash)
        return True
    
    def get_known_head(self, agent_id: str) -> tuple[int, bytes] | None:
        """
        Get known head for an agent.
        
        Returns:
            Tuple of (sequence, entry_hash) or None
        """
        return self._known_heads.get(agent_id)
    
    def clear_agent(self, agent_id: str) -> None:
        """Clear known head for an agent."""
        self._known_heads.pop(agent_id, None)
    
    def clear_all(self) -> None:
        """Clear all known heads."""
        self._known_heads.clear()


def detect_fork(
    chain_a: Sequence[StateEntry],
    chain_b: Sequence[StateEntry],
) -> int | None:
    """
    Detect where two chains fork.
    
    Args:
        chain_a: First chain
        chain_b: Second chain
        
    Returns:
        Sequence number where fork occurred, or None if no fork
    """
    if not chain_a or not chain_b:
        return None
    
    # Find common prefix length
    min_len = min(len(chain_a), len(chain_b))
    
    for i in range(min_len):
        if chain_a[i].entry_hash != chain_b[i].entry_hash:
            return chain_a[i].sequence
    
    return None
