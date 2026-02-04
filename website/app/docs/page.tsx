import { Badge } from "@/components/ui/badge";
import Link from "next/link";

export default function DocsPage() {
  return (
    <article className="prose prose-invert max-w-none">
      <Badge variant="outline" className="mb-4">
        Documentation
      </Badge>

      <h1 className="text-4xl font-bold mb-4">Introduction to SigAid</h1>

      <p className="text-lg text-muted-foreground mb-8">
        SigAid is a cryptographic identity protocol for AI agents. It provides
        verifiable identity, exclusive leasing, and tamper-proof audit trails
        for autonomous systems.
      </p>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Why SigAid?</h2>

      <p className="text-muted-foreground mb-4">
        As AI agents gain autonomy and interact with real-world services, three
        critical questions emerge:
      </p>

      <ul className="space-y-2 mb-6">
        <li className="flex items-start gap-3">
          <span className="text-primary">1.</span>
          <span>
            <strong>Identity:</strong> How do you verify an agent is who it
            claims to be?
          </span>
        </li>
        <li className="flex items-start gap-3">
          <span className="text-primary">2.</span>
          <span>
            <strong>Exclusivity:</strong> How do you ensure only one instance is
            operating?
          </span>
        </li>
        <li className="flex items-start gap-3">
          <span className="text-primary">3.</span>
          <span>
            <strong>Auditability:</strong> How do you maintain a tamper-proof
            record of actions?
          </span>
        </li>
      </ul>

      <p className="text-muted-foreground mb-8">
        SigAid answers all three with state-of-the-art cryptography: Ed25519
        signatures for identity, exclusive leases for singleton enforcement, and
        hash-chained state entries for auditability.
      </p>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Core Concepts</h2>

      <div className="grid md:grid-cols-2 gap-4 not-prose mb-8">
        <Link
          href="/docs/concepts/identity"
          className="block p-4 rounded-lg border border-border hover:border-primary/50 transition-colors"
        >
          <h3 className="font-semibold mb-1">Agent Identity</h3>
          <p className="text-sm text-muted-foreground">
            Ed25519 keypairs that serve as unforgeable agent identifiers.
          </p>
        </Link>
        <Link
          href="/docs/concepts/leasing"
          className="block p-4 rounded-lg border border-border hover:border-primary/50 transition-colors"
        >
          <h3 className="font-semibold mb-1">Exclusive Leasing</h3>
          <p className="text-sm text-muted-foreground">
            Atomic locks ensuring only one agent instance can operate at a time.
          </p>
        </Link>
        <Link
          href="/docs/concepts/state-chain"
          className="block p-4 rounded-lg border border-border hover:border-primary/50 transition-colors"
        >
          <h3 className="font-semibold mb-1">State Chain</h3>
          <p className="text-sm text-muted-foreground">
            Cryptographically linked history of all agent actions.
          </p>
        </Link>
        <Link
          href="/docs/concepts/verification"
          className="block p-4 rounded-lg border border-border hover:border-primary/50 transition-colors"
        >
          <h3 className="font-semibold mb-1">Verification</h3>
          <p className="text-sm text-muted-foreground">
            Proof bundles that services use to verify agent authenticity.
          </p>
        </Link>
      </div>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Quick Example</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`from sigaid import AgentClient

# Create agent with cryptographic identity
agent = AgentClient.create()

# Acquire exclusive lease
async with agent.lease():
    # Record tamper-proof action
    await agent.record_action("transaction", {
        "type": "payment",
        "amount": 100.00
    })

    # Generate proof for verification
    proof = agent.create_proof(challenge=challenge)`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Next Steps</h2>

      <div className="flex flex-col gap-2 not-prose">
        <Link
          href="/docs/quickstart"
          className="text-primary hover:underline flex items-center gap-2"
        >
          Quick Start Guide
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 7l5 5m0 0l-5 5m5-5H6"
            />
          </svg>
        </Link>
        <Link
          href="/docs/installation"
          className="text-primary hover:underline flex items-center gap-2"
        >
          Installation
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 7l5 5m0 0l-5 5m5-5H6"
            />
          </svg>
        </Link>
        <Link
          href="/playground"
          className="text-primary hover:underline flex items-center gap-2"
        >
          Try the Playground
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M13 7l5 5m0 0l-5 5m5-5H6"
            />
          </svg>
        </Link>
      </div>
    </article>
  );
}
