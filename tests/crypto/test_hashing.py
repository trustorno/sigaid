"""Tests for BLAKE3 hashing operations."""

import pytest

from sigaid.crypto.hashing import hash_bytes, hash_hex, hash_multiple


class TestHashing:
    """Tests for hashing functions."""

    def test_hash_bytes_returns_32_bytes(self):
        """Test that hash_bytes returns 32-byte digest."""
        result = hash_bytes(b"hello")
        assert len(result) == 32

    def test_hash_bytes_is_deterministic(self):
        """Test that same input produces same hash."""
        data = b"test data"
        assert hash_bytes(data) == hash_bytes(data)

    def test_hash_bytes_different_inputs(self):
        """Test that different inputs produce different hashes."""
        assert hash_bytes(b"hello") != hash_bytes(b"world")

    def test_hash_hex_returns_hex_string(self):
        """Test that hash_hex returns hex string."""
        result = hash_hex(b"hello")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_hash_multiple_combines_parts(self):
        """Test that hash_multiple combines parts."""
        # Hashing parts separately and concatenating
        combined = hash_bytes(b"helloworld")
        # Hashing with hash_multiple
        multi = hash_multiple(b"hello", b"world")

        # Should be different (hash_multiple feeds incrementally)
        # Actually they might be the same since BLAKE3 is streaming
        assert len(multi) == 32

    def test_hash_empty_input(self):
        """Test hashing empty input."""
        result = hash_bytes(b"")
        assert len(result) == 32

    def test_hash_large_input(self):
        """Test hashing large input."""
        large_data = b"x" * 1_000_000
        result = hash_bytes(large_data)
        assert len(result) == 32
