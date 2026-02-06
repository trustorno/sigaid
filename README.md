<p align="center">
  <img src="docs/assets/sigaid-logo.svg" alt="SigAid" width="180">
</p>

<h1 align="center">SigAid</h1>

<p align="center">
  <strong>Cryptographic Identity for AI Agents</strong><br>
  Prevent clones. Verify actions. Build trust.
</p>

<p align="center">
  <a href="https://pypi.org/project/sigaid/"><img src="https://img.shields.io/pypi/v/sigaid?color=blue" alt="PyPI"></a>
  <a href="https://pypi.org/project/sigaid/"><img src="https://img.shields.io/pypi/pyversions/sigaid" alt="Python"></a>
  <a href="https://github.com/trustorno/sigaid/actions"><img src="https://img.shields.io/github/actions/workflow/status/trustorno/sigaid/ci.yml?label=tests" alt="Tests"></a>
  <a href="https://codecov.io/gh/trustorno/sigaid"><img src="https://img.shields.io/codecov/c/github/trustorno/sigaid" alt="Coverage"></a>
  <a href="https://github.com/trustorno/sigaid/blob/main/LICENSE"><img src="https://img.shields.io/github/license/trustorno/sigaid" alt="License"></a>
</p>

<p align="center">
  <a href="#installation">Installation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#how-it-works">How It Works</a> •
  <a href="#documentation">Docs</a>
</p>

---

## The Problem

When AI agents act autonomously—making purchases, calling APIs, executing code—how do you answer:

| Question | Risk |
|----------|------|
| **Is this the real agent?** | Impersonation, spoofing |
| **Is there only ONE instance running?** | Clone attacks, double-spending |
| **What has this agent done before?** | No audit trail, no accountability |
| **Can I trust this agent?** | Unknown reputation |

**SigAid solves this** with cryptographic identity, exclusive leasing (anti-clone), and tamper-evident action logs.

---

## Installation

```bash
pip install sigaid
```

With framework integrations:

```bash
pip install sigaid[langchain]      # LangChain
pip install sigaid[crewai]         # CrewAI
pip install sigaid[autogen]        # AutoGen
pip install sigaid[all]            # All frameworks
```

---

## Quick Start

### 30-Second Example

```python
import sigaid

# Wrap any agent with one line
agent = sigaid.wrap(my_langchain_agent, api_key="sk_xxx")

# Use exactly as before - now with verifiable identity
result = agent.invoke({"input": "Book a flight to Tokyo"})

# Agent actions are now signed and traceable
print(agent._sigaid.agent_id)  # aid_7Xq9YkPz...
```

### Direct SDK Usage

```python
from sigaid import AgentClient

async def main():
    # Create agent with cryptographic identity
    client = AgentClient.create(api_key="sk_xxx")

    async with client.lease() as lease:  # Exclusive - no clones allowed
        # Record verifiable actions
        await client.record_action(
            "payment",
            {"amount": 100, "to": "merchant_xyz"}
        )

        # Generate proof for third parties
        proof = client.create_proof(challenge=b"verify_me")

    await client.close()
```

### Verify an Agent (Service Side)

```python
from sigaid import Verifier

verifier = Verifier(api_key="sk_xxx")

result = await verifier.verify(proof_bundle, require_lease=True)
if result.valid:
    print(f"Agent {result.agent_id} verified")
    print(f"Reputation: {result.reputation_score}")
```

---

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                         YOUR AGENT                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Identity  │    │   Lease     │    │   Actions   │         │
│  │   Ed25519   │    │  (1 only)   │    │  Hash Chain │         │
│  │   keypair   │    │             │    │             │         │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘         │
└─────────┼──────────────────┼──────────────────┼─────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SIGAID AUTHORITY                            │
│                                                                  │
│  • Registers agent identities                                    │
│  • Enforces exclusive leasing (anti-clone)                       │
│  • Stores tamper-evident action history                          │
│  • Verifies proofs for third parties                             │
└─────────────────────────────────────────────────────────────────┘
```

### Four Core Primitives

| Primitive | What It Does | Crypto |
|-----------|-------------|--------|
| **Identity** | Unique agent ID derived from public key | Ed25519 |
| **Lease** | Only ONE instance can operate at a time | PASETO v4 |
| **State Chain** | Immutable, signed action history | BLAKE3 + Ed25519 |
| **Proof Bundle** | Verifiable proof for third parties | Challenge-response |

---

## Use Cases

| Scenario | How SigAid Helps |
|----------|------------------|
| **Financial agents** | Prevent double-spending, audit all transactions |
| **Multi-agent systems** | Verify agent-to-agent interactions |
| **Autonomous workflows** | Ensure only one instance runs critical tasks |
| **API access control** | Services verify agent identity before granting access |
| **Compliance & audit** | Tamper-evident logs for regulatory requirements |

---

## Framework Integrations

SigAid wraps popular agent frameworks with zero code changes:

```python
import sigaid

# LangChain
agent = sigaid.wrap(langchain_agent, api_key="sk_xxx")

# CrewAI
crew = sigaid.wrap(my_crew, api_key="sk_xxx")

# AutoGen
agent = sigaid.wrap(autogen_agent, api_key="sk_xxx")

# Self-hosted authority
agent = sigaid.wrap(
    my_agent,
    authority_url="https://my-authority.com",
    api_key="sk_xxx"
)
```

| Framework | Status | Install |
|-----------|--------|---------|
| LangChain | ✅ Supported | `pip install sigaid[langchain]` |
| CrewAI | ✅ Supported | `pip install sigaid[crewai]` |
| AutoGen | ✅ Supported | `pip install sigaid[autogen]` |
| OpenAI Agents | ✅ Supported | Base package |

---

## Authority Service

SigAid requires an Authority service for registration, leasing, and verification:

| Option | Best For | Setup |
|--------|----------|-------|
| **Hosted** | Most users | `https://api.sigaid.com` — [sign up](https://sigaid.com) |
| **Self-hosted** | Enterprise / air-gapped | [Self-Hosting Guide](docs/SELF_HOSTING.md) |
| **Mock** | Unit tests, CI | Built-in `MockAuthority` |

### Testing Without Network

```python
from sigaid.testing import MockAuthority

mock = MockAuthority()  # In-memory, no network
agent = mock.create_agent(public_key)
lease = mock.acquire_lease(agent.agent_id, "session-1", ttl=300)
```

See [Testing Guide](docs/TESTING.md) for details.

---

## Configuration

### Environment Variables

```bash
export SIGAID_API_KEY=sk_xxx                        # Required
export SIGAID_AUTHORITY_URL=https://api.sigaid.com  # Optional (default)
export SIGAID_LOG_LEVEL=INFO                        # Optional
```

### Priority Order

1. Explicit parameter → 2. Environment variable → 3. Default

```python
# All equivalent when SIGAID_API_KEY is set:
sigaid.wrap(agent)
sigaid.wrap(agent, api_key=os.environ["SIGAID_API_KEY"])
```

---

## Core Concepts

### Agent Identity

Each agent has a unique `AgentID` derived from its Ed25519 public key:

```
aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1
└─┬─┘└──────────────┬───────────────┘
prefix    base58(pubkey + checksum)
```

### Exclusive Leasing

**Only one instance per agent can operate at a time.** Clone attempts fail immediately:

```python
# Instance A acquires lease
async with client_a.lease():

    # Instance B tries to acquire → REJECTED
    async with client_b.lease():  # Raises LeaseHeldByAnotherInstance
        pass
```

### State Chain

Tamper-evident log of all agent actions:

```
Entry 0          Entry 1          Entry 2
┌─────────┐      ┌─────────┐      ┌─────────┐
│ action  │──────│ action  │──────│ action  │
│ hash    │ prev │ hash    │ prev │ hash    │
│ sig     │      │ sig     │      │ sig     │
└─────────┘      └─────────┘      └─────────┘
```

### Proof Bundles

Complete proof package for third-party verification:

```python
proof = client.create_proof(challenge=service_nonce)
# Contains: agent_id, lease_token, state_head, challenge_response, signature
```

---

## Security

| Feature | Implementation |
|---------|----------------|
| Identity keys | Ed25519 (256-bit) |
| Hashing | BLAKE3 |
| Lease tokens | PASETO v4 (encrypted) |
| Domain separation | Prevents cross-protocol attacks |
| Constant-time comparison | Timing attack prevention |

---

## Development

```bash
# Clone and install
git clone https://github.com/trustorno/sigaid.git
cd sigaid
pip install -e ".[dev]"

# Run tests (uses MockAuthority, no network)
pytest tests/ -v

# Type checking
mypy sigaid/

# Linting
ruff check sigaid/
```

### Run Reference Authority Locally

```bash
cd examples/authority
docker-compose up -d

# Test against local authority
SIGAID_AUTHORITY_URL=http://localhost:8000 pytest tests/integration/
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [API Reference](docs/API.md) | Authority API specification |
| [Self-Hosting Guide](docs/SELF_HOSTING.md) | Deploy your own Authority |
| [Testing Guide](docs/TESTING.md) | MockAuthority and test patterns |

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`pytest tests/ -v`)
4. Run linting (`ruff check sigaid/`)
5. Submit a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <sub>Built by <a href="https://trustorno.com">Trustorno</a></sub>
</p>
