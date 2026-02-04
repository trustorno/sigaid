# SigAid

Cryptographically secure agent identity protocol with exclusive leasing, state continuity, and verification capabilities.

## Features

- **Ed25519-based Identity**: Agents identified by their public key
- **Exclusive Leasing**: Only one instance can operate at a time (prevents clones)
- **State Chain**: Tamper-evident, append-only history of actions
- **Verification**: Third parties can cryptographically verify agent identity

## Installation

```bash
pip install sigaid
```

Or install from source:

```bash
git clone https://github.com/sigaid/sigaid-python.git
cd sigaid-python
pip install -e ".[dev]"
```

## Quick Start

```python
import asyncio
from sigaid import AgentClient, Verifier, ActionType

async def main():
    # Create a new agent
    client = AgentClient.create()

    async with client.lease() as lease:
        # Initialize state chain
        await client.initialize_state_chain()

        # Record actions
        await client.record_action(
            ActionType.TRANSACTION,
            {"hotel": "Hilton", "amount": 180},
            "Booked hotel room"
        )

        # Create proof for verification
        verifier = Verifier()
        challenge = verifier.create_challenge()
        proof = client.create_proof(challenge)

        # Verify
        result = verifier.verify_offline(proof, challenge)
        print(f"Valid: {result.valid}")

    await client.close()

asyncio.run(main())
```

## Core Concepts

### Agent Identity

Each agent has a unique identity derived from an Ed25519 keypair:

```python
from sigaid import KeyPair, AgentID

# Generate new keypair
keypair = KeyPair.generate()

# Get agent ID (derived from public key)
agent_id = keypair.to_agent_id()
print(agent_id)  # aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1

# Save/load encrypted keyfile
keypair.to_encrypted_file(Path("agent.key"), "password")
keypair = KeyPair.from_encrypted_file(Path("agent.key"), "password")
```

### Exclusive Leasing

Only one instance of an agent can operate at a time:

```python
from sigaid import AgentClient, LeaseHeldByAnotherInstance

client1 = AgentClient.from_keypair(keypair)
client2 = AgentClient.from_keypair(keypair)  # Clone!

async with client1.lease():
    # client1 holds the lease

    try:
        async with client2.lease():  # Will fail!
            pass
    except LeaseHeldByAnotherInstance:
        print("Clone rejected!")
```

### State Chain

Every action is recorded in a tamper-evident chain:

```python
async with client.lease():
    # Initialize chain
    await client.initialize_state_chain()

    # Record actions
    entry = await client.record_action(
        ActionType.TRANSACTION,
        {"amount": 100, "to": "service_a"},
        "Payment to service A"
    )

    # Each entry links to previous
    print(f"Sequence: {entry.sequence}")
    print(f"Previous hash: {entry.prev_hash.hex()}")
    print(f"Entry hash: {entry.entry_hash.hex()}")
```

### Verification

Third parties can verify agent identity:

```python
from sigaid import Verifier

# Service creates challenge
verifier = Verifier()
challenge = verifier.create_challenge()

# Agent creates proof
proof = client.create_proof(challenge)

# Service verifies
result = verifier.verify_offline(proof, challenge)

if result.valid:
    print(f"Agent {result.agent_id} verified!")
    print(f"State chain has {proof.state_head.sequence + 1} entries")
```

## Cryptographic Primitives

| Purpose | Algorithm | Why |
|---------|-----------|-----|
| Agent Identity Keys | **Ed25519** | Fast, secure, 128-bit security |
| Key Derivation | **HKDF-SHA256** | RFC 5869 compliant |
| Hashing | **BLAKE3** | Faster than SHA-256, 256-bit security |
| Lease Tokens | **PASETO v4.local** | Modern JWT alternative |

## Project Structure

```
sigaid/
├── crypto/          # Cryptographic primitives
│   ├── keys.py      # Ed25519 keypair management
│   ├── signing.py   # Domain-separated signatures
│   ├── hashing.py   # BLAKE3 hashing
│   └── tokens.py    # PASETO token management
├── identity/        # Identity management
│   ├── agent_id.py  # AgentID generation/validation
│   └── storage.py   # Secure key storage
├── lease/           # Lease management
│   ├── manager.py   # Lease acquisition/renewal
│   └── heartbeat.py # Background renewal
├── state/           # State chain
│   ├── chain.py     # State chain operations
│   └── verification.py  # Fork detection
├── verification/    # Proof verification
│   ├── prover.py    # Proof generation
│   └── verifier.py  # Proof verification
├── client/          # Client interfaces
│   ├── agent.py     # Main AgentClient
│   └── http.py      # HTTP transport
└── models/          # Data models
    ├── state.py     # StateEntry
    ├── lease.py     # Lease
    └── proof.py     # ProofBundle
```

## Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=sigaid --cov-report=term-missing
```

## Running Demos

```bash
# Basic usage
python demos/basic_usage.py

# Clone rejection
python demos/clone_rejection.py

# State chain
python demos/state_chain.py

# Verification
python demos/verification.py
```

## License

MIT License - see LICENSE file for details.

## Links

- **Website**: https://sigaid.com
- **Documentation**: https://docs.sigaid.com
- **GitHub**: https://github.com/sigaid/sigaid-python
