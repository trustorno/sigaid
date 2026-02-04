# SigAid - Secure Agent Identity Protocol

A cryptographically secure agent identity protocol with exclusive leasing, state continuity, and verification capabilities.

## Features

- **Cryptographic Identity**: Ed25519-based agent identities with checksums
- **Exclusive Leasing**: Prevents "clone" attacks - only one instance per agent
- **State Chain**: Hash-linked action log for verifiable history
- **Proof Bundles**: Cryptographic proofs for service verification
- **Framework Integrations**: One-line wrapping for LangChain, CrewAI, AutoGen

## Installation

```bash
pip install sigaid
```

For framework integrations:

```bash
pip install sigaid[langchain]   # LangChain support
pip install sigaid[crewai]      # CrewAI support
pip install sigaid[autogen]     # AutoGen support
pip install sigaid[all-integrations]  # All frameworks
```

## Quick Start

### One-Line Framework Integration

```python
import sigaid

# Wrap your existing agent - that's it!
agent = sigaid.wrap(my_langchain_agent)

# Use exactly as before
result = agent.invoke({"input": "Hello"})

# Agent now has verifiable identity
print(agent._sigaid.agent_id)
```

### Direct SDK Usage

```python
import asyncio
from sigaid import AgentClient

async def main():
    # Create new agent
    client = AgentClient.create()
    print(f"Agent ID: {client.agent_id}")
    
    # Acquire exclusive lease
    async with client.lease() as lease:
        # Record actions
        await client.record_action(
            "transaction",
            {"amount": 100, "recipient": "merchant_123"},
            summary="Processed payment"
        )
        
        # Create proof for verification
        proof = client.create_proof(challenge=b"verifier_nonce")
    
    await client.close()

asyncio.run(main())
```

### Service-Side Verification

```python
from sigaid import Verifier

verifier = Verifier(api_key="...")

result = await verifier.verify(
    proof_bundle,
    require_lease=True,
    min_reputation_score=0.7,
)

if result.valid:
    print(f"Agent {result.agent_id} verified!")
```

## Core Concepts

### Agent Identity

Each agent has a unique cryptographic identity:
- **AgentID**: Derived from Ed25519 public key (`aid_7Xq9YkPz...`)
- **KeyPair**: Used for signing actions and proofs
- Stored in encrypted keyfiles for persistence

### Exclusive Leasing

Prevents "clone" attacks where multiple instances use the same identity:
- Only one instance can hold a lease at a time
- Atomic acquisition via Authority service
- Automatic renewal while in use
- Clone attempts are rejected

### State Chain

Tamper-evident log of agent actions:
- Hash-linked entries (BLAKE3)
- Signed with Ed25519
- Fork detection for clone prevention
- Verifiable by services

### Proof Bundles

Complete proof for verification:
- Agent identity
- Active lease
- State chain head
- Challenge-response signature

## Security

| Feature | Implementation |
|---------|---------------|
| Identity Keys | Ed25519 |
| Hashing | BLAKE3 |
| Lease Tokens | PASETO v4 |
| Domain Separation | Prevents cross-protocol attacks |
| Constant-time comparisons | Timing attack prevention |

## Framework Support

| Framework | Status | Installation |
|-----------|--------|--------------|
| LangChain | Supported | `pip install sigaid[langchain]` |
| CrewAI | Supported | `pip install sigaid[crewai]` |
| AutoGen | Supported | `pip install sigaid[autogen]` |
| OpenAI Agents | Supported | Base package |

## Environment Variables

```bash
SIGAID_API_KEY=sk_live_xxx     # API key for Authority
SIGAID_AUTHORITY_URL=https://api.sigaid.com  # Authority URL
SIGAID_LOG_LEVEL=INFO          # Logging verbosity
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Type checking
mypy sigaid/

# Linting
ruff check sigaid/
```

## License

MIT License
