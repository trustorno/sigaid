#!/usr/bin/env python3
"""Clone rejection demo for SigAid protocol.

This demo shows how SigAid prevents clone attacks by ensuring
only one instance of an agent can operate at a time through
exclusive leasing.
"""

import asyncio

from sigaid import AgentClient, KeyPair, LeaseHeldByAnotherInstance


async def main():
    print("=" * 60)
    print("SigAid Clone Rejection Demo")
    print("=" * 60)

    # Create a keypair (simulating the agent's identity)
    keypair = KeyPair.generate()
    print(f"\nAgent ID: {keypair.to_agent_id().short}")

    # Create two clients with the SAME keypair (simulating a clone)
    print("\nCreating two agent instances with same identity (simulating clone)...")

    client1 = AgentClient.from_keypair(keypair, authority_url="")
    client2 = AgentClient.from_keypair(keypair, authority_url="")  # Clone!

    try:
        # First instance acquires lease
        print("\n1. Instance 1 acquiring lease...")
        lease1 = await client1.acquire_lease()
        print(f"   Instance 1 acquired lease (session: {lease1.session_id[:16]}...)")
        print(f"   Instance 1 has_lease: {client1.has_lease}")

        # Second instance tries to acquire lease - should fail!
        print("\n2. Instance 2 (clone) attempting to acquire lease...")
        try:
            # Note: In local-only mode, this will succeed because there's no
            # central authority to enforce exclusivity. In production with
            # the Authority service + Redis, this would fail.
            lease2 = await client2.acquire_lease()

            # In local mode, we simulate the rejection by checking session IDs
            if lease1.session_id != lease2.session_id:
                print("   [LOCAL MODE] Both instances got local leases")
                print("   In production, the Authority service would reject this!")
                print("\n   Simulating production behavior...")

                # Simulate what would happen with Authority service
                raise LeaseHeldByAnotherInstance(
                    str(keypair.to_agent_id()),
                    lease1.session_id,
                )

        except LeaseHeldByAnotherInstance as e:
            print(f"   REJECTED: {e}")
            print("   Clone attack prevented!")

        # First instance can still operate
        print("\n3. Instance 1 continues operating...")
        await client1.initialize_state_chain()
        entry = await client1.record_action(
            "transaction",
            {"amount": 100},
            action_summary="Legitimate transaction",
            sync_to_authority=False,
        )
        print(f"   Recorded action: {entry.action_summary}")

        # Release lease
        print("\n4. Instance 1 releasing lease...")
        await client1.release_lease()
        print(f"   Instance 1 has_lease: {client1.has_lease}")

        # Now Instance 2 can acquire
        print("\n5. Instance 2 can now acquire lease...")
        lease2 = await client2.acquire_lease()
        print(f"   Instance 2 acquired lease (session: {lease2.session_id[:16]}...)")

    finally:
        await client1.close()
        await client2.close()

    print("\n" + "=" * 60)
    print("Key Takeaways:")
    print("- Only ONE instance can hold an active lease at a time")
    print("- Clone attempts are rejected by the Authority service")
    print("- Legitimate instances can acquire lease after previous releases")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
