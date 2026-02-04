"""State chain verification utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sigaid.models.state import StateEntry
from sigaid.exceptions import ForkDetected, ChainIntegrityError, InvalidStateEntry
from sigaid.crypto.hashing import hash_state_entry, verify_chain

if TYPE_CHECKING:
    pass


class ChainVerifier:
    """Verifies state chain integrity and detects forks.

    The ChainVerifier maintains knowledge of agent state heads
    and can detect if an agent presents a forked chain.

    Example:
        verifier = ChainVerifier()

        # Verify a claimed head
        try:
            verifier.verify_head(agent_id, claimed_head)
        except ForkDetected as e:
            print(f"Fork detected: {e}")
    """

    def __init__(self):
        """Initialize verifier."""
        self._known_heads: dict[str, StateEntry] = {}

    def record_head(self, agent_id: str, head: StateEntry) -> None:
        """Record known head for an agent.

        Args:
            agent_id: Agent identifier
            head: State entry to record as head
        """
        self._known_heads[agent_id] = head

    def get_known_head(self, agent_id: str) -> StateEntry | None:
        """Get known head for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Known StateEntry or None
        """
        return self._known_heads.get(agent_id)

    def verify_head(
        self,
        agent_id: str,
        claimed_head: StateEntry,
        chain: list[StateEntry] | None = None,
    ) -> bool:
        """Verify a claimed head against known state.

        Args:
            agent_id: Agent identifier
            claimed_head: Claimed state head
            chain: Optional chain entries for full verification

        Returns:
            True if verified

        Raises:
            ForkDetected: If fork is detected
            InvalidStateEntry: If entry is invalid
        """
        # Verify entry integrity
        if not claimed_head.verify_hash():
            raise InvalidStateEntry("Entry hash verification failed")

        known_head = self._known_heads.get(agent_id)

        if known_head is None:
            # First interaction - accept and record
            self._known_heads[agent_id] = claimed_head
            return True

        # Check sequence ordering
        if claimed_head.sequence < known_head.sequence:
            raise ForkDetected(
                agent_id,
                expected_seq=known_head.sequence,
                found_seq=claimed_head.sequence,
                message="Claimed head is behind known head",
            )

        if claimed_head.sequence == known_head.sequence:
            if claimed_head.entry_hash != known_head.entry_hash:
                raise ForkDetected(
                    agent_id,
                    expected_seq=known_head.sequence,
                    found_seq=claimed_head.sequence,
                    message="Same sequence, different hash",
                )
            return True

        # claimed_head.sequence > known_head.sequence
        # Need to verify chain continuity
        if chain:
            self._verify_chain_extends(known_head, claimed_head, chain)

        # Update known head
        self._known_heads[agent_id] = claimed_head
        return True

    def _verify_chain_extends(
        self,
        known_head: StateEntry,
        claimed_head: StateEntry,
        chain: list[StateEntry],
    ) -> None:
        """Verify that chain properly extends from known head to claimed head.

        Args:
            known_head: Known state head
            claimed_head: Claimed new head
            chain: Chain entries between known and claimed

        Raises:
            ForkDetected: If chain doesn't properly extend
            ChainIntegrityError: If chain is invalid
        """
        # Find known head in chain
        known_idx = None
        for i, entry in enumerate(chain):
            if entry.entry_hash == known_head.entry_hash:
                known_idx = i
                break

        if known_idx is None:
            raise ForkDetected(
                known_head.agent_id,
                expected_seq=known_head.sequence,
                found_seq=claimed_head.sequence,
                message="Known head not found in provided chain",
            )

        # Verify chain from known head to claimed head
        relevant_chain = chain[known_idx:]
        verify_chain(relevant_chain)

        # Verify claimed head is at end
        if chain[-1].entry_hash != claimed_head.entry_hash:
            raise ForkDetected(
                known_head.agent_id,
                expected_seq=claimed_head.sequence,
                found_seq=chain[-1].sequence,
                message="Claimed head doesn't match chain end",
            )

    def verify_chain_integrity(self, entries: list[StateEntry]) -> bool:
        """Verify integrity of a chain of entries.

        Args:
            entries: List of entries to verify

        Returns:
            True if chain is valid

        Raises:
            ChainIntegrityError: If chain is invalid
        """
        return verify_chain(entries)

    def verify_entry_signature(self, entry: StateEntry, public_key: bytes) -> bool:
        """Verify an entry's signature.

        Args:
            entry: Entry to verify
            public_key: Agent's public key

        Returns:
            True if signature is valid
        """
        return entry.verify_signature(public_key)

    def clear_agent(self, agent_id: str) -> None:
        """Clear known state for an agent.

        Args:
            agent_id: Agent identifier
        """
        self._known_heads.pop(agent_id, None)

    def clear_all(self) -> None:
        """Clear all known state."""
        self._known_heads.clear()
