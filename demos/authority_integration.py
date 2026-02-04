#!/usr/bin/env python3
"""Authority integration demo for SigAid protocol.

This demo shows full integration with the Authority Service:
1. Registering an agent with the Authority
2. Acquiring a lease with cryptographic verification
3. Syncing state chain entries to the Authority
4. Clone rejection in action

Prerequisites:
- Authority service running at http://localhost:8001
- Database configured and migrated

To run:
    # Start Authority first
    cd authority && uvicorn main:app --port 8001

    # Run demo
    python demos/authority_integration.py
"""

import asyncio
import sys

from sigaid import AgentClient, Verifier, ActionType
from sigaid.exceptions import LeaseHeldByAnotherInstance


AUTHORITY_URL = "http://localhost:8001"


async def check_authority():
    """Check if Authority is running."""
    import httpx

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{AUTHORITY_URL}/health", timeout=5.0)
            if response.status_code == 200:
                return True
    except Exception:
        pass
    return False


async def main():
    print("=" * 60)
    print("SigAid Authority Integration Demo")
    print("=" * 60)

    # Check Authority is running
    print("\nChecking Authority service...")
    if not await check_authority():
        print(f"ERROR: Authority not running at {AUTHORITY_URL}")
        print("Start it with: uvicorn authority.main:app --port 8001")
        sys.exit(1)
    print(f"Authority running at {AUTHORITY_URL}")

    # 1. Create and register agent
    print("\n1. Creating and registering agent...")
    client = AgentClient.create(authority_url=AUTHORITY_URL)

    async with client:
        # Register with Authority
        await client.register(metadata={"demo": True, "version": "1.0"})
        print(f"   Agent ID: {client.agent_id}")
        print("   Registered with Authority")

        # 2. Acquire lease with signature verification
        print("\n2. Acquiring lease (with crypto verification)...")
        async with client.lease() as lease:
            print(f"   Session: {lease.session_id[:16]}...")
            print(f"   Token: {lease.token[:50]}...")
            print(f"   Expires: {lease.expires_at}")

            # 3. Initialize and sync state chain
            print("\n3. Syncing state chain to Authority...")

            # Genesis entry
            genesis = await client.initialize_state_chain("Agent created via demo")
            print(f"   Genesis synced (seq: {genesis.sequence})")

            # Transaction entries
            entry1 = await client.record_action(
                action_type=ActionType.TRANSACTION,
                action_data={"amount": 100, "currency": "CHF"},
                action_summary="Demo transaction 1",
            )
            print(f"   Entry synced (seq: {entry1.sequence})")

            entry2 = await client.record_action(
                action_type=ActionType.ATTESTATION,
                action_data={"verified": True},
                action_summary="Demo attestation",
            )
            print(f"   Entry synced (seq: {entry2.sequence})")

            # 4. Get agent info from Authority
            print("\n4. Fetching agent info from Authority...")
            info = await client.get_agent_info()
            print(f"   Status: {info.get('status')}")
            print(f"   Transactions: {info.get('total_transactions')}")
            print(f"   Reputation: {info.get('reputation_score')}")

            # 5. Demonstrate clone rejection
            print("\n5. Testing clone rejection...")
            clone = AgentClient.from_keypair(
                client.keypair, authority_url=AUTHORITY_URL
            )

            async with clone:
                try:
                    await clone.acquire_lease()
                    print("   ERROR: Clone should have been rejected!")
                except LeaseHeldByAnotherInstance as e:
                    print(f"   Clone rejected: {e}")

            # 6. Create and verify proof
            print("\n6. Creating verification proof...")
            verifier = Verifier()
            challenge = verifier.create_challenge()
            proof = client.create_proof(challenge)

            result = verifier.verify_offline(proof, challenge)
            print(f"   Proof valid: {result.valid}")
            print(f"   State head: seq {proof.state_head.sequence}")

        print("\n7. Lease released")

    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
