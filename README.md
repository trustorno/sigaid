# SigAid

<div align="center">

**Cryptographic Identity Protocol for AI Agents**

*One identity. One instance. Complete audit trail.*

[![Tests](https://img.shields.io/badge/tests-160%20passing-success?style=for-the-badge)](./tests)
[![Python](https://img.shields.io/badge/python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white)](./pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](./LICENSE)

[Website](https://sigaid.com) • [Documentation](https://sigaid.com/docs) • [Playground](https://sigaid.com/playground)

</div>

---

## The Problem

How do you trust an AI agent? Three fundamental questions:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#6366f1', 'primaryTextColor': '#fff', 'primaryBorderColor': '#818cf8', 'lineColor': '#94a3b8', 'secondaryColor': '#1e1b4b', 'tertiaryColor': '#312e81', 'background': '#0f0f23', 'mainBkg': '#1e1b4b', 'secondBkg': '#312e81', 'fontFamily': 'ui-monospace, monospace'}}}%%
flowchart LR
    subgraph Q[" "]
        direction TB
        Q1["🤔 <b>Who is this agent?</b>"]
        Q2["🔒 <b>Is it the only instance?</b>"]
        Q3["📋 <b>What has it done?</b>"]
    end

    subgraph A[" "]
        direction TB
        A1["🔑 <b>IDENTITY</b><br/>Ed25519 Cryptographic Keys"]
        A2["⚡ <b>EXCLUSIVITY</b><br/>Atomic Lease System"]
        A3["🔗 <b>AUDITABILITY</b><br/>Hash-Linked State Chain"]
    end

    Q1 -.->|solved by| A1
    Q2 -.->|solved by| A2
    Q3 -.->|solved by| A3

    style Q fill:#0f172a,stroke:#334155,stroke-width:0px
    style A fill:#0f172a,stroke:#334155,stroke-width:0px
    style Q1 fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#e2e8f0
    style Q2 fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#e2e8f0
    style Q3 fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#e2e8f0
    style A1 fill:#059669,stroke:#34d399,stroke-width:2px,color:#fff
    style A2 fill:#059669,stroke:#34d399,stroke-width:2px,color:#fff
    style A3 fill:#059669,stroke:#34d399,stroke-width:2px,color:#fff
```

---

## Architecture

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'primaryColor': '#6366f1', 'primaryTextColor': '#fff', 'lineColor': '#64748b', 'fontFamily': 'ui-monospace, monospace'}}}%%
flowchart TB
    subgraph AGENTS["🤖 AI AGENTS"]
        direction LR
        A1["Agent 1"]
        A2["Agent 2"]
        A3["Agent N"]
    end

    subgraph SDK["📦 SIGAID SDK"]
        direction LR
        S1["🔐 Crypto"]
        S2["📝 Lease"]
        S3["🔗 State"]
        S4["✅ Verify"]
    end

    subgraph AUTHORITY["🏛️ AUTHORITY SERVICE"]
        direction TB
        AU1["Lease<br/>Manager"]
        AU2["State<br/>Chains"]
        AU3["Proof<br/>Verifier"]
    end

    subgraph STORAGE["💾 STORAGE"]
        direction LR
        DB[("PostgreSQL")]
        RD[("Redis")]
    end

    subgraph SERVICES["🌐 THIRD-PARTY SERVICES"]
        direction LR
        V1["Service A"]
        V2["Service B"]
    end

    AGENTS --> SDK
    SDK --> AUTHORITY
    AUTHORITY --> STORAGE
    SERVICES -.->|"verify proofs"| AUTHORITY

    style AGENTS fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#e2e8f0
    style SDK fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#e2e8f0
    style AUTHORITY fill:#4c1d95,stroke:#a78bfa,stroke-width:2px,color:#e2e8f0
    style STORAGE fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#e2e8f0
    style SERVICES fill:#1e3a5f,stroke:#60a5fa,stroke-width:2px,color:#e2e8f0

    style A1 fill:#3730a3,stroke:#818cf8,color:#e2e8f0
    style A2 fill:#3730a3,stroke:#818cf8,color:#e2e8f0
    style A3 fill:#3730a3,stroke:#818cf8,color:#e2e8f0
    style S1 fill:#4338ca,stroke:#a5b4fc,color:#fff
    style S2 fill:#4338ca,stroke:#a5b4fc,color:#fff
    style S3 fill:#4338ca,stroke:#a5b4fc,color:#fff
    style S4 fill:#4338ca,stroke:#a5b4fc,color:#fff
    style AU1 fill:#5b21b6,stroke:#c4b5fd,color:#fff
    style AU2 fill:#5b21b6,stroke:#c4b5fd,color:#fff
    style AU3 fill:#5b21b6,stroke:#c4b5fd,color:#fff
    style DB fill:#047857,stroke:#6ee7b7,color:#fff
    style RD fill:#b91c1c,stroke:#fca5a5,color:#fff
    style V1 fill:#1e40af,stroke:#93c5fd,color:#fff
    style V2 fill:#1e40af,stroke:#93c5fd,color:#fff
```

---

## How It Works

### 1️⃣ Agent Identity

Each agent has a unique cryptographic identity derived from an Ed25519 keypair:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'fontFamily': 'ui-monospace, monospace'}}}%%
flowchart TB
    SEED["🌱 <b>Master Seed</b><br/><code>256 bits from CSPRNG</code>"]

    SEED --> HKDF

    subgraph HKDF["🔄 HKDF-SHA256 Key Derivation"]
        direction LR
        H1[" "]
    end

    HKDF --> IK & SK

    IK["🔑 <b>Identity Key</b><br/><code>Ed25519 Private</code>"]
    SK["🔏 <b>State Key</b><br/><code>Ed25519 Private</code>"]

    IK --> PK["📤 <b>Public Key</b><br/><code>32 bytes</code>"]
    PK --> AID["🆔 <b>AgentID</b><br/><code>aid_7Xq9YkPzN3mW...</code>"]

    style SEED fill:#059669,stroke:#34d399,stroke-width:2px,color:#fff
    style HKDF fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#e2e8f0
    style H1 fill:#1e1b4b,stroke:#1e1b4b
    style IK fill:#4338ca,stroke:#818cf8,stroke-width:2px,color:#fff
    style SK fill:#4338ca,stroke:#818cf8,stroke-width:2px,color:#fff
    style PK fill:#6366f1,stroke:#a5b4fc,stroke-width:2px,color:#fff
    style AID fill:#7c3aed,stroke:#c4b5fd,stroke-width:3px,color:#fff
```

```python
from sigaid import AgentClient

agent = AgentClient.create()
print(agent.agent_id)  # aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1
```

---

### 2️⃣ Exclusive Leasing

Only **ONE** instance can operate at any time. Clones are cryptographically rejected:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'fontFamily': 'ui-monospace, monospace', 'actorTextColor': '#e2e8f0', 'actorBkg': '#3730a3', 'actorBorder': '#818cf8', 'signalColor': '#94a3b8', 'signalTextColor': '#e2e8f0'}}}%%
sequenceDiagram
    autonumber

    participant I1 as 🤖 Instance 1
    participant AUTH as 🏛️ Authority
    participant I2 as 👿 Clone

    Note over I1,I2: Same keypair = Same agent identity

    I1->>+AUTH: LeaseRequest(agent_id, signature)

    Note over AUTH: 🔒 Redis SETNX<br/>(atomic operation)

    AUTH->>-I1: ✅ LeaseGranted(PASETO token)

    rect rgba(34, 197, 94, 0.1)
        Note over I1,AUTH: 🟢 LEASE ACTIVE (10 min TTL)
    end

    I2->>+AUTH: LeaseRequest(same agent_id!)

    Note over AUTH: ❌ Lease exists!

    AUTH->>-I2: 🚫 REJECTED

    Note over I2: ⛔ Clone blocked!
```

```python
client1 = AgentClient.from_keypair(keypair)
client2 = AgentClient.from_keypair(keypair)  # Clone!

async with client1.lease():
    async with client2.lease():  # 💥 LeaseHeldByAnotherInstance
        pass
```

---

### 3️⃣ State Chain

Every action is cryptographically signed and hash-linked — tamper-proof by design:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'fontFamily': 'ui-monospace, monospace'}}}%%
flowchart LR
    subgraph G["🌱 GENESIS"]
        G0["seq: 0"]
        G1["prev: <code>0x0000...</code>"]
        G2["action: <code>create</code>"]
        G3["sig: <code>Ed25519</code>"]
        G4["hash: <code>0xA1B2...</code>"]
    end

    subgraph E1["📝 ENTRY 1"]
        E1_0["seq: 1"]
        E1_1["prev: <code>0xA1B2...</code>"]
        E1_2["action: <code>booking</code>"]
        E1_3["sig: <code>Ed25519</code>"]
        E1_4["hash: <code>0xC3D4...</code>"]
    end

    subgraph E2["📝 ENTRY 2"]
        E2_0["seq: 2"]
        E2_1["prev: <code>0xC3D4...</code>"]
        E2_2["action: <code>payment</code>"]
        E2_3["sig: <code>Ed25519</code>"]
        E2_4["hash: <code>0xE5F6...</code>"]
    end

    G -->|"🔗"| E1 -->|"🔗"| E2

    style G fill:#059669,stroke:#34d399,stroke-width:2px,color:#fff
    style E1 fill:#4338ca,stroke:#818cf8,stroke-width:2px,color:#fff
    style E2 fill:#6366f1,stroke:#a5b4fc,stroke-width:2px,color:#fff
```

> ⚠️ **Tamper one entry → Break the entire chain. Fork detection catches inconsistencies.**

```python
async with agent.lease():
    entry = await agent.record_action("transaction", {"amount": 100})
    print(f"Sequence: {entry.sequence}, Hash: {entry.entry_hash.hex()[:16]}...")
```

---

### 4️⃣ Verification

Services verify agents with cryptographic proof bundles:

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'fontFamily': 'ui-monospace, monospace', 'actorTextColor': '#e2e8f0', 'actorBkg': '#3730a3', 'actorBorder': '#818cf8'}}}%%
sequenceDiagram
    autonumber

    participant S as 🌐 Service
    participant A as 🤖 Agent
    participant AUTH as 🏛️ Authority

    S->>A: 🎲 Challenge(nonce)

    Note over A: 📦 Create ProofBundle<br/>• agent_id<br/>• lease_token<br/>• state_head<br/>• signatures

    A->>S: 📨 ProofBundle

    S->>+AUTH: 🔍 VerifyRequest

    Note over AUTH: ✓ Signatures valid<br/>✓ Lease active<br/>✓ Chain intact<br/>✓ No forks

    AUTH->>-S: ✅ Verified!

    Note over S: 🎉 Trust established
```

```python
from sigaid import Verifier

verifier = Verifier(api_key="...")
result = await verifier.verify(proof_bundle, require_lease=True)

if result.valid:
    print(f"✅ Verified: {result.agent_id}")
```

---

## Cryptographic Stack

```mermaid
%%{init: {'theme': 'dark', 'themeVariables': { 'fontFamily': 'ui-monospace, monospace'}}}%%
flowchart TB
    subgraph APP["🚀 APPLICATION LAYER"]
        A1["AgentClient"]
        A2["Verifier"]
    end

    subgraph CRYPTO["🔐 CRYPTOGRAPHIC PRIMITIVES"]
        direction LR

        subgraph SIG["Signatures"]
            ED["<b>Ed25519</b><br/>128-bit security<br/>64-byte signatures"]
        end

        subgraph HASH["Hashing"]
            BL["<b>BLAKE3</b><br/>256-bit security<br/>Faster than SHA-256"]
        end

        subgraph TOK["Tokens"]
            PA["<b>PASETO v4</b><br/>Symmetric AEAD<br/>No alg confusion"]
        end

        subgraph PQ["Post-Quantum"]
            DI["<b>Dilithium-3</b><br/>Hybrid mode<br/>Future-proof"]
        end
    end

    subgraph SEC["🛡️ SECURITY LAYER"]
        DS["Domain Separation — Prevents cross-protocol attacks"]
    end

    APP --> CRYPTO
    CRYPTO --> SEC

    style APP fill:#1e1b4b,stroke:#6366f1,stroke-width:2px,color:#e2e8f0
    style CRYPTO fill:#0f172a,stroke:#334155,stroke-width:2px,color:#e2e8f0
    style SEC fill:#064e3b,stroke:#34d399,stroke-width:2px,color:#e2e8f0
    style SIG fill:#312e81,stroke:#6366f1,stroke-width:1px,color:#e2e8f0
    style HASH fill:#312e81,stroke:#6366f1,stroke-width:1px,color:#e2e8f0
    style TOK fill:#312e81,stroke:#6366f1,stroke-width:1px,color:#e2e8f0
    style PQ fill:#4c1d95,stroke:#a78bfa,stroke-width:1px,color:#e2e8f0
    style ED fill:#4338ca,stroke:#818cf8,color:#fff
    style BL fill:#4338ca,stroke:#818cf8,color:#fff
    style PA fill:#4338ca,stroke:#818cf8,color:#fff
    style DI fill:#7c3aed,stroke:#c4b5fd,color:#fff
    style DS fill:#059669,stroke:#34d399,color:#fff
```

| Component | Algorithm | Why |
|-----------|-----------|-----|
| **Signatures** | Ed25519 | Fast, compact (64 bytes), battle-tested |
| **Key Derivation** | HKDF-SHA256 | RFC 5869 compliant, deterministic |
| **Hashing** | BLAKE3 | 4x faster than SHA-256, Merkle tree mode |
| **Tokens** | PASETO v4.local | No algorithm confusion vulnerabilities |
| **Post-Quantum** | Dilithium-3 | NIST PQC winner, hybrid with Ed25519 |

---

## Quick Start

```bash
pip install sigaid
```

```python
import asyncio
from sigaid import AgentClient

async def main():
    # Create agent with cryptographic identity
    agent = AgentClient.create()
    print(f"🤖 Agent: {agent.agent_id}")

    # Acquire exclusive lease
    async with agent.lease():
        # Record tamper-proof action
        await agent.record_action("booked_flight", {
            "flight": "UA123",
            "amount": 450.00
        })

        # Create verification proof
        proof = agent.create_proof(challenge=b"nonce")

    await agent.close()

asyncio.run(main())
```

---

## Installation Options

```bash
pip install sigaid           # Core SDK
pip install sigaid[pq]       # + Post-quantum signatures
pip install sigaid[hsm]      # + Hardware security modules
pip install sigaid[server]   # + Self-hosted Authority
pip install sigaid[all]      # Everything
```

---

## Project Structure

```
sigaid/
├── crypto/           # 🔐 Ed25519, BLAKE3, PASETO, Dilithium
├── identity/         # 🆔 AgentID generation & storage
├── lease/            # ⚡ Exclusive lease management
├── state/            # 🔗 Hash-linked state chain
├── verification/     # ✅ Proof creation & verification
└── client/           # 📦 AgentClient SDK interface

authority/            # 🏛️ FastAPI Authority Service
website/              # 🌐 Next.js Marketing & Docs
```

---

## API Reference

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/v1/agents` | Register new agent |
| `POST` | `/v1/leases` | Acquire exclusive lease |
| `PUT` | `/v1/leases/{id}` | Renew lease |
| `DELETE` | `/v1/leases/{id}` | Release lease |
| `POST` | `/v1/state/{id}` | Append to state chain |
| `GET` | `/v1/state/{id}` | Get current state head |
| `POST` | `/v1/verify` | Verify proof bundle |

---

## Security Features

| Feature | Protection |
|:--------|:-----------|
| 🔐 **Domain-separated signatures** | Prevents cross-protocol attacks |
| ⏱️ **Constant-time operations** | Resistant to timing attacks |
| 🔒 **Encrypted keyfiles** | scrypt + ChaCha20-Poly1305 |
| 🔑 **HSM support** | Keys never leave hardware |
| 🛡️ **Post-quantum ready** | Hybrid Ed25519 + Dilithium-3 |
| 🔍 **Fork detection** | Catches state chain tampering |

---

## Use Cases

| Use Case | How SigAid Helps |
|:---------|:-----------------|
| 💰 **Financial Agents** | Complete audit trail for every transaction |
| 🏨 **Booking Systems** | Prevent double-booking with exclusive leases |
| 🤖 **Multi-Agent Systems** | Cryptographically verify which agent did what |
| 🚗 **Autonomous Systems** | Guarantee single point of control |
| 📋 **Compliance** | Tamper-proof logs for regulators |

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v --cov=sigaid

# 160 tests passing ✅
```

---

<div align="center">

## Links

[🌐 Website](https://sigaid.com) • [📚 Documentation](https://sigaid.com/docs) • [🎮 Playground](https://sigaid.com/playground) • [💻 GitHub](https://github.com/trustorno/sigaid)

---

**MIT License** — Built with 🔐 by the SigAid team

</div>
