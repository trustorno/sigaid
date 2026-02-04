"""PASETO v4 token service for lease management.

Security features:
- Token revocation checking
- Key rotation support with graceful transition
- Key ID tracking for revocation
"""

import hashlib
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Callable

import pyseto
from pyseto import Key

from ..config import settings


# Type for revocation check callback
RevocationChecker = Callable[[str], bool]  # jti -> is_revoked


class TokenService:
    """Service for creating and verifying PASETO v4.local tokens.

    Supports:
    - Token revocation via JTI checking
    - Key rotation with multiple active keys
    - Key ID embedding for revocation tracking
    """

    def __init__(
        self,
        secret_key: Optional[bytes] = None,
        previous_keys: Optional[list[bytes]] = None,
        revocation_checker: Optional[RevocationChecker] = None,
    ):
        """
        Initialize with a 32-byte secret key.

        Args:
            secret_key: Primary 32-byte PASETO key. If not provided, uses settings.
            previous_keys: List of previous keys for rotation (still valid for verification)
            revocation_checker: Callback to check if a token JTI is revoked
        """
        # Primary key
        if secret_key:
            self._secret = secret_key
        else:
            self._secret = settings.paseto_key_bytes

        if len(self._secret) != 32:
            raise ValueError("PASETO secret key must be 32 bytes")

        self._key = Key.new(version=4, purpose="local", key=self._secret)
        self._key_id = self._compute_key_id(self._secret)

        # Previous keys for rotation
        self._previous_keys: list[tuple[Key, str]] = []  # (Key, key_id) pairs
        prev_keys = previous_keys or settings.paseto_previous_keys
        for prev_key in prev_keys:
            if len(prev_key) == 32:
                key = Key.new(version=4, purpose="local", key=prev_key)
                key_id = self._compute_key_id(prev_key)
                self._previous_keys.append((key, key_id))

        # Revocation checker
        self._revocation_checker = revocation_checker

    @staticmethod
    def _compute_key_id(key: bytes) -> str:
        """Compute a short key ID for tracking."""
        return hashlib.blake2b(key, digest_size=8).hexdigest()

    @property
    def key_id(self) -> str:
        """Current key ID (for embedding in tokens)."""
        return self._key_id

    def set_revocation_checker(self, checker: RevocationChecker) -> None:
        """Set the revocation checker callback.

        Args:
            checker: Function that takes a JTI and returns True if revoked
        """
        self._revocation_checker = checker

    def create_lease_token(
        self,
        agent_id: str,
        session_id: str,
        ttl_seconds: int = 600,
        sequence: int = 0,
    ) -> tuple[str, str, datetime]:
        """
        Create a PASETO v4.local lease token.

        The token includes:
        - agent_id: The agent this lease belongs to
        - session_id: Unique session identifier
        - jti: Unique token ID for revocation tracking
        - kid: Key ID for key rotation tracking
        - iat/exp: Issued at / expiry timestamps
        - seq: Sequence number for replay protection

        Returns:
            tuple of (token, jti, expires_at)
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=ttl_seconds)
        jti = secrets.token_hex(16)

        payload = {
            "agent_id": agent_id,
            "session_id": session_id,
            "iat": now.isoformat(),
            "exp": expires_at.isoformat(),
            "jti": jti,
            "kid": self._key_id,  # Key ID for rotation tracking
            "seq": sequence,
        }

        # Encode as PASETO v4.local token
        token = pyseto.encode(
            self._key,
            payload=json.dumps(payload).encode("utf-8"),
        )

        return token.decode("utf-8"), jti, expires_at

    def verify_lease_token(self, token: str, check_revocation: bool = True) -> dict:
        """
        Verify and decode a lease token.

        Performs the following checks:
        1. Cryptographic verification (decryption)
        2. Expiration check
        3. Revocation check (if revocation_checker is set)

        Supports key rotation by trying previous keys if primary fails.

        Args:
            token: The PASETO token to verify
            check_revocation: Whether to check the revocation list (default True)

        Returns:
            The payload dict if valid

        Raises:
            TokenExpiredError: If token has expired
            TokenRevokedError: If token has been revoked
            TokenInvalidError: If token is malformed or invalid
        """
        payload = None
        token_bytes = token.encode("utf-8")

        # Try primary key first
        try:
            decoded = pyseto.decode(self._key, token_bytes)
            payload = json.loads(decoded.payload.decode("utf-8"))
        except pyseto.DecryptError:
            # Try previous keys for rotation support
            for prev_key, _ in self._previous_keys:
                try:
                    decoded = pyseto.decode(prev_key, token_bytes)
                    payload = json.loads(decoded.payload.decode("utf-8"))
                    break
                except pyseto.DecryptError:
                    continue

        if payload is None:
            raise TokenInvalidError("Invalid token: decryption failed with all keys")

        try:
            # Check expiration
            exp = datetime.fromisoformat(payload["exp"])
            if exp < datetime.now(timezone.utc):
                raise TokenExpiredError("Lease token has expired")

            # Check revocation
            if check_revocation and self._revocation_checker:
                jti = payload.get("jti")
                if jti and self._revocation_checker(jti):
                    raise TokenRevokedError(
                        f"Token has been revoked",
                        jti=jti,
                        agent_id=payload.get("agent_id"),
                    )

            return payload
        except (TokenExpiredError, TokenRevokedError):
            raise
        except json.JSONDecodeError as e:
            raise TokenInvalidError(f"Malformed token payload: {e}")

    def refresh_lease_token(
        self,
        current_token: str,
        ttl_seconds: int = 600,
        new_sequence: int = None,
    ) -> tuple[str, str, datetime]:
        """
        Refresh a lease token with new expiration.

        Validates the current token and issues a new one.
        """
        payload = self.verify_lease_token(current_token)

        sequence = new_sequence if new_sequence is not None else payload.get("seq", 0) + 1

        return self.create_lease_token(
            agent_id=payload["agent_id"],
            session_id=payload["session_id"],
            ttl_seconds=ttl_seconds,
            sequence=sequence,
        )


class TokenExpiredError(Exception):
    """Token has expired."""
    pass


class TokenInvalidError(Exception):
    """Token is invalid."""
    pass


class TokenRevokedError(Exception):
    """Token has been revoked."""

    def __init__(self, message: str, jti: Optional[str] = None, agent_id: Optional[str] = None):
        super().__init__(message)
        self.jti = jti
        self.agent_id = agent_id


# Singleton instance
_token_service: Optional[TokenService] = None


def get_token_service() -> TokenService:
    """Get or create the token service singleton."""
    global _token_service
    if _token_service is None:
        _token_service = TokenService()
    return _token_service


def reset_token_service() -> None:
    """Reset the token service singleton (for testing or key rotation)."""
    global _token_service
    _token_service = None
