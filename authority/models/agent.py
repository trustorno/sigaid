"""SigAid Agent model."""

from datetime import datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, Integer, String, DateTime, Enum, LargeBinary, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class AgentStatus(PyEnum):
    """Status of a SigAid agent."""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class SigAidAgent(Base):
    """Registered SigAid agents.

    Each agent has a unique identity derived from an Ed25519 public key.
    The agent_id is in format: aid_<base58(public_key + checksum)>
    """
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(64), unique=True, nullable=False, index=True)
    public_key = Column(LargeBinary(32), nullable=False)  # 32-byte Ed25519 public key

    status = Column(
        Enum(AgentStatus, values_callable=lambda x: [e.value for e in x], name="agent_status"),
        nullable=False,
        default=AgentStatus.ACTIVE,
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata (flexible JSON for additional info)
    agent_metadata = Column("metadata", JSON, default=dict)

    # Relationships
    leases = relationship("SigAidLease", back_populates="agent", cascade="all, delete-orphan")
    state_entries = relationship("SigAidStateEntry", back_populates="agent", cascade="all, delete-orphan")
    reputation = relationship("SigAidReputation", back_populates="agent", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_agents_public_key", "public_key"),
    )
