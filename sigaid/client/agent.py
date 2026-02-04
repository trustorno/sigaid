"""Main agent client for SigAid protocol."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, TYPE_CHECKING

from sigaid.crypto.keys import KeyPair
from sigaid.identity.agent_id import AgentID
from sigaid.lease.manager import LeaseManager
from sigaid.state.chain import StateChain
from sigaid.verification.prover import Prover
from sigaid.models.state import StateEntry, ActionType
from sigaid.models.proof import ProofBundle
from sigaid.models.lease import Lease
from sigaid.constants import DEFAULT_AUTHORITY_URL
from sigaid.exceptions import LeaseNotHeld

if TYPE_CHECKING:
    from sigaid.client.http import HttpClient


class AgentClient:
    """Main SDK entry point for agents.

    The AgentClient provides a high-level interface for:
    - Acquiring exclusive leases
    - Recording actions to the state chain
    - Creating verification proofs

    Example:
        # Create new agent
        client = AgentClient.create()

        # Use with lease
        async with client.lease() as lease:
            # Record an action
            await client.record_action(
                "booked_hotel",
                {"hotel": "Hilton", "amount": 180}
            )

            # Create proof for verification
            proof = client.create_proof(challenge=b"abc123")

        # Clean up
        await client.close()
    """

    def __init__(
        self,
        agent_id: AgentID,
        keypair: KeyPair,
        authority_url: str = DEFAULT_AUTHORITY_URL,
        *,
        auto_renew_lease: bool = True,
        state_persistence_path: Path | None = None,
        http_client: HttpClient | None = None,
    ):
        """Initialize agent client.

        Args:
            agent_id: Agent identifier
            keypair: Agent's keypair
            authority_url: URL of Authority service
            auto_renew_lease: Whether to auto-renew leases
            state_persistence_path: Path for local state persistence
            http_client: Optional pre-configured HTTP client
        """
        self._agent_id = agent_id
        self._keypair = keypair
        self._authority_url = authority_url
        self._auto_renew = auto_renew_lease
        self._state_path = state_persistence_path
        self._http_client = http_client
        self._owns_http_client = http_client is None

        # Components (lazily initialized)
        self._lease_manager: LeaseManager | None = None
        self._state_chain: StateChain | None = None
        self._prover: Prover | None = None
        self._initialized = False

    @classmethod
    def create(
        cls,
        authority_url: str = DEFAULT_AUTHORITY_URL,
        **kwargs,
    ) -> AgentClient:
        """Create new agent with fresh identity.

        Args:
            authority_url: URL of Authority service
            **kwargs: Additional arguments for __init__

        Returns:
            New AgentClient with generated keypair
        """
        keypair = KeyPair.generate()
        agent_id = keypair.to_agent_id()
        return cls(agent_id, keypair, authority_url, **kwargs)

    @classmethod
    def from_keypair(
        cls,
        keypair: KeyPair,
        authority_url: str = DEFAULT_AUTHORITY_URL,
        **kwargs,
    ) -> AgentClient:
        """Create client from existing keypair.

        Args:
            keypair: Existing KeyPair
            authority_url: URL of Authority service
            **kwargs: Additional arguments for __init__

        Returns:
            AgentClient with the given keypair
        """
        agent_id = keypair.to_agent_id()
        return cls(agent_id, keypair, authority_url, **kwargs)

    @classmethod
    def from_file(
        cls,
        path: Path,
        password: str,
        authority_url: str = DEFAULT_AUTHORITY_URL,
        **kwargs,
    ) -> AgentClient:
        """Load agent from encrypted keyfile.

        Args:
            path: Path to encrypted keyfile
            password: Decryption password
            authority_url: URL of Authority service
            **kwargs: Additional arguments for __init__

        Returns:
            AgentClient loaded from file
        """
        keypair = KeyPair.from_encrypted_file(path, password)
        agent_id = keypair.to_agent_id()
        return cls(agent_id, keypair, authority_url, **kwargs)

    @property
    def agent_id(self) -> AgentID:
        """Get agent ID."""
        return self._agent_id

    @property
    def keypair(self) -> KeyPair:
        """Get keypair."""
        return self._keypair

    @property
    def state_head(self) -> StateEntry | None:
        """Get current state chain head."""
        if self._state_chain:
            return self._state_chain.head
        return None

    @property
    def has_lease(self) -> bool:
        """Check if agent holds a valid lease."""
        return self._lease_manager is not None and self._lease_manager.has_lease

    @property
    def current_lease(self) -> Lease | None:
        """Get current lease if held."""
        if self._lease_manager:
            return self._lease_manager.current_lease
        return None

    async def _initialize(self) -> None:
        """Initialize components."""
        if self._initialized:
            return

        # Create HTTP client if needed
        if self._http_client is None and self._authority_url:
            from sigaid.client.http import HttpClient

            self._http_client = HttpClient(self._authority_url)

        # Initialize components
        self._lease_manager = LeaseManager(
            keypair=self._keypair,
            http_client=self._http_client,
            auto_renew=self._auto_renew,
        )

        self._state_chain = StateChain(
            agent_id=str(self._agent_id),
            keypair=self._keypair,
            http_client=self._http_client,
            persistence_path=self._state_path,
        )

        self._prover = Prover(self._keypair)

        # Load state
        await self._state_chain.load()

        self._initialized = True

    @asynccontextmanager
    async def lease(self) -> AsyncIterator[Lease]:
        """Acquire exclusive lease as async context manager.

        Yields:
            Active Lease object

        Raises:
            LeaseHeldByAnotherInstance: If another instance holds the lease

        Example:
            async with client.lease() as lease:
                print(f"Lease acquired until {lease.expires_at}")
                # Do work...
        """
        await self._initialize()
        async with self._lease_manager.acquire() as lease:
            yield lease

    async def acquire_lease(self) -> Lease:
        """Acquire exclusive lease (manual management).

        Call release_lease() when done.

        Returns:
            Acquired Lease

        Raises:
            LeaseHeldByAnotherInstance: If another instance holds the lease
        """
        await self._initialize()
        return await self._lease_manager.acquire_lease()

    async def release_lease(self) -> None:
        """Release current lease."""
        if self._lease_manager:
            await self._lease_manager.release_lease()

    async def record_action(
        self,
        action_type: ActionType | str,
        action_data: dict[str, Any] | None = None,
        action_summary: str | None = None,
        *,
        require_lease: bool = True,
        sync_to_authority: bool = True,
    ) -> StateEntry:
        """Record an action to the state chain.

        Args:
            action_type: Type of action (e.g., "transaction")
            action_data: Full action data (will be hashed)
            action_summary: Human-readable summary (auto-generated if not provided)
            require_lease: Whether to require an active lease
            sync_to_authority: Whether to sync to Authority service

        Returns:
            The new StateEntry

        Raises:
            LeaseNotHeld: If require_lease is True and no lease held
        """
        await self._initialize()

        if require_lease and not self.has_lease:
            raise LeaseNotHeld("Action requires an active lease")

        if action_summary is None:
            action_summary = f"Action: {action_type}"

        if sync_to_authority and self._http_client:
            return await self._state_chain.append_and_sync(
                action_type=action_type,
                action_summary=action_summary,
                action_data=action_data,
            )
        else:
            return self._state_chain.append(
                action_type=action_type,
                action_summary=action_summary,
                action_data=action_data,
            )

    def create_proof(self, challenge: bytes) -> ProofBundle:
        """Create proof bundle for verification.

        Args:
            challenge: Challenge bytes from verifier

        Returns:
            Signed ProofBundle
        """
        if self._prover is None:
            self._prover = Prover(self._keypair)

        return self._prover.create_proof(
            challenge=challenge,
            lease=self.current_lease,
            state_head=self.state_head,
        )

    async def initialize_state_chain(
        self,
        summary: str = "Agent created",
    ) -> StateEntry:
        """Initialize the state chain with genesis entry.

        Args:
            summary: Summary for genesis entry

        Returns:
            Genesis StateEntry
        """
        await self._initialize()
        return self._state_chain.initialize(summary)

    def save_keypair(self, path: Path, password: str) -> None:
        """Save keypair to encrypted file.

        Args:
            path: File path
            password: Encryption password
        """
        self._keypair.to_encrypted_file(path, password)

    async def close(self) -> None:
        """Release resources and close connections."""
        # Release lease if held
        if self._lease_manager:
            await self._lease_manager.release_lease()

        # Close HTTP client if we own it
        if self._owns_http_client and self._http_client:
            await self._http_client.close()
            self._http_client = None

    async def __aenter__(self) -> AgentClient:
        """Async context manager entry."""
        await self._initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    def __repr__(self) -> str:
        """Debug representation."""
        return f"AgentClient(agent_id={self._agent_id})"
