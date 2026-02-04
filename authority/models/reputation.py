"""SigAid Reputation model."""

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database import Base


class SigAidReputation(Base):
    """Cached reputation metrics for agents.

    Computed/updated periodically based on state chain history.
    """
    __tablename__ = "reputation"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(
        String(64),
        ForeignKey("agents.agent_id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # Metrics
    total_transactions = Column(BigInteger, default=0)
    successful_transactions = Column(BigInteger, default=0)
    age_days = Column(Integer, default=0)
    last_activity_at = Column(DateTime(timezone=True), nullable=True)

    # Computed score (0.0 - 1.0)
    score = Column(Float, default=0.0)

    # Last update
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationship
    agent = relationship("SigAidAgent", back_populates="reputation")
