"""State chain management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

from sigaid.models.state import StateEntry, ActionType, create_genesis_entry
from sigaid.constants import GENESIS_PREV_HASH
from sigaid.exceptions import StateChainError, InvalidStateEntry

if TYPE_CHECKING:
    from sigaid.crypto.keys import KeyPair
    from sigaid.client.http import HttpClient


class StateChain:
    """Manages the state chain for an agent.

    The state chain is an append-only log of actions performed by the agent.
    Each entry is cryptographically linked to the previous entry, making
    tampering detectable.

    Example:
        chain = StateChain(agent_id, keypair)

        # Record actions
        entry = chain.append(
            action_type=ActionType.TRANSACTION,
            action_summary="Booked hotel",
            action_data={"amount": 180},
        )

        # Get current head
        head = chain.head

        # Verify chain integrity
        chain.verify()
    """

    def __init__(
        self,
        agent_id: str,
        keypair: KeyPair,
        http_client: HttpClient | None = None,
        persistence_path: Path | None = None,
    ):
        """Initialize state chain.

        Args:
            agent_id: Agent identifier
            keypair: Agent's keypair for signing entries
            http_client: HTTP client for Authority API (optional)
            persistence_path: Path to persist chain locally (optional)
        """
        self._agent_id = agent_id
        self._keypair = keypair
        self._http_client = http_client
        self._persistence_path = persistence_path
        self._entries: list[StateEntry] = []
        self._loaded = False

    @property
    def agent_id(self) -> str:
        """Get agent ID."""
        return self._agent_id

    @property
    def head(self) -> StateEntry | None:
        """Get the current head (most recent entry)."""
        return self._entries[-1] if self._entries else None

    @property
    def sequence(self) -> int:
        """Get current sequence number."""
        return len(self._entries) - 1 if self._entries else -1

    @property
    def length(self) -> int:
        """Get number of entries in the chain."""
        return len(self._entries)

    def __len__(self) -> int:
        """Get number of entries."""
        return len(self._entries)

    def __iter__(self) -> Iterator[StateEntry]:
        """Iterate over entries."""
        return iter(self._entries)

    def __getitem__(self, index: int) -> StateEntry:
        """Get entry by index."""
        return self._entries[index]

    async def load(self) -> None:
        """Load chain from persistence or Authority."""
        if self._loaded:
            return

        # Try loading from local persistence first
        if self._persistence_path and self._persistence_path.exists():
            self._load_from_file()
            self._loaded = True
            return

        # Try loading from Authority
        if self._http_client:
            await self._load_from_authority()
            self._loaded = True
            return

        self._loaded = True

    def _load_from_file(self) -> None:
        """Load chain from local file."""
        data = json.loads(self._persistence_path.read_text())
        self._entries = [StateEntry.from_dict(e) for e in data["entries"]]

    async def _load_from_authority(self) -> None:
        """Load chain from Authority service."""
        response = await self._http_client.get(f"/v1/state/{self._agent_id}/history")
        if response.get("entries"):
            self._entries = [StateEntry.from_dict(e) for e in response["entries"]]

    def _save_to_file(self) -> None:
        """Save chain to local file."""
        if not self._persistence_path:
            return

        self._persistence_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "agent_id": self._agent_id,
            "entries": [e.to_dict() for e in self._entries],
        }
        self._persistence_path.write_text(json.dumps(data, indent=2))

    def append(
        self,
        action_type: ActionType | str,
        action_summary: str,
        action_data: dict[str, Any] | None = None,
    ) -> StateEntry:
        """Append a new entry to the chain.

        Args:
            action_type: Type of action
            action_summary: Human-readable summary
            action_data: Full action data (will be hashed)

        Returns:
            The new StateEntry
        """
        # Determine prev_hash and sequence
        if self._entries:
            prev_hash = self._entries[-1].entry_hash
            sequence = len(self._entries)
        else:
            prev_hash = GENESIS_PREV_HASH
            sequence = 0

        # Create entry
        entry = StateEntry.create(
            agent_id=self._agent_id,
            sequence=sequence,
            prev_hash=prev_hash,
            action_type=action_type,
            action_summary=action_summary,
            action_data=action_data,
            keypair=self._keypair,
        )

        self._entries.append(entry)

        # Persist
        self._save_to_file()

        return entry

    async def append_and_sync(
        self,
        action_type: ActionType | str,
        action_summary: str,
        action_data: dict[str, Any] | None = None,
    ) -> StateEntry:
        """Append entry and sync to Authority.

        Args:
            action_type: Type of action
            action_summary: Human-readable summary
            action_data: Full action data

        Returns:
            The new StateEntry
        """
        entry = self.append(action_type, action_summary, action_data)

        if self._http_client:
            await self._sync_entry(entry)

        return entry

    async def _sync_entry(self, entry: StateEntry) -> None:
        """Sync entry to Authority service."""
        await self._http_client.post(
            f"/v1/state/{self._agent_id}",
            json=entry.to_dict(),
        )

    def verify(self) -> bool:
        """Verify chain integrity.

        Returns:
            True if chain is valid

        Raises:
            StateChainError: If chain is invalid
        """
        from sigaid.crypto.hashing import verify_chain

        if not self._entries:
            return True

        # Verify hash chain
        verify_chain(self._entries)

        # Verify all signatures
        public_key = self._keypair.public_key_bytes()
        for entry in self._entries:
            if not entry.verify_signature(public_key):
                raise InvalidStateEntry(f"Invalid signature at sequence {entry.sequence}")

        return True

    def get_entries_since(self, sequence: int) -> list[StateEntry]:
        """Get entries since a given sequence number.

        Args:
            sequence: Starting sequence (exclusive)

        Returns:
            List of entries after the given sequence
        """
        return [e for e in self._entries if e.sequence > sequence]

    def get_entry_by_hash(self, entry_hash: bytes) -> StateEntry | None:
        """Find entry by its hash.

        Args:
            entry_hash: Entry hash to find

        Returns:
            StateEntry if found, None otherwise
        """
        for entry in self._entries:
            if entry.entry_hash == entry_hash:
                return entry
        return None

    def initialize(self, summary: str = "Agent created") -> StateEntry:
        """Initialize chain with genesis entry.

        Args:
            summary: Summary for genesis entry

        Returns:
            Genesis StateEntry

        Raises:
            StateChainError: If chain is already initialized
        """
        if self._entries:
            raise StateChainError("Chain already initialized")

        entry = create_genesis_entry(self._agent_id, self._keypair, summary)
        self._entries.append(entry)
        self._save_to_file()
        return entry

    def clear(self) -> None:
        """Clear all entries (use with caution!)."""
        self._entries = []
        if self._persistence_path and self._persistence_path.exists():
            self._persistence_path.unlink()
