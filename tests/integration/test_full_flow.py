"""Integration tests for full agent flow."""

import pytest

from sigaid.crypto.keys import KeyPair
from sigaid.client.agent import AgentClient
from sigaid.verification.verifier import Verifier
from sigaid.models.state import ActionType


class TestFullFlow:
    """Tests for complete agent workflow."""

    @pytest.fixture
    def keypair(self):
        """Create a keypair for testing."""
        return KeyPair.generate()

    @pytest.mark.asyncio
    async def test_create_agent_and_record_actions(self, keypair):
        """Test creating agent and recording actions."""
        # Create agent (offline mode, no HTTP client)
        client = AgentClient.from_keypair(
            keypair,
            authority_url="",  # Disable HTTP client
        )

        try:
            # Acquire lease (local mode)
            async with client.lease() as lease:
                assert lease is not None
                assert client.has_lease

                # Initialize state chain
                genesis = await client.initialize_state_chain()
                assert genesis.sequence == 0

                # Record actions
                entry1 = await client.record_action(
                    action_type=ActionType.TRANSACTION,
                    action_data={"hotel": "Hilton", "amount": 180},
                    action_summary="Booked hotel room",
                    sync_to_authority=False,
                )
                assert entry1.sequence == 1

                entry2 = await client.record_action(
                    action_type="transaction",
                    action_data={"flight": "LH123", "amount": 350},
                    action_summary="Booked flight",
                    sync_to_authority=False,
                )
                assert entry2.sequence == 2

                # Check state head
                assert client.state_head == entry2

            # Lease should be released
            assert not client.has_lease

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_proof_creation_and_verification(self, keypair):
        """Test creating and verifying proofs."""
        client = AgentClient.from_keypair(keypair, authority_url="")
        verifier = Verifier()  # Offline mode

        try:
            async with client.lease() as lease:
                await client.initialize_state_chain()
                await client.record_action(
                    "transaction",
                    {"amount": 100},
                    sync_to_authority=False,
                )

                # Create challenge
                challenge = verifier.create_challenge()

                # Create proof
                proof = client.create_proof(challenge)

                assert proof.agent_id == str(client.agent_id)
                assert proof.state_head is not None

                # Verify proof (offline)
                result = verifier.verify_offline(proof, challenge)

                assert result.valid
                assert result.signature_valid
                assert result.challenge_valid
                assert result.chain_valid

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_agent_from_new_creation(self):
        """Test creating agent with AgentClient.create()."""
        client = AgentClient.create(authority_url="")

        try:
            assert client.agent_id is not None
            assert str(client.agent_id).startswith("aid_")

            async with client.lease():
                await client.initialize_state_chain()
                entry = await client.record_action(
                    "attestation",
                    {"test": True},
                    sync_to_authority=False,
                )
                assert entry is not None

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_state_chain_continuity(self, keypair):
        """Test that state chain maintains continuity across sessions."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"

            # Session 1: Create agent and record actions
            client1 = AgentClient.from_keypair(
                keypair,
                authority_url="",
                state_persistence_path=state_path,
            )

            try:
                async with client1.lease():
                    await client1.initialize_state_chain()
                    entry1 = await client1.record_action(
                        "transaction",
                        {"session": 1},
                        sync_to_authority=False,
                    )
                    head1 = client1.state_head
            finally:
                await client1.close()

            # Session 2: Load and continue
            client2 = AgentClient.from_keypair(
                keypair,
                authority_url="",
                state_persistence_path=state_path,
            )

            try:
                async with client2.lease():
                    # State should be loaded
                    assert client2.state_head.entry_hash == head1.entry_hash

                    # Continue chain
                    entry2 = await client2.record_action(
                        "transaction",
                        {"session": 2},
                        sync_to_authority=False,
                    )

                    # Verify continuity
                    assert entry2.prev_hash == head1.entry_hash
                    assert entry2.sequence == head1.sequence + 1

            finally:
                await client2.close()
