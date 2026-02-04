# SigAid

**Cryptographic Identity Protocol for AI Agents**

One identity. One instance. Complete audit trail.

[![Tests](https://img.shields.io/badge/tests-160%20passing-success)](./tests)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](./pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

---

## What is SigAid?

SigAid is a cryptographic protocol that gives AI agents **verifiable identity**, **exclusive operation guarantees**, and **tamper-proof audit trails**. It solves the fundamental trust problem: *How do you know which agent you're dealing with, that it's the only one operating, and what it has done?*

```mermaid
flowchart LR
    subgraph Questions
        Q1["Who is this agent?"]
        Q2["Is it the only one?"]
        Q3["What has it done?"]
    end

    subgraph Solutions
        S1["IDENTITY<br/>Ed25519 Keys"]
        S2["EXCLUSIVITY<br/>Lease System"]
        S3["AUDITABILITY<br/>State Chain"]
    end

    Q1 --> S1
    Q2 --> S2
    Q3 --> S3

    style S1 fill:#4f46e5,color:#fff
    style S2 fill:#4f46e5,color:#fff
    style S3 fill:#4f46e5,color:#fff
```

---

## Architecture Overview

```mermaid
flowchart TB
    subgraph Agents["AI Agents"]
        A1["Agent 1<br/>(Python)"]
        A2["Agent 2<br/>(Python)"]
        A3["Agent N<br/>(Python)"]
    end

    subgraph SDK["SigAid SDK"]
        direction LR
        SDK1["Crypto"]
        SDK2["Lease"]
        SDK3["State"]
    end

    subgraph Authority["Authority Service (FastAPI)"]
        LM["Lease Manager"]
        SC["State Chains"]
        VM["Verification"]
    end

    subgraph Storage["Storage Layer"]
        PG[("PostgreSQL<br/>State")]
        RD[("Redis<br/>Leases")]
    end

    subgraph Verifiers["Third-Party Services"]
        V1["Service A<br/>(Verifier)"]
        V2["Service B<br/>(Verifier)"]
    end

    A1 & A2 & A3 --> SDK
    SDK --> Authority
    Authority --> PG & RD
    V1 & V2 -.->|"verify proofs"| Authority

    style Authority fill:#1e1b4b,color:#fff
    style SDK fill:#312e81,color:#fff
```

---

## How It Works

### 1. Agent Identity

Each agent has a unique cryptographic identity derived from an Ed25519 keypair:

```mermaid
flowchart TB
    SEED["Master Seed<br/>(256 bits from CSPRNG)"]

    SEED --> HKDF["HKDF-SHA256"]

    HKDF --> IK["Identity Key<br/>(Ed25519)"]
    HKDF --> SK["State Key<br/>(Ed25519)"]

    IK --> PK["Public Key<br/>(32 bytes)"]
    PK --> AID["AgentID<br/>aid_7Xq9YkPzN3mWvR5tH8jL2c..."]

    style SEED fill:#059669,color:#fff
    style AID fill:#4f46e5,color:#fff
```

```python
from sigaid import AgentClient

# Create agent with new identity
agent = AgentClient.create()
print(f"Agent ID: {agent.agent_id}")
# Output: aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1
```

### 2. Exclusive Leasing

Only ONE instance of an agent can operate at any time. Clones are rejected:

```mermaid
sequenceDiagram
    participant I1 as Instance 1
    participant Auth as Authority
    participant I2 as Instance 2 (Clone)

    I1->>Auth: LeaseRequest (agent_id, signature)
    Note over Auth: Redis SETNX<br/>(atomic)
    Auth->>I1: LeaseGranted (PASETO token)

    rect rgb(34, 197, 94, 0.1)
        Note over I1,Auth: LEASE ACTIVE
    end

    I2->>Auth: LeaseRequest (same agent_id!)
    Auth->>I2: REJECTED<br/>"Lease held by another instance"

    Note over I2: Clone blocked!
```

```python
# Clone rejection in action
client1 = AgentClient.from_keypair(keypair)
client2 = AgentClient.from_keypair(keypair)  # Same keys = clone!

async with client1.lease():
    try:
        async with client2.lease():  # REJECTED!
            pass
    except LeaseHeldByAnotherInstance:
        print("Clone blocked!")
```

### 3. State Chain

Every action is cryptographically signed and hash-linked into a tamper-proof chain:

```mermaid
flowchart TB
    subgraph G["Genesis Entry (Seq: 0)"]
        G1["prev_hash: 0x00..."]
        G2["action: genesis"]
        G3["signature: Ed25519"]
        G4["entry_hash: 0xA1..."]
    end

    subgraph E1["Entry 1 (Seq: 1)"]
        E1_1["prev_hash: 0xA1..."]
        E1_2["action: booking"]
        E1_3["data_hash: 0xB2..."]
        E1_4["signature: Ed25519"]
        E1_5["entry_hash: 0xC3..."]
    end

    subgraph E2["Entry 2 (Seq: 2)"]
        E2_1["prev_hash: 0xC3..."]
        E2_2["action: payment"]
        E2_3["data_hash: 0xD4..."]
        E2_4["signature: Ed25519"]
        E2_5["entry_hash: 0xE5..."]
    end

    G4 -->|"hash link"| E1_1
    E1_5 -->|"hash link"| E2_1

    style G fill:#1e1b4b,color:#fff
    style E1 fill:#312e81,color:#fff
    style E2 fill:#4338ca,color:#fff
```

> **Any tampering breaks the chain! Fork detection catches inconsistencies.**

```python
async with agent.lease():
    # Record action - automatically signed and linked
    entry = await agent.record_action(
        action_type="transaction",
        data={"amount": 100, "recipient": "hotel_service"}
    )
    print(f"Sequence: {entry.sequence}")
    print(f"Hash: {entry.entry_hash.hex()[:16]}...")
```

### 4. Verification

Services verify agent identity with cryptographic proof bundles:

```mermaid
sequenceDiagram
    participant S as Service
    participant A as Agent
    participant Auth as Authority

    S->>A: Challenge (nonce)

    Note over A: Create Proof Bundle:<br/>- agent_id<br/>- lease_token<br/>- state_head<br/>- challenge_sig

    A->>S: ProofBundle

    S->>Auth: Verify Request

    Note over Auth: Checks:<br/>✓ Signatures valid<br/>✓ Lease active<br/>✓ State valid<br/>✓ No forks detected

    Auth->>S: Verified<br/>{valid: true, agent_id, reputation}
```

```python
from sigaid import Verifier

verifier = Verifier(api_key="your_key")

result = await verifier.verify(
    proof_bundle,
    require_lease=True,
    min_reputation_score=0.8
)

if result.valid:
    print(f"Verified: {result.agent_id}")
```

---

## Cryptographic Primitives

```mermaid
flowchart TB
    APP["Application Layer"]

    APP --> ED["Ed25519<br/>Signatures<br/><small>128-bit security</small>"]
    APP --> BL["BLAKE3<br/>Hashing<br/><small>256-bit security</small>"]
    APP --> PA["PASETO v4<br/>Tokens<br/><small>Symmetric AEAD</small>"]
    APP --> DI["Dilithium-3<br/>Post-Quantum<br/><small>Hybrid mode</small>"]

    ED & BL & PA & DI --> DS["Domain Separation<br/><small>Prevents cross-protocol attacks</small>"]

    style APP fill:#1e1b4b,color:#fff
    style ED fill:#4f46e5,color:#fff
    style BL fill:#4f46e5,color:#fff
    style PA fill:#4f46e5,color:#fff
    style DI fill:#7c3aed,color:#fff
    style DS fill:#059669,color:#fff
```

| Component | Algorithm | Purpose |
|-----------|-----------|---------|
| Identity Keys | **Ed25519** | Agent signatures (fast, 64-byte sigs) |
| Key Derivation | **HKDF-SHA256** | Derive keys from master seed |
| State Hashing | **BLAKE3** | Chain integrity (faster than SHA-256) |
| Lease Tokens | **PASETO v4.local** | Secure tokens (no algorithm confusion) |
| Post-Quantum | **Dilithium-3** | Future-proof hybrid signatures |

---

## Installation

```bash
pip install sigaid
```

Optional features:

```bash
pip install sigaid[pq]      # Post-quantum signatures
pip install sigaid[hsm]     # Hardware security modules
pip install sigaid[server]  # Self-hosted Authority
pip install sigaid[all]     # Everything
```

---

## Quick Start

```python
import asyncio
from sigaid import AgentClient

async def main():
    # Create agent with cryptographic identity
    agent = AgentClient.create()
    print(f"Agent: {agent.agent_id}")

    # Acquire exclusive lease
    async with agent.lease():
        # Record tamper-proof action
        await agent.record_action("booked_flight", {
            "flight": "UA123",
            "amount": 450.00
        })

        # Create verification proof
        proof = agent.create_proof(challenge=b"service_nonce")

    await agent.close()

asyncio.run(main())
```

---

## Project Structure

```mermaid
flowchart LR
    subgraph SDK["sigaid/ (Python SDK)"]
        direction TB
        CR["crypto/<br/><small>Keys, Signing, Hashing, Tokens</small>"]
        ID["identity/<br/><small>AgentID, Storage</small>"]
        LE["lease/<br/><small>Manager, Heartbeat</small>"]
        ST["state/<br/><small>Chain, Merkle</small>"]
        VE["verification/<br/><small>Prover, Verifier</small>"]
        CL["client/<br/><small>AgentClient, HTTP</small>"]
    end

    subgraph AUTH["authority/ (FastAPI)"]
        direction TB
        RO["routers/"]
        SE["services/"]
        AL["alembic/"]
    end

    subgraph WEB["website/ (Next.js)"]
        direction TB
        AP["app/"]
        CO["components/"]
    end

    style SDK fill:#1e1b4b,color:#fff
    style AUTH fill:#312e81,color:#fff
    style WEB fill:#4338ca,color:#fff
```

```
sigaid/
├── crypto/                  # Cryptographic primitives
│   ├── keys.py              # Ed25519 keypair management
│   ├── signing.py           # Domain-separated signatures
│   ├── hashing.py           # BLAKE3 hashing
│   ├── tokens.py            # PASETO lease tokens
│   ├── hybrid.py            # Post-quantum (Ed25519 + Dilithium)
│   └── hsm/                 # Hardware security module support
│
├── identity/                # Identity management
│   ├── agent_id.py          # AgentID format & validation
│   └── storage.py           # Encrypted keyfile storage
│
├── lease/                   # Exclusive leasing
│   ├── manager.py           # Lease acquisition & renewal
│   └── heartbeat.py         # Background auto-renewal
│
├── state/                   # State chain
│   ├── chain.py             # Append, verify, fork detection
│   └── merkle.py            # Merkle proofs for inclusion
│
├── verification/            # Proof system
│   ├── prover.py            # Create proof bundles
│   └── verifier.py          # Verify proofs (online/offline)
│
└── client/                  # SDK interface
    ├── agent.py             # Main AgentClient class
    └── http.py              # HTTP transport to Authority

authority/                   # Authority Service (FastAPI)
├── routers/                 # API endpoints
├── services/                # Business logic
└── main.py                  # Application entry

website/                     # Marketing & Docs (Next.js)
├── app/                     # Pages
└── components/              # UI components
```

---

## Running the Authority Service

### Docker (Recommended)

```bash
docker-compose up -d
curl http://localhost:8001/health
```

### Local Development

```bash
pip install -e ".[authority]"

export POSTGRES_HOST=localhost
export POSTGRES_DB=sigaid
export REDIS_URL=redis://localhost:6379

cd authority && alembic upgrade head
uvicorn authority.main:app --port 8001
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/agents` | Register agent |
| `GET` | `/v1/agents/{id}` | Get agent info |
| `POST` | `/v1/leases` | Acquire lease |
| `PUT` | `/v1/leases/{id}` | Renew lease |
| `DELETE` | `/v1/leases/{id}` | Release lease |
| `POST` | `/v1/state/{id}` | Append state |
| `GET` | `/v1/state/{id}` | Get state head |
| `POST` | `/v1/verify` | Verify proof |

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=sigaid
```

---

## Security Features

| Feature | Description |
|---------|-------------|
| **Domain-separated signatures** | Prevents cross-protocol attacks |
| **Constant-time operations** | Resistant to timing attacks |
| **Encrypted keyfiles** | scrypt + ChaCha20-Poly1305 |
| **HSM support** | Keys never leave hardware |
| **Post-quantum ready** | Hybrid Ed25519 + Dilithium-3 |
| **Fork detection** | Catches state chain tampering |

---

## Use Cases

| Use Case | How SigAid Helps |
|----------|------------------|
| **Financial Agents** | Audit trail for every transaction |
| **Booking Systems** | Prevent double-booking with exclusive leases |
| **Multi-Agent Orchestration** | Verify which agent did what |
| **Autonomous Systems** | Guarantee single point of control |
| **Compliance** | Tamper-proof logs for regulators |

---

## License

MIT License - see [LICENSE](./LICENSE) for details.

---

## Links

- **Website**: https://sigaid.com
- **Documentation**: https://sigaid.com/docs
- **GitHub**: https://github.com/trustorno/sigaid
