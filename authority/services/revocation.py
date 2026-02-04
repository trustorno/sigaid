"""Token and key revocation service.

Provides centralized revocation management:
- Revoke individual tokens by JTI
- Revoke all tokens for an agent
- Revoke PASETO keys (for rotation)
- Check revocation status
- Clean up expired revocations
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..models.revocation import SigAidRevokedToken, SigAidKeyRevocation


class RevocationService:
    """Service for managing token and key revocations."""

    def __init__(self, db: Session):
        """Initialize with database session.

        Args:
            db: SQLAlchemy database session
        """
        self._db = db

    def revoke_token(
        self,
        token_jti: str,
        agent_id: str,
        original_expiry: datetime,
        revoked_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> SigAidRevokedToken:
        """Revoke a specific token.

        Args:
            token_jti: The token's unique identifier (JTI claim)
            agent_id: Agent that owns the token
            original_expiry: Token's original expiration time
            revoked_by: Who revoked the token (admin user, system, etc.)
            reason: Reason for revocation

        Returns:
            The created revocation record
        """
        revocation = SigAidRevokedToken(
            token_jti=token_jti,
            agent_id=agent_id,
            original_expiry=original_expiry,
            revoked_by=revoked_by,
            revocation_reason=reason,
        )
        self._db.add(revocation)
        self._db.commit()
        self._db.refresh(revocation)
        return revocation

    def is_token_revoked(self, token_jti: str) -> bool:
        """Check if a token is revoked.

        Args:
            token_jti: The token's unique identifier

        Returns:
            True if the token is revoked
        """
        revocation = self._db.query(SigAidRevokedToken).filter(
            SigAidRevokedToken.token_jti == token_jti
        ).first()
        return revocation is not None

    def get_token_revocation(self, token_jti: str) -> Optional[SigAidRevokedToken]:
        """Get revocation details for a token.

        Args:
            token_jti: The token's unique identifier

        Returns:
            Revocation record if found, None otherwise
        """
        return self._db.query(SigAidRevokedToken).filter(
            SigAidRevokedToken.token_jti == token_jti
        ).first()

    def revoke_all_agent_tokens(
        self,
        agent_id: str,
        revoked_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> int:
        """Mark an agent for full token revocation.

        Note: This doesn't actually revoke existing tokens individually.
        Instead, use this in combination with checking agent status
        or implementing a "revoked after" timestamp on the agent.

        For immediate revocation, you need to revoke specific tokens
        or implement additional checks in token verification.

        Args:
            agent_id: Agent to revoke tokens for
            revoked_by: Who initiated the revocation
            reason: Reason for revocation

        Returns:
            Number of active tokens that were revoked
        """
        # This would need to be implemented based on your lease tracking
        # For now, return 0 as a placeholder
        return 0

    def revoke_key(
        self,
        key_id: str,
        revoked_by: Optional[str] = None,
        reason: Optional[str] = None,
        grace_period_end: Optional[datetime] = None,
    ) -> SigAidKeyRevocation:
        """Revoke a PASETO key.

        Used during key rotation to mark old keys as no longer valid
        for issuing new tokens (they may still be valid for verification
        during the grace period).

        Args:
            key_id: The key identifier (8-byte hash, hex encoded)
            revoked_by: Who revoked the key
            reason: Reason for revocation
            grace_period_end: Until when tokens from this key are still valid

        Returns:
            The created revocation record
        """
        revocation = SigAidKeyRevocation(
            key_id=key_id,
            revoked_by=revoked_by,
            revocation_reason=reason,
            grace_period_end=grace_period_end,
        )
        self._db.add(revocation)
        self._db.commit()
        self._db.refresh(revocation)
        return revocation

    def is_key_revoked(self, key_id: str, check_grace_period: bool = True) -> bool:
        """Check if a PASETO key is revoked.

        Args:
            key_id: The key identifier
            check_grace_period: If True, keys in grace period are not considered revoked

        Returns:
            True if the key is revoked (and past grace period if checked)
        """
        revocation = self._db.query(SigAidKeyRevocation).filter(
            SigAidKeyRevocation.key_id == key_id
        ).first()

        if revocation is None:
            return False

        if check_grace_period and revocation.grace_period_end:
            # Key is in grace period
            if datetime.now(timezone.utc) < revocation.grace_period_end:
                return False

        return True

    def cleanup_expired_revocations(self, retention_hours: int = 24) -> int:
        """Clean up revocation records for expired tokens.

        Tokens that have passed their original expiry time no longer need
        to be tracked in the revocation list.

        Args:
            retention_hours: Keep revocations this many hours after token expiry

        Returns:
            Number of records deleted
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)

        result = self._db.query(SigAidRevokedToken).filter(
            SigAidRevokedToken.original_expiry < cutoff
        ).delete()

        self._db.commit()
        return result


def create_revocation_checker(db_session_factory) -> callable:
    """Create a revocation checker function for TokenService.

    Args:
        db_session_factory: Callable that returns a database session

    Returns:
        Function that checks if a JTI is revoked
    """
    def check_revocation(jti: str) -> bool:
        db = db_session_factory()
        try:
            service = RevocationService(db)
            return service.is_token_revoked(jti)
        finally:
            db.close()

    return check_revocation
