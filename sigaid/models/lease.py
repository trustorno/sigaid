"""Lease model for exclusive agent operation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any


class LeaseStatus(str, Enum):
    """Status of a lease."""

    ACTIVE = "active"
    EXPIRED = "expired"
    RELEASED = "released"
    REVOKED = "revoked"


@dataclass
class Lease:
    """Represents an exclusive lease for an agent.

    A lease grants exclusive operation rights to a single instance
    of an agent. Only the lease holder can perform actions.

    Example:
        lease = Lease(
            agent_id="aid_xxx",
            session_id="sid_xxx",
            token="v4.local.xxx",
            acquired_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )

        if lease.is_active:
            # Perform actions
            pass

        if lease.should_renew:
            # Renew before expiry
            pass
    """

    agent_id: str
    session_id: str
    token: str
    acquired_at: datetime
    expires_at: datetime
    status: LeaseStatus = LeaseStatus.ACTIVE
    sequence: int = 0
    renewal_buffer_seconds: int = 60

    @property
    def is_active(self) -> bool:
        """Check if lease is currently active.

        Returns:
            True if lease is active and not expired
        """
        if self.status != LeaseStatus.ACTIVE:
            return False
        return datetime.now(timezone.utc) < self.expires_at

    @property
    def is_expired(self) -> bool:
        """Check if lease has expired.

        Returns:
            True if lease has expired
        """
        return datetime.now(timezone.utc) >= self.expires_at

    @property
    def should_renew(self) -> bool:
        """Check if lease should be renewed.

        Returns True if we're within the renewal buffer period.

        Returns:
            True if lease should be renewed soon
        """
        if not self.is_active:
            return False
        renewal_threshold = self.expires_at - timedelta(seconds=self.renewal_buffer_seconds)
        return datetime.now(timezone.utc) >= renewal_threshold

    @property
    def time_remaining(self) -> timedelta:
        """Get time remaining on the lease.

        Returns:
            Time until expiration (may be negative if expired)
        """
        return self.expires_at - datetime.now(timezone.utc)

    @property
    def ttl_seconds(self) -> float:
        """Get TTL in seconds.

        Returns:
            Seconds until expiration (may be negative)
        """
        return self.time_remaining.total_seconds()

    def renew(self, new_token: str, new_expires_at: datetime) -> None:
        """Update lease with renewed token.

        Args:
            new_token: New lease token
            new_expires_at: New expiration time
        """
        self.token = new_token
        self.expires_at = new_expires_at
        self.sequence += 1

    def release(self) -> None:
        """Mark lease as released."""
        self.status = LeaseStatus.RELEASED

    def expire(self) -> None:
        """Mark lease as expired."""
        self.status = LeaseStatus.EXPIRED

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "token": self.token,
            "acquired_at": self.acquired_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status.value,
            "sequence": self.sequence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Lease:
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            Lease instance
        """
        return cls(
            agent_id=data["agent_id"],
            session_id=data["session_id"],
            token=data["token"],
            acquired_at=datetime.fromisoformat(data["acquired_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            status=LeaseStatus(data.get("status", "active")),
            sequence=data.get("sequence", 0),
        )

    def __repr__(self) -> str:
        """Debug representation."""
        session_display = self.session_id[:8] + "..." if len(self.session_id) > 8 else self.session_id
        return (
            f"Lease(agent_id={self.agent_id!r}, "
            f"session_id={session_display}, "
            f"status={self.status.value}, "
            f"ttl={self.ttl_seconds:.0f}s)"
        )
