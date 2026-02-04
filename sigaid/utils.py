"""Utility functions for SigAid protocol."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any


def generate_session_id() -> str:
    """Generate a unique session ID.

    Returns:
        32-character hex string
    """
    return secrets.token_hex(16)


def generate_nonce(length: int = 32) -> bytes:
    """Generate a random nonce.

    Args:
        length: Nonce length in bytes

    Returns:
        Random bytes
    """
    return secrets.token_bytes(length)


def utc_now() -> datetime:
    """Get current UTC time.

    Returns:
        Timezone-aware datetime in UTC
    """
    return datetime.now(timezone.utc)


def iso_timestamp() -> str:
    """Get current UTC time as ISO 8601 string.

    Returns:
        ISO 8601 formatted timestamp
    """
    return utc_now().isoformat()


def truncate_hex(data: bytes, length: int = 8) -> str:
    """Truncate bytes to hex string with ellipsis.

    Args:
        data: Bytes to truncate
        length: Number of hex chars to show

    Returns:
        Truncated hex string like "abc123..."
    """
    hex_str = data.hex()
    if len(hex_str) > length:
        return f"{hex_str[:length]}..."
    return hex_str


def constant_time_compare(a: bytes, b: bytes) -> bool:
    """Compare two byte strings in constant time.

    This prevents timing attacks when comparing secrets.

    Args:
        a: First byte string
        b: Second byte string

    Returns:
        True if equal
    """
    if len(a) != len(b):
        return False

    result = 0
    for x, y in zip(a, b):
        result |= x ^ y

    return result == 0


def serialize_for_signing(data: dict[str, Any]) -> bytes:
    """Serialize a dictionary for signing in canonical form.

    Keys are sorted to ensure consistent ordering.

    Args:
        data: Dictionary to serialize

    Returns:
        Canonical JSON bytes
    """
    import json

    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
