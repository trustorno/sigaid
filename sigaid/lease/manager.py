"""Lease acquisition and management."""

from __future__ import annotations

import asyncio
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, AsyncIterator

from sigaid.constants import (
    DEFAULT_LEASE_RENEWAL_BUFFER_SECONDS,
    DEFAULT_LEASE_TTL_SECONDS,
    DOMAIN_LEASE,
    SESSION_ID_PREFIX,
)
from sigaid.exceptions import (
    LeaseError,
    LeaseExpired,
    LeaseHeldByAnotherInstance,
    LeaseNotHeld,
    LeaseRenewalFailed,
)
from sigaid.models.lease import Lease, LeaseRequest

if TYPE_CHECKING:
    from sigaid.crypto.keys import KeyPair
    from sigaid.client.authority import AuthorityClient


def generate_session_id() -> str:
    """Generate unique session identifier."""
    return SESSION_ID_PREFIX + secrets.token_hex(16)


class LeaseManager:
    """
    Manages exclusive lease acquisition for an agent.
    
    The lease ensures only one instance of an agent can operate at a time,
    preventing "clone" attacks where multiple instances use the same identity.
    
    Example:
        manager = LeaseManager(agent_id, keypair, authority_client)
        
        async with manager.acquire() as lease:
            # Only one instance can be here at a time
            print(f"Holding lease until {lease.expires_at}")
    """
    
    def __init__(
        self,
        agent_id: str,
        keypair: KeyPair,
        authority: AuthorityClient,
        *,
        ttl_seconds: int = DEFAULT_LEASE_TTL_SECONDS,
        renewal_buffer_seconds: int = DEFAULT_LEASE_RENEWAL_BUFFER_SECONDS,
    ):
        """
        Initialize lease manager.
        
        Args:
            agent_id: Agent identifier
            keypair: Agent's keypair for signing
            authority: Authority client for API calls
            ttl_seconds: Lease time-to-live
            renewal_buffer_seconds: Renew when this many seconds remain
        """
        self._agent_id = agent_id
        self._keypair = keypair
        self._authority = authority
        self._ttl_seconds = ttl_seconds
        self._renewal_buffer = renewal_buffer_seconds
        
        self._current_lease: Lease | None = None
        self._session_id: str | None = None
        self._renewal_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()
    
    @property
    def agent_id(self) -> str:
        """Get agent ID."""
        return self._agent_id
    
    @property
    def current_lease(self) -> Lease | None:
        """Get current lease (if held)."""
        return self._current_lease
    
    @property
    def is_holding_lease(self) -> bool:
        """Check if currently holding a valid lease."""
        return (
            self._current_lease is not None and
            self._current_lease.is_valid
        )
    
    async def acquire(self, timeout: float | None = None) -> Lease:
        """
        Acquire exclusive lease.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            Acquired Lease
            
        Raises:
            LeaseHeldByAnotherInstance: If another instance holds the lease
            LeaseError: If acquisition fails
        """
        async with self._lock:
            if self.is_holding_lease:
                return self._current_lease
            
            # Generate new session ID
            self._session_id = generate_session_id()
            
            # Create signed lease request
            timestamp = datetime.now(timezone.utc)
            nonce = secrets.token_bytes(32)
            
            request_data = (
                self._agent_id.encode("utf-8") +
                timestamp.isoformat().encode("utf-8") +
                nonce
            )
            signature = self._keypair.sign_with_domain(request_data, DOMAIN_LEASE)
            
            request = LeaseRequest(
                agent_id=self._agent_id,
                timestamp=timestamp,
                nonce=nonce,
                signature=signature,
            )
            
            # Call authority to acquire lease
            try:
                response = await self._authority.acquire_lease(
                    request,
                    self._session_id,
                    self._ttl_seconds,
                    timeout=timeout,
                )
            except Exception as e:
                if "held by another" in str(e).lower():
                    raise LeaseHeldByAnotherInstance(self._agent_id) from e
                raise LeaseError(f"Failed to acquire lease: {e}") from e
            
            self._current_lease = response.lease
            return self._current_lease
    
    async def release(self) -> None:
        """
        Release the current lease.
        
        This allows other instances to acquire the lease immediately
        rather than waiting for expiration.
        """
        async with self._lock:
            if self._current_lease is None:
                return
            
            # Stop renewal task if running
            if self._renewal_task and not self._renewal_task.done():
                self._renewal_task.cancel()
                try:
                    await self._renewal_task
                except asyncio.CancelledError:
                    pass
            
            # Notify authority
            try:
                await self._authority.release_lease(
                    self._agent_id,
                    self._session_id,
                )
            except Exception:
                pass  # Best effort - lease will expire anyway
            
            self._current_lease = None
            self._session_id = None
            self._renewal_task = None
    
    async def renew(self) -> Lease:
        """
        Renew the current lease.
        
        Returns:
            Renewed Lease with extended expiration
            
        Raises:
            LeaseNotHeld: If no lease is held
            LeaseRenewalFailed: If renewal fails
        """
        async with self._lock:
            if not self.is_holding_lease:
                raise LeaseNotHeld("Cannot renew - no lease held")
            
            try:
                response = await self._authority.renew_lease(
                    self._agent_id,
                    self._session_id,
                    self._current_lease.token,
                    self._ttl_seconds,
                )
            except Exception as e:
                raise LeaseRenewalFailed(f"Failed to renew lease: {e}") from e
            
            self._current_lease = response.lease
            return self._current_lease
    
    def start_auto_renewal(self) -> None:
        """
        Start background task for automatic lease renewal.
        
        The task will renew the lease when it's close to expiration.
        """
        if self._renewal_task and not self._renewal_task.done():
            return  # Already running
        
        self._renewal_task = asyncio.create_task(self._auto_renewal_loop())
    
    def stop_auto_renewal(self) -> None:
        """Stop the auto-renewal background task."""
        if self._renewal_task and not self._renewal_task.done():
            self._renewal_task.cancel()
    
    async def _auto_renewal_loop(self) -> None:
        """Background loop for automatic lease renewal."""
        while True:
            try:
                if not self.is_holding_lease:
                    break
                
                # Check if renewal needed
                if self._current_lease.should_renew(self._renewal_buffer):
                    await self.renew()
                
                # Sleep until next check (half the renewal buffer)
                await asyncio.sleep(self._renewal_buffer / 2)
            
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue trying
                await asyncio.sleep(5)
    
    @asynccontextmanager
    async def hold(self) -> AsyncIterator[Lease]:
        """
        Context manager for holding a lease.
        
        Acquires the lease on entry, releases on exit.
        Auto-renewal is enabled while in context.
        
        Example:
            async with manager.hold() as lease:
                # Do work while holding lease
                pass
        """
        lease = await self.acquire()
        self.start_auto_renewal()
        try:
            yield lease
        finally:
            self.stop_auto_renewal()
            await self.release()
    
    def require_lease(self) -> Lease:
        """
        Get current lease, raising if not held.
        
        Returns:
            Current valid Lease
            
        Raises:
            LeaseNotHeld: If no valid lease is held
        """
        if not self.is_holding_lease:
            raise LeaseNotHeld("Operation requires holding a lease")
        return self._current_lease
