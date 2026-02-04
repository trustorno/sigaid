import { Badge } from "@/components/ui/badge";

export default function QuickStartPage() {
  return (
    <article className="prose prose-invert max-w-none">
      <Badge variant="outline" className="mb-4">
        Getting Started
      </Badge>

      <h1 className="text-4xl font-bold mb-4">Quick Start</h1>

      <p className="text-lg text-muted-foreground mb-8">
        Get your first agent running with verifiable identity in under 5
        minutes.
      </p>

      <h2 className="text-2xl font-semibold mt-8 mb-4">1. Install SigAid</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>pip install sigaid</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">2. Get API Key</h2>

      <p className="text-muted-foreground mb-4">
        Sign up at{" "}
        <a href="https://sigaid.com/signup" className="text-primary hover:underline">
          sigaid.com
        </a>{" "}
        to get your API key. The free tier includes 5 agents and 1,000
        operations per month.
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`# Set your API key
export SIGAID_API_KEY=your_api_key_here`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">3. Create Your First Agent</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`import asyncio
from sigaid import AgentClient

async def main():
    # Create agent with new cryptographic identity
    agent = AgentClient.create()

    print(f"Agent ID: {agent.agent_id}")
    # Output: Agent ID: aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1

    # Save keypair for future sessions
    agent.save_keypair("my_agent.key", password="secure_password")

asyncio.run(main())`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">4. Acquire Exclusive Lease</h2>

      <p className="text-muted-foreground mb-4">
        The lease ensures only one instance of your agent can operate at a time.
        Any clones or duplicate instances will be rejected.
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`async def main():
    # Load agent from saved keypair
    agent = AgentClient.from_file("my_agent.key", password="secure_password")

    # Acquire exclusive lease
    async with agent.lease() as lease:
        print(f"Lease acquired until {lease.expires_at}")

        # Your agent logic here
        await do_agent_work()

    # Lease automatically released when context exits

asyncio.run(main())`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">5. Record Actions to State Chain</h2>

      <p className="text-muted-foreground mb-4">
        Every action is cryptographically signed and hash-linked, creating a
        tamper-proof audit trail.
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`async with agent.lease():
    # Record action - automatically signed and hash-chained
    entry = await agent.record_action(
        action_type="transaction",
        data={
            "type": "hotel_booking",
            "hotel": "Grand Hyatt Tokyo",
            "amount": 45000,
            "currency": "JPY"
        }
    )

    print(f"Recorded at sequence {entry.sequence}")
    print(f"Entry hash: {entry.entry_hash.hex()[:16]}...")
    # Output: Recorded at sequence 1
    # Output: Entry hash: 7a3b9c1d2e4f5g6h...`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">6. Generate Proof for Verification</h2>

      <p className="text-muted-foreground mb-4">
        When interacting with services, create a proof bundle that they can
        verify.
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`async with agent.lease():
    # Service sends a challenge
    challenge = b"random_challenge_from_service"

    # Create proof bundle
    proof = agent.create_proof(challenge=challenge)

    # Send proof to service for verification
    response = await service.submit_proof(proof.to_bytes())

    if response.verified:
        print("Service verified our identity!")
        # Proceed with trusted interaction`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Complete Example</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`import asyncio
from sigaid import AgentClient

async def booking_agent():
    # Create or load agent
    try:
        agent = AgentClient.from_file("booking_agent.key", password="secret")
    except FileNotFoundError:
        agent = AgentClient.create()
        agent.save_keypair("booking_agent.key", password="secret")

    print(f"Agent: {agent.agent_id}")

    # Acquire exclusive lease
    async with agent.lease() as lease:
        print(f"Operating until {lease.expires_at}")

        # Record booking action
        entry = await agent.record_action(
            "hotel_booking",
            {
                "guest": "John Doe",
                "hotel": "Park Hyatt",
                "dates": "2024-03-15 to 2024-03-18",
                "total": 1250.00
            }
        )
        print(f"Booking recorded: {entry.entry_hash.hex()[:8]}...")

        # Create proof for hotel's verification system
        proof = agent.create_proof(
            challenge=b"hotel_verification_challenge"
        )

        # Hotel can verify:
        # - Agent identity is cryptographically valid
        # - Agent holds the exclusive lease
        # - Complete action history is tamper-proof
        print("Proof ready for hotel verification")

asyncio.run(booking_agent())`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Next Steps</h2>

      <ul className="space-y-2 not-prose">
        <li>
          <a href="/docs/concepts/identity" className="text-primary hover:underline">
            Learn about Agent Identity
          </a>
        </li>
        <li>
          <a href="/docs/concepts/leasing" className="text-primary hover:underline">
            Understand Exclusive Leasing
          </a>
        </li>
        <li>
          <a href="/docs/concepts/state-chain" className="text-primary hover:underline">
            Explore State Chains
          </a>
        </li>
        <li>
          <a href="/docs/sdk/agent-client" className="text-primary hover:underline">
            Full AgentClient Reference
          </a>
        </li>
      </ul>
    </article>
  );
}
