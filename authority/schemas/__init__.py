"""Pydantic schemas for SigAid Authority API."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# === Agent Schemas ===

class AgentCreate(BaseModel):
    """Request to create a new agent."""
    agent_id: str = Field(..., description="Agent ID (aid_xxx format)")
    public_key: str = Field(..., description="Base64-encoded Ed25519 public key")
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Agent information response."""
    agent_id: str
    public_key: str  # Base64-encoded
    status: str
    created_at: datetime
    revoked_at: Optional[datetime] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Reputation (if available)
    total_transactions: int = 0
    successful_transactions: int = 0
    age_days: int = 0
    reputation_score: float = 0.0


# === Lease Schemas ===

class LeaseAcquireRequest(BaseModel):
    """Request to acquire a lease."""
    agent_id: str
    session_id: str
    timestamp: str  # ISO 8601
    nonce: str  # Hex-encoded
    ttl_seconds: int = Field(default=600, ge=60, le=3600)
    signature: str  # Hex-encoded signature


class LeaseResponse(BaseModel):
    """Lease acquisition response."""
    agent_id: str
    session_id: str
    lease_token: str  # PASETO token
    acquired_at: datetime
    expires_at: datetime
    sequence: int = 0


class LeaseRenewRequest(BaseModel):
    """Request to renew a lease."""
    session_id: str
    current_token: str
    ttl_seconds: int = Field(default=600, ge=60, le=3600)


class LeaseReleaseRequest(BaseModel):
    """Request to release a lease."""
    session_id: str
    token: str


class LeaseStatusResponse(BaseModel):
    """Lease status response."""
    agent_id: str
    active: bool
    session_id: Optional[str] = None
    expires_at: Optional[datetime] = None
    holder_session_id: Optional[str] = None  # If held by another


class LeaseError(BaseModel):
    """Lease error response."""
    error: str
    message: str
    holder_session_id: Optional[str] = None


# === State Chain Schemas ===

class StateEntryCreate(BaseModel):
    """Request to append a state entry."""
    agent_id: str
    sequence: int
    prev_hash: str  # Base64-encoded
    timestamp: str  # ISO 8601
    action_type: str
    action_summary: str
    action_data_hash: str  # Base64-encoded
    signature: str  # Base64-encoded
    entry_hash: str  # Base64-encoded


class StateEntryResponse(BaseModel):
    """State entry response."""
    agent_id: str
    sequence: int
    prev_hash: str
    entry_hash: str
    action_type: str
    action_summary: str
    action_data_hash: Optional[str] = None
    signature: str
    created_at: datetime


class StateHeadResponse(BaseModel):
    """Current state head response."""
    agent_id: str
    sequence: int
    entry_hash: str
    created_at: datetime


class StateHistoryResponse(BaseModel):
    """State history response."""
    agent_id: str
    entries: list[StateEntryResponse]
    total_count: int


# === Verification Schemas ===

class VerifyRequest(BaseModel):
    """Request to verify a proof bundle."""
    proof: dict[str, Any]  # Full proof bundle
    require_lease: bool = True
    min_reputation_score: Optional[float] = None


class VerifyResponse(BaseModel):
    """Verification result response."""
    valid: bool
    agent_id: str
    lease_active: bool = False
    state_verified: bool = False
    agent_info: Optional[AgentResponse] = None
    error_message: Optional[str] = None


# === API Key Schemas ===

class APIKeyCreate(BaseModel):
    """Request to create an API key."""
    name: str
    rate_limit_per_minute: int = Field(default=1000, ge=1, le=10000)


class APIKeyResponse(BaseModel):
    """API key creation response (only shown once)."""
    api_key: str  # Plain text key (only returned on creation)
    name: str
    created_at: datetime
    rate_limit_per_minute: int
