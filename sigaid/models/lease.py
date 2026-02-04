"""Lease-related data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any


class LeaseStatus(str, Enum):
    """Lease status enumeration."""
    ACTIVE = "active"
    EXPIRED = "expired"
    RELEASED = "released"


@dataclass
class Lease:
    """
    Exclusive lease for agent identity.
    
    A lease grants exclusive control over an agent identity for a limited time.
    Only one instance can hold a lease for a given agent at any time.
    
    Example:
        async with client.lease() as lease:
            print(f"Lease expires at: {lease.expires_at}")
            # Do work while holding lease
    """
    agent_id: str
    session_id: str
    token: str
    acquired_at: datetime
    expires_at: datetime
    sequence: int = 0
    
    @property
    def status(self) -> LeaseStatus:
        """Get current lease status."""
        now = datetime.now(timezone.utc)
        if now >= self.expires_at:
            return LeaseStatus.EXPIRED
        return LeaseStatus.ACTIVE
    
    @property
    def is_valid(self) -> bool:
        """Check if lease is currently valid."""
        return self.status == LeaseStatus.ACTIVE
    
    @property
    def time_remaining(self) -> timedelta:
        """Get time remaining until expiration."""
        now = datetime.now(timezone.utc)
        remaining = self.expires_at - now
        return max(remaining, timedelta(0))
    
    @property
    def seconds_remaining(self) -> float:
        """Get seconds remaining until expiration."""
        return self.time_remaining.total_seconds()
    
    def should_renew(self, buffer_seconds: int = 60) -> bool:
        """
        Check if lease should be renewed.
        
        Args:
            buffer_seconds: Renew when this many seconds remain
            
        Returns:
            True if should renew now
        """
        return self.seconds_remaining <= buffer_seconds
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "token": self.token,
            "acquired_at": self.acquired_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "sequence": self.sequence,
            "status": self.status.value,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Lease:
        """Create from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            session_id=data["session_id"],
            token=data["token"],
            acquired_at=datetime.fromisoformat(data["acquired_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            sequence=data.get("sequence", 0),
        )
    
    def __repr__(self) -> str:
        return (
            f"Lease(agent_id={self.agent_id!r}, "
            f"status={self.status.value}, "
            f"expires_in={self.seconds_remaining:.0f}s)"
        )


@dataclass
class LeaseRequest:
    """Request to acquire a lease."""
    agent_id: str
    timestamp: datetime
    nonce: bytes
    signature: bytes
    
    def to_bytes(self) -> bytes:
        """Serialize for signing."""
        import struct
        return (
            self.agent_id.encode("utf-8") +
            self.timestamp.isoformat().encode("utf-8") +
            self.nonce
        )


@dataclass
class LeaseResponse:
    """Response from lease acquisition."""
    lease: Lease
    renewal_before: datetime
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LeaseResponse:
        """Create from dictionary."""
        return cls(
            lease=Lease.from_dict(data["lease"]),
            renewal_before=datetime.fromisoformat(data["renewal_before"]),
        )
