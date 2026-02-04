# SigAid

**Cryptographic Identity Protocol for AI Agents**

One identity. One instance. Complete audit trail.

[![Tests](https://img.shields.io/badge/tests-160%20passing-success)](./tests)
[![Python](https://img.shields.io/badge/python-3.11+-blue)](./pyproject.toml)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

---

## The Problem

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'nodeBorder': '#333', 'mainBkg': 'transparent', 'clusterBkg': 'transparent'}}}%%
graph LR
    Q1[Who is this agent?] --> A1[Identity]
    Q2[Is it the only instance?] --> A2[Exclusivity]
    Q3[What has it done?] --> A3[Auditability]

    A1 --> S1[Ed25519 Keys]
    A2 --> S2[Lease System]
    A3 --> S3[State Chain]

    style Q1 fill:none,stroke:#666
    style Q2 fill:none,stroke:#666
    style Q3 fill:none,stroke:#666
    style A1 fill:none,stroke:#666
    style A2 fill:none,stroke:#666
    style A3 fill:none,stroke:#666
    style S1 fill:none,stroke:#666
    style S2 fill:none,stroke:#666
    style S3 fill:none,stroke:#666
```

---

## Architecture

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'mainBkg': 'transparent', 'clusterBkg': 'transparent'}}}%%
graph TB
    subgraph Agents
        A1[Agent 1]
        A2[Agent 2]
        A3[Agent N]
    end

    subgraph SDK[SigAid SDK]
        C[Crypto]
        L[Lease]
        S[State]
        V[Verify]
    end

    subgraph Authority[Authority Service]
        LM[Lease Manager]
        SC[State Chains]
        PV[Proof Verifier]
    end

    subgraph Storage
        PG[(PostgreSQL)]
        RD[(Redis)]
    end

    Agents --> SDK
    SDK --> Authority
    Authority --> Storage

    Services[Third-Party Services] -.-> Authority

    style A1 fill:none,stroke:#666
    style A2 fill:none,stroke:#666
    style A3 fill:none,stroke:#666
    style C fill:none,stroke:#666
    style L fill:none,stroke:#666
    style S fill:none,stroke:#666
    style V fill:none,stroke:#666
    style LM fill:none,stroke:#666
    style SC fill:none,stroke:#666
    style PV fill:none,stroke:#666
    style PG fill:none,stroke:#666
    style RD fill:none,stroke:#666
    style Services fill:none,stroke:#666
```

---

## Key Hierarchy

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'mainBkg': 'transparent'}}}%%
graph TB
    Seed[Master Seed<br/>256 bits] --> HKDF[HKDF-SHA256]

    HKDF --> IK[Identity Key<br/>Ed25519]
    HKDF --> SK[State Key<br/>Ed25519]

    IK --> PK[Public Key<br/>32 bytes]
    PK --> AID[AgentID<br/>aid_7Xq9YkPz...]

    style Seed fill:none,stroke:#666
    style HKDF fill:none,stroke:#666
    style IK fill:none,stroke:#666
    style SK fill:none,stroke:#666
    style PK fill:none,stroke:#666
    style AID fill:none,stroke:#666
```

```python
from sigaid import AgentClient

agent = AgentClient.create()
print(agent.agent_id)  # aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1
```

---

## Exclusive Leasing

Only one instance can operate at a time. Clones are rejected.

```mermaid
sequenceDiagram
    participant I1 as Instance 1
    participant Auth as Authority
    participant I2 as Instance 2

    I1->>Auth: LeaseRequest(agent_id, sig)
    Note over Auth: SETNX atomic check
    Auth->>I1: LeaseGranted(token)

    Note over I1,Auth: Lease Active

    I2->>Auth: LeaseRequest(same agent_id)
    Auth->>I2: Rejected - lease held
```

```python
async with client1.lease():
    async with client2.lease():  # Raises LeaseHeldByAnotherInstance
        pass
```

---

## State Chain

Every action is signed and hash-linked.

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'mainBkg': 'transparent'}}}%%
graph LR
    G[Genesis<br/>seq: 0<br/>hash: 0xA1] --> E1[Entry 1<br/>seq: 1<br/>prev: 0xA1<br/>hash: 0xB2]
    E1 --> E2[Entry 2<br/>seq: 2<br/>prev: 0xB2<br/>hash: 0xC3]
    E2 --> E3[Entry 3<br/>seq: 3<br/>prev: 0xC3<br/>hash: 0xD4]

    style G fill:none,stroke:#666
    style E1 fill:none,stroke:#666
    style E2 fill:none,stroke:#666
    style E3 fill:none,stroke:#666
```

Tamper with any entry and the chain breaks. Fork detection catches inconsistencies.

```python
async with agent.lease():
    entry = await agent.record_action("payment", {"amount": 100})
```

---

## Verification

```mermaid
sequenceDiagram
    participant S as Service
    participant A as Agent
    participant Auth as Authority

    S->>A: Challenge(nonce)
    A->>S: ProofBundle
    S->>Auth: Verify(proof)
    Note over Auth: Check signatures<br/>Check lease<br/>Check chain
    Auth->>S: Valid
```

```python
result = await verifier.verify(proof_bundle)
if result.valid:
    print(f"Verified: {result.agent_id}")
```

---

## Cryptographic Stack

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'mainBkg': 'transparent', 'clusterBkg': 'transparent'}}}%%
graph TB
    subgraph Signatures
        ED[Ed25519]
    end

    subgraph Hashing
        BL[BLAKE3]
    end

    subgraph Tokens
        PA[PASETO v4]
    end

    subgraph Post-Quantum
        DI[Dilithium-3]
    end

    ED & BL & PA & DI --> DS[Domain Separation]

    style ED fill:none,stroke:#666
    style BL fill:none,stroke:#666
    style PA fill:none,stroke:#666
    style DI fill:none,stroke:#666
    style DS fill:none,stroke:#666
```

| Component | Algorithm | Purpose |
|-----------|-----------|---------|
| Signatures | Ed25519 | Fast, 64-byte signatures |
| Hashing | BLAKE3 | Faster than SHA-256 |
| Tokens | PASETO v4 | No algorithm confusion |
| Post-Quantum | Dilithium-3 | Future-proof hybrid |

---

## Quick Start

```bash
pip install sigaid
```

```python
import asyncio
from sigaid import AgentClient

async def main():
    agent = AgentClient.create()

    async with agent.lease():
        await agent.record_action("booked_flight", {
            "flight": "UA123",
            "amount": 450.00
        })
        proof = agent.create_proof(challenge=b"nonce")

asyncio.run(main())
```

---

## Installation

```bash
pip install sigaid           # Core SDK
pip install sigaid[pq]       # Post-quantum signatures
pip install sigaid[hsm]      # Hardware security modules
pip install sigaid[server]   # Self-hosted Authority
pip install sigaid[all]      # Everything
```

---

## Project Structure

```
sigaid/
├── crypto/          # Ed25519, BLAKE3, PASETO, Dilithium
├── identity/        # AgentID generation & storage
├── lease/           # Exclusive lease management
├── state/           # Hash-linked state chain
├── verification/    # Proof creation & verification
└── client/          # AgentClient interface

authority/           # FastAPI service
website/             # Next.js docs
```

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /v1/agents | Register agent |
| POST | /v1/leases | Acquire lease |
| PUT | /v1/leases/{id} | Renew lease |
| DELETE | /v1/leases/{id} | Release lease |
| POST | /v1/state/{id} | Append state |
| GET | /v1/state/{id} | Get state head |
| POST | /v1/verify | Verify proof |

---

## Links

- Website: https://sigaid.com
- Documentation: https://sigaid.com/docs
- GitHub: https://github.com/trustorno/sigaid

MIT License
