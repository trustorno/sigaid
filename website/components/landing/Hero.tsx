"use client";

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden pt-16">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-primary/5 via-transparent to-transparent" />

      {/* Animated grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.03)_1px,transparent_1px)] bg-[size:64px_64px]" />

      <div className="container mx-auto px-4 py-20 relative z-10">
        <div className="max-w-4xl mx-auto text-center">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <Badge variant="outline" className="mb-6 px-4 py-1.5 text-sm">
              <span className="text-accent mr-2">New</span>
              Post-quantum hybrid signatures now available
            </Badge>
          </motion.div>

          {/* Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
            className="text-4xl md:text-6xl lg:text-7xl font-bold tracking-tight mb-6"
          >
            Cryptographic Identity
            <br />
            <span className="text-gradient">for AI Agents</span>
          </motion.h1>

          {/* Subheadline */}
          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="text-lg md:text-xl text-muted-foreground mb-8 max-w-2xl mx-auto"
          >
            One identity. One instance. Complete audit trail.
            <br />
            Give your AI agents verifiable cryptographic identity with exclusive
            leasing and tamper-proof state chains.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
            className="flex flex-col sm:flex-row gap-4 justify-center mb-12"
          >
            <Button size="xl" variant="glow" asChild>
              <Link href="/signup">
                Start Building
                <svg
                  className="ml-2 w-4 h-4"
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
            </Button>
            <Button size="xl" variant="outline" asChild>
              <Link href="/docs">
                Read the Docs
              </Link>
            </Button>
          </motion.div>

          {/* Install command */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="inline-flex items-center gap-3 bg-card border border-border rounded-lg px-4 py-3"
          >
            <span className="text-muted-foreground">$</span>
            <code className="text-sm font-mono">pip install sigaid</code>
            <button
              className="text-muted-foreground hover:text-foreground transition-colors"
              onClick={() => navigator.clipboard.writeText("pip install sigaid")}
            >
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
                  d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
            </button>
          </motion.div>
        </div>

        {/* Floating code preview */}
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.5 }}
          className="max-w-3xl mx-auto mt-16"
        >
          <div className="border-gradient rounded-xl overflow-hidden">
            <div className="bg-card/80 backdrop-blur-sm p-1">
              {/* Window controls */}
              <div className="flex items-center gap-2 px-3 py-2 border-b border-border">
                <div className="w-3 h-3 rounded-full bg-destructive/50" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                <div className="w-3 h-3 rounded-full bg-accent/50" />
                <span className="ml-2 text-xs text-muted-foreground font-mono">
                  main.py
                </span>
              </div>
              {/* Code */}
              <pre className="p-4 text-sm overflow-x-auto border-0 bg-transparent">
                <code>{`from sigaid import AgentClient

# Create agent with cryptographic identity
agent = AgentClient.create()

# Acquire exclusive lease - only one instance can run
async with agent.lease() as lease:
    # Record tamper-proof action to state chain
    await agent.record_action("booked_flight", {
        "flight": "UA123",
        "amount": 450.00
    })

    # Generate proof for third-party verification
    proof = agent.create_proof(challenge=service_challenge)

    # Service can verify: identity, lease, and history
    await service.verify(proof)  # ✓ Verified`}</code>
              </pre>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
