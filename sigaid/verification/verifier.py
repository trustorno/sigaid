"""Verification service for proof bundles."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from sigaid.constants import DEFAULT_AUTHORITY_URL, DOMAIN_VERIFY
from sigaid.crypto.signing import verify_with_domain
from sigaid.exceptions import (
    AgentNotFound,
    AgentRevoked,
    ProofInvalid,
    VerificationError,
)
from sigaid.models.proof import ProofBundle, VerificationResult
from sigaid.state.verification import StateVerifier

if TYPE_CHECKING:
    from sigaid.client.authority import AuthorityClient


class Verifier:
    """
    Verification service for proof bundles.
    
    Used by services to verify agent identity, lease status, and state integrity.
    
    Example:
        verifier = Verifier(api_key="...")
        
        # Verify proof from agent
        result = await verifier.verify(proof_bundle)
        
        if result.valid:
            print(f"Agent {result.agent_id} verified")
            print(f"Lease expires: {result.lease_expires_at}")
            print(f"Reputation: {result.reputation_score}")
        else:
            print(f"Verification failed: {result.error_message}")
    """
    
    def __init__(
        self,
        api_key: str | None = None,
        authority_url: str = DEFAULT_AUTHORITY_URL,
        *,
        cache_ttl: int = 300,
        offline_mode: bool = False,
    ):
        """
        Initialize verifier.
        
        Args:
            api_key: SigAid API key for Authority calls
            authority_url: Authority service URL
            cache_ttl: Cache TTL for verification results
            offline_mode: If True, only do offline verification
        """
        self._api_key = api_key
        self._authority_url = authority_url
        self._cache_ttl = cache_ttl
        self._offline_mode = offline_mode
        
        self._authority: AuthorityClient | None = None
        self._state_verifier = StateVerifier()
        
        # Simple TTL cache: agent_id -> (result, expiry)
        self._cache: dict[str, tuple[VerificationResult, datetime]] = {}
    
    async def _get_authority(self) -> AuthorityClient:
        """Get or create Authority client."""
        if self._authority is None:
            from sigaid.client.authority import AuthorityClient
            self._authority = AuthorityClient(
                base_url=self._authority_url,
                api_key=self._api_key,
            )
        return self._authority
    
    async def verify(
        self,
        proof: ProofBundle,
        *,
        require_lease: bool = True,
        min_reputation_score: float | None = None,
        max_state_age: timedelta | None = None,
        use_cache: bool = True,
    ) -> VerificationResult:
        """
        Verify agent proof bundle.
        
        Performs:
        1. Signature verification (offline)
        2. Lease verification (via Authority)
        3. State chain verification
        4. Optional reputation check
        
        Args:
            proof: ProofBundle from agent
            require_lease: Require active lease (default True)
            min_reputation_score: Minimum required reputation (0.0-1.0)
            max_state_age: Maximum age of state head
            use_cache: Use cached results (default True)
            
        Returns:
            VerificationResult with details
        """
        # Check cache
        if use_cache:
            cached = self._get_cached(proof.agent_id)
            if cached is not None:
                return cached
        
        try:
            # Step 1: Offline signature verification
            if not await self._verify_signatures(proof):
                return self._cache_and_return(VerificationResult.failure(
                    proof.agent_id,
                    "invalid_signature",
                    "Proof bundle signature verification failed",
                ))
            
            # Step 2: Online verification via Authority
            if not self._offline_mode:
                result = await self._verify_online(proof, require_lease)
                if not result.valid:
                    return self._cache_and_return(result)
            else:
                result = VerificationResult(
                    valid=True,
                    agent_id=proof.agent_id,
                    signature_valid=True,
                )
            
            # Step 3: State verification
            if proof.state_head:
                try:
                    # Get agent's public key
                    authority = await self._get_authority()
                    agent_info = await authority.get_agent(proof.agent_id)
                    
                    self._state_verifier.verify_head(
                        proof.agent_id,
                        proof.state_head,
                        agent_info.public_key,
                        max_age=max_state_age,
                    )
                    
                    result = VerificationResult(
                        valid=True,
                        agent_id=proof.agent_id,
                        lease_valid=result.lease_valid,
                        lease_expires_at=result.lease_expires_at,
                        signature_valid=True,
                        state_head_sequence=proof.state_head.sequence,
                        state_head_hash=proof.state_head.entry_hash,
                        reputation_score=result.reputation_score,
                    )
                except Exception as e:
                    return self._cache_and_return(VerificationResult.failure(
                        proof.agent_id,
                        "state_verification_failed",
                        f"State verification failed: {e}",
                    ))
            
            # Step 4: Reputation check
            if min_reputation_score is not None:
                if result.reputation_score is None or result.reputation_score < min_reputation_score:
                    return self._cache_and_return(VerificationResult.failure(
                        proof.agent_id,
                        "insufficient_reputation",
                        f"Reputation {result.reputation_score} < {min_reputation_score}",
                    ))
            
            return self._cache_and_return(result)
        
        except Exception as e:
            return self._cache_and_return(VerificationResult.failure(
                proof.agent_id,
                "verification_error",
                f"Verification error: {e}",
            ))
    
    async def verify_offline(
        self,
        proof: ProofBundle,
        public_key: bytes,
        *,
        known_state_head: tuple[int, bytes] | None = None,
    ) -> VerificationResult:
        """
        Verify proof bundle offline (no Authority calls).
        
        Only verifies signatures and state chain integrity.
        Does NOT verify lease is currently active.
        
        Args:
            proof: ProofBundle from agent
            public_key: Agent's known public key
            known_state_head: Known (sequence, hash) for fork detection
            
        Returns:
            VerificationResult
        """
        # Verify challenge response
        challenge_valid = verify_with_domain(
            public_key,
            proof.challenge_response,
            proof.challenge,
            DOMAIN_VERIFY,
        )
        
        if not challenge_valid:
            return VerificationResult.failure(
                proof.agent_id,
                "invalid_challenge_response",
                "Challenge response signature invalid",
            )
        
        # Verify bundle signature
        bundle_valid = verify_with_domain(
            public_key,
            proof.signature,
            proof.signable_bytes(),
            DOMAIN_VERIFY,
        )
        
        if not bundle_valid:
            return VerificationResult.failure(
                proof.agent_id,
                "invalid_bundle_signature",
                "Bundle signature invalid",
            )
        
        # Verify state head if provided
        if proof.state_head:
            if not proof.state_head.verify_signature(public_key):
                return VerificationResult.failure(
                    proof.agent_id,
                    "invalid_state_signature",
                    "State head signature invalid",
                )
            
            # Check against known head
            if known_state_head:
                known_seq, known_hash = known_state_head
                if proof.state_head.sequence == known_seq:
                    if proof.state_head.entry_hash != known_hash:
                        return VerificationResult.failure(
                            proof.agent_id,
                            "fork_detected",
                            f"State fork at sequence {known_seq}",
                        )
        
        return VerificationResult.success(
            agent_id=proof.agent_id,
            lease_expires_at=datetime.now(timezone.utc),  # Unknown without Authority
            state_head_sequence=proof.state_head.sequence if proof.state_head else None,
            state_head_hash=proof.state_head.entry_hash if proof.state_head else None,
        )
    
    async def _verify_signatures(self, proof: ProofBundle) -> bool:
        """Verify proof bundle signatures."""
        # We need the agent's public key from Authority
        try:
            authority = await self._get_authority()
            agent_info = await authority.get_agent(proof.agent_id)
            public_key = agent_info.public_key
        except Exception:
            # Can't get public key - fail
            return False
        
        # Verify challenge response
        if not verify_with_domain(
            public_key,
            proof.challenge_response,
            proof.challenge,
            DOMAIN_VERIFY,
        ):
            return False
        
        # Verify bundle signature
        if not verify_with_domain(
            public_key,
            proof.signature,
            proof.signable_bytes(),
            DOMAIN_VERIFY,
        ):
            return False
        
        return True
    
    async def _verify_online(
        self,
        proof: ProofBundle,
        require_lease: bool,
    ) -> VerificationResult:
        """Verify via Authority service."""
        authority = await self._get_authority()
        
        try:
            result = await authority.verify_proof(proof, require_lease=require_lease)
            return result
        except AgentNotFound:
            return VerificationResult.failure(
                proof.agent_id,
                "agent_not_found",
                "Agent not registered",
            )
        except AgentRevoked:
            return VerificationResult.failure(
                proof.agent_id,
                "agent_revoked",
                "Agent has been revoked",
            )
        except Exception as e:
            return VerificationResult.failure(
                proof.agent_id,
                "authority_error",
                f"Authority verification failed: {e}",
            )
    
    def _get_cached(self, agent_id: str) -> VerificationResult | None:
        """Get cached result if valid."""
        entry = self._cache.get(agent_id)
        if entry is None:
            return None
        
        result, expiry = entry
        if datetime.now(timezone.utc) > expiry:
            del self._cache[agent_id]
            return None
        
        return result
    
    def _cache_and_return(self, result: VerificationResult) -> VerificationResult:
        """Cache result and return it."""
        expiry = datetime.now(timezone.utc) + timedelta(seconds=self._cache_ttl)
        self._cache[result.agent_id] = (result, expiry)
        return result
    
    def clear_cache(self, agent_id: str | None = None) -> None:
        """
        Clear verification cache.
        
        Args:
            agent_id: Specific agent to clear, or None for all
        """
        if agent_id:
            self._cache.pop(agent_id, None)
        else:
            self._cache.clear()
    
    async def close(self) -> None:
        """Close verifier and release resources."""
        if self._authority:
            await self._authority.close()
            self._authority = None


# Re-export
VerificationResult = VerificationResult
