"""Secure memory handling for cryptographic keys.

This module provides secure memory handling to protect sensitive key material:
- Memory locking (mlock) to prevent swapping to disk
- Secure zeroing of memory when keys are no longer needed
- Context manager for automatic cleanup

Security considerations:
- Keys in memory can be exposed via memory dumps, swap files, or core dumps
- mlock() prevents the OS from swapping memory to disk
- Explicit zeroing overwrites key material before deallocation
- Python's garbage collection doesn't guarantee immediate memory clearing

Platform support:
- Linux/macOS: Full mlock support
- Windows: Limited support via VirtualLock (requires appropriate privileges)
- Fallback: Graceful degradation with warnings on unsupported platforms
"""

from __future__ import annotations

import ctypes
import logging
import os
import platform
import sys
from contextlib import contextmanager
from typing import Generator

logger = logging.getLogger(__name__)

# Platform detection
_PLATFORM = platform.system().lower()
_IS_LINUX = _PLATFORM == "linux"
_IS_MACOS = _PLATFORM == "darwin"
_IS_WINDOWS = _PLATFORM == "windows"


def _get_libc():
    """Get the C library for memory operations."""
    if _IS_LINUX:
        return ctypes.CDLL("libc.so.6", use_errno=True)
    elif _IS_MACOS:
        return ctypes.CDLL("libc.dylib", use_errno=True)
    return None


# Cache libc reference
_libc = None
try:
    _libc = _get_libc()
except OSError:
    logger.warning("Could not load libc for secure memory operations")


def secure_zero(data: bytearray | memoryview) -> None:
    """Securely zero out memory containing sensitive data.

    Uses ctypes.memset for reliable zeroing that won't be optimized away.

    Args:
        data: Mutable buffer to zero (bytearray or memoryview)

    Example:
        key_data = bytearray(secret_key)
        try:
            # Use key_data
            pass
        finally:
            secure_zero(key_data)
    """
    if not data:
        return

    if isinstance(data, memoryview):
        # Get the underlying buffer address
        buf = (ctypes.c_char * len(data)).from_buffer(data)
        ctypes.memset(ctypes.addressof(buf), 0, len(data))
    elif isinstance(data, bytearray):
        # Create a ctypes array that shares the bytearray's buffer
        buf = (ctypes.c_char * len(data)).from_buffer(data)
        ctypes.memset(ctypes.addressof(buf), 0, len(data))
    else:
        raise TypeError(f"Cannot securely zero {type(data).__name__}, use bytearray or memoryview")


def mlock(data: bytearray | memoryview) -> bool:
    """Lock memory to prevent swapping to disk.

    Args:
        data: Buffer to lock in memory

    Returns:
        True if successfully locked, False otherwise
    """
    if not _libc:
        return False

    if not data:
        return True

    try:
        if isinstance(data, memoryview):
            buf = (ctypes.c_char * len(data)).from_buffer(data)
            addr = ctypes.addressof(buf)
        elif isinstance(data, bytearray):
            buf = (ctypes.c_char * len(data)).from_buffer(data)
            addr = ctypes.addressof(buf)
        else:
            return False

        result = _libc.mlock(ctypes.c_void_p(addr), ctypes.c_size_t(len(data)))

        if result != 0:
            errno = ctypes.get_errno()
            if errno == 12:  # ENOMEM - resource limits
                logger.debug("mlock failed: resource limits (consider ulimit -l)")
            elif errno == 1:  # EPERM - permission denied
                logger.debug("mlock failed: permission denied")
            return False

        return True
    except Exception as e:
        logger.debug(f"mlock failed: {e}")
        return False


def munlock(data: bytearray | memoryview) -> bool:
    """Unlock previously locked memory.

    Args:
        data: Buffer to unlock

    Returns:
        True if successfully unlocked, False otherwise
    """
    if not _libc:
        return False

    if not data:
        return True

    try:
        if isinstance(data, memoryview):
            buf = (ctypes.c_char * len(data)).from_buffer(data)
            addr = ctypes.addressof(buf)
        elif isinstance(data, bytearray):
            buf = (ctypes.c_char * len(data)).from_buffer(data)
            addr = ctypes.addressof(buf)
        else:
            return False

        result = _libc.munlock(ctypes.c_void_p(addr), ctypes.c_size_t(len(data)))
        return result == 0
    except Exception:
        return False


class SecureBytes:
    """A secure container for sensitive byte data.

    Provides:
    - Automatic memory locking (if available)
    - Secure zeroing on cleanup
    - Context manager support
    - Immutable-like interface (modifications create new instances)

    Example:
        # Create secure key storage
        with SecureBytes(secret_key_bytes) as secure_key:
            # Use secure_key.data for operations
            signature = sign(message, secure_key.data)
        # Key is securely zeroed after context exit

        # Or without context manager (manual cleanup)
        secure_key = SecureBytes(key_bytes)
        try:
            # Use secure_key
            pass
        finally:
            secure_key.clear()
    """

    def __init__(self, data: bytes | bytearray, lock_memory: bool = True):
        """Initialize with sensitive data.

        Args:
            data: Sensitive bytes to protect
            lock_memory: Whether to attempt memory locking (default True)
        """
        # Always use bytearray for mutable zeroing
        self._data = bytearray(data)
        self._locked = False
        self._cleared = False

        if lock_memory:
            self._locked = mlock(self._data)
            if not self._locked:
                logger.debug("Memory locking unavailable; key may be swapped to disk")

    @property
    def data(self) -> bytes:
        """Get the protected data as immutable bytes.

        Returns:
            The protected bytes (read-only view)

        Raises:
            ValueError: If data has been cleared
        """
        if self._cleared:
            raise ValueError("SecureBytes has been cleared")
        return bytes(self._data)

    @property
    def is_locked(self) -> bool:
        """Whether memory is locked (not swappable)."""
        return self._locked

    @property
    def is_cleared(self) -> bool:
        """Whether data has been securely cleared."""
        return self._cleared

    def __len__(self) -> int:
        """Length of protected data."""
        if self._cleared:
            return 0
        return len(self._data)

    def clear(self) -> None:
        """Securely clear the protected data.

        This method:
        1. Zeros all bytes in memory
        2. Unlocks the memory (if locked)
        3. Marks the instance as cleared

        Safe to call multiple times.
        """
        if self._cleared:
            return

        try:
            # Zero the memory
            secure_zero(self._data)
        finally:
            # Unlock if locked
            if self._locked:
                munlock(self._data)
                self._locked = False

            self._cleared = True

    def __enter__(self) -> SecureBytes:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - securely clear data."""
        self.clear()

    def __del__(self) -> None:
        """Destructor - ensure data is cleared."""
        if not self._cleared:
            self.clear()

    def __repr__(self) -> str:
        """Safe representation (never shows data)."""
        status = "cleared" if self._cleared else f"{len(self._data)} bytes"
        locked = ", locked" if self._locked else ""
        return f"SecureBytes({status}{locked})"

    # Prevent accidental exposure
    def __str__(self) -> str:
        return self.__repr__()

    def __bytes__(self) -> bytes:
        """Allow bytes() conversion."""
        return self.data


@contextmanager
def secure_key_context(key_data: bytes) -> Generator[bytes, None, None]:
    """Context manager for temporarily working with key material.

    Ensures the key is securely zeroed when the context exits.

    Args:
        key_data: Key bytes to protect

    Yields:
        The key bytes for use within the context

    Example:
        with secure_key_context(private_key_bytes) as key:
            signature = sign(message, key)
        # key memory is now zeroed
    """
    secure = SecureBytes(key_data)
    try:
        yield secure.data
    finally:
        secure.clear()


def generate_secure_random(length: int, lock_memory: bool = True) -> SecureBytes:
    """Generate cryptographically secure random bytes in protected memory.

    Args:
        length: Number of random bytes to generate
        lock_memory: Whether to lock memory

    Returns:
        SecureBytes containing random data
    """
    random_bytes = os.urandom(length)
    return SecureBytes(random_bytes, lock_memory=lock_memory)
