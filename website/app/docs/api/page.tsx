import { Badge } from "@/components/ui/badge";

export default function ApiOverviewPage() {
  return (
    <article className="prose prose-invert max-w-none">
      <Badge variant="outline" className="mb-4">
        API Reference
      </Badge>

      <h1 className="text-4xl font-bold mb-4">API Overview</h1>

      <p className="text-lg text-muted-foreground mb-8">
        The SigAid Authority API provides endpoints for agent management, lease
        operations, state chain storage, and verification.
      </p>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Base URL</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>https://api.sigaid.com/v1</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Authentication</h2>

      <p className="text-muted-foreground mb-4">
        All API requests require authentication via API key:
      </p>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`Authorization: Bearer your_api_key_here`}</code>
      </pre>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Endpoints</h2>

      <div className="overflow-x-auto mb-8">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4">Method</th>
              <th className="text-left py-2 pr-4">Endpoint</th>
              <th className="text-left py-2">Description</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-border bg-muted/30">
              <td className="py-2 pr-4" colSpan={3}>
                <strong>Agents</strong>
              </td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs text-accent">POST</td>
              <td className="py-2 pr-4 font-mono text-xs">/agents</td>
              <td className="py-2">Register new agent</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs text-primary">GET</td>
              <td className="py-2 pr-4 font-mono text-xs">/agents/{"{agent_id}"}</td>
              <td className="py-2">Get agent info</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs text-destructive">DELETE</td>
              <td className="py-2 pr-4 font-mono text-xs">/agents/{"{agent_id}"}</td>
              <td className="py-2">Revoke agent</td>
            </tr>

            <tr className="border-b border-border bg-muted/30">
              <td className="py-2 pr-4" colSpan={3}>
                <strong>Leases</strong>
              </td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs text-accent">POST</td>
              <td className="py-2 pr-4 font-mono text-xs">/leases</td>
              <td className="py-2">Acquire lease</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs text-yellow-500">PUT</td>
              <td className="py-2 pr-4 font-mono text-xs">/leases/{"{agent_id}"}</td>
              <td className="py-2">Renew lease</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs text-destructive">DELETE</td>
              <td className="py-2 pr-4 font-mono text-xs">/leases/{"{agent_id}"}</td>
              <td className="py-2">Release lease</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs text-primary">GET</td>
              <td className="py-2 pr-4 font-mono text-xs">/leases/{"{agent_id}"}</td>
              <td className="py-2">Check lease status</td>
            </tr>

            <tr className="border-b border-border bg-muted/30">
              <td className="py-2 pr-4" colSpan={3}>
                <strong>State</strong>
              </td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs text-accent">POST</td>
              <td className="py-2 pr-4 font-mono text-xs">/state/{"{agent_id}"}</td>
              <td className="py-2">Append state entry</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs text-primary">GET</td>
              <td className="py-2 pr-4 font-mono text-xs">/state/{"{agent_id}"}</td>
              <td className="py-2">Get state head</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs text-primary">GET</td>
              <td className="py-2 pr-4 font-mono text-xs">/state/{"{agent_id}"}/history</td>
              <td className="py-2">Get state history</td>
            </tr>

            <tr className="border-b border-border bg-muted/30">
              <td className="py-2 pr-4" colSpan={3}>
                <strong>Verification</strong>
              </td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs text-accent">POST</td>
              <td className="py-2 pr-4 font-mono text-xs">/verify</td>
              <td className="py-2">Verify proof bundle</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Rate Limits</h2>

      <div className="overflow-x-auto mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4">Endpoint</th>
              <th className="text-left py-2 pr-4">Free</th>
              <th className="text-left py-2 pr-4">Pro</th>
              <th className="text-left py-2">Enterprise</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">Lease acquire</td>
              <td className="py-2 pr-4">5/min</td>
              <td className="py-2 pr-4">60/min</td>
              <td className="py-2">Unlimited</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">Lease renew</td>
              <td className="py-2 pr-4">60/min</td>
              <td className="py-2 pr-4">300/min</td>
              <td className="py-2">Unlimited</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">State append</td>
              <td className="py-2 pr-4">100/min</td>
              <td className="py-2 pr-4">1000/min</td>
              <td className="py-2">Unlimited</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4">Verify</td>
              <td className="py-2 pr-4">100/min</td>
              <td className="py-2 pr-4">10000/min</td>
              <td className="py-2">Unlimited</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 className="text-2xl font-semibold mt-8 mb-4">Error Responses</h2>

      <pre className="bg-card border border-border rounded-lg p-4 overflow-x-auto mb-6">
        <code>{`{
  "error": {
    "code": "LEASE_HELD",
    "message": "Lease is held by another instance",
    "details": {
      "holder_session": "sid_xxx...",
      "expires_at": "2024-01-15T10:30:00Z"
    }
  }
}`}</code>
      </pre>

      <h3 className="text-xl font-semibold mt-6 mb-3">Error Codes</h3>

      <div className="overflow-x-auto mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-2 pr-4">Code</th>
              <th className="text-left py-2 pr-4">HTTP</th>
              <th className="text-left py-2">Description</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">AGENT_NOT_FOUND</td>
              <td className="py-2 pr-4">404</td>
              <td className="py-2">Agent does not exist</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">LEASE_HELD</td>
              <td className="py-2 pr-4">409</td>
              <td className="py-2">Lease held by another instance</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">LEASE_EXPIRED</td>
              <td className="py-2 pr-4">401</td>
              <td className="py-2">Lease token has expired</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">INVALID_SIGNATURE</td>
              <td className="py-2 pr-4">401</td>
              <td className="py-2">Signature verification failed</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">SEQUENCE_MISMATCH</td>
              <td className="py-2 pr-4">409</td>
              <td className="py-2">State sequence conflict</td>
            </tr>
            <tr className="border-b border-border">
              <td className="py-2 pr-4 font-mono text-xs">RATE_LIMITED</td>
              <td className="py-2 pr-4">429</td>
              <td className="py-2">Too many requests</td>
            </tr>
          </tbody>
        </table>
      </div>

      <h2 className="text-2xl font-semibold mt-8 mb-4">SDKs</h2>

      <p className="text-muted-foreground mb-4">
        We provide official SDKs that handle authentication, signatures, and
        error handling:
      </p>

      <ul className="space-y-2 not-prose">
        <li>
          <a href="/docs/sdk/agent-client" className="text-primary hover:underline">
            Python SDK (sigaid)
          </a>
        </li>
        <li className="text-muted-foreground">
            TypeScript SDK (coming soon)
        </li>
        <li className="text-muted-foreground">
            Go SDK (coming soon)
        </li>
      </ul>
    </article>
  );
}
