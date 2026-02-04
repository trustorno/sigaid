import { Badge } from "@/components/ui/badge";

export default function LeasingPage() {
  return (
    <article className="prose prose-invert max-w-none">
      <Badge variant="outline" className="mb-4">
        Core Concepts
      </Badge>

      <h1 className="text-4xl font-bold mb-4">Exclusive Leasing</h1>

      <p className="text-lg text-muted-foreground mb-8">
        Exclusive leasing ensures only one instance of an agent can operate at
        any time. Clones and duplicate instances are cryptographically prevented
        from acquiring a lease.
      </p>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Why Exclusive Leasing?</h2>

      <p className="text-muted-foreground mb-4">
        Without exclusivity controls, multiple copies of an agent can:
      </p>

      <ul className="space-y-2 mb-6">
        <li>Make conflicting decisions (double-booking, duplicate transactions)</li>
        <li>Corrupt shared state</li>
        <li>Create audit trail inconsistencies</li>
        <li>Be exploited by malicious actors running unauthorized clones</li>
      </ul>

      <p className="text-muted-foreground mb-6">
        SigAid solves this with atomic lease acquisition - if an agent already
        holds a lease, all other instances are rejected.
      </p>

      <h2 className="text-2xl font-semibold mt-8 mb-4">How It Works</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`Client                                    Authority
   │                                          │
   │──── LeaseRequest ───────────────────────►│
   │     {                                    │
   │       agent_id,                          │
   │       timestamp,                         │
   │       nonce,                             │
   │       signature                          │
   │     }                                    │
   │                                          │
   │◄─── LeaseResponse ──────────────────────│
   │     {                                    │
   │       lease_token (PASETO),              │
   │       expires_at,                        │
   │       renewal_before                     │
   │     }                                    │
   │                                          │`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Atomic Acquisition</h2>

      <p className="text-muted-foreground mb-4">
        Lease acquisition uses atomic operations (Redis SETNX) to guarantee
        exclusivity:
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`# Atomic lease acquisition (Authority server)
async def acquire_lease(agent_id, session_id, ttl=600):
    key = f"lease:{agent_id}"

    # Atomic SET if not exists, with expiration
    result = await redis.set(
        key,
        session_id,
        nx=True,   # Only set if not exists
        ex=ttl     # Expire after TTL
    )

    return result is not None  # True if acquired`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Using Leases in Code</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`from sigaid import AgentClient

agent = AgentClient.from_file("agent.key", password="secret")

# Acquire exclusive lease
async with agent.lease() as lease:
    print(f"Lease acquired: {lease.session_id}")
    print(f"Expires at: {lease.expires_at}")

    # Only this instance can operate
    await do_agent_work()

# Lease automatically released when context exits
# Other instances can now acquire`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Clone Rejection</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`# Instance 1 acquires lease
agent1 = AgentClient.from_file("agent.key", password="secret")
async with agent1.lease():
    print("Instance 1 operating...")

    # Instance 2 tries to acquire same lease
    agent2 = AgentClient.from_file("agent.key", password="secret")
    try:
        async with agent2.lease():  # REJECTED!
            pass
    except LeaseHeldByAnotherInstance as e:
        print(f"Clone rejected: {e}")
        # Output: Clone rejected: Lease held by another instance`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Lease Tokens (PASETO v4)</h2>

      <p className="text-muted-foreground mb-4">
        Lease tokens use PASETO v4.local for authenticated encryption:
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`# Lease token format
v4.local.<encrypted_payload>.<footer>

# Payload contents
{
  "agent_id": "aid_xxxxx",
  "session_id": "sid_xxxxx",
  "iat": 1707000000,          # Issued at
  "exp": 1707000600,          # Expires (10 minutes)
  "jti": "unique_token_id",   # Token ID
  "seq": 42                   # Monotonic sequence
}`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Auto-Renewal</h2>

      <p className="text-muted-foreground mb-4">
        By default, leases auto-renew in the background to prevent expiration
        during long operations:
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`# Auto-renewal enabled by default
async with agent.lease():
    # Lease will auto-renew at 80% of TTL
    await long_running_operation()  # Hours of work
    # Lease stays valid throughout

# Disable auto-renewal if needed
async with agent.lease(auto_renew=False):
    # Must complete before lease expires
    await quick_operation()`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Lease Configuration</h2>

      <div className="overflow-x-auto mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4">Option</th>
              <th className="text-left py-2 pr-4">Default</th>
              <th className="text-left py-2">Description</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">ttl</td>
              <td className="py-2 pr-4">600s</td>
              <td className="py-2">Lease duration</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">auto_renew</td>
              <td className="py-2 pr-4">True</td>
              <td className="py-2">Background renewal</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">renew_threshold</td>
              <td className="py-2 pr-4">0.8</td>
              <td className="py-2">Renew at 80% of TTL</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">retry_attempts</td>
              <td className="py-2 pr-4">3</td>
              <td className="py-2">Acquisition retries</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Next Steps</h2>

      <ul className="space-y-2 not-prose">
        <li>
          <a href="/docs/concepts/state-chain" className="text-primary hover:underline">
            Learn about State Chains
          </a>
        </li>
        <li>
          <a href="/docs/api/leases" className="text-primary hover:underline">
            Lease API Reference
          </a>
        </li>
      </ul>
    </article>
  );
}
