"""Tests for crypto/hashing.py - BLAKE3 hashing operations."""

import pytest

from sigaid.crypto.hashing import (
    hash_bytes,
    hash_hex,
    hash_multiple,
    ZERO_HASH,
)
from sigaid.constants import BLAKE3_HASH_SIZE


class TestHashBytes:
    """Tests for hash_bytes function."""
    
    def test_produces_correct_length(self):
        """hash_bytes() should produce 32-byte hash."""
        result = hash_bytes(b"test data")
        assert len(result) == BLAKE3_HASH_SIZE
    
    def test_is_deterministic(self):
        """hash_bytes() should be deterministic."""
        data = b"same data"
        assert hash_bytes(data) == hash_bytes(data)
    
    def test_different_input_different_hash(self):
        """Different inputs should produce different hashes."""
        hash1 = hash_bytes(b"input 1")
        hash2 = hash_bytes(b"input 2")
        assert hash1 != hash2
    
    def test_empty_input_produces_hash(self):
        """Empty input should produce valid hash."""
        result = hash_bytes(b"")
        assert len(result) == BLAKE3_HASH_SIZE


class TestHashHex:
    """Tests for hash_hex function."""
    
    def test_produces_hex_string(self):
        """hash_hex() should produce hex string."""
        result = hash_hex(b"test data")
        assert isinstance(result, str)
        assert len(result) == BLAKE3_HASH_SIZE * 2  # 2 hex chars per byte
    
    def test_matches_hash_bytes(self):
        """hash_hex() should match hash_bytes().hex()."""
        data = b"test data"
        assert hash_hex(data) == hash_bytes(data).hex()


class TestHashMultiple:
    """Tests for hash_multiple function."""
    
    def test_hashes_multiple_items(self):
        """hash_multiple() should combine items."""
        result = hash_multiple(b"item1", b"item2", b"item3")
        assert len(result) == BLAKE3_HASH_SIZE
    
    def test_order_matters(self):
        """Different order should produce different hash."""
        hash1 = hash_multiple(b"a", b"b")
        hash2 = hash_multiple(b"b", b"a")
        assert hash1 != hash2
    
    def test_concatenation_ambiguity(self):
        """Length prefixing should prevent concatenation ambiguity."""
        # These would be identical without length prefixes
        hash1 = hash_multiple(b"ab", b"cd")
        hash2 = hash_multiple(b"abc", b"d")
        assert hash1 != hash2


class TestZeroHash:
    """Tests for ZERO_HASH constant."""
    
    def test_correct_length(self):
        """ZERO_HASH should be 32 bytes."""
        assert len(ZERO_HASH) == BLAKE3_HASH_SIZE
    
    def test_all_zeros(self):
        """ZERO_HASH should be all zeros."""
        assert ZERO_HASH == bytes(BLAKE3_HASH_SIZE)
