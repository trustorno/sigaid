#!/usr/bin/env python3
"""
Basic usage demo for SigAid SDK.

This demo shows how to:
1. Create an agent identity
2. Record actions to state chain
3. Create proof bundles for verification
"""

import asyncio
from sigaid import AgentClient
from sigaid.models.state import ActionType


async def main():
    print("=" * 60)
    print("SigAid Basic Usage Demo")
    print("=" * 60)
    
    # Create a new agent
    print("\n1. Creating new agent...")
    client = AgentClient.create()
    print(f"   Agent ID: {client.agent_id}")
    
    # Note: In this demo, we don't connect to a real Authority service
    # In production, the client would communicate with the Authority
    
    print("\n2. Agent identity details:")
    print(f"   Public key: {client.keypair.public_key_bytes().hex()[:32]}...")
    
    # Demonstrate state chain (local only in this demo)
    print("\n3. State chain operations (local mode):")
    
    # Manually append to chain without lease (for demo)
    entry1 = client._state_chain.append(
        ActionType.TRANSACTION,
        "Processed payment of $100",
        {"amount": 100, "currency": "USD"},
    )
    print(f"   Entry 1: seq={entry1.sequence}, hash={entry1.entry_hash.hex()[:16]}...")
    
    entry2 = client._state_chain.append(
        ActionType.TOOL_CALL,
        "Called search API",
        {"query": "hotels in Paris"},
    )
    print(f"   Entry 2: seq={entry2.sequence}, hash={entry2.entry_hash.hex()[:16]}...")
    
    entry3 = client._state_chain.append(
        ActionType.DECISION,
        "Selected hotel based on price",
        {"hotel_id": "H123", "price": 180},
    )
    print(f"   Entry 3: seq={entry3.sequence}, hash={entry3.entry_hash.hex()[:16]}...")
    
    # Verify chain integrity
    print("\n4. Verifying state chain integrity...")
    is_valid = client._state_chain.verify()
    print(f"   Chain valid: {is_valid}")
    print(f"   Chain length: {client._state_chain.length}")
    print(f"   Chain head hash: {client._state_chain.head.entry_hash.hex()[:32]}...")
    
    # Show signature verification
    print("\n5. Verifying entry signatures...")
    for entry in client._state_chain:
        sig_valid = entry.verify_signature(client.keypair.public_key_bytes())
        print(f"   Entry {entry.sequence}: signature valid = {sig_valid}")
    
    # Save keypair
    print("\n6. Saving agent identity to encrypted file...")
    # In a real app, use a secure password
    # client.save_to_file(Path("agent.key"), "password123")
    print("   (Skipped in demo - use client.save_to_file() in real code)")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)
    
    # Cleanup
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
