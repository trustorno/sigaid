# SigAid Authority API Documentation

## Base URLs

| Deployment | Base URL |
|------------|----------|
| **Hosted Service** | `https://api.sigaid.com/v1` |
| **Self-Hosted** | `https://your-authority.com/v1` |
| **Local Development** | `http://localhost:8000/v1` |

## Authentication

All API requests require authentication via API key:

```
X-API-Key: sk_xxx
```

Or via Bearer token:

```
Authorization: Bearer sk_xxx
```

Get your API key:
- **Hosted**: Sign up at sigaid.com
- **Self-hosted**: Generate via Authority admin CLI

### Rate Limits

| Endpoint Type | Requests/Minute |
|---------------|-----------------|
| Agent Registration | 30 |
| Lease Acquire | 30 |
| Lease Renew | 120 |
| State Append | 200 |
| State Read | 500 |
| Verify | 1000 |

Rate limit headers are returned on all responses:
- `X-RateLimit-Limit`: Maximum requests per minute
- `X-RateLimit-Remaining`: Remaining requests in current window

---

## Agents

### Register Agent

Register a new agent with the Authority.

```
POST /v1/agents
```

**Request Body:**
```json
{
  "agent_id": "aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1",
  "public_key": "base64-encoded-32-byte-ed25519-public-key",
  "metadata": {
    "name": "My Agent",
    "version": "1.0.0"
  }
}
```

**Response (201 Created):**
```json
{
  "agent_id": "aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1",
  "public_key": "base64-encoded-key",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "metadata": {},
  "total_transactions": 0,
  "successful_transactions": 0,
  "age_days": 0,
  "reputation_score": 0.0
}
```

**Errors:**
- `409 Conflict`: Agent already exists

---

### Get Agent

Get agent information and reputation.

```
GET /v1/agents/{agent_id}
```

**Response (200 OK):**
```json
{
  "agent_id": "aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1",
  "public_key": "base64-encoded-key",
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z",
  "metadata": {},
  "total_transactions": 42,
  "successful_transactions": 41,
  "age_days": 30,
  "reputation_score": 0.95
}
```

**Errors:**
- `404 Not Found`: Agent not found

---

## Leases

### Acquire Lease

Acquire an exclusive lease for an agent. Only one instance can hold a lease at a time.

```
POST /v1/leases
```

**Request Body:**
```json
{
  "agent_id": "aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1",
  "session_id": "unique-session-id",
  "timestamp": "2024-01-15T10:30:00Z",
  "nonce": "hex-encoded-32-byte-nonce",
  "ttl_seconds": 600,
  "signature": "hex-encoded-64-byte-ed25519-signature"
}
```

**Signature Format:**
The signature is computed over: `{agent_id}:{session_id}:{timestamp}:{nonce}`
with domain separation using `sigaid.lease.v1`.

**Response (200 OK):**
```json
{
  "agent_id": "aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1",
  "session_id": "unique-session-id",
  "lease_token": "v4.local.xxx...",
  "acquired_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-15T10:40:00Z",
  "sequence": 0
}
```

**Errors:**
- `401 Unauthorized`: Invalid signature
- `404 Not Found`: Agent not found
- `409 Conflict`: Lease held by another instance

```json
{
  "detail": {
    "error": "lease_held",
    "message": "Lease held by another session",
    "holder_session_id": "other-session-id"
  }
}
```

---

### Renew Lease

Renew an existing lease before it expires.

```
PUT /v1/leases/{agent_id}
```

**Request Body:**
```json
{
  "session_id": "unique-session-id",
  "current_token": "v4.local.xxx...",
  "ttl_seconds": 600
}
```

**Response (200 OK):**
```json
{
  "agent_id": "aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1",
  "session_id": "unique-session-id",
  "lease_token": "v4.local.new-token...",
  "acquired_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-01-15T10:50:00Z",
  "sequence": 1
}
```

**Errors:**
- `403 Forbidden`: Session mismatch
- `404 Not Found`: No active lease
- `410 Gone`: Lease expired

---

### Release Lease

Release a lease when done.

```
DELETE /v1/leases/{agent_id}
```

**Request Body:**
```json
{
  "session_id": "unique-session-id",
  "token": "v4.local.xxx..."
}
```

**Response:** `204 No Content`

---

### Get Lease Status

Check if an agent has an active lease.

```
GET /v1/leases/{agent_id}
```

**Response (200 OK):**
```json
{
  "agent_id": "aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1",
  "active": true,
  "session_id": "unique-session-id",
  "expires_at": "2024-01-15T10:40:00Z"
}
```

---

## State Chain

### Append State Entry

Append a new entry to the agent's state chain. Requires an active lease.

```
POST /v1/state/{agent_id}
```

**Request Body:**
```json
{
  "agent_id": "aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1",
  "sequence": 1,
  "prev_hash": "base64-encoded-32-byte-hash",
  "timestamp": "2024-01-15T10:35:00Z",
  "action_type": "transaction",
  "action_summary": "Payment to service A",
  "action_data_hash": "base64-encoded-32-byte-hash",
  "signature": "base64-encoded-64-byte-signature",
  "entry_hash": "base64-encoded-32-byte-hash"
}
```

**Action Types:**
- `transaction` - Financial or resource transaction
- `attestation` - Third-party attestation
- `upgrade` - Agent capability upgrade
- `reset` - State reset (with authority approval)
- `custom` - Custom action type

**Response (201 Created):**
```json
{
  "agent_id": "aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1",
  "sequence": 1,
  "prev_hash": "base64-hash",
  "entry_hash": "base64-hash",
  "action_type": "transaction",
  "action_summary": "Payment to service A",
  "action_data_hash": "base64-hash",
  "signature": "base64-signature",
  "created_at": "2024-01-15T10:35:00Z"
}
```

**Errors:**
- `401 Unauthorized`: Invalid signature or entry hash
- `403 Forbidden`: No active lease
- `409 Conflict`: Sequence mismatch or fork detected

---

### Get State Head

Get the current state chain head for an agent.

```
GET /v1/state/{agent_id}
```

**Response (200 OK):**
```json
{
  "agent_id": "aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1",
  "sequence": 42,
  "entry_hash": "base64-encoded-32-byte-hash",
  "created_at": "2024-01-15T10:35:00Z"
}
```

---

### Get State History

Get state chain history for an agent.

```
GET /v1/state/{agent_id}/history?limit=100&offset=0
```

**Query Parameters:**
- `limit` (default: 100): Maximum entries to return
- `offset` (default: 0): Number of entries to skip

**Response (200 OK):**
```json
{
  "agent_id": "aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1",
  "entries": [
    {
      "sequence": 42,
      "prev_hash": "base64-hash",
      "entry_hash": "base64-hash",
      "action_type": "transaction",
      "action_summary": "Payment",
      "signature": "base64-signature",
      "created_at": "2024-01-15T10:35:00Z"
    }
  ],
  "total_count": 43
}
```

---

## Verification

### Verify Proof Bundle

Verify an agent's proof bundle. Requires API key.

```
POST /v1/verify
```

**Headers:**
```
X-API-Key: your-api-key
```

**Request Body:**
```json
{
  "proof": {
    "agent_id": "aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1",
    "challenge": "hex-encoded-challenge",
    "challenge_response": "hex-encoded-signature",
    "lease_token": "v4.local.xxx...",
    "state_head": { ... }
  },
  "require_lease": true,
  "min_reputation_score": 0.5
}
```

**Response (200 OK):**
```json
{
  "valid": true,
  "agent_id": "aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1",
  "lease_active": true,
  "state_verified": true,
  "agent_info": {
    "agent_id": "aid_...",
    "reputation_score": 0.95,
    "total_transactions": 42
  }
}
```

---

## API Keys

### Create API Key

Create a new API key for verification requests.

```
POST /v1/api-keys
```

**Request Body:**
```json
{
  "name": "My Service",
  "rate_limit_per_minute": 1000
}
```

**Response (201 Created):**
```json
{
  "api_key": "sk_live_xxx...",
  "name": "My Service",
  "created_at": "2024-01-15T10:30:00Z",
  "rate_limit_per_minute": 1000
}
```

**Note:** The `api_key` is only returned once. Store it securely.

---

## Health Check

```
GET /health
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "sigaid-authority"
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message"
}
```

Or for structured errors:

```json
{
  "detail": {
    "error": "error_code",
    "message": "Human readable message",
    "field": "additional_info"
  }
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 204 | No Content |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 410 | Gone |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |
