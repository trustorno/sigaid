"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const navigation = [
  {
    title: "Getting Started",
    items: [
      { title: "Introduction", href: "/docs" },
      { title: "Quick Start", href: "/docs/quickstart" },
      { title: "Installation", href: "/docs/installation" },
    ],
  },
  {
    title: "Core Concepts",
    items: [
      { title: "Agent Identity", href: "/docs/concepts/identity" },
      { title: "Exclusive Leasing", href: "/docs/concepts/leasing" },
      { title: "State Chain", href: "/docs/concepts/state-chain" },
      { title: "Verification", href: "/docs/concepts/verification" },
    ],
  },
  {
    title: "SDK Reference",
    items: [
      { title: "AgentClient", href: "/docs/sdk/agent-client" },
      { title: "Verifier", href: "/docs/sdk/verifier" },
      { title: "KeyPair", href: "/docs/sdk/keypair" },
      { title: "StateEntry", href: "/docs/sdk/state-entry" },
    ],
  },
  {
    title: "Cryptography",
    items: [
      { title: "Key Generation", href: "/docs/crypto/keys" },
      { title: "Signatures", href: "/docs/crypto/signatures" },
      { title: "State Hashing", href: "/docs/crypto/hashing" },
      { title: "Post-Quantum", href: "/docs/crypto/post-quantum" },
      { title: "HSM Support", href: "/docs/crypto/hsm" },
    ],
  },
  {
    title: "API Reference",
    items: [
      { title: "Overview", href: "/docs/api" },
      { title: "Agents", href: "/docs/api/agents" },
      { title: "Leases", href: "/docs/api/leases" },
      { title: "State", href: "/docs/api/state" },
      { title: "Verification", href: "/docs/api/verification" },
    ],
  },
  {
    title: "Guides",
    items: [
      { title: "Financial Agents", href: "/docs/guides/financial" },
      { title: "Multi-Agent Systems", href: "/docs/guides/multi-agent" },
      { title: "Security Best Practices", href: "/docs/guides/security" },
      { title: "Self-Hosting", href: "/docs/guides/self-hosting" },
    ],
  },
];

export function DocsSidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden lg:block w-64 border-r border-border bg-card/30 sticky top-16 h-[calc(100vh-4rem)] overflow-y-auto">
      <nav className="p-4 space-y-6">
        {navigation.map((section) => (
          <div key={section.title}>
            <h4 className="font-semibold text-sm mb-2 text-muted-foreground uppercase tracking-wide">
              {section.title}
            </h4>
            <ul className="space-y-1">
              {section.items.map((item) => (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    className={cn(
                      "block px-3 py-2 text-sm rounded-md transition-colors",
                      pathname === item.href
                        ? "bg-primary/10 text-primary font-medium"
                        : "text-muted-foreground hover:text-foreground hover:bg-muted"
                    )}
                  >
                    {item.title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
    </aside>
  );
}
