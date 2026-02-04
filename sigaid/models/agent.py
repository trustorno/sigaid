"""Agent information model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    """Status of an agent."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


@dataclass
class AgentInfo:
    """Information about a registered agent.

    Returned by the Authority service when querying agent details.
    """

    agent_id: str
    public_key: bytes
    status: AgentStatus
    created_at: datetime
    owner_id: str | None = None
    revoked_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Reputation metrics
    total_transactions: int = 0
    successful_transactions: int = 0
    age_days: int = 0
    reputation_score: float = 0.0

    @property
    def is_active(self) -> bool:
        """Check if agent is active.

        Returns:
            True if agent status is ACTIVE
        """
        return self.status == AgentStatus.ACTIVE

    @property
    def success_rate(self) -> float:
        """Calculate transaction success rate.

        Returns:
            Success rate between 0.0 and 1.0
        """
        if self.total_transactions == 0:
            return 0.0
        return self.successful_transactions / self.total_transactions

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        import base64

        result = {
            "agent_id": self.agent_id,
            "public_key": base64.b64encode(self.public_key).decode("ascii"),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "total_transactions": self.total_transactions,
            "successful_transactions": self.successful_transactions,
            "age_days": self.age_days,
            "reputation_score": self.reputation_score,
        }

        if self.owner_id:
            result["owner_id"] = self.owner_id

        if self.revoked_at:
            result["revoked_at"] = self.revoked_at.isoformat()

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentInfo:
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            AgentInfo instance
        """
        import base64

        revoked_at = None
        if data.get("revoked_at"):
            revoked_at = datetime.fromisoformat(data["revoked_at"])

        return cls(
            agent_id=data["agent_id"],
            public_key=base64.b64decode(data["public_key"]),
            status=AgentStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            owner_id=data.get("owner_id"),
            revoked_at=revoked_at,
            metadata=data.get("metadata", {}),
            total_transactions=data.get("total_transactions", 0),
            successful_transactions=data.get("successful_transactions", 0),
            age_days=data.get("age_days", 0),
            reputation_score=data.get("reputation_score", 0.0),
        )

    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"AgentInfo(agent_id={self.agent_id!r}, "
            f"status={self.status.value}, "
            f"reputation={self.reputation_score:.2f})"
        )


@dataclass
class VerificationResult:
    """Result of verifying a proof bundle."""

    valid: bool
    agent_id: str
    agent_info: AgentInfo | None = None
    lease_active: bool = False
    state_verified: bool = False
    error_message: str | None = None

    # Verification details
    signature_valid: bool = False
    challenge_valid: bool = False
    chain_valid: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        result = {
            "valid": self.valid,
            "agent_id": self.agent_id,
            "lease_active": self.lease_active,
            "state_verified": self.state_verified,
            "signature_valid": self.signature_valid,
            "challenge_valid": self.challenge_valid,
            "chain_valid": self.chain_valid,
        }

        if self.agent_info:
            result["agent_info"] = self.agent_info.to_dict()

        if self.error_message:
            result["error_message"] = self.error_message

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VerificationResult:
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            VerificationResult instance
        """
        agent_info = None
        if data.get("agent_info"):
            agent_info = AgentInfo.from_dict(data["agent_info"])

        return cls(
            valid=data["valid"],
            agent_id=data["agent_id"],
            agent_info=agent_info,
            lease_active=data.get("lease_active", False),
            state_verified=data.get("state_verified", False),
            error_message=data.get("error_message"),
            signature_valid=data.get("signature_valid", False),
            challenge_valid=data.get("challenge_valid", False),
            chain_valid=data.get("chain_valid", False),
        )
