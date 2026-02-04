"""PASETO v4 token management for leases."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import pyseto
from pyseto import Key

from sigaid.exceptions import TokenExpired, TokenInvalid


class LeaseTokenManager:
    """PASETO v4 token management for leases.

    PASETO (Platform-Agnostic Security Tokens) is a secure alternative to JWT
    that prevents algorithm confusion attacks and other common JWT vulnerabilities.

    Example:
        manager = LeaseTokenManager(secret_key)

        # Create token
        token = manager.create_token(
            agent_id="aid_xxx",
            session_id="sid_xxx",
            ttl=timedelta(minutes=10)
        )

        # Verify token
        payload = manager.verify_token(token)
    """

    def __init__(self, secret_key: bytes):
        """Initialize with 32-byte secret key.

        In production, this key is managed by the Authority service.

        Args:
            secret_key: 32-byte symmetric key for token encryption

        Raises:
            ValueError: If secret_key is not 32 bytes
        """
        if len(secret_key) != 32:
            raise ValueError("Secret key must be 32 bytes")
        self._key = Key.new(version=4, purpose="local", key=secret_key)

    def create_token(
        self,
        agent_id: str,
        session_id: str,
        ttl: timedelta = timedelta(minutes=10),
        sequence: int = 0,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """Create a new lease token.

        Args:
            agent_id: The agent identifier
            session_id: Unique session identifier
            ttl: Token time-to-live
            sequence: Monotonic sequence number (for replay protection)
            extra_claims: Additional claims to include

        Returns:
            PASETO v4.local token string
        """
        now = datetime.now(timezone.utc)
        payload = {
            "agent_id": agent_id,
            "session_id": session_id,
            "iat": now.isoformat(),
            "exp": (now + ttl).isoformat(),
            "jti": secrets.token_hex(16),
            "seq": sequence,
        }

        if extra_claims:
            payload.update(extra_claims)

        token = pyseto.encode(self._key, payload)
        return token.decode("utf-8") if isinstance(token, bytes) else token

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify and decode a lease token.

        Args:
            token: PASETO token string

        Returns:
            Decoded payload dictionary

        Raises:
            TokenExpired: If token has expired
            TokenInvalid: If token is malformed or invalid
        """
        try:
            decoded = pyseto.decode(self._key, token.encode("utf-8") if isinstance(token, str) else token)
            payload = decoded.payload

            # Handle both dict and bytes payload
            if isinstance(payload, bytes):
                import json
                payload = json.loads(payload.decode("utf-8"))

            # Check expiration
            exp = datetime.fromisoformat(payload["exp"])
            if exp < datetime.now(timezone.utc):
                raise TokenExpired(f"Token expired at {exp.isoformat()}")

            return payload

        except TokenExpired:
            raise
        except Exception as e:
            raise TokenInvalid(f"Invalid token: {e}") from e

    def decode_token(self, token: str, check_expiry: bool = False) -> dict[str, Any]:
        """Decode and verify a token, optionally checking expiry.

        Use this when you need the token contents but don't want expiry checks
        (e.g., for inspection or logging purposes).

        Args:
            token: PASETO token string
            check_expiry: Whether to raise TokenExpired if token is expired

        Returns:
            Decoded payload

        Raises:
            TokenInvalid: If token cannot be decoded
            TokenExpired: If check_expiry=True and token is expired
        """
        try:
            decoded = pyseto.decode(self._key, token.encode("utf-8") if isinstance(token, str) else token)
            payload = decoded.payload
            if isinstance(payload, bytes):
                import json
                payload = json.loads(payload.decode("utf-8"))

            if check_expiry:
                exp = datetime.fromisoformat(payload["exp"])
                if exp < datetime.now(timezone.utc):
                    raise TokenExpired(f"Token expired at {exp.isoformat()}")

            return payload
        except TokenExpired:
            raise
        except Exception as e:
            raise TokenInvalid(f"Cannot decode token: {e}") from e

    def refresh_token(
        self,
        old_token: str,
        ttl: timedelta = timedelta(minutes=10),
    ) -> str:
        """Refresh a token with a new expiration.

        Args:
            old_token: Current valid token
            ttl: New time-to-live

        Returns:
            New token with updated expiration

        Raises:
            TokenExpired: If old token is already expired
            TokenInvalid: If old token is invalid
        """
        payload = self.verify_token(old_token)
        return self.create_token(
            agent_id=payload["agent_id"],
            session_id=payload["session_id"],
            ttl=ttl,
            sequence=payload["seq"] + 1,
        )
