"""Utility functions for SigAid."""

from __future__ import annotations

import secrets
import string
from datetime import datetime, timezone


def generate_nonce(length: int = 32) -> bytes:
    """Generate cryptographically secure random nonce."""
    return secrets.token_bytes(length)


def generate_id(prefix: str = "", length: int = 16) -> str:
    """Generate random ID with optional prefix."""
    chars = string.ascii_lowercase + string.digits
    random_part = "".join(secrets.choice(chars) for _ in range(length))
    return f"{prefix}{random_part}" if prefix else random_part


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def iso_now() -> str:
    """Get current UTC datetime as ISO string."""
    return utc_now().isoformat()


def constant_time_compare(a: bytes, b: bytes) -> bool:
    """
    Compare two byte strings in constant time.
    
    Prevents timing attacks by taking the same time regardless of
    where the strings differ.
    """
    if len(a) != len(b):
        return False
    
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    
    return result == 0
