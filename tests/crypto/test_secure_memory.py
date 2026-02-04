"""Tests for secure memory handling."""

import ctypes
import platform
import pytest

from sigaid.crypto.secure_memory import (
    SecureBytes,
    secure_zero,
    mlock,
    munlock,
    secure_key_context,
    generate_secure_random,
)


class TestSecureZero:
    """Tests for secure_zero function."""

    def test_zeros_bytearray(self):
        """Test zeroing a bytearray."""
        data = bytearray(b"secret data here")
        original_len = len(data)

        secure_zero(data)

        assert len(data) == original_len
        assert all(b == 0 for b in data)

    def test_zeros_memoryview(self):
        """Test zeroing a memoryview."""
        data = bytearray(b"another secret")
        view = memoryview(data)

        secure_zero(view)

        assert all(b == 0 for b in data)

    def test_empty_bytearray(self):
        """Test zeroing empty bytearray does nothing."""
        data = bytearray()
        secure_zero(data)  # Should not raise
        assert len(data) == 0

    def test_rejects_immutable_bytes(self):
        """Test that immutable bytes raises TypeError."""
        data = b"immutable"
        with pytest.raises(TypeError):
            secure_zero(data)

    def test_zeros_large_buffer(self):
        """Test zeroing large buffer."""
        data = bytearray(b"x" * 10000)
        secure_zero(data)
        assert all(b == 0 for b in data)


class TestSecureBytes:
    """Tests for SecureBytes class."""

    def test_create_from_bytes(self):
        """Test creating SecureBytes from bytes."""
        secret = b"my secret key material"
        secure = SecureBytes(secret)

        assert secure.data == secret
        assert len(secure) == len(secret)
        assert not secure.is_cleared

    def test_create_from_bytearray(self):
        """Test creating SecureBytes from bytearray."""
        secret = bytearray(b"another secret")
        secure = SecureBytes(secret)

        assert secure.data == bytes(secret)

    def test_clear_zeros_data(self):
        """Test clear() zeros the data."""
        secret = b"secret to clear"
        secure = SecureBytes(secret, lock_memory=False)

        secure.clear()

        assert secure.is_cleared
        assert len(secure) == 0

    def test_clear_multiple_times_safe(self):
        """Test clear() can be called multiple times."""
        secure = SecureBytes(b"data", lock_memory=False)
        secure.clear()
        secure.clear()  # Should not raise
        assert secure.is_cleared

    def test_data_raises_after_clear(self):
        """Test accessing data after clear raises."""
        secure = SecureBytes(b"data", lock_memory=False)
        secure.clear()

        with pytest.raises(ValueError, match="cleared"):
            _ = secure.data

    def test_context_manager(self):
        """Test using SecureBytes as context manager."""
        with SecureBytes(b"context secret", lock_memory=False) as secure:
            assert secure.data == b"context secret"
            assert not secure.is_cleared

        assert secure.is_cleared

    def test_context_manager_clears_on_exception(self):
        """Test context manager clears even on exception."""
        secure = None
        try:
            with SecureBytes(b"data", lock_memory=False) as s:
                secure = s
                raise ValueError("test error")
        except ValueError:
            pass

        assert secure.is_cleared

    def test_repr_does_not_expose_data(self):
        """Test repr doesn't show actual data."""
        secure = SecureBytes(b"super secret", lock_memory=False)
        repr_str = repr(secure)

        assert "super secret" not in repr_str
        assert "12 bytes" in repr_str

    def test_repr_shows_cleared(self):
        """Test repr shows cleared status."""
        secure = SecureBytes(b"data", lock_memory=False)
        secure.clear()

        assert "cleared" in repr(secure)

    def test_str_does_not_expose_data(self):
        """Test str() doesn't show actual data."""
        secure = SecureBytes(b"secret", lock_memory=False)
        assert "secret" not in str(secure)

    def test_bytes_conversion(self):
        """Test bytes() conversion."""
        secret = b"convert me"
        secure = SecureBytes(secret, lock_memory=False)

        assert bytes(secure) == secret

    def test_memory_locking_attempted(self):
        """Test that memory locking is attempted."""
        secure = SecureBytes(b"lock me", lock_memory=True)
        # is_locked may be True or False depending on platform/permissions
        # Just verify it doesn't crash
        _ = secure.is_locked
        secure.clear()

    def test_destructor_clears_data(self):
        """Test __del__ clears data."""
        secure = SecureBytes(b"destructor test", lock_memory=False)
        # Explicitly call __del__
        secure.__del__()
        assert secure.is_cleared


class TestMlockMunlock:
    """Tests for mlock/munlock functions."""

    def test_mlock_returns_bool(self):
        """Test mlock returns boolean."""
        data = bytearray(b"test data")
        result = mlock(data)
        assert isinstance(result, bool)
        # Cleanup
        if result:
            munlock(data)

    def test_munlock_returns_bool(self):
        """Test munlock returns boolean."""
        data = bytearray(b"test data")
        result = munlock(data)
        assert isinstance(result, bool)

    def test_mlock_empty_data(self):
        """Test mlock with empty data."""
        result = mlock(bytearray())
        assert result is True  # Empty data is "successfully" locked

    def test_munlock_empty_data(self):
        """Test munlock with empty data."""
        result = munlock(bytearray())
        assert result is True


class TestSecureKeyContext:
    """Tests for secure_key_context function."""

    def test_yields_key_data(self):
        """Test context manager yields key data."""
        key = b"my encryption key"

        with secure_key_context(key) as k:
            assert k == key

    def test_clears_on_exit(self):
        """Test key is cleared on context exit."""
        key = b"temporary key"

        with secure_key_context(key) as _:
            pass
        # Can't directly verify zeroing, but no exception means success

    def test_clears_on_exception(self):
        """Test key is cleared even on exception."""
        key = b"exception key"

        try:
            with secure_key_context(key) as _:
                raise RuntimeError("test")
        except RuntimeError:
            pass
        # No exception from cleanup means success


class TestGenerateSecureRandom:
    """Tests for generate_secure_random function."""

    def test_generates_requested_length(self):
        """Test generates bytes of requested length."""
        secure = generate_secure_random(32, lock_memory=False)
        assert len(secure) == 32
        secure.clear()

    def test_generates_random_data(self):
        """Test generates different data each time."""
        s1 = generate_secure_random(16, lock_memory=False)
        s2 = generate_secure_random(16, lock_memory=False)

        assert s1.data != s2.data

        s1.clear()
        s2.clear()

    def test_returns_secure_bytes(self):
        """Test returns SecureBytes instance."""
        secure = generate_secure_random(16, lock_memory=False)
        assert isinstance(secure, SecureBytes)
        secure.clear()

    def test_can_lock_memory(self):
        """Test memory locking option works."""
        secure = generate_secure_random(16, lock_memory=True)
        # Just verify it doesn't crash
        secure.clear()


class TestSecureBytesLocking:
    """Additional tests for SecureBytes locking behavior."""

    def test_locked_status_reflects_reality(self):
        """Test is_locked returns actual status."""
        secure = SecureBytes(b"test", lock_memory=True)

        # is_locked is True if mlock succeeded, False otherwise
        # We just verify it's a boolean
        assert isinstance(secure.is_locked, bool)
        secure.clear()

    def test_clear_unlocks_memory(self):
        """Test clear unlocks memory."""
        secure = SecureBytes(b"test", lock_memory=True)
        was_locked = secure.is_locked

        secure.clear()

        # After clear, should not be locked
        assert not secure._locked

    def test_bytes_conversion_after_clear_raises(self):
        """Test bytes() conversion after clear raises."""
        secure = SecureBytes(b"test", lock_memory=False)
        secure.clear()

        with pytest.raises(ValueError, match="cleared"):
            bytes(secure)


class TestMlockEdgeCases:
    """Edge case tests for mlock/munlock."""

    def test_mlock_with_memoryview(self):
        """Test mlock with memoryview."""
        data = bytearray(b"test data")
        view = memoryview(data)
        result = mlock(view)
        assert isinstance(result, bool)
        if result:
            munlock(view)

    def test_munlock_with_memoryview(self):
        """Test munlock with memoryview."""
        data = bytearray(b"test data")
        view = memoryview(data)
        # First try to lock
        mlock(view)
        # Then unlock
        result = munlock(view)
        assert isinstance(result, bool)

    def test_mlock_with_other_type_fails(self):
        """Test mlock with unsupported type returns False."""
        result = mlock(b"immutable bytes")
        assert result is False

    def test_munlock_with_other_type_fails(self):
        """Test munlock with unsupported type returns False."""
        result = munlock(b"immutable bytes")
        assert result is False
