"""Lease heartbeat for background renewal."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, Awaitable

if TYPE_CHECKING:
    from sigaid.lease.manager import LeaseManager

logger = logging.getLogger(__name__)


class LeaseHeartbeat:
    """Background heartbeat to keep lease alive.

    The heartbeat runs as a background task and automatically
    renews the lease before it expires.

    Example:
        heartbeat = LeaseHeartbeat(lease_manager)
        heartbeat.start()

        # ... do work ...

        heartbeat.stop()
    """

    def __init__(
        self,
        lease_manager: LeaseManager,
        check_interval_seconds: float = 10.0,
        on_renewal: Callable[[datetime], Awaitable[None]] | None = None,
        on_expiry: Callable[[], Awaitable[None]] | None = None,
        on_error: Callable[[Exception], Awaitable[None]] | None = None,
    ):
        """Initialize heartbeat.

        Args:
            lease_manager: LeaseManager to keep alive
            check_interval_seconds: How often to check lease status
            on_renewal: Callback when lease is renewed
            on_expiry: Callback when lease expires
            on_error: Callback on renewal error
        """
        self._manager = lease_manager
        self._check_interval = check_interval_seconds
        self._on_renewal = on_renewal
        self._on_expiry = on_expiry
        self._on_error = on_error
        self._task: asyncio.Task | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if heartbeat is running."""
        return self._running and self._task is not None and not self._task.done()

    def start(self) -> None:
        """Start the heartbeat background task."""
        if self.is_running:
            return

        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())

    def stop(self) -> None:
        """Stop the heartbeat background task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

    async def _heartbeat_loop(self) -> None:
        """Main heartbeat loop."""
        consecutive_errors = 0
        max_consecutive_errors = 3

        while self._running:
            try:
                await asyncio.sleep(self._check_interval)

                if not self._running:
                    break

                lease = self._manager.current_lease
                if not lease:
                    logger.warning("Heartbeat: No lease held")
                    if self._on_expiry:
                        await self._on_expiry()
                    break

                if lease.is_expired:
                    logger.warning("Heartbeat: Lease expired")
                    if self._on_expiry:
                        await self._on_expiry()
                    break

                if lease.should_renew:
                    logger.debug("Heartbeat: Renewing lease")
                    renewed = await self._manager.renew_lease()
                    consecutive_errors = 0

                    if self._on_renewal:
                        await self._on_renewal(renewed.expires_at)

            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Heartbeat error: {e}")

                if self._on_error:
                    await self._on_error(e)

                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Heartbeat: Too many errors, stopping")
                    break

                # Exponential backoff
                await asyncio.sleep(min(30, 2**consecutive_errors))

        self._running = False

    async def wait(self) -> None:
        """Wait for heartbeat to complete."""
        if self._task:
            try:
                await self._task
            except asyncio.CancelledError:
                pass
