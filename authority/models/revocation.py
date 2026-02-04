"""SigAid Token Revocation model.

Provides a revocation list for invalidating tokens before their natural expiry.
This is critical for:
- Emergency response to compromised tokens
- Forced logout of agents
- Immediate access termination
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Index, Text
from sqlalchemy.sql import func

from ..database import Base


class SigAidRevokedToken(Base):
    """Revoked tokens that should be rejected even if cryptographically valid.

    Tokens are identified by their unique JTI (JWT ID) claim.
    Entries can be cleaned up after the token's original expiry time.
    """
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Token identifier (JTI claim from PASETO token)
    token_jti = Column(String(64), unique=True, nullable=False, index=True)

    # Agent that owned this token (for audit trail)
    agent_id = Column(String(64), nullable=False, index=True)

    # Original token expiry (for cleanup purposes)
    original_expiry = Column(DateTime(timezone=True), nullable=False)

    # Revocation metadata
    revoked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_by = Column(String(255), nullable=True)  # Admin user or system process
    revocation_reason = Column(Text, nullable=True)

    __table_args__ = (
        # Index for cleanup queries (find tokens past their expiry)
        Index("idx_revoked_tokens_expiry", "original_expiry"),
        # Compound index for agent-specific revocation queries
        Index("idx_revoked_tokens_agent", "agent_id", "revoked_at"),
    )


class SigAidKeyRevocation(Base):
    """Revoked PASETO keys for key rotation.

    When a PASETO key is rotated, the old key ID is added here.
    Tokens signed with revoked keys are rejected.
    """
    __tablename__ = "revoked_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Key identifier (first 8 bytes of key hash, hex encoded)
    key_id = Column(String(16), unique=True, nullable=False, index=True)

    # Revocation metadata
    revoked_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    revoked_by = Column(String(255), nullable=True)
    revocation_reason = Column(Text, nullable=True)

    # Grace period end (tokens issued before this are still valid during transition)
    grace_period_end = Column(DateTime(timezone=True), nullable=True)
