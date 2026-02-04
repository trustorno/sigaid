#!/usr/bin/env python3
"""
Clone rejection demo for SigAid SDK.

This demo shows how SigAid prevents "clone" attacks where
multiple instances try to use the same agent identity.

Note: This demo requires a running Authority service to work.
In offline mode, it demonstrates the concept.
"""

import asyncio
from sigaid import AgentClient
from sigaid.crypto.keys import KeyPair
from sigaid.exceptions import LeaseHeldByAnotherInstance


async def demo_clone_rejection_concept():
    """Demonstrate the clone rejection concept."""
    print("=" * 60)
    print("SigAid Clone Rejection Demo")
    print("=" * 60)
    
    # Create a keypair (this represents the agent identity)
    print("\n1. Creating shared agent identity...")
    keypair = KeyPair.generate()
    agent_id = keypair.to_agent_id()
    print(f"   Agent ID: {agent_id}")
    
    print("\n2. Concept: Exclusive Leasing")
    print("   ----------------------------------------")
    print("   SigAid uses exclusive leases to prevent clones:")
    print("   - Only ONE instance can hold a lease at a time")
    print("   - Lease is stored atomically (Redis SETNX)")
    print("   - Second instance trying to acquire = REJECTED")
    print()
    
    # Show what the code would look like
    print("3. Example code that would prevent clones:")
    print("""
    # First instance acquires lease successfully
    client1 = AgentClient.from_keypair(keypair)
    async with client1.lease() as lease:
        print(f"Instance 1 has lease until {lease.expires_at}")
        
        # Second instance (clone) tries to acquire
        client2 = AgentClient.from_keypair(keypair)  # Same keypair!
        
        try:
            async with client2.lease():
                pass  # Would never get here
        except LeaseHeldByAnotherInstance as e:
            print(f"Clone blocked: {e}")
    """)
    
    print("\n4. How it works:")
    print("   ----------------------------------------")
    print("   a) Instance 1 sends lease request to Authority")
    print("   b) Authority atomically sets: lease:{agent_id} = session_1")
    print("   c) Instance 1 receives lease token, proceeds")
    print()
    print("   d) Instance 2 (clone) sends lease request")
    print("   e) Authority checks: lease:{agent_id} already exists!")
    print("   f) Authority rejects: LeaseHeldByAnotherInstance")
    print()
    
    print("\n5. Security guarantees:")
    print("   ----------------------------------------")
    print("   - No race conditions (atomic Redis operations)")
    print("   - Cannot forge lease tokens (PASETO encryption)")
    print("   - Cannot impersonate (Ed25519 signatures)")
    print("   - State chain detects forks (hash linking)")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo_clone_rejection_concept())
