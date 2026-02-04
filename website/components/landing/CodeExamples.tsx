"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

const examples = {
  quickstart: {
    title: "Quick Start",
    description: "Get your agent running with verifiable identity in 5 lines",
    code: `from sigaid import AgentClient

# Create agent with cryptographic identity
agent = AgentClient.create()
print(f"Agent ID: {agent.agent_id}")
# Output: Agent ID: aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1

# Acquire exclusive lease
async with agent.lease() as lease:
    print(f"Lease acquired until {lease.expires_at}")

    # Your agent logic here
    await do_agent_work()`,
  },
  statechain: {
    title: "State Chain",
    description: "Record tamper-proof history of all agent actions",
    code: `async with agent.lease():
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

    # Get complete audit trail
    history = await agent.get_state_history(limit=10)
    for entry in history:
        print(f"  [{entry.sequence}] {entry.action_type}")`,
  },
  verification: {
    title: "Verification",
    description: "Prove your agent's identity to any service",
    code: `# Agent side: create proof bundle
async with agent.lease():
    # Service sends a challenge
    challenge = await service.get_challenge()

    # Agent creates cryptographic proof
    proof = agent.create_proof(challenge=challenge)

    # Proof contains: identity, lease token, state head, signature
    response = await service.submit_proof(proof)


# Service side: verify the proof
from sigaid import Verifier

verifier = Verifier(api_key="your_api_key")

result = await verifier.verify(
    proof_bundle,
    require_lease=True,        # Must have active lease
    min_reputation_score=0.8,  # Optional: check reputation
)

if result.valid:
    print(f"Verified: {result.agent_id}")
    print(f"State entries: {result.state_entry_count}")`,
  },
  hybrid: {
    title: "Post-Quantum",
    description: "Future-proof with hybrid Ed25519 + Dilithium-3 signatures",
    code: `from sigaid.crypto.hybrid import HybridKeyPair, HybridSigner

# Generate post-quantum hybrid keypair
keypair = HybridKeyPair.generate()

# Sign with both Ed25519 (fast) and Dilithium-3 (quantum-safe)
signer = HybridSigner(keypair)

signature = signer.sign(
    message=b"critical_transaction_data",
    domain="agent.transaction.v1"
)

# Signature includes both classical and PQ components
# Valid as long as EITHER algorithm remains secure
is_valid = signer.verify(
    signature=signature,
    message=b"critical_transaction_data",
    domain="agent.transaction.v1"
)`,
  },
};

export function CodeExamples() {
  const [activeTab, setActiveTab] = useState("quickstart");

  return (
    <section className="py-24">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            See It in Action
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Clean, intuitive API designed for developers. Get started in minutes.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="max-w-4xl mx-auto"
        >
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-4 mb-6">
              {Object.entries(examples).map(([key, example]) => (
                <TabsTrigger key={key} value={key} className="text-sm">
                  {example.title}
                </TabsTrigger>
              ))}
            </TabsList>

            {Object.entries(examples).map(([key, example]) => (
              <TabsContent key={key} value={key}>
                <div className="border-gradient rounded-xl overflow-hidden">
                  <div className="bg-card">
                    {/* Header */}
                    <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                      <div>
                        <h3 className="font-semibold">{example.title}</h3>
                        <p className="text-sm text-muted-foreground">
                          {example.description}
                        </p>
                      </div>
                      <button
                        className="text-muted-foreground hover:text-foreground transition-colors p-2"
                        onClick={() => navigator.clipboard.writeText(example.code)}
                      >
                        <svg
                          className="w-5 h-5"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                          />
                        </svg>
                      </button>
                    </div>
                    {/* Code */}
                    <pre className="p-4 text-sm overflow-x-auto border-0 bg-transparent">
                      <code className="language-python">{example.code}</code>
                    </pre>
                  </div>
                </div>
              </TabsContent>
            ))}
          </Tabs>
        </motion.div>
      </div>
    </section>
  );
}
