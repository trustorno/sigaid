import { Badge } from "@/components/ui/badge";

export default function InstallationPage() {
  return (
    <article className="prose prose-invert max-w-none">
      <Badge variant="outline" className="mb-4">
        Getting Started
      </Badge>

      <h1 className="text-4xl font-bold mb-4">Installation</h1>

      <p className="text-lg text-muted-foreground mb-8">
        Install SigAid and its dependencies for your project.
      </p>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Requirements</h2>

      <ul className="space-y-2 mb-6">
        <li>Python 3.11 or higher</li>
        <li>pip or uv package manager</li>
      </ul>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Basic Installation</h2>

      <p className="text-muted-foreground mb-4">
        Install SigAid using pip:
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>pip install sigaid</code>
      </pre>

      <p className="text-muted-foreground mb-4">
        Or using uv (recommended for faster installation):
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>uv add sigaid</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Optional Dependencies</h2>

      <h3 className="text-xl font-semibold mt-6 mb-3">Post-Quantum Cryptography</h3>

      <p className="text-muted-foreground mb-4">
        For post-quantum hybrid signatures (Ed25519 + Dilithium-3):
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>pip install sigaid[pq]</code>
      </pre>

      <h3 className="text-xl font-semibold mt-6 mb-3">HSM Support</h3>

      <p className="text-muted-foreground mb-4">
        For hardware security module integration via PKCS#11:
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>pip install sigaid[hsm]</code>
      </pre>

      <h3 className="text-xl font-semibold mt-6 mb-3">Authority Server</h3>

      <p className="text-muted-foreground mb-4">
        To run your own Authority server:
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>pip install sigaid[server]</code>
      </pre>

      <h3 className="text-xl font-semibold mt-6 mb-3">All Features</h3>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>pip install sigaid[all]</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Development Installation</h2>

      <p className="text-muted-foreground mb-4">
        For contributing to SigAid or running tests:
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`git clone https://github.com/trustorno/sigaid.git
cd sigaid
pip install -e ".[dev]"

# Run tests
pytest tests/ -v`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Environment Configuration</h2>

      <p className="text-muted-foreground mb-4">
        Set your API key as an environment variable:
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`# Linux/macOS
export SIGAID_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:SIGAID_API_KEY="your_api_key_here"

# Or in your .env file
SIGAID_API_KEY=your_api_key_here`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Configuration Options</h2>

      <p className="text-muted-foreground mb-4">
        SigAid can be configured via environment variables:
      </p>

      <div className="overflow-x-auto mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4">Variable</th>
              <th className="text-left py-2 pr-4">Default</th>
              <th className="text-left py-2">Description</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">SIGAID_API_KEY</td>
              <td className="py-2 pr-4 text-muted-foreground">-</td>
              <td className="py-2">API key for hosted Authority</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">SIGAID_AUTHORITY_URL</td>
              <td className="py-2 pr-4 font-mono text-xs text-muted-foreground">
                https://api.sigaid.com
              </td>
              <td className="py-2">Authority server URL</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">SIGAID_LEASE_TTL</td>
              <td className="py-2 pr-4 text-muted-foreground">600</td>
              <td className="py-2">Lease duration in seconds</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">SIGAID_AUTO_RENEW</td>
              <td className="py-2 pr-4 text-muted-foreground">true</td>
              <td className="py-2">Auto-renew leases</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">SIGAID_LOG_LEVEL</td>
              <td className="py-2 pr-4 text-muted-foreground">INFO</td>
              <td className="py-2">Logging verbosity</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Verify Installation</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`python -c "import sigaid; print(sigaid.__version__)"
# Output: 0.1.0`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Next Steps</h2>

      <ul className="space-y-2 not-prose">
        <li>
          <a href="/docs/quickstart" className="text-primary hover:underline">
            Follow the Quick Start guide
          </a>
        </li>
        <li>
          <a href="/playground" className="text-primary hover:underline">
            Try the interactive Playground
          </a>
        </li>
      </ul>
    </article>
  );
}
