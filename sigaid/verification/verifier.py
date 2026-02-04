"""Proof verification for services."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from sigaid.models.proof import ProofBundle
from sigaid.models.agent import AgentInfo, VerificationResult
from sigaid.identity.agent_id import AgentID
from sigaid.state.verification import ChainVerifier
from sigaid.exceptions import ProofInvalid, VerificationError

if TYPE_CHECKING:
    from sigaid.client.http import HttpClient


class Verifier:
    """Verifies agent proof bundles.

    The Verifier is used by services that need to verify agent identity
    before allowing them to perform actions.

    Example:
        verifier = Verifier(api_key="...")

        # Generate challenge
        challenge = verifier.create_challenge()

        # Agent responds with proof
        proof = await agent.create_proof(challenge)

        # Verify the proof
        result = await verifier.verify(proof, challenge)
        if result.valid:
            print(f"Agent {result.agent_id} verified!")
            print(f"Reputation: {result.agent_info.reputation_score}")
    """

    def __init__(
        self,
        api_key: str | None = None,
        authority_url: str = "https://api.sigaid.com",
        http_client: HttpClient | None = None,
        cache_ttl_seconds: int = 300,
    ):
        """Initialize verifier.

        Args:
            api_key: API key for Authority service
            authority_url: URL of Authority service
            http_client: Optional pre-configured HTTP client
            cache_ttl_seconds: TTL for verification cache
        """
        self._api_key = api_key
        self._authority_url = authority_url
        self._http_client = http_client
        self._cache_ttl = cache_ttl_seconds
        self._chain_verifier = ChainVerifier()
        self._verification_cache: dict[str, tuple[VerificationResult, datetime]] = {}

    def create_challenge(self, length: int = 32) -> bytes:
        """Create a random challenge for agents to sign.

        Args:
            length: Challenge length in bytes

        Returns:
            Random challenge bytes
        """
        return secrets.token_bytes(length)

    async def verify(
        self,
        proof: ProofBundle,
        challenge: bytes,
        *,
        require_lease: bool = True,
        min_reputation_score: float | None = None,
        max_state_age: timedelta | None = None,
    ) -> VerificationResult:
        """Verify an agent proof bundle.

        Args:
            proof: Proof bundle from agent
            challenge: Original challenge bytes
            require_lease: Whether to require an active lease
            min_reputation_score: Minimum required reputation score
            max_state_age: Maximum age of state head

        Returns:
            VerificationResult with details

        Raises:
            VerificationError: If verification fails critically
        """
        result = VerificationResult(
            valid=False,
            agent_id=proof.agent_id,
        )

        try:
            # Validate agent ID format
            agent_id = AgentID(proof.agent_id)
            public_key = agent_id.to_public_key_bytes()

            # Verify challenge response
            result.challenge_valid = proof.verify_challenge_response(public_key, challenge)
            if not result.challenge_valid:
                result.error_message = "Challenge response invalid"
                return result

            # Verify bundle signature
            result.signature_valid = proof.verify_signature(public_key)
            if not result.signature_valid:
                result.error_message = "Bundle signature invalid"
                return result

            # Verify state chain if present
            if proof.state_head:
                try:
                    self._chain_verifier.verify_head(proof.agent_id, proof.state_head)
                    result.chain_valid = True
                    result.state_verified = True
                except Exception as e:
                    result.error_message = f"State chain error: {e}"
                    return result
            else:
                result.chain_valid = True  # No chain to verify

            # Check state age if required
            if max_state_age and proof.state_head:
                state_age = datetime.now(timezone.utc) - proof.state_head.timestamp
                if state_age > max_state_age:
                    result.error_message = f"State too old: {state_age}"
                    return result

            # Verify with Authority if available
            if self._http_client and self._api_key:
                authority_result = await self._verify_with_authority(
                    proof, require_lease, min_reputation_score
                )
                result.lease_active = authority_result.get("lease_active", False)
                result.agent_info = authority_result.get("agent_info")

                if require_lease and not result.lease_active:
                    result.error_message = "Lease not active"
                    return result

                if min_reputation_score and result.agent_info:
                    if result.agent_info.reputation_score < min_reputation_score:
                        result.error_message = (
                            f"Reputation {result.agent_info.reputation_score} "
                            f"below minimum {min_reputation_score}"
                        )
                        return result
            else:
                # Offline mode - can't verify lease
                if require_lease:
                    result.lease_active = bool(proof.lease_token)
                else:
                    result.lease_active = True

            result.valid = True
            return result

        except Exception as e:
            result.error_message = str(e)
            return result

    async def _verify_with_authority(
        self,
        proof: ProofBundle,
        require_lease: bool,
        min_reputation_score: float | None,
    ) -> dict[str, Any]:
        """Verify proof with Authority service."""
        response = await self._http_client.post(
            "/v1/verify",
            json={
                "proof": proof.to_dict(),
                "require_lease": require_lease,
                "min_reputation_score": min_reputation_score,
            },
            headers={"Authorization": f"Bearer {self._api_key}"},
        )

        result = {
            "lease_active": response.get("lease_active", False),
        }

        if response.get("agent_info"):
            result["agent_info"] = AgentInfo.from_dict(response["agent_info"])

        return result

    def verify_offline(
        self,
        proof: ProofBundle,
        challenge: bytes,
        known_state_head: StateEntry | None = None,
    ) -> VerificationResult:
        """Verify proof without calling Authority.

        Only verifies cryptographic signatures and state chain.
        Does NOT verify lease is currently active.

        Args:
            proof: Proof bundle from agent
            challenge: Original challenge bytes
            known_state_head: Previously known state head for fork detection

        Returns:
            VerificationResult (note: lease_active will always be False)
        """
        from sigaid.models.state import StateEntry

        result = VerificationResult(
            valid=False,
            agent_id=proof.agent_id,
            lease_active=False,  # Can't verify without Authority
        )

        try:
            # Validate agent ID format
            agent_id = AgentID(proof.agent_id)
            public_key = agent_id.to_public_key_bytes()

            # Verify challenge response
            result.challenge_valid = proof.verify_challenge_response(public_key, challenge)
            if not result.challenge_valid:
                result.error_message = "Challenge response invalid"
                return result

            # Verify bundle signature
            result.signature_valid = proof.verify_signature(public_key)
            if not result.signature_valid:
                result.error_message = "Bundle signature invalid"
                return result

            # Verify state chain
            if proof.state_head:
                if not proof.state_head.verify_signature(public_key):
                    result.error_message = "State entry signature invalid"
                    return result

                if not proof.state_head.verify_hash():
                    result.error_message = "State entry hash invalid"
                    return result

                # Check for fork if we have known state
                if known_state_head:
                    self._chain_verifier.record_head(proof.agent_id, known_state_head)
                    self._chain_verifier.verify_head(proof.agent_id, proof.state_head)

                result.chain_valid = True
                result.state_verified = True
            else:
                result.chain_valid = True

            result.valid = True
            return result

        except Exception as e:
            result.error_message = str(e)
            return result

    def record_state_head(self, agent_id: str, state_head: StateEntry) -> None:
        """Record known state head for fork detection.

        Args:
            agent_id: Agent identifier
            state_head: State entry to record
        """
        from sigaid.models.state import StateEntry

        self._chain_verifier.record_head(agent_id, state_head)


# Import for type hints
from sigaid.models.state import StateEntry
