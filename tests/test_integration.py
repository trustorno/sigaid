"""Integration tests for SigAid SDK with Authority Service."""

import asyncio
import base64
import pytest
from datetime import datetime, timezone

# SDK imports
from sigaid.client.agent import AgentClient
from sigaid.client.http import HttpClient
from sigaid.crypto.keys import KeyPair
from sigaid.models.state import ActionType
from sigaid.constants import DOMAIN_LEASE


# Authority URL (default local)
AUTHORITY_URL = "http://localhost:8001"


class TestIntegration:
    """Integration tests for SDK <-> Authority communication."""

    @pytest.fixture
    def keypair(self):
        """Generate a fresh keypair for testing."""
        return KeyPair.generate()

    @pytest.fixture
    def agent_client(self, keypair):
        """Create an agent client."""
        return AgentClient.from_keypair(keypair, authority_url=AUTHORITY_URL)

    @pytest.mark.asyncio
    async def test_agent_registration(self, agent_client):
        """Test agent registration with Authority."""
        async with agent_client:
            # Register agent
            response = await agent_client.register(metadata={"test": True})

            assert "agent_id" in response
            assert response["agent_id"] == str(agent_client.agent_id)
            assert response["status"] == "active"

    @pytest.mark.asyncio
    async def test_lease_acquisition(self, agent_client):
        """Test lease acquisition flow."""
        async with agent_client:
            # Register first
            await agent_client.register()

            # Acquire lease
            async with agent_client.lease() as lease:
                assert lease is not None
                assert lease.is_active
                assert lease.agent_id == str(agent_client.agent_id)

    @pytest.mark.asyncio
    async def test_state_chain_append(self, agent_client):
        """Test appending to state chain."""
        async with agent_client:
            # Register
            await agent_client.register()

            # Acquire lease and record action
            async with agent_client.lease():
                # Initialize state chain
                genesis = await agent_client.initialize_state_chain("Test agent")
                assert genesis.sequence == 0

                # Record an action
                entry = await agent_client.record_action(
                    action_type=ActionType.TRANSACTION,
                    action_data={"amount": 100, "recipient": "test"},
                    action_summary="Test transaction",
                )

                assert entry.sequence == 1
                assert entry.action_type == ActionType.TRANSACTION

    @pytest.mark.asyncio
    async def test_clone_rejection(self, keypair):
        """Test that clones (same keypair) cannot both hold leases."""
        client1 = AgentClient.from_keypair(keypair, authority_url=AUTHORITY_URL)
        client2 = AgentClient.from_keypair(keypair, authority_url=AUTHORITY_URL)

        async with client1:
            # Register agent
            await client1.register()

            # Client 1 acquires lease
            async with client1.lease():
                # Client 2 should fail to acquire
                async with client2:
                    from sigaid.exceptions import LeaseHeldByAnotherInstance

                    with pytest.raises(LeaseHeldByAnotherInstance):
                        await client2.acquire_lease()

    @pytest.mark.asyncio
    async def test_signature_verification(self, keypair):
        """Test that signatures are properly verified by Authority."""
        client = AgentClient.from_keypair(keypair, authority_url=AUTHORITY_URL)

        async with client:
            await client.register()

            # The lease acquisition will fail if signature verification fails
            async with client.lease() as lease:
                assert lease.is_active

    @pytest.mark.asyncio
    async def test_state_chain_sync(self, agent_client):
        """Test that state chain entries are synced to Authority."""
        async with agent_client:
            await agent_client.register()

            async with agent_client.lease():
                # Initialize and add entry
                await agent_client.initialize_state_chain()

                entry = await agent_client.record_action(
                    action_type="transaction",
                    action_data={"test": "data"},
                )

                # Verify entry hash is valid
                assert entry.verify_hash()

                # Verify signature
                assert entry.verify_signature(
                    agent_client.keypair.public_key_bytes()
                )


# Manual test script
async def manual_test():
    """Run manual integration test (for debugging)."""
    print("=== SigAid Integration Test ===\n")

    # Create agent
    print("1. Creating agent...")
    client = AgentClient.create(authority_url=AUTHORITY_URL)
    print(f"   Agent ID: {client.agent_id}")

    try:
        async with client:
            # Register
            print("\n2. Registering with Authority...")
            response = await client.register(metadata={"test": True})
            print(f"   Registered: {response.get('agent_id')}")
            print(f"   Status: {response.get('status')}")

            # Acquire lease
            print("\n3. Acquiring lease...")
            async with client.lease() as lease:
                print(f"   Session: {lease.session_id}")
                print(f"   Expires: {lease.expires_at}")

                # Initialize state chain
                print("\n4. Initializing state chain...")
                genesis = await client.initialize_state_chain("Test agent created")
                print(f"   Genesis entry: sequence={genesis.sequence}")

                # Record action
                print("\n5. Recording action...")
                entry = await client.record_action(
                    action_type=ActionType.TRANSACTION,
                    action_data={"amount": 100, "recipient": "test_user"},
                    action_summary="Test transaction",
                )
                print(f"   Entry: sequence={entry.sequence}, hash={entry.entry_hash.hex()[:16]}...")

                # Create proof
                print("\n6. Creating proof bundle...")
                proof = client.create_proof(challenge=b"test_challenge_123")
                print(f"   Proof created for agent: {proof.agent_id}")

            print("\n7. Lease released.")

        print("\n=== Test Completed Successfully ===")

    except Exception as e:
        print(f"\n!!! Test Failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(manual_test())
