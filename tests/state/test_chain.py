"""Tests for state chain operations."""

import tempfile
from pathlib import Path

import pytest

from sigaid.crypto.keys import KeyPair
from sigaid.state.chain import StateChain
from sigaid.models.state import ActionType
from sigaid.exceptions import StateChainError


class TestStateChain:
    """Tests for StateChain class."""

    @pytest.fixture
    def keypair(self):
        """Create a keypair for testing."""
        return KeyPair.generate()

    @pytest.fixture
    def chain(self, keypair):
        """Create a state chain for testing."""
        return StateChain(
            agent_id=str(keypair.to_agent_id()),
            keypair=keypair,
        )

    def test_initialize_creates_genesis(self, chain):
        """Test that initialize creates genesis entry."""
        entry = chain.initialize()

        assert entry.sequence == 0
        assert chain.head == entry
        assert len(chain) == 1

    def test_initialize_only_once(self, chain):
        """Test that chain can only be initialized once."""
        chain.initialize()

        with pytest.raises(StateChainError):
            chain.initialize()

    def test_append_entry(self, chain):
        """Test appending entries to chain."""
        chain.initialize()

        entry = chain.append(
            action_type=ActionType.TRANSACTION,
            action_summary="Test transaction",
            action_data={"amount": 100},
        )

        assert entry.sequence == 1
        assert chain.head == entry
        assert len(chain) == 2

    def test_append_links_to_previous(self, chain):
        """Test that append creates proper hash links."""
        genesis = chain.initialize()
        entry1 = chain.append(ActionType.TRANSACTION, "First", {"n": 1})
        entry2 = chain.append(ActionType.TRANSACTION, "Second", {"n": 2})

        assert entry1.prev_hash == genesis.entry_hash
        assert entry2.prev_hash == entry1.entry_hash

    def test_verify_valid_chain(self, chain):
        """Test verifying a valid chain."""
        chain.initialize()
        chain.append(ActionType.TRANSACTION, "Action 1", {})
        chain.append(ActionType.TRANSACTION, "Action 2", {})

        assert chain.verify()

    def test_iterate_entries(self, chain):
        """Test iterating over entries."""
        chain.initialize()
        chain.append(ActionType.TRANSACTION, "Action 1", {})
        chain.append(ActionType.TRANSACTION, "Action 2", {})

        entries = list(chain)
        assert len(entries) == 3
        assert entries[0].sequence == 0
        assert entries[2].sequence == 2

    def test_get_entry_by_index(self, chain):
        """Test getting entry by index."""
        chain.initialize()
        entry = chain.append(ActionType.TRANSACTION, "Test", {})

        assert chain[1] == entry

    def test_get_entries_since(self, chain):
        """Test getting entries since a sequence."""
        chain.initialize()
        chain.append(ActionType.TRANSACTION, "Action 1", {})
        chain.append(ActionType.TRANSACTION, "Action 2", {})

        entries = chain.get_entries_since(0)
        assert len(entries) == 2
        assert entries[0].sequence == 1

    def test_get_entry_by_hash(self, chain):
        """Test finding entry by hash."""
        chain.initialize()
        entry = chain.append(ActionType.TRANSACTION, "Test", {})

        found = chain.get_entry_by_hash(entry.entry_hash)
        assert found == entry

        not_found = chain.get_entry_by_hash(b"x" * 32)
        assert not_found is None

    def test_persistence(self, keypair):
        """Test chain persistence to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "state.json"

            # Create and populate chain
            chain1 = StateChain(
                agent_id=str(keypair.to_agent_id()),
                keypair=keypair,
                persistence_path=path,
            )
            chain1.initialize()
            chain1.append(ActionType.TRANSACTION, "Test", {"data": "value"})

            assert path.exists()

            # Load in new chain instance
            chain2 = StateChain(
                agent_id=str(keypair.to_agent_id()),
                keypair=keypair,
                persistence_path=path,
            )
            chain2._load_from_file()

            assert len(chain2) == 2
            assert chain2.head.entry_hash == chain1.head.entry_hash

    def test_clear_chain(self, chain):
        """Test clearing the chain."""
        chain.initialize()
        chain.append(ActionType.TRANSACTION, "Test", {})

        chain.clear()

        assert len(chain) == 0
        assert chain.head is None

    def test_action_type_as_string(self, chain):
        """Test using action type as string."""
        chain.initialize()
        entry = chain.append("transaction", "Test", {})

        assert entry.action_type == ActionType.TRANSACTION
