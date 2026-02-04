"""Proof bundle and verification result models."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from sigaid.constants import DOMAIN_VERIFY

if TYPE_CHECKING:
    from sigaid.models.state import StateEntry
    from sigaid.crypto.keys import KeyPair


@dataclass
class ProofBundle:
    """
    Complete proof bundle for agent verification.
    
    A ProofBundle contains everything needed to verify an agent's identity,
    current lease, and state chain integrity.
    
    Example:
        # Agent creates proof
        proof = client.create_proof(challenge=nonce)
        
        # Service verifies proof
        result = await verifier.verify(proof)
    """
    agent_id: str
    lease_token: str
    state_head: StateEntry | None
    challenge: bytes
    challenge_response: bytes  # Signature over challenge
    timestamp: datetime
    signature: bytes  # Signature over entire bundle
    
    # Optional attestations
    user_attestation: bytes | None = None
    third_party_attestations: list[bytes] = field(default_factory=list)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "agent_id": self.agent_id,
            "lease_token": self.lease_token,
            "state_head": self.state_head.to_dict() if self.state_head else None,
            "challenge": self.challenge.hex(),
            "challenge_response": self.challenge_response.hex(),
            "timestamp": self.timestamp.isoformat(),
            "signature": self.signature.hex(),
            "user_attestation": self.user_attestation.hex() if self.user_attestation else None,
            "third_party_attestations": [a.hex() for a in self.third_party_attestations],
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProofBundle:
        """Create from dictionary."""
        from sigaid.models.state import StateEntry
        
        return cls(
            agent_id=data["agent_id"],
            lease_token=data["lease_token"],
            state_head=StateEntry.from_dict(data["state_head"]) if data.get("state_head") else None,
            challenge=bytes.fromhex(data["challenge"]),
            challenge_response=bytes.fromhex(data["challenge_response"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            signature=bytes.fromhex(data["signature"]),
            user_attestation=bytes.fromhex(data["user_attestation"]) if data.get("user_attestation") else None,
            third_party_attestations=[bytes.fromhex(a) for a in data.get("third_party_attestations", [])],
        )
    
    def to_bytes(self) -> bytes:
        """Serialize to bytes for transmission."""
        return json.dumps(self.to_dict()).encode("utf-8")
    
    @classmethod
    def from_bytes(cls, data: bytes) -> ProofBundle:
        """Deserialize from bytes."""
        return cls.from_dict(json.loads(data.decode("utf-8")))
    
    def signable_bytes(self) -> bytes:
        """Get bytes that are signed for the bundle signature."""
        # All fields except the final signature
        parts = [
            self.agent_id.encode("utf-8"),
            self.lease_token.encode("utf-8"),
            self.state_head.entry_hash if self.state_head else bytes(32),
            self.challenge,
            self.challenge_response,
            self.timestamp.isoformat().encode("utf-8"),
        ]
        return b"".join(parts)


@dataclass
class ProofBundleBuilder:
    """
    Builder for creating proof bundles.
    
    Example:
        builder = ProofBundleBuilder(agent_id, keypair, lease_token, state_head)
        proof = builder.build(challenge=nonce)
    """
    agent_id: str
    keypair: KeyPair
    lease_token: str
    state_head: StateEntry | None
    
    def build(
        self,
        challenge: bytes,
        user_attestation: bytes | None = None,
        third_party_attestations: list[bytes] | None = None,
    ) -> ProofBundle:
        """
        Build and sign a proof bundle.
        
        Args:
            challenge: Challenge bytes from verifier
            user_attestation: Optional user attestation
            third_party_attestations: Optional third-party attestations
            
        Returns:
            Signed ProofBundle
        """
        timestamp = datetime.now(timezone.utc)
        
        # Sign challenge
        challenge_response = self.keypair.sign_with_domain(challenge, DOMAIN_VERIFY)
        
        # Build signable content
        signable = (
            self.agent_id.encode("utf-8") +
            self.lease_token.encode("utf-8") +
            (self.state_head.entry_hash if self.state_head else bytes(32)) +
            challenge +
            challenge_response +
            timestamp.isoformat().encode("utf-8")
        )
        
        # Sign bundle
        signature = self.keypair.sign_with_domain(signable, DOMAIN_VERIFY)
        
        return ProofBundle(
            agent_id=self.agent_id,
            lease_token=self.lease_token,
            state_head=self.state_head,
            challenge=challenge,
            challenge_response=challenge_response,
            timestamp=timestamp,
            signature=signature,
            user_attestation=user_attestation,
            third_party_attestations=third_party_attestations or [],
        )


@dataclass
class VerificationResult:
    """
    Result of proof bundle verification.
    
    Returned by Verifier after checking a ProofBundle.
    """
    valid: bool
    agent_id: str
    
    # Details (only populated if valid=True)
    lease_valid: bool = False
    lease_expires_at: datetime | None = None
    signature_valid: bool = False
    state_head_sequence: int | None = None
    state_head_hash: bytes | None = None
    
    # Reputation (if available)
    reputation_score: float | None = None
    
    # Error information (if valid=False)
    error_code: str | None = None
    error_message: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "valid": self.valid,
            "agent_id": self.agent_id,
            "lease_valid": self.lease_valid,
            "signature_valid": self.signature_valid,
        }
        
        if self.lease_expires_at:
            result["lease_expires_at"] = self.lease_expires_at.isoformat()
        if self.state_head_sequence is not None:
            result["state_head_sequence"] = self.state_head_sequence
        if self.state_head_hash:
            result["state_head_hash"] = self.state_head_hash.hex()
        if self.reputation_score is not None:
            result["reputation_score"] = self.reputation_score
        if self.error_code:
            result["error_code"] = self.error_code
            result["error_message"] = self.error_message
        
        return result
    
    @classmethod
    def success(
        cls,
        agent_id: str,
        lease_expires_at: datetime,
        state_head_sequence: int | None = None,
        state_head_hash: bytes | None = None,
        reputation_score: float | None = None,
    ) -> VerificationResult:
        """Create successful verification result."""
        return cls(
            valid=True,
            agent_id=agent_id,
            lease_valid=True,
            lease_expires_at=lease_expires_at,
            signature_valid=True,
            state_head_sequence=state_head_sequence,
            state_head_hash=state_head_hash,
            reputation_score=reputation_score,
        )
    
    @classmethod
    def failure(
        cls,
        agent_id: str,
        error_code: str,
        error_message: str,
    ) -> VerificationResult:
        """Create failed verification result."""
        return cls(
            valid=False,
            agent_id=agent_id,
            error_code=error_code,
            error_message=error_message,
        )
