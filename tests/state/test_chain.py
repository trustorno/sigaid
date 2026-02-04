"""Tests for state/chain.py - State chain operations."""

import pytest
from datetime import datetime, timezone

from sigaid.state.chain import StateChain
from sigaid.models.state import ActionType, StateEntry
from sigaid.crypto.keys import KeyPair
from sigaid.crypto.hashing import ZERO_HASH


class TestStateChain:
    """Tests for StateChain class."""
    
    @pytest.fixture
    def chain(self, keypair):
        """Create a fresh state chain."""
        agent_id = str(keypair.to_agent_id())
        return StateChain(agent_id, keypair)
    
    def test_new_chain_is_empty(self, chain):
        """New chain should be empty."""
        assert chain.is_empty
        assert chain.length == 0
        assert chain.head is None
        assert chain.sequence == -1
    
    def test_append_creates_entry(self, chain):
        """append() should create and return entry."""
        entry = chain.append(
            ActionType.TRANSACTION,
            "Test transaction",
            {"amount": 100},
        )
        
        assert isinstance(entry, StateEntry)
        assert entry.action_type == ActionType.TRANSACTION
        assert entry.action_summary == "Test transaction"
        assert entry.sequence == 0
        assert entry.prev_hash == ZERO_HASH  # First entry
    
    def test_append_increments_sequence(self, chain):
        """Each append should increment sequence."""
        chain.append(ActionType.TRANSACTION, "First")
        chain.append(ActionType.TRANSACTION, "Second")
        chain.append(ActionType.TRANSACTION, "Third")
        
        assert chain.sequence == 2
        assert chain.length == 3
    
    def test_append_links_entries(self, chain):
        """Entries should be linked via prev_hash."""
        entry1 = chain.append(ActionType.TRANSACTION, "First")
        entry2 = chain.append(ActionType.TRANSACTION, "Second")
        
        assert entry2.prev_hash == entry1.entry_hash
    
    def test_head_returns_latest(self, chain):
        """head should return most recent entry."""
        chain.append(ActionType.TRANSACTION, "First")
        entry2 = chain.append(ActionType.TRANSACTION, "Second")
        
        assert chain.head == entry2
    
    def test_get_entry_by_sequence(self, chain):
        """get_entry() should retrieve by sequence."""
        entries = []
        for i in range(5):
            entries.append(chain.append(ActionType.TRANSACTION, f"Entry {i}"))
        
        for i, entry in enumerate(entries):
            assert chain.get_entry(i) == entry
        
        assert chain.get_entry(10) is None
        assert chain.get_entry(-1) is None
    
    def test_get_entries_range(self, chain):
        """get_entries() should return range."""
        for i in range(10):
            chain.append(ActionType.TRANSACTION, f"Entry {i}")
        
        subset = chain.get_entries(2, 5)
        
        assert len(subset) == 3
        assert subset[0].sequence == 2
        assert subset[-1].sequence == 4
    
    def test_verify_valid_chain(self, chain):
        """verify() should pass for valid chain."""
        for i in range(5):
            chain.append(ActionType.TRANSACTION, f"Entry {i}")
        
        assert chain.verify()
    
    def test_iteration(self, chain):
        """Chain should support iteration."""
        for i in range(5):
            chain.append(ActionType.TRANSACTION, f"Entry {i}")
        
        entries = list(chain)
        assert len(entries) == 5
        
        for i, entry in enumerate(entries):
            assert entry.sequence == i
    
    def test_indexing(self, chain):
        """Chain should support indexing."""
        for i in range(5):
            chain.append(ActionType.TRANSACTION, f"Entry {i}")
        
        assert chain[0].sequence == 0
        assert chain[-1].sequence == 4
    
    def test_persistence(self, chain, keypair, temp_dir):
        """Chain should persist and restore."""
        path = temp_dir / "chain.json"
        agent_id = str(keypair.to_agent_id())
        
        # Create chain with entries
        chain_with_path = StateChain(agent_id, keypair, persistence_path=path)
        chain_with_path.append(ActionType.TRANSACTION, "Entry 1")
        chain_with_path.append(ActionType.TRANSACTION, "Entry 2")
        
        # Load in new instance
        restored = StateChain(agent_id, keypair, persistence_path=path)
        
        assert restored.length == 2
        assert restored.head.action_summary == "Entry 2"


class TestStateEntrySignatures:
    """Tests for state entry signature verification."""
    
    def test_entry_signature_valid(self, keypair):
        """Entry signature should be valid."""
        agent_id = str(keypair.to_agent_id())
        chain = StateChain(agent_id, keypair)
        
        entry = chain.append(ActionType.TRANSACTION, "Test")
        
        assert entry.verify_signature(keypair.public_key_bytes())
    
    def test_entry_hash_valid(self, keypair):
        """Entry hash should be valid."""
        agent_id = str(keypair.to_agent_id())
        chain = StateChain(agent_id, keypair)
        
        entry = chain.append(ActionType.TRANSACTION, "Test")
        
        assert entry.verify_hash()
    
    def test_wrong_key_fails_signature(self, keypair):
        """Signature should fail with wrong key."""
        agent_id = str(keypair.to_agent_id())
        chain = StateChain(agent_id, keypair)
        
        entry = chain.append(ActionType.TRANSACTION, "Test")
        wrong_keypair = KeyPair.generate()
        
        assert not entry.verify_signature(wrong_keypair.public_key_bytes())
