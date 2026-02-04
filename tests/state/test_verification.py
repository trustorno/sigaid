"""Tests for state chain verification."""

import pytest

from sigaid.crypto.keys import KeyPair
from sigaid.state.chain import StateChain
from sigaid.state.verification import ChainVerifier
from sigaid.models.state import ActionType, StateEntry
from sigaid.constants import GENESIS_PREV_HASH
from sigaid.exceptions import ForkDetected, InvalidStateEntry


class TestChainVerifier:
    """Tests for ChainVerifier class."""

    @pytest.fixture
    def keypair(self):
        """Create a keypair for testing."""
        return KeyPair.generate()

    @pytest.fixture
    def chain(self, keypair):
        """Create a populated state chain."""
        chain = StateChain(
            agent_id=str(keypair.to_agent_id()),
            keypair=keypair,
        )
        chain.initialize()
        chain.append(ActionType.TRANSACTION, "Action 1", {"n": 1})
        chain.append(ActionType.TRANSACTION, "Action 2", {"n": 2})
        return chain

    @pytest.fixture
    def verifier(self):
        """Create a chain verifier."""
        return ChainVerifier()

    def test_verify_head_first_interaction(self, verifier, chain):
        """Test verifying head on first interaction."""
        result = verifier.verify_head(chain.agent_id, chain.head)

        assert result is True
        assert verifier.get_known_head(chain.agent_id) == chain.head

    def test_verify_head_same_sequence(self, verifier, chain):
        """Test verifying same head twice."""
        verifier.verify_head(chain.agent_id, chain.head)
        result = verifier.verify_head(chain.agent_id, chain.head)

        assert result is True

    def test_verify_head_extended_chain(self, verifier, chain, keypair):
        """Test verifying extended chain."""
        # Record initial head
        verifier.verify_head(chain.agent_id, chain.head)

        # Extend chain
        chain.append(ActionType.TRANSACTION, "Action 3", {"n": 3})

        # Verify new head
        result = verifier.verify_head(chain.agent_id, chain.head)
        assert result is True

    def test_detect_fork_behind_known(self, verifier, chain, keypair):
        """Test detecting fork when claimed head is behind known."""
        # Extend chain and record head
        chain.append(ActionType.TRANSACTION, "Action 3", {"n": 3})
        verifier.verify_head(chain.agent_id, chain.head)

        # Try to verify an older entry
        old_head = chain[1]  # Sequence 1

        with pytest.raises(ForkDetected) as exc_info:
            verifier.verify_head(chain.agent_id, old_head)

        assert "behind known head" in str(exc_info.value)

    def test_detect_fork_same_sequence_different_hash(self, verifier, chain, keypair):
        """Test detecting fork with same sequence but different hash."""
        verifier.verify_head(chain.agent_id, chain.head)

        # Create a different entry with same sequence
        forked_entry = StateEntry.create(
            agent_id=chain.agent_id,
            sequence=chain.head.sequence,
            prev_hash=chain[chain.head.sequence - 1].entry_hash,
            action_type=ActionType.TRANSACTION,
            action_summary="Forked action",
            action_data={"forked": True},
            keypair=keypair,
        )

        with pytest.raises(ForkDetected) as exc_info:
            verifier.verify_head(chain.agent_id, forked_entry)

        assert "different hash" in str(exc_info.value)

    def test_verify_entry_signature(self, verifier, chain, keypair):
        """Test verifying entry signature."""
        entry = chain.head
        public_key = keypair.public_key_bytes()

        assert verifier.verify_entry_signature(entry, public_key)

    def test_verify_entry_signature_wrong_key(self, verifier, chain):
        """Test that wrong key fails signature verification."""
        entry = chain.head
        wrong_key = KeyPair.generate().public_key_bytes()

        assert not verifier.verify_entry_signature(entry, wrong_key)

    def test_clear_agent(self, verifier, chain):
        """Test clearing known state for an agent."""
        verifier.verify_head(chain.agent_id, chain.head)
        assert verifier.get_known_head(chain.agent_id) is not None

        verifier.clear_agent(chain.agent_id)
        assert verifier.get_known_head(chain.agent_id) is None

    def test_clear_all(self, verifier, chain):
        """Test clearing all known state."""
        verifier.verify_head(chain.agent_id, chain.head)
        verifier.clear_all()

        assert verifier.get_known_head(chain.agent_id) is None
