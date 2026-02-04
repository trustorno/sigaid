#!/usr/bin/env python3
"""State chain demo for SigAid protocol.

This demo shows:
1. Building a state chain with linked entries
2. Verifying chain integrity
3. Detecting tampering/forks
"""

import asyncio

from sigaid import KeyPair, StateEntry, ActionType
from sigaid.state.chain import StateChain
from sigaid.state.verification import ChainVerifier
from sigaid.crypto.hashing import hash_bytes
from sigaid.constants import GENESIS_PREV_HASH


async def main():
    print("=" * 60)
    print("SigAid State Chain Demo")
    print("=" * 60)

    keypair = KeyPair.generate()
    agent_id = str(keypair.to_agent_id())

    print(f"\nAgent ID: {keypair.to_agent_id().short}")

    # Create state chain
    chain = StateChain(agent_id=agent_id, keypair=keypair)

    # 1. Build the chain
    print("\n1. Building state chain...")

    genesis = chain.initialize("Agent genesis")
    print(f"   [0] Genesis: {genesis.action_summary}")
    print(f"       prev_hash: {genesis.prev_hash.hex()[:16]}... (zero - genesis)")
    print(f"       entry_hash: {genesis.entry_hash.hex()[:16]}...")

    entries_data = [
        ("transaction", "User authentication", {"user": "alice", "method": "oauth"}),
        ("transaction", "API call to service A", {"endpoint": "/api/data", "status": 200}),
        ("transaction", "Data processing", {"records": 150, "duration_ms": 230}),
        ("attestation", "Checkpoint verified", {"checkpoint": "alpha"}),
        ("transaction", "API call to service B", {"endpoint": "/api/submit", "status": 201}),
    ]

    for action_type, summary, data in entries_data:
        entry = chain.append(action_type, summary, data)
        print(f"   [{entry.sequence}] {entry.action_type.value}: {entry.action_summary}")
        print(f"       prev_hash: {entry.prev_hash.hex()[:16]}... (links to [{entry.sequence - 1}])")
        print(f"       entry_hash: {entry.entry_hash.hex()[:16]}...")

    # 2. Verify chain integrity
    print("\n2. Verifying chain integrity...")
    try:
        chain.verify()
        print("   Chain integrity: VALID")
        print(f"   Total entries: {len(chain)}")
        print(f"   Current head: sequence {chain.head.sequence}")
    except Exception as e:
        print(f"   Chain integrity: FAILED - {e}")

    # 3. Demonstrate fork detection
    print("\n3. Fork detection demo...")
    verifier = ChainVerifier()

    # Record the current head
    verifier.record_head(agent_id, chain.head)
    print(f"   Recorded known head: seq {chain.head.sequence}")

    # Simulate a forked entry (attacker tries to rewrite history)
    print("\n   Simulating fork attack...")
    forked_entry = StateEntry.create(
        agent_id=agent_id,
        sequence=chain.head.sequence,  # Same sequence
        prev_hash=chain[chain.head.sequence - 1].entry_hash,
        action_type=ActionType.TRANSACTION,
        action_summary="FORKED: Malicious transaction",  # Different content!
        action_data={"malicious": True},
        keypair=keypair,
    )
    print(f"   Forked entry created with same sequence but different content")
    print(f"   Original hash: {chain.head.entry_hash.hex()[:16]}...")
    print(f"   Forked hash:   {forked_entry.entry_hash.hex()[:16]}...")

    # Try to verify the forked entry
    try:
        verifier.verify_head(agent_id, forked_entry)
        print("   Fork detection: FAILED (should not happen)")
    except Exception as e:
        print(f"   Fork detection: CAUGHT - {type(e).__name__}")
        print(f"   Message: {e}")

    # 4. Show that legitimate extensions work
    print("\n4. Legitimate chain extension...")
    chain.append("transaction", "Final legitimate action", {"final": True})
    print(f"   Extended chain to sequence {chain.head.sequence}")

    try:
        verifier.verify_head(agent_id, chain.head)
        print("   Verification: PASSED (legitimate extension accepted)")
    except Exception as e:
        print(f"   Verification: FAILED - {e}")

    # 5. Display full chain
    print("\n5. Full chain visualization:")
    print("   " + "-" * 50)
    for entry in chain:
        sig_prefix = entry.signature.hex()[:8]
        hash_prefix = entry.entry_hash.hex()[:8]
        print(f"   | [{entry.sequence}] {entry.action_type.value}: {entry.action_summary[:30]}")
        print(f"   |     sig: {sig_prefix}...  hash: {hash_prefix}...")
        if entry.sequence < len(chain) - 1:
            print("   |     |")
            print("   |     v (hash links to next)")
    print("   " + "-" * 50)

    print("\n" + "=" * 60)
    print("Key Takeaways:")
    print("- Each entry links to previous via cryptographic hash")
    print("- Chain integrity can be verified by re-computing hashes")
    print("- Fork attacks are detected by comparing entry hashes")
    print("- Only the legitimate owner (with private key) can extend")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
