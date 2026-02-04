"""SigAid API Key model."""

from sqlalchemy import Column, Integer, String, DateTime, LargeBinary, Boolean, Index
from sqlalchemy.sql import func

from ..database import Base


class SigAidAPIKey(Base):
    """API keys for third-party services to verify agents.

    Services need an API key to call the verify endpoint.
    """
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key_hash = Column(LargeBinary(32), nullable=False, unique=True)  # BLAKE3 hash of API key
    name = Column(String(255), nullable=False)  # Human-readable name

    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=1000)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_api_keys_hash", "key_hash"),
    )
