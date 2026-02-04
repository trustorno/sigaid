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
    """
    Background heartbeat task for lease renewal.
    
    Monitors lease expiration and triggers renewal when needed.
    Also handles callbacks for lease events.
    
    Example:
        heartbeat = LeaseHeartbeat(lease_manager)
        
        @heartbeat.on_renewed
        async def handle_renewal(new_lease):
            print(f"Lease renewed until {new_lease.expires_at}")
        
        @heartbeat.on_lost
        async def handle_lost(reason):
            print(f"Lost lease: {reason}")
        
        heartbeat.start()
        # ... later ...
        heartbeat.stop()
    """
    
    def __init__(
        self,
        manager: LeaseManager,
        *,
        check_interval_seconds: float = 10.0,
        renewal_buffer_seconds: float = 60.0,
        max_renewal_retries: int = 3,
    ):
        """
        Initialize heartbeat.
        
        Args:
            manager: LeaseManager to monitor
            check_interval_seconds: How often to check lease status
            renewal_buffer_seconds: Renew when this many seconds remain
            max_renewal_retries: Max retries before giving up
        """
        self._manager = manager
        self._check_interval = check_interval_seconds
        self._renewal_buffer = renewal_buffer_seconds
        self._max_retries = max_renewal_retries
        
        self._task: asyncio.Task | None = None
        self._running = False
        
        # Callbacks
        self._on_renewed: list[Callable] = []
        self._on_lost: list[Callable] = []
        self._on_expiring: list[Callable] = []
    
    def on_renewed(self, callback: Callable) -> Callable:
        """
        Register callback for lease renewal.
        
        Callback receives the new Lease object.
        """
        self._on_renewed.append(callback)
        return callback
    
    def on_lost(self, callback: Callable) -> Callable:
        """
        Register callback for lease loss.
        
        Callback receives the reason string.
        """
        self._on_lost.append(callback)
        return callback
    
    def on_expiring(self, callback: Callable) -> Callable:
        """
        Register callback for lease expiring soon.
        
        Called before attempting renewal.
        Callback receives seconds remaining.
        """
        self._on_expiring.append(callback)
        return callback
    
    def start(self) -> None:
        """Start the heartbeat background task."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._heartbeat_loop())
        logger.debug("Lease heartbeat started")
    
    def stop(self) -> None:
        """Stop the heartbeat background task."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.debug("Lease heartbeat stopped")
    
    async def _heartbeat_loop(self) -> None:
        """Main heartbeat loop."""
        retry_count = 0
        
        while self._running:
            try:
                await asyncio.sleep(self._check_interval)
                
                if not self._manager.is_holding_lease:
                    continue
                
                lease = self._manager.current_lease
                seconds_remaining = lease.seconds_remaining
                
                # Check if expiring soon
                if seconds_remaining <= self._renewal_buffer:
                    # Notify expiring callbacks
                    for callback in self._on_expiring:
                        try:
                            result = callback(seconds_remaining)
                            if asyncio.iscoroutine(result):
                                await result
                        except Exception as e:
                            logger.warning(f"Expiring callback error: {e}")
                    
                    # Attempt renewal
                    try:
                        new_lease = await self._manager.renew()
                        retry_count = 0  # Reset on success
                        
                        # Notify renewed callbacks
                        for callback in self._on_renewed:
                            try:
                                result = callback(new_lease)
                                if asyncio.iscoroutine(result):
                                    await result
                            except Exception as e:
                                logger.warning(f"Renewed callback error: {e}")
                        
                        logger.debug(f"Lease renewed, expires at {new_lease.expires_at}")
                    
                    except Exception as e:
                        retry_count += 1
                        logger.warning(f"Lease renewal failed (attempt {retry_count}): {e}")
                        
                        if retry_count >= self._max_retries:
                            # Notify lost callbacks
                            reason = f"Renewal failed after {retry_count} attempts: {e}"
                            for callback in self._on_lost:
                                try:
                                    result = callback(reason)
                                    if asyncio.iscoroutine(result):
                                        await result
                                except Exception as e2:
                                    logger.warning(f"Lost callback error: {e2}")
                            
                            logger.error(f"Lease lost: {reason}")
                            break
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(self._check_interval)
    
    @property
    def is_running(self) -> bool:
        """Check if heartbeat is running."""
        return self._running and self._task is not None and not self._task.done()
