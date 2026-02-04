import { Badge } from "@/components/ui/badge";

export default function VerificationPage() {
  return (
    <article className="prose prose-invert max-w-none">
      <Badge variant="outline" className="mb-4">
        Core Concepts
      </Badge>

      <h1 className="text-4xl font-bold mb-4">Verification</h1>

      <p className="text-lg text-muted-foreground mb-8">
        Verification allows services to cryptographically confirm an agent's
        identity, lease status, and state chain integrity before trusting it.
      </p>

      <h2 className="text-2xl font-semibold mt-8 mb-4">The Verification Flow</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`Service                      Agent                      Authority
   │                           │                            │
   │── Challenge ─────────────►│                            │
   │   { nonce }               │                            │
   │                           │                            │
   │◄─ ProofBundle ───────────│                            │
   │   {                       │                            │
   │     agent_id,             │                            │
   │     lease_token,          │                            │
   │     challenge_response,   │                            │
   │     state_head,           │                            │
   │     signature             │                            │
   │   }                       │                            │
   │                           │                            │
   │───────────────────────── VerifyRequest ──────────────►│
   │                                                        │
   │◄──────────────────────── VerifyResponse ─────────────│
   │   {                                                    │
   │     valid: true,                                       │
   │     agent_info,                                        │
   │     reputation                                         │
   │   }                                                    │`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Agent Side: Creating Proofs</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`from sigaid import AgentClient

agent = AgentClient.from_file("agent.key", password="secret")

async with agent.lease():
    # Service sends a challenge (prevents replay attacks)
    challenge = await service.get_challenge()

    # Create proof bundle
    proof = agent.create_proof(challenge=challenge)

    # Proof contains:
    # - agent_id: Your identity
    # - lease_token: Proves active lease
    # - state_head: Current state chain head
    # - challenge_response: Signed challenge
    # - signature: Covers entire bundle

    # Send to service
    response = await service.submit_proof(proof.to_bytes())`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Service Side: Verifying Proofs</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`from sigaid import Verifier

# Create verifier with your API key
verifier = Verifier(api_key="your_api_key")

# Generate challenge for agent
challenge = secrets.token_bytes(32)
await send_challenge_to_agent(challenge)

# Receive proof from agent
proof_bytes = await receive_proof_from_agent()
proof = ProofBundle.from_bytes(proof_bytes)

# Verify with Authority
result = await verifier.verify(
    proof,
    require_lease=True,          # Must have active lease
    min_reputation_score=0.8,    # Optional: check reputation
    max_state_age=timedelta(hours=24),  # Optional: recent activity
)

if result.valid:
    print(f"Verified agent: {result.agent_id}")
    print(f"State entries: {result.state_entry_count}")
    print(f"Reputation: {result.reputation_score}")
else:
    print(f"Verification failed: {result.error}")`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Proof Bundle Contents</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`@dataclass
class ProofBundle:
    """Complete proof bundle for verification."""

    agent_id: str              # Agent's identity
    lease_token: str           # PASETO lease token
    state_head: StateEntry     # Current state chain head
    challenge_response: bytes  # Signature over challenge
    timestamp: datetime        # When proof was created
    signature: bytes           # Signature over entire bundle

    # Optional attestations
    user_attestation: bytes | None = None
    third_party_attestations: list[bytes] = []`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">What Gets Verified</h2>

      <div className="overflow-x-auto mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4">Check</th>
              <th className="text-left py-2">Description</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">Identity Signature</td>
              <td className="py-2">Proof was signed by the claimed agent</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">Challenge Response</td>
              <td className="py-2">Agent signed the correct challenge</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">Lease Token</td>
              <td className="py-2">Valid, unexpired lease from Authority</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">Lease Holder</td>
              <td className="py-2">Token belongs to this agent</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">State Chain</td>
              <td className="py-2">Head matches Authority records</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">Fork Detection</td>
              <td className="py-2">No chain divergence detected</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Offline Verification</h2>

      <p className="text-muted-foreground mb-4">
        For scenarios where Authority is unavailable, you can verify signatures
        and chain integrity locally:
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`# Offline verification (no Authority call)
result = await verifier.verify_offline(
    proof,
    known_state_head=last_known_head,  # Your recorded head
)

# What's verified offline:
# ✓ Signature validity
# ✓ Challenge response
# ✓ State chain integrity from known head

# What's NOT verified offline:
# ✗ Lease is currently active
# ✗ State head matches Authority
# ✗ No other instance is operating`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Verification Result</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`@dataclass
class VerificationResult:
    valid: bool
    agent_id: str | None
    error: str | None

    # Agent info (if valid)
    created_at: datetime | None
    state_entry_count: int
    last_activity: datetime | None

    # Reputation (if valid)
    reputation_score: float | None  # 0.0 to 1.0
    successful_operations: int
    total_operations: int`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Best Practices</h2>

      <ul className="space-y-2 mb-6">
        <li>
          <strong>Always use challenges:</strong> Random challenges prevent
          replay attacks
        </li>
        <li>
          <strong>Verify lease status:</strong> Unless you have a specific
          reason, require active leases
        </li>
        <li>
          <strong>Check reputation:</strong> For high-value operations, require
          minimum reputation
        </li>
        <li>
          <strong>Store verification results:</strong> Keep records for audit
          purposes
        </li>
        <li>
          <strong>Handle failures gracefully:</strong> Have fallback procedures
          for verification failures
        </li>
      </ul>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Next Steps</h2>

      <ul className="space-y-2 not-prose">
        <li>
          <a href="/docs/sdk/verifier" className="text-primary hover:underline">
            Verifier API Reference
          </a>
        </li>
        <li>
          <a href="/docs/api/verification" className="text-primary hover:underline">
            Verification API Endpoints
          </a>
        </li>
        <li>
          <a href="/docs/guides/security" className="text-primary hover:underline">
            Security Best Practices
          </a>
        </li>
      </ul>
    </article>
  );
}
