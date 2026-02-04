import { Badge } from "@/components/ui/badge";

export default function StateChainPage() {
  return (
    <article className="prose prose-invert max-w-none">
      <Badge variant="outline" className="mb-4">
        Core Concepts
      </Badge>

      <h1 className="text-4xl font-bold mb-4">State Chain</h1>

      <p className="text-lg text-muted-foreground mb-8">
        The state chain is a cryptographically linked sequence of all agent
        actions. Each entry is signed and hash-chained, creating a tamper-proof
        audit trail.
      </p>

      <h2 className="text-2xl font-semibold mt-8 mb-4">How It Works</h2>

      <p className="text-muted-foreground mb-4">
        Each state entry contains:
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`State Entry N:
┌─────────────────────────────────────────────┐
│ prev_hash: BLAKE3(Entry N-1)                │
│ sequence: N                                 │
│ timestamp: RFC 3339                         │
│ action_type: "transaction" | "upgrade" | ..│
│ action_hash: BLAKE3(action_data)            │
│ agent_signature: Ed25519(above fields)      │
│ entry_hash: BLAKE3(all above)               │
└─────────────────────────────────────────────┘
          │
          ▼
State Entry N+1:
┌─────────────────────────────────────────────┐
│ prev_hash: entry_hash from Entry N          │
│ ...                                         │
└─────────────────────────────────────────────┘`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Recording Actions</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`async with agent.lease():
    # Record action - automatically signed and hash-chained
    entry = await agent.record_action(
        action_type="transaction",
        data={
            "type": "hotel_booking",
            "hotel": "Grand Hyatt Tokyo",
            "amount": 45000,
            "currency": "JPY",
            "confirmation": "ABC123"
        }
    )

    print(f"Sequence: {entry.sequence}")        # 1
    print(f"Entry hash: {entry.entry_hash.hex()[:16]}...")
    print(f"Prev hash: {entry.prev_hash.hex()[:16]}...")

    # Record another action
    entry2 = await agent.record_action(
        action_type="notification",
        data={"message": "Booking confirmed", "channel": "email"}
    )

    # Entry2.prev_hash == Entry1.entry_hash (hash-linked)`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Action Types</h2>

      <div className="overflow-x-auto mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4">Type</th>
              <th className="text-left py-2">Use Case</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">transaction</td>
              <td className="py-2">Financial operations, bookings, purchases</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">attestation</td>
              <td className="py-2">Certifying facts, signing documents</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">upgrade</td>
              <td className="py-2">Agent software updates</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">reset</td>
              <td className="py-2">State reset (with reason)</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">custom</td>
              <td className="py-2">Any application-specific action</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Retrieving History</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`# Get recent state history
history = await agent.get_state_history(limit=10)

for entry in history:
    print(f"[{entry.sequence}] {entry.action_type}")
    print(f"  Time: {entry.timestamp}")
    print(f"  Hash: {entry.entry_hash.hex()[:8]}...")

# Get specific entry by sequence
entry = await agent.get_state_entry(sequence=5)

# Get current head
head = agent.state_head
print(f"Current sequence: {head.sequence}")`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Fork Detection</h2>

      <p className="text-muted-foreground mb-4">
        If someone tries to tamper with the state chain or create a fork, it
        will be detected:
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`def verify_state_chain(agent_id, claimed_head):
    # Get our recorded head for this agent
    known_head = get_known_head(agent_id)

    if known_head is None:
        # First interaction - accept and record
        record_head(agent_id, claimed_head)
        return True

    # Check if claimed head extends known head
    if claimed_head.sequence < known_head.sequence:
        raise ForkDetected("Claimed head is behind known head")

    if claimed_head.sequence == known_head.sequence:
        if claimed_head.entry_hash != known_head.entry_hash:
            raise ForkDetected("Same sequence, different hash")
        return True

    # claimed_head.sequence > known_head.sequence
    # Verify chain from known_head to claimed_head
    chain = fetch_chain(agent_id, known_head.sequence, claimed_head.sequence)
    verify_chain_integrity(chain)

    record_head(agent_id, claimed_head)
    return True`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Chain Verification</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`from sigaid.state import verify_chain

# Verify a chain of entries
entries = await agent.get_state_history(limit=100)

if verify_chain(entries):
    print("Chain integrity verified!")
else:
    print("Chain has been tampered with!")

# Verify single entry signature
entry = await agent.get_state_entry(5)
if entry.verify_signature(agent.public_key_bytes()):
    print("Signature valid!")

# Verify entry hash
if entry.verify_hash():
    print("Hash valid!")`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">State Entry Model</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`@dataclass(frozen=True)
class StateEntry:
    """Immutable state chain entry."""

    agent_id: str           # aid_xxx format
    sequence: int           # Monotonic sequence number
    prev_hash: bytes        # 32 bytes, BLAKE3 of previous
    timestamp: datetime     # When recorded
    action_type: str        # transaction, attestation, etc.
    action_summary: str     # Human-readable summary
    action_data_hash: bytes # 32 bytes, hash of full data
    signature: bytes        # 64 bytes, Ed25519
    entry_hash: bytes       # 32 bytes, hash of this entry`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Data Privacy</h2>

      <p className="text-muted-foreground mb-4">
        The state chain stores <strong>hashes</strong> of action data, not the
        data itself. This provides:
      </p>

      <ul className="space-y-2 mb-6">
        <li>
          <strong>Privacy:</strong> Sensitive data stays with you
        </li>
        <li>
          <strong>Verifiability:</strong> Anyone can verify data matches the
          recorded hash
        </li>
        <li>
          <strong>Efficiency:</strong> Chain stays small regardless of data size
        </li>
      </ul>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`# Only the hash is stored on the chain
entry = await agent.record_action(
    action_type="transaction",
    data={"secret": "sensitive_info"}  # Not stored
)

# Later, prove the data matches
original_data = {"secret": "sensitive_info"}
data_hash = blake3(json.dumps(original_data).encode())

assert entry.action_data_hash == data_hash  # Verifiable!`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Next Steps</h2>

      <ul className="space-y-2 not-prose">
        <li>
          <a href="/docs/concepts/verification" className="text-primary hover:underline">
            Learn about Verification
          </a>
        </li>
        <li>
          <a href="/docs/crypto/hashing" className="text-primary hover:underline">
            State Hashing Deep Dive
          </a>
        </li>
        <li>
          <a href="/docs/sdk/state-entry" className="text-primary hover:underline">
            StateEntry API Reference
          </a>
        </li>
      </ul>
    </article>
  );
}
