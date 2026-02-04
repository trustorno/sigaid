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

# Using hosted service (https://api.sigaid.com)
agent = sigaid.wrap(my_langchain_agent, api_key="sk_xxx")

# Using self-hosted authority
agent = sigaid.wrap(
    my_langchain_agent,
    authority_url="https://my-authority.com",
    api_key="sk_xxx"
)

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
    # Create new agent (hosted service)
    client = AgentClient.create(api_key="sk_xxx")

    # Or with self-hosted authority
    client = AgentClient.create(
        authority_url="https://my-authority.com",
        api_key="sk_xxx"
    )

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

verifier = Verifier(
    authority_url="https://api.sigaid.com",  # or your self-hosted URL
    api_key="sk_xxx"
)

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

## Configuration

### Environment Variables

```bash
SIGAID_AUTHORITY_URL=https://api.sigaid.com  # Authority service URL
SIGAID_API_KEY=sk_xxx                        # API key for Authority
SIGAID_LOG_LEVEL=INFO                        # Logging verbosity
```

### Configuration Priority

Both `authority_url` and `api_key` follow the same priority order:

1. **Explicit parameter** - passed directly to function
2. **Environment variable** - `SIGAID_AUTHORITY_URL` / `SIGAID_API_KEY`
3. **Default** - `https://api.sigaid.com` (authority_url only)

```python
# All three are equivalent when env vars are set:
agent = sigaid.wrap(my_agent)
agent = sigaid.wrap(my_agent, api_key=os.environ["SIGAID_API_KEY"])
agent = sigaid.wrap(
    my_agent,
    authority_url=os.environ["SIGAID_AUTHORITY_URL"],
    api_key=os.environ["SIGAID_API_KEY"]
)
```

### Self-Hosted vs Hosted

| Deployment | Authority URL | API Key |
|------------|---------------|---------|
| **Hosted** (default) | `https://api.sigaid.com` | Get from sigaid.com |
| **Self-hosted** | Your server URL | Generate with your Authority |

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
