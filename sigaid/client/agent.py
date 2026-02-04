"""Main AgentClient - primary SDK entry point for agents."""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, AsyncIterator

from sigaid.client.authority import AuthorityClient
from sigaid.constants import DEFAULT_AUTHORITY_URL
from sigaid.crypto.keys import KeyPair
from sigaid.exceptions import AgentNotFound, LeaseNotHeld, SigAidError
from sigaid.identity.agent_id import AgentID
from sigaid.lease.manager import LeaseManager
from sigaid.models.agent import AgentInfo
from sigaid.models.lease import Lease
from sigaid.models.proof import ProofBundle, ProofBundleBuilder
from sigaid.models.state import ActionType, StateEntry
from sigaid.state.chain import StateChain

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AgentClient:
    """
    Main SDK entry point for agents.
    
    AgentClient provides a high-level interface for:
    - Creating and managing agent identity
    - Acquiring exclusive leases
    - Recording actions to state chain
    - Creating proof bundles for verification
    
    Example:
        # Create new agent
        client = AgentClient.create()
        
        # Use lease context for operations
        async with client.lease() as lease:
            # Record actions
            await client.record_action("transaction", {"amount": 100})
            
            # Create proof for service
            proof = client.create_proof(challenge=b"nonce123")
        
        # Close when done
        await client.close()
    
    One-line framework integration:
        import sigaid
        agent = sigaid.wrap(my_langchain_agent)
    """
    
    def __init__(
        self,
        agent_id: AgentID,
        keypair: KeyPair,
        authority_url: str = DEFAULT_AUTHORITY_URL,
        *,
        api_key: str | None = None,
        auto_renew_lease: bool = True,
        state_persistence_path: Path | None = None,
    ):
        """
        Initialize AgentClient.
        
        Use factory methods (create, from_keypair, from_file) instead of
        direct construction.
        
        Args:
            agent_id: Agent's identifier
            keypair: Agent's keypair
            authority_url: Authority service URL
            api_key: Optional API key
            auto_renew_lease: Enable automatic lease renewal
            state_persistence_path: Optional local state persistence
        """
        self._agent_id = agent_id
        self._keypair = keypair
        self._authority_url = authority_url
        self._api_key = api_key or os.environ.get("SIGAID_API_KEY")
        self._auto_renew = auto_renew_lease
        self._state_path = state_persistence_path
        
        # Initialize components
        self._authority = AuthorityClient(
            base_url=authority_url,
            api_key=self._api_key,
        )

        self._lease_manager = LeaseManager(
            agent_id=str(agent_id),
            keypair=keypair,
            authority=self._authority,
        )

        self._state_chain = StateChain(
            agent_id=str(agent_id),
            keypair=keypair,
            authority=self._authority,
            persistence_path=state_persistence_path,
        )

        self._closed = False
        self._registered = False  # Track if registered with Authority
    
    # ========== Factory Methods ==========
    
    @classmethod
    def create(
        cls,
        authority_url: str = DEFAULT_AUTHORITY_URL,
        *,
        api_key: str | None = None,
        name: str | None = None,
        register: bool = True,
    ) -> AgentClient:
        """
        Create new agent with fresh identity.

        Note: This creates the agent locally. Registration with Authority
        happens automatically on first lease acquisition (lazy registration).
        Use `await client.register()` for explicit registration.

        Args:
            authority_url: Authority service URL
            api_key: API key (or SIGAID_API_KEY env var)
            name: Optional human-readable name
            register: If True, will register on first lease (default True)

        Returns:
            New AgentClient instance
        """
        keypair = KeyPair.generate()
        agent_id = keypair.to_agent_id()

        client = cls(
            agent_id=agent_id,
            keypair=keypair,
            authority_url=authority_url,
            api_key=api_key,
        )

        # Store registration preference and name for lazy registration
        client._should_register = register
        client._agent_name = name

        return client

    @classmethod
    async def create_async(
        cls,
        authority_url: str = DEFAULT_AUTHORITY_URL,
        *,
        api_key: str | None = None,
        name: str | None = None,
        register: bool = True,
    ) -> AgentClient:
        """
        Create new agent with fresh identity and register immediately.

        This is the async version that registers with Authority before returning.

        Args:
            authority_url: Authority service URL
            api_key: API key (or SIGAID_API_KEY env var)
            name: Optional human-readable name
            register: Register with Authority (default True)

        Returns:
            New AgentClient instance (already registered)
        """
        client = cls.create(
            authority_url=authority_url,
            api_key=api_key,
            name=name,
            register=register,
        )

        # Register immediately if requested
        if register:
            await client.register(name=name)

        return client
    
    @classmethod
    def from_keypair(
        cls,
        keypair: KeyPair,
        authority_url: str = DEFAULT_AUTHORITY_URL,
        **kwargs,
    ) -> AgentClient:
        """
        Load agent from existing keypair.
        
        Args:
            keypair: Existing KeyPair
            authority_url: Authority service URL
            **kwargs: Additional arguments
            
        Returns:
            AgentClient instance
        """
        agent_id = keypair.to_agent_id()
        return cls(
            agent_id=agent_id,
            keypair=keypair,
            authority_url=authority_url,
            **kwargs,
        )
    
    @classmethod
    def from_file(
        cls,
        path: Path,
        password: str,
        authority_url: str = DEFAULT_AUTHORITY_URL,
        **kwargs,
    ) -> AgentClient:
        """
        Load agent from encrypted keyfile.
        
        Args:
            path: Path to encrypted keyfile
            password: Decryption password
            authority_url: Authority service URL
            **kwargs: Additional arguments
            
        Returns:
            AgentClient instance
        """
        keypair = KeyPair.from_encrypted_file(path, password)
        return cls.from_keypair(keypair, authority_url, **kwargs)
    
    @classmethod
    def from_seed(
        cls,
        seed: bytes,
        authority_url: str = DEFAULT_AUTHORITY_URL,
        **kwargs,
    ) -> AgentClient:
        """
        Create agent from deterministic seed.
        
        Args:
            seed: 32-byte seed
            authority_url: Authority service URL
            **kwargs: Additional arguments
            
        Returns:
            AgentClient instance
        """
        keypair = KeyPair.from_seed(seed)
        return cls.from_keypair(keypair, authority_url, **kwargs)
    
    # ========== Properties ==========
    
    @property
    def agent_id(self) -> AgentID:
        """Get agent identifier."""
        return self._agent_id
    
    @property
    def keypair(self) -> KeyPair:
        """Get agent's keypair."""
        return self._keypair
    
    @property
    def state_head(self) -> StateEntry | None:
        """Get current state chain head."""
        return self._state_chain.head
    
    @property
    def state_sequence(self) -> int:
        """Get current state sequence number."""
        return self._state_chain.sequence
    
    @property
    def is_holding_lease(self) -> bool:
        """Check if currently holding a valid lease."""
        return self._lease_manager.is_holding_lease
    
    @property
    def current_lease(self) -> Lease | None:
        """Get current lease (if held)."""
        return self._lease_manager.current_lease
    
    # ========== Lease Operations ==========

    @asynccontextmanager
    async def lease(self) -> AsyncIterator[Lease]:
        """
        Acquire exclusive lease context manager.

        Only one instance can hold the lease at a time.
        Auto-renewal is enabled while in context.

        Note: This will automatically register with Authority on first call
        if registration was requested during creation.

        Example:
            async with client.lease() as lease:
                # Safe to operate - we have exclusive control
                await client.record_action(...)

        Raises:
            LeaseHeldByAnotherInstance: If another instance holds the lease
        """
        # Ensure registered before acquiring lease
        await self._ensure_registered()

        # Ensure state chain is synced with Authority
        await self._state_chain.ensure_synced()

        async with self._lease_manager.hold() as lease:
            yield lease
    
    async def acquire_lease(self) -> Lease:
        """
        Acquire exclusive lease.
        
        For manual lease management. Prefer using `async with client.lease()`.
        
        Returns:
            Acquired Lease
        """
        return await self._lease_manager.acquire()
    
    async def release_lease(self) -> None:
        """Release current lease."""
        await self._lease_manager.release()

    # ========== Registration ==========

    async def register(self, name: str | None = None) -> AgentInfo:
        """
        Register this agent with the Authority service.

        Args:
            name: Optional human-readable name for the agent

        Returns:
            AgentInfo with registration details

        Note:
            This is called automatically on first lease if registration
            was requested during creation.
        """
        if self._registered:
            logger.debug(f"Agent {self._agent_id} already registered")
            return await self._authority.get_agent(str(self._agent_id))

        logger.info(f"Registering agent {self._agent_id} with Authority")

        agent_info = await self._authority.create_agent(
            public_key=self._keypair.public_key_bytes(),
            name=name or getattr(self, "_agent_name", None),
            metadata={
                "created_at": datetime.now(timezone.utc).isoformat(),
                "sdk_version": "0.1.0",
            },
        )

        self._registered = True
        logger.info(f"Agent {self._agent_id} registered successfully")

        return agent_info

    async def _ensure_registered(self) -> None:
        """
        Ensure agent is registered with Authority (lazy registration).

        This is called automatically before lease acquisition.
        """
        if self._registered:
            return

        # Check if registration was requested
        should_register = getattr(self, "_should_register", True)
        if not should_register:
            self._registered = True  # Mark as "done" even if not registered
            return

        try:
            # First check if already registered (e.g., from previous session)
            await self._authority.get_agent(str(self._agent_id))
            self._registered = True
            logger.debug(f"Agent {self._agent_id} already exists on Authority")
        except AgentNotFound:
            # Not registered yet, register now
            await self.register()

    @property
    def is_registered(self) -> bool:
        """Check if agent is registered with Authority."""
        return self._registered

    # ========== State Operations ==========
    
    async def record_action(
        self,
        action_type: str | ActionType,
        data: dict[str, Any] | None = None,
        *,
        summary: str | None = None,
        sync: bool = True,
    ) -> StateEntry:
        """
        Record action to state chain.
        
        Args:
            action_type: Type of action (string or ActionType enum)
            data: Action data (will be hashed, not stored)
            summary: Human-readable summary (auto-generated if not provided)
            sync: Sync with Authority (default True)
            
        Returns:
            Created StateEntry
            
        Raises:
            LeaseNotHeld: If no lease is held
        """
        if not self.is_holding_lease:
            raise LeaseNotHeld("Must hold lease to record actions")
        
        # Convert string to ActionType
        if isinstance(action_type, str):
            try:
                action_type = ActionType(action_type)
            except ValueError:
                action_type = ActionType.CUSTOM
        
        # Generate summary if not provided
        if summary is None:
            summary = f"{action_type.value}: {str(data)[:100]}" if data else action_type.value
        
        if sync:
            return await self._state_chain.append_and_sync(
                action_type=action_type,
                action_summary=summary,
                action_data=data,
            )
        else:
            return self._state_chain.append(
                action_type=action_type,
                action_summary=summary,
                action_data=data,
            )
    
    async def sync_state(self) -> int:
        """
        Sync local state chain with Authority.

        This fetches any missing entries from Authority and verifies
        chain consistency.

        Returns:
            Number of entries synced

        Raises:
            ForkDetected: If local and remote chains have diverged
        """
        # Ensure initial sync is done first
        await self._state_chain.ensure_synced()

        # Then fetch any new entries
        return await self._state_chain.sync_from_authority()
    
    # ========== Verification ==========
    
    def create_proof(self, challenge: bytes) -> ProofBundle:
        """
        Create proof bundle for verification.
        
        Args:
            challenge: Challenge bytes from verifier
            
        Returns:
            ProofBundle to send to verifier
            
        Raises:
            LeaseNotHeld: If no lease is held
        """
        if not self.is_holding_lease:
            raise LeaseNotHeld("Must hold lease to create proofs")
        
        builder = ProofBundleBuilder(
            agent_id=str(self._agent_id),
            keypair=self._keypair,
            lease_token=self._lease_manager.current_lease.token,
            state_head=self._state_chain.head,
        )
        
        return builder.build(challenge)
    
    # ========== Key Management ==========
    
    def save_to_file(self, path: Path, password: str) -> None:
        """
        Save agent keypair to encrypted file.
        
        Args:
            path: File path
            password: Encryption password
        """
        self._keypair.to_encrypted_file(path, password)
    
    # ========== Lifecycle ==========
    
    async def close(self) -> None:
        """
        Close client and release resources.
        
        Releases lease if held, closes connections.
        """
        if self._closed:
            return
        
        self._closed = True
        
        # Release lease if held
        if self.is_holding_lease:
            await self.release_lease()
        
        # Close authority client
        await self._authority.close()
    
    async def __aenter__(self) -> AgentClient:
        """Async context manager entry with initialization."""
        # Ensure registered on entry
        await self._ensure_registered()

        # Sync state chain with Authority
        await self._state_chain.ensure_synced()

        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    def __repr__(self) -> str:
        return f"AgentClient(agent_id={self._agent_id})"
