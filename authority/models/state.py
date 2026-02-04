"""SigAid State Entry model."""

from enum import Enum as PyEnum

from sqlalchemy import (
    Column, BigInteger, String, DateTime, Enum, LargeBinary,
    Text, ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class ActionType(PyEnum):
    """Types of actions in the state chain."""
    TRANSACTION = "transaction"
    ATTESTATION = "attestation"
    UPGRADE = "upgrade"
    RESET = "reset"
    CUSTOM = "custom"


class SigAidStateEntry(Base):
    """State chain entries for tamper-evident history.

    Each entry links to the previous via cryptographic hash,
    creating an append-only, verifiable log of agent actions.
    """
    __tablename__ = "state_entries"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    agent_id = Column(
        String(64),
        ForeignKey("agents.agent_id", ondelete="CASCADE"),
        nullable=False
    )

    # Chain linking
    sequence = Column(BigInteger, nullable=False)
    prev_hash = Column(LargeBinary(32), nullable=False)  # 32-byte BLAKE3 hash
    entry_hash = Column(LargeBinary(32), nullable=False, unique=True)  # 32-byte BLAKE3 hash

    # Action details
    action_type = Column(
        Enum(ActionType, values_callable=lambda x: [e.value for e in x], name="action_type"),
        nullable=False,
    )
    action_summary = Column(Text, nullable=True)
    action_data_hash = Column(LargeBinary(32), nullable=True)  # Hash of full action data

    # Signature
    signature = Column(LargeBinary(64), nullable=False)  # 64-byte Ed25519 signature

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationship
    agent = relationship("SigAidAgent", back_populates="state_entries")

    __table_args__ = (
        UniqueConstraint("agent_id", "sequence", name="uq_state_agent_seq"),
        Index("idx_state_agent_seq", "agent_id", "sequence"),
        Index("idx_state_entry_hash", "entry_hash"),
    )
