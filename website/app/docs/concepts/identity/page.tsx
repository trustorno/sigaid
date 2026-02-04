import { Badge } from "@/components/ui/badge";

export default function IdentityPage() {
  return (
    <article className="prose prose-invert max-w-none">
      <Badge variant="outline" className="mb-4">
        Core Concepts
      </Badge>

      <h1 className="text-4xl font-bold mb-4">Agent Identity</h1>

      <p className="text-lg text-muted-foreground mb-8">
        Every SigAid agent has a unique, cryptographically verifiable identity
        derived from an Ed25519 keypair.
      </p>

      <h2 className="text-2xl font-semibold mt-8 mb-4">How Identity Works</h2>

      <p className="text-muted-foreground mb-4">
        An agent's identity is based on public key cryptography:
      </p>

      <ol className="space-y-3 mb-6">
        <li>
          <strong>Key Generation:</strong> A random Ed25519 keypair is generated
          (32-byte private key, 32-byte public key)
        </li>
        <li>
          <strong>AgentID Derivation:</strong> The public key is encoded with
          Base58 and prefixed with <code>aid_</code>
        </li>
        <li>
          <strong>Signing:</strong> The private key signs all agent operations
          with domain separation
        </li>
        <li>
          <strong>Verification:</strong> Anyone with the AgentID (public key)
          can verify signatures
        </li>
      </ol>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`Master Seed (256 bits, from CSPRNG)
    │
    ├─► Identity Key (Ed25519) - Long-term, for signing
    │       └─► Public Key = AgentID
    │
    ├─► Session Key (derived via HKDF) - Per-lease session
    │
    └─► State Signing Key (Ed25519) - For state chain entries`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">AgentID Format</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`# AgentID Format
aid_<base58(public_key)>

# Example
aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1

# Components:
# - "aid_" prefix: Identifies as an AgentID
# - Base58 encoding: No ambiguous characters (0, O, I, l)
# - Last 4 chars: Built-in checksum`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Creating an Identity</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`from sigaid import AgentClient
from sigaid.crypto import KeyPair

# Option 1: Auto-generate new identity
agent = AgentClient.create()
print(agent.agent_id)  # aid_7Xq9YkPz...

# Option 2: Generate keypair explicitly
keypair = KeyPair.generate()
agent = AgentClient.from_keypair(keypair)

# Option 3: Derive from seed (deterministic)
seed = b"32_byte_seed_for_deterministic_key"
keypair = KeyPair.from_seed(seed)

# Option 4: Load from encrypted file
agent = AgentClient.from_file("agent.key", password="secure")`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Domain-Separated Signatures</h2>

      <p className="text-muted-foreground mb-4">
        All signatures include a domain tag to prevent cross-protocol attacks:
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`# Signature domains
"agent.identity.v1"    # Identity proofs
"agent.lease.v1"       # Lease operations
"agent.state.v1"       # State chain entries
"agent.verify.v1"      # Verification requests

# How it works internally
def sign(private_key, message, domain):
    domain_bytes = domain.encode('utf-8')
    tagged = len(domain_bytes).to_bytes(2) + domain_bytes + message
    return ed25519_sign(private_key, tagged)`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Key Properties</h2>

      <div className="overflow-x-auto mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4">Property</th>
              <th className="text-left py-2">Value</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">Algorithm</td>
              <td className="py-2">Ed25519</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">Private Key Size</td>
              <td className="py-2">32 bytes</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">Public Key Size</td>
              <td className="py-2">32 bytes</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">Signature Size</td>
              <td className="py-2">64 bytes</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">Security Level</td>
              <td className="py-2">128-bit (quantum: 64-bit)</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">Signing Speed</td>
              <td className="py-2">~60,000/sec</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Security Considerations</h2>

      <ul className="space-y-2 mb-6">
        <li>
          <strong>Never share private keys:</strong> The private key is the
          agent's identity. Anyone with it can impersonate the agent.
        </li>
        <li>
          <strong>Use encrypted storage:</strong> Always encrypt keypairs at
          rest with <code>save_keypair()</code>.
        </li>
        <li>
          <strong>Rotate compromised keys:</strong> If a key is compromised,
          create a new identity and revoke the old one.
        </li>
        <li>
          <strong>Consider HSM:</strong> For high-security applications, use
          hardware security modules.
        </li>
      </ul>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Next Steps</h2>

      <ul className="space-y-2 not-prose">
        <li>
          <a href="/docs/concepts/leasing" className="text-primary hover:underline">
            Learn about Exclusive Leasing
          </a>
        </li>
        <li>
          <a href="/docs/crypto/keys" className="text-primary hover:underline">
            Deep dive into Key Generation
          </a>
        </li>
        <li>
          <a href="/docs/crypto/hsm" className="text-primary hover:underline">
            HSM Support for Enterprise
          </a>
        </li>
      </ul>
    </article>
  );
}
