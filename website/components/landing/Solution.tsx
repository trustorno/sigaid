"use client";

import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const features = [
  {
    badge: "Identity",
    icon: (
      <svg
        className="w-6 h-6"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"
        />
      </svg>
    ),
    title: "Ed25519 Cryptographic Keys",
    description:
      "Each agent gets a unique keypair. The public key becomes the AgentID - a verifiable, unforgeable identity.",
    code: `agent_id = aid_7Xq9YkPzN3mWvR5tH8jL2c...`,
  },
  {
    badge: "Exclusivity",
    icon: (
      <svg
        className="w-6 h-6"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
        />
      </svg>
    ),
    title: "Exclusive Leasing",
    description:
      "Only one instance can hold an active lease at a time. Clones are cryptographically prevented from operating.",
    code: `async with agent.lease():  # Atomic lock`,
  },
  {
    badge: "Auditability",
    icon: (
      <svg
        className="w-6 h-6"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
    ),
    title: "Tamper-Proof State Chain",
    description:
      "Every action is cryptographically signed and hash-chained. Fork detection catches any tampering attempts.",
    code: `entry_hash = BLAKE3(prev_hash || action)`,
  },
];

export function Solution() {
  return (
    <section className="py-24 bg-gradient-to-b from-transparent via-primary/5 to-transparent">
      <div className="container mx-auto px-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <Badge variant="success" className="mb-4">
            The Solution
          </Badge>
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            Three Pillars of Agent Trust
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            SigAid provides cryptographic guarantees for identity, exclusivity,
            and auditability - everything services need to trust your agents.
          </p>
        </motion.div>

        <div className="grid md:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <Card className="h-full border-gradient">
                <CardContent className="p-6">
                  <Badge variant="outline" className="mb-4">
                    {feature.badge}
                  </Badge>
                  <div className="w-12 h-12 rounded-lg bg-primary/10 text-primary flex items-center justify-center mb-4">
                    {feature.icon}
                  </div>
                  <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                  <p className="text-muted-foreground mb-4">
                    {feature.description}
                  </p>
                  <code className="text-xs bg-muted px-2 py-1 rounded font-mono text-muted-foreground">
                    {feature.code}
                  </code>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
