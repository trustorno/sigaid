"""SigAid Lease model."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from ..database import Base


class SigAidLease(Base):
    """Active leases for exclusive agent operation.

    Only one lease can be active per agent at a time.
    Uses PostgreSQL advisory locks for atomic acquisition.
    """
    __tablename__ = "leases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(
        String(64),
        ForeignKey("agents.agent_id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    session_id = Column(String(64), nullable=False)  # Unique session identifier

    # Token tracking
    token_jti = Column(String(64), nullable=False)  # Token ID for revocation
    sequence = Column(Integer, default=0)  # Monotonic for replay protection

    # Timestamps
    acquired_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_renewed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationship
    agent = relationship("SigAidAgent", back_populates="leases")

    __table_args__ = (
        Index("idx_leases_expires", "expires_at"),
    )
