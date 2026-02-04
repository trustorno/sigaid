#!/usr/bin/env python3
"""Verification demo for SigAid protocol.

This demo shows how a third-party service can verify an agent's
identity and history using cryptographic proofs.
"""

import asyncio
import secrets

from sigaid import AgentClient, Verifier, ActionType, KeyPair


async def main():
    print("=" * 60)
    print("SigAid Verification Demo")
    print("=" * 60)

    # === AGENT SIDE ===
    print("\n[AGENT] Creating agent and building history...")

    client = AgentClient.create(authority_url="")

    try:
        async with client.lease():
            await client.initialize_state_chain()

            # Build some history
            await client.record_action(
                ActionType.TRANSACTION,
                {"type": "registration", "service": "hotel_booking"},
                "Registered with hotel booking service",
                sync_to_authority=False,
            )
            await client.record_action(
                ActionType.TRANSACTION,
                {"hotel": "Marriott", "amount": 350},
                "Booked Marriott hotel",
                sync_to_authority=False,
            )
            await client.record_action(
                ActionType.ATTESTATION,
                {"rating": 5, "from": "hotel_service"},
                "Received 5-star rating from hotel service",
                sync_to_authority=False,
            )

            print(f"   Agent ID: {client.agent_id.short}")
            print(f"   State chain length: {client.state_head.sequence + 1} entries")

            # === SERVICE SIDE ===
            print("\n[SERVICE] Hotel booking service wants to verify agent...")

            verifier = Verifier()

            # Step 1: Service creates a challenge
            print("\n   Step 1: Creating challenge...")
            challenge = verifier.create_challenge(32)
            print(f"   Challenge: {challenge.hex()}")

            # Step 2: Agent creates proof
            print("\n   Step 2: Agent creating proof bundle...")
            proof = client.create_proof(challenge)
            print(f"   Proof created:")
            print(f"     - Agent ID: {proof.agent_id}")
            print(f"     - Has lease token: {bool(proof.lease_token)}")
            print(f"     - State head seq: {proof.state_head.sequence}")
            print(f"     - Challenge response: {proof.challenge_response.hex()[:32]}...")

            # Step 3: Service verifies proof
            print("\n   Step 3: Service verifying proof...")
            result = verifier.verify_offline(proof, challenge)

            print(f"\n   Verification Result:")
            print(f"     - Valid: {result.valid}")
            print(f"     - Signature valid: {result.signature_valid}")
            print(f"     - Challenge valid: {result.challenge_valid}")
            print(f"     - State chain valid: {result.chain_valid}")

            if result.valid:
                print("\n   Agent VERIFIED! Service can trust this agent.")
                print(f"   Agent has {proof.state_head.sequence + 1} recorded actions")
            else:
                print(f"\n   Verification FAILED: {result.error_message}")

            # === TAMPERING DETECTION ===
            print("\n[DEMO] Demonstrating tampering detection...")

            # Create a fake proof with wrong signature
            print("\n   Creating tampered proof (wrong key)...")
            fake_keypair = KeyPair.generate()
            fake_proof = proof.__class__.create(
                agent_id=str(client.agent_id),  # Claim to be the real agent
                lease_token=proof.lease_token,
                state_head=proof.state_head,
                challenge=challenge,
                keypair=fake_keypair,  # But sign with different key!
            )

            fake_result = verifier.verify_offline(fake_proof, challenge)
            print(f"   Tampered proof valid: {fake_result.valid}")
            print(f"   Error: {fake_result.error_message}")

            # Wrong challenge
            print("\n   Verifying with wrong challenge...")
            wrong_challenge = secrets.token_bytes(32)
            wrong_result = verifier.verify_offline(proof, wrong_challenge)
            print(f"   Wrong challenge valid: {wrong_result.valid}")
            print(f"   Error: {wrong_result.error_message}")

    finally:
        await client.close()

    print("\n" + "=" * 60)
    print("Key Takeaways:")
    print("- Services can verify agent identity cryptographically")
    print("- Challenge-response prevents replay attacks")
    print("- Tampering with proofs is detectable")
    print("- State chain provides verifiable history")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
