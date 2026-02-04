"use client";

import { motion } from "framer-motion";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const securityFeatures = [
  {
    title: "Ed25519 Signatures",
    description: "256-bit security with 64-byte signatures. Fast, compact, and battle-tested.",
    icon: "🔐",
  },
  {
    title: "BLAKE3 Hashing",
    description: "State-of-the-art hash function. Faster than SHA-256 with 256-bit security.",
    icon: "🔗",
  },
  {
    title: "PASETO Tokens",
    description: "Modern JWT alternative. No algorithm confusion attacks possible.",
    icon: "🎫",
  },
  {
    title: "Domain Separation",
    description: "Signatures are tagged by purpose. Cross-protocol attacks prevented.",
    icon: "🏷️",
  },
  {
    title: "HSM Support",
    description: "PKCS#11 integration for hardware security modules. Keys never leave the HSM.",
    icon: "🔒",
  },
  {
    title: "Post-Quantum Ready",
    description: "Hybrid Ed25519 + Dilithium-3 signatures for quantum resistance.",
    icon: "⚛️",
  },
];

export function Security() {
  return (
    <section className="py-24">
      <div className="container mx-auto px-4">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left: Description */}
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <Badge variant="outline" className="mb-4">
              Security First
            </Badge>
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              State-of-the-Art Cryptography
            </h2>
            <p className="text-lg text-muted-foreground mb-6">
              SigAid uses the same cryptographic primitives trusted by security
              professionals worldwide. No compromises, no shortcuts.
            </p>

            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-accent/20 text-accent flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg
                    className="w-4 h-4"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div>
                  <h4 className="font-medium">Open Source</h4>
                  <p className="text-sm text-muted-foreground">
                    Full transparency. Review every line of cryptographic code.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-accent/20 text-accent flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg
                    className="w-4 h-4"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div>
                  <h4 className="font-medium">No Custom Crypto</h4>
                  <p className="text-sm text-muted-foreground">
                    Uses established libraries: cryptography, blake3, pyseto.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-accent/20 text-accent flex items-center justify-center flex-shrink-0 mt-0.5">
                  <svg
                    className="w-4 h-4"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
                <div>
                  <h4 className="font-medium">Constant-Time Operations</h4>
                  <p className="text-sm text-muted-foreground">
                    Resistant to timing attacks on signature verification.
                  </p>
                </div>
              </div>
            </div>
          </motion.div>

          {/* Right: Feature Grid */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="grid grid-cols-2 gap-4"
          >
            {securityFeatures.map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, scale: 0.95 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
              >
                <Card className="h-full bg-card/50">
                  <CardContent className="p-4">
                    <div className="text-2xl mb-2">{feature.icon}</div>
                    <h4 className="font-medium text-sm mb-1">{feature.title}</h4>
                    <p className="text-xs text-muted-foreground">
                      {feature.description}
                    </p>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </motion.div>
        </div>
      </div>
    </section>
  );
}
