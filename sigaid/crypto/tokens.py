"""PASETO v4 token management for lease tokens."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import pyseto
from pyseto import Key

from sigaid.constants import PASETO_KEY_SIZE
from sigaid.exceptions import TokenError, TokenExpired, TokenInvalid


class LeaseTokenManager:
    """
    PASETO v4 token management for lease operations.
    
    PASETO (Platform-Agnostic SEcurity TOkens) provides authenticated
    encryption for tokens, avoiding JWT's algorithm confusion vulnerabilities.
    
    This class is used by the Authority service to create and verify
    lease tokens. Agents receive tokens but cannot forge them.
    
    Example:
        # Authority side - create tokens
        manager = LeaseTokenManager(secret_key)
        token = manager.create_token("aid_xxx", "sid_xxx")
        
        # Verify token
        payload = manager.verify_token(token)
    """

    def __init__(self, secret_key: bytes):
        """
        Initialize with 32-byte secret key.
        
        In production, this key is managed by the Authority service
        and should be stored securely (e.g., in a secrets manager).
        
        Args:
            secret_key: 32-byte secret key for token encryption
            
        Raises:
            TokenError: If secret key is invalid
        """
        if len(secret_key) != PASETO_KEY_SIZE:
            raise ValueError(f"Secret key must be {PASETO_KEY_SIZE} bytes, got {len(secret_key)}")
        self._key = Key.new(version=4, purpose="local", key=secret_key)

    @classmethod
    def generate_key(cls) -> bytes:
        """
        Generate a new random secret key.
        
        Returns:
            32-byte secret key
        """
        return secrets.token_bytes(PASETO_KEY_SIZE)

    def create_token(
        self,
        agent_id: str,
        session_id: str,
        ttl: timedelta = timedelta(minutes=10),
        sequence: int = 0,
        metadata: dict[str, Any] | None = None,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """
        Create new lease token.

        Args:
            agent_id: Agent identifier (aid_xxx format)
            session_id: Session identifier (sid_xxx format)
            ttl: Token time-to-live (default 10 minutes)
            sequence: Monotonic sequence number for replay protection
            metadata: Optional additional claims (stored under 'meta' key)
            extra_claims: Optional claims to add directly to payload

        Returns:
            PASETO token string
        """
        now = datetime.now(timezone.utc)

        payload = {
            "agent_id": agent_id,
            "session_id": session_id,
            "iat": now.isoformat(),
            "exp": (now + ttl).isoformat(),
            "jti": secrets.token_hex(16),  # Unique token ID
            "seq": sequence,
        }

        if metadata:
            payload["meta"] = metadata

        if extra_claims:
            payload.update(extra_claims)

        # Encode payload as JSON bytes for pyseto
        payload_bytes = json.dumps(payload).encode("utf-8")
        token = pyseto.encode(self._key, payload_bytes)
        return token.decode("utf-8")

    def verify_token(self, token: str) -> dict[str, Any]:
        """
        Verify and decode lease token.

        Args:
            token: PASETO token string

        Returns:
            Decoded payload dictionary

        Raises:
            TokenExpired: If token has expired
            TokenInvalid: If token is invalid or tampered
        """
        try:
            decoded = pyseto.decode(self._key, token.encode("utf-8"))
            # pyseto returns bytes, decode as JSON
            payload = json.loads(decoded.payload.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise TokenInvalid(f"Invalid token payload: {e}") from e
        except Exception as e:
            raise TokenInvalid(f"Invalid token: {e}") from e

        # Check expiration
        try:
            exp = datetime.fromisoformat(payload["exp"])
            if exp < datetime.now(timezone.utc):
                raise TokenExpired(f"Token expired at {payload['exp']}")
        except KeyError:
            raise TokenInvalid("Token missing expiration claim")
        except ValueError as e:
            raise TokenInvalid(f"Invalid expiration format: {e}") from e

        return payload

    def refresh_token(
        self,
        old_token: str,
        ttl: timedelta = timedelta(minutes=10),
    ) -> str:
        """
        Refresh a token, incrementing the sequence number.
        
        The old token is verified before creating a new one.
        
        Args:
            old_token: Current valid token
            ttl: New token time-to-live
            
        Returns:
            New PASETO token string
            
        Raises:
            TokenExpired: If old token has expired
            TokenInvalid: If old token is invalid
        """
        old_payload = self.verify_token(old_token)
        
        return self.create_token(
            agent_id=old_payload["agent_id"],
            session_id=old_payload["session_id"],
            ttl=ttl,
            sequence=old_payload.get("seq", 0) + 1,
            metadata=old_payload.get("meta"),
        )


def decode_token_unverified(token: str) -> dict[str, Any]:
    """
    Decode token payload without verification.
    
    WARNING: This does NOT verify the token! Only use for inspection.
    
    Args:
        token: PASETO token string
        
    Returns:
        Decoded payload (unverified)
    """
    # PASETO v4.local tokens are encrypted, so we can't decode without key
    # This is a stub that would need the token manager
    raise NotImplementedError(
        "PASETO local tokens are encrypted. Use LeaseTokenManager.verify_token() instead."
    )


def extract_token_claims_unsafe(token: str) -> dict[str, str]:
    """
    Extract basic token structure without decryption.
    
    Returns version and purpose, but not payload (encrypted).
    
    Args:
        token: PASETO token string
        
    Returns:
        Dictionary with 'version' and 'purpose'
    """
    parts = token.split(".")
    if len(parts) < 2:
        raise TokenInvalid("Invalid token format")
    
    return {
        "version": parts[0],  # e.g., "v4"
        "purpose": parts[1],  # e.g., "local"
    }
