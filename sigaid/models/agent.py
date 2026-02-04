"""Agent-related data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    """Agent status enumeration."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


@dataclass
class AgentInfo:
    """
    Information about a registered agent.
    
    Returned by Authority when querying agent details.
    """
    agent_id: str
    public_key: bytes
    status: AgentStatus
    created_at: datetime
    owner_id: str | None = None
    name: str | None = None
    revoked_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # Statistics
    total_state_entries: int = 0
    last_activity: datetime | None = None
    
    def is_active(self) -> bool:
        """Check if agent is in active status."""
        return self.status == AgentStatus.ACTIVE
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "public_key": self.public_key.hex(),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "owner_id": self.owner_id,
            "name": self.name,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "metadata": self.metadata,
            "total_state_entries": self.total_state_entries,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentInfo:
        """Create from dictionary."""
        return cls(
            agent_id=data["agent_id"],
            public_key=bytes.fromhex(data["public_key"]),
            status=AgentStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            owner_id=data.get("owner_id"),
            name=data.get("name"),
            revoked_at=datetime.fromisoformat(data["revoked_at"]) if data.get("revoked_at") else None,
            metadata=data.get("metadata", {}),
            total_state_entries=data.get("total_state_entries", 0),
            last_activity=datetime.fromisoformat(data["last_activity"]) if data.get("last_activity") else None,
        )


@dataclass
class ReputationScore:
    """
    Agent reputation metrics.
    
    Computed based on agent's history and behavior.
    """
    agent_id: str
    score: float  # 0.0 to 1.0
    total_transactions: int
    successful_transactions: int
    age_days: int
    last_updated: datetime
    
    # Breakdown
    transaction_score: float = 0.0
    longevity_score: float = 0.0
    consistency_score: float = 0.0
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "score": self.score,
            "total_transactions": self.total_transactions,
            "successful_transactions": self.successful_transactions,
            "age_days": self.age_days,
            "last_updated": self.last_updated.isoformat(),
            "breakdown": {
                "transaction_score": self.transaction_score,
                "longevity_score": self.longevity_score,
                "consistency_score": self.consistency_score,
            }
        }
