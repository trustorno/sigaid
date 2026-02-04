"""Lease manager for acquiring and managing exclusive leases."""

from __future__ import annotations

import asyncio
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, AsyncIterator, Any

from sigaid.models.lease import Lease, LeaseStatus
from sigaid.constants import (
    DEFAULT_LEASE_TTL_SECONDS,
    DEFAULT_LEASE_RENEWAL_BUFFER_SECONDS,
    DOMAIN_LEASE,
)
from sigaid.exceptions import (
    LeaseHeldByAnotherInstance,
    LeaseExpired,
    LeaseNotHeld,
    LeaseRenewalFailed,
)

if TYPE_CHECKING:
    from sigaid.crypto.keys import KeyPair
    from sigaid.client.http import HttpClient


class LeaseManager:
    """Manages lease acquisition, renewal, and release.

    The LeaseManager ensures only one instance of an agent can operate
    at a time by acquiring an exclusive lease from the Authority.

    Example:
        manager = LeaseManager(keypair, http_client)

        async with manager.acquire() as lease:
            # Exclusive access granted
            print(f"Lease acquired: {lease.session_id}")
            # Do work...

        # Lease automatically released
    """

    def __init__(
        self,
        keypair: KeyPair,
        http_client: HttpClient | None = None,
        ttl_seconds: int = DEFAULT_LEASE_TTL_SECONDS,
        renewal_buffer_seconds: int = DEFAULT_LEASE_RENEWAL_BUFFER_SECONDS,
        auto_renew: bool = True,
    ):
        """Initialize lease manager.

        Args:
            keypair: Agent's keypair for signing lease requests
            http_client: HTTP client for Authority API (optional for local-only mode)
            ttl_seconds: Lease time-to-live in seconds
            renewal_buffer_seconds: Seconds before expiry to start renewal
            auto_renew: Whether to automatically renew leases
        """
        self._keypair = keypair
        self._http_client = http_client
        self._ttl_seconds = ttl_seconds
        self._renewal_buffer_seconds = renewal_buffer_seconds
        self._auto_renew = auto_renew
        self._current_lease: Lease | None = None
        self._renewal_task: asyncio.Task | None = None
        self._session_id: str | None = None

    @property
    def agent_id(self) -> str:
        """Get agent ID."""
        return str(self._keypair.to_agent_id())

    @property
    def current_lease(self) -> Lease | None:
        """Get current lease if held."""
        return self._current_lease

    @property
    def has_lease(self) -> bool:
        """Check if a valid lease is held."""
        return self._current_lease is not None and self._current_lease.is_active

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[Lease]:
        """Acquire exclusive lease as async context manager.

        Yields:
            Active Lease object

        Raises:
            LeaseHeldByAnotherInstance: If another instance holds the lease
        """
        lease = await self.acquire_lease()
        try:
            yield lease
        finally:
            await self.release_lease()

    async def acquire_lease(self) -> Lease:
        """Acquire an exclusive lease.

        Returns:
            Acquired Lease object

        Raises:
            LeaseHeldByAnotherInstance: If another instance holds the lease
        """
        self._session_id = secrets.token_hex(16)

        if self._http_client:
            lease = await self._acquire_remote()
        else:
            lease = self._acquire_local()

        self._current_lease = lease

        # Start auto-renewal if enabled
        if self._auto_renew:
            self._start_renewal_task()

        return lease

    async def _acquire_remote(self) -> Lease:
        """Acquire lease from Authority service."""
        timestamp = datetime.now(timezone.utc)
        nonce = secrets.token_bytes(32)

        # Create signed lease request
        request_data = {
            "agent_id": self.agent_id,
            "session_id": self._session_id,
            "timestamp": timestamp.isoformat(),
            "nonce": nonce.hex(),
            "ttl_seconds": self._ttl_seconds,
        }

        # Sign the request
        signable = f"{self.agent_id}:{self._session_id}:{timestamp.isoformat()}:{nonce.hex()}".encode()
        signature = self._keypair.sign(signable, domain=DOMAIN_LEASE)

        request_data["signature"] = signature.hex()

        # Send to Authority
        response = await self._http_client.post("/v1/leases", json=request_data)

        if response.get("error") == "lease_held":
            raise LeaseHeldByAnotherInstance(
                self.agent_id,
                response.get("holder_session_id"),
            )

        return Lease(
            agent_id=self.agent_id,
            session_id=self._session_id,
            token=response["lease_token"],
            acquired_at=datetime.fromisoformat(response["acquired_at"]),
            expires_at=datetime.fromisoformat(response["expires_at"]),
            renewal_buffer_seconds=self._renewal_buffer_seconds,
        )

    def _acquire_local(self) -> Lease:
        """Create a local-only lease (for testing/offline mode)."""
        now = datetime.now(timezone.utc)
        return Lease(
            agent_id=self.agent_id,
            session_id=self._session_id,
            token=f"local:{self._session_id}",
            acquired_at=now,
            expires_at=now + timedelta(seconds=self._ttl_seconds),
            renewal_buffer_seconds=self._renewal_buffer_seconds,
        )

    async def renew_lease(self) -> Lease:
        """Renew the current lease.

        Returns:
            Renewed Lease object

        Raises:
            LeaseNotHeld: If no lease is currently held
            LeaseRenewalFailed: If renewal fails
        """
        if not self._current_lease:
            raise LeaseNotHeld("No lease to renew")

        if self._http_client:
            lease = await self._renew_remote()
        else:
            lease = self._renew_local()

        self._current_lease = lease
        return lease

    async def _renew_remote(self) -> Lease:
        """Renew lease with Authority service."""
        response = await self._http_client.put(
            f"/v1/leases/{self.agent_id}",
            json={
                "session_id": self._session_id,
                "current_token": self._current_lease.token,
                "ttl_seconds": self._ttl_seconds,
            },
        )

        if response.get("error"):
            raise LeaseRenewalFailed(response.get("message", "Unknown error"))

        self._current_lease.renew(
            new_token=response["lease_token"],
            new_expires_at=datetime.fromisoformat(response["expires_at"]),
        )
        return self._current_lease

    def _renew_local(self) -> Lease:
        """Renew local lease."""
        now = datetime.now(timezone.utc)
        self._current_lease.renew(
            new_token=f"local:{self._session_id}:{self._current_lease.sequence + 1}",
            new_expires_at=now + timedelta(seconds=self._ttl_seconds),
        )
        return self._current_lease

    async def release_lease(self) -> None:
        """Release the current lease."""
        # Stop renewal task
        self._stop_renewal_task()

        if not self._current_lease:
            return

        if self._http_client:
            await self._release_remote()

        self._current_lease.release()
        self._current_lease = None
        self._session_id = None

    async def _release_remote(self) -> None:
        """Release lease with Authority service."""
        try:
            await self._http_client.delete(
                f"/v1/leases/{self.agent_id}",
                json={
                    "session_id": self._session_id,
                    "token": self._current_lease.token,
                },
            )
        except Exception:
            # Best effort release
            pass

    def _start_renewal_task(self) -> None:
        """Start background renewal task."""
        if self._renewal_task and not self._renewal_task.done():
            return

        self._renewal_task = asyncio.create_task(self._renewal_loop())

    def _stop_renewal_task(self) -> None:
        """Stop background renewal task."""
        if self._renewal_task and not self._renewal_task.done():
            self._renewal_task.cancel()
            self._renewal_task = None

    async def _renewal_loop(self) -> None:
        """Background loop to renew lease before expiry."""
        while self._current_lease and self._current_lease.is_active:
            try:
                # Wait until we should renew
                wait_seconds = max(
                    0,
                    self._current_lease.ttl_seconds - self._renewal_buffer_seconds,
                )
                await asyncio.sleep(wait_seconds)

                # Check if still active
                if not self._current_lease or not self._current_lease.is_active:
                    break

                # Renew
                await self.renew_lease()

            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue trying
                await asyncio.sleep(5)

    def check_lease(self) -> None:
        """Check that we hold a valid lease.

        Raises:
            LeaseNotHeld: If no lease is held
            LeaseExpired: If lease has expired
        """
        if not self._current_lease:
            raise LeaseNotHeld("No lease held")
        if self._current_lease.is_expired:
            raise LeaseExpired("Lease has expired")
