#!/usr/bin/env python3
"""Basic usage demo for SigAid protocol.

This demo shows:
1. Creating an agent with fresh identity
2. Acquiring an exclusive lease
3. Recording actions to the state chain
4. Creating verification proofs
"""

import asyncio
from pathlib import Path
import tempfile

from sigaid import AgentClient, Verifier, ActionType


async def main():
    print("=" * 60)
    print("SigAid Basic Usage Demo")
    print("=" * 60)

    # Create a temporary directory for persistence
    with tempfile.TemporaryDirectory() as tmpdir:
        state_path = Path(tmpdir) / "agent_state.json"
        key_path = Path(tmpdir) / "agent.key"

        # 1. Create a new agent
        print("\n1. Creating new agent...")
        client = AgentClient.create(
            authority_url="",  # Offline mode for demo
            state_persistence_path=state_path,
        )

        print(f"   Agent ID: {client.agent_id}")
        print(f"   Agent ID (short): {client.agent_id.short}")

        # Save keypair for later
        client.save_keypair(key_path, "demo_password")
        print(f"   Keypair saved to: {key_path}")

        try:
            # 2. Acquire exclusive lease
            print("\n2. Acquiring exclusive lease...")
            async with client.lease() as lease:
                print(f"   Session ID: {lease.session_id[:16]}...")
                print(f"   Expires at: {lease.expires_at}")
                print(f"   Has lease: {client.has_lease}")

                # 3. Initialize state chain
                print("\n3. Initializing state chain...")
                genesis = await client.initialize_state_chain("Demo agent created")
                print(f"   Genesis entry created (seq: {genesis.sequence})")

                # 4. Record actions
                print("\n4. Recording actions...")

                # Transaction 1
                entry1 = await client.record_action(
                    action_type=ActionType.TRANSACTION,
                    action_data={
                        "type": "hotel_booking",
                        "hotel": "Grand Hotel",
                        "nights": 3,
                        "amount_chf": 450,
                    },
                    action_summary="Booked hotel: Grand Hotel for 3 nights",
                    sync_to_authority=False,
                )
                print(f"   Recorded: {entry1.action_summary} (seq: {entry1.sequence})")

                # Transaction 2
                entry2 = await client.record_action(
                    action_type=ActionType.TRANSACTION,
                    action_data={
                        "type": "flight_booking",
                        "flight": "LX1234",
                        "from": "ZRH",
                        "to": "LHR",
                        "amount_chf": 280,
                    },
                    action_summary="Booked flight: ZRH to LHR",
                    sync_to_authority=False,
                )
                print(f"   Recorded: {entry2.action_summary} (seq: {entry2.sequence})")

                # Attestation
                entry3 = await client.record_action(
                    action_type=ActionType.ATTESTATION,
                    action_data={"verified": True, "by": "demo_service"},
                    action_summary="Identity verified by demo service",
                    sync_to_authority=False,
                )
                print(f"   Recorded: {entry3.action_summary} (seq: {entry3.sequence})")

                # 5. Create verification proof
                print("\n5. Creating verification proof...")
                verifier = Verifier()
                challenge = verifier.create_challenge()
                print(f"   Challenge: {challenge.hex()[:32]}...")

                proof = client.create_proof(challenge)
                print(f"   Proof created for agent: {proof.agent_id}")
                print(f"   State head sequence: {proof.state_head.sequence}")

                # 6. Verify the proof (offline)
                print("\n6. Verifying proof (offline)...")
                result = verifier.verify_offline(proof, challenge)

                print(f"   Valid: {result.valid}")
                print(f"   Signature valid: {result.signature_valid}")
                print(f"   Challenge valid: {result.challenge_valid}")
                print(f"   Chain valid: {result.chain_valid}")

            # Lease automatically released
            print("\n7. Lease released")
            print(f"   Has lease: {client.has_lease}")

        finally:
            await client.close()

        # 8. Reload agent from file
        print("\n8. Reloading agent from saved keypair...")
        client2 = AgentClient.from_file(
            key_path,
            "demo_password",
            authority_url="",
            state_persistence_path=state_path,
        )

        try:
            async with client2.lease():
                print(f"   Reloaded agent: {client2.agent_id.short}")
                print(f"   State chain length: {len(list(client2._state_chain))}")
                print(f"   Current head: seq {client2.state_head.sequence}")
        finally:
            await client2.close()

    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
