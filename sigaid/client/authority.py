"""Authority service client."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from sigaid.client.http import HTTPClient
from sigaid.constants import DEFAULT_AUTHORITY_URL
from sigaid.exceptions import AgentNotFound, AgentRevoked, AuthorityError
from sigaid.models.agent import AgentInfo, AgentStatus
from sigaid.models.lease import Lease, LeaseRequest, LeaseResponse
from sigaid.models.proof import ProofBundle, VerificationResult
from sigaid.models.state import StateEntry

if TYPE_CHECKING:
    pass


class AuthorityClient:
    """
    Client for SigAid Authority service API.
    
    The Authority service manages:
    - Agent registration
    - Lease management
    - State chain storage
    - Verification
    
    Example:
        client = AuthorityClient(api_key="...")
        
        # Get agent info
        agent = await client.get_agent("aid_xxx")
        
        # Acquire lease
        lease = await client.acquire_lease(request, session_id, ttl)
    """
    
    def __init__(
        self,
        base_url: str = DEFAULT_AUTHORITY_URL,
        api_key: str | None = None,
        *,
        timeout: float = 30.0,
    ):
        """
        Initialize Authority client.
        
        Args:
            base_url: Authority service URL
            api_key: API key for authentication
            timeout: Request timeout
        """
        self._http = HTTPClient(base_url, api_key, timeout=timeout)
    
    # ========== Agent Operations ==========
    
    async def create_agent(
        self,
        public_key: bytes,
        name: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AgentInfo:
        """
        Register a new agent.
        
        Args:
            public_key: Agent's Ed25519 public key
            name: Optional human-readable name
            metadata: Optional metadata
            
        Returns:
            AgentInfo for the new agent
        """
        data = {
            "public_key": public_key.hex(),
            "name": name,
            "metadata": metadata or {},
        }
        
        response = await self._http.post("/v1/agents", data)
        return AgentInfo.from_dict(response)
    
    async def get_agent(self, agent_id: str) -> AgentInfo:
        """
        Get agent information.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentInfo
            
        Raises:
            AgentNotFound: If agent doesn't exist
        """
        try:
            response = await self._http.get(f"/v1/agents/{agent_id}")
            return AgentInfo.from_dict(response)
        except AuthorityError as e:
            if "not found" in str(e).lower():
                raise AgentNotFound(agent_id) from e
            raise
    
    async def revoke_agent(self, agent_id: str) -> None:
        """
        Revoke an agent.
        
        Args:
            agent_id: Agent identifier
        """
        await self._http.delete(f"/v1/agents/{agent_id}")
    
    # ========== Lease Operations ==========
    
    async def acquire_lease(
        self,
        request: LeaseRequest,
        session_id: str,
        ttl_seconds: int,
        timeout: float | None = None,
    ) -> LeaseResponse:
        """
        Acquire exclusive lease for an agent.
        
        Args:
            request: Signed lease request
            session_id: Unique session identifier
            ttl_seconds: Lease time-to-live
            timeout: Optional request timeout
            
        Returns:
            LeaseResponse with lease details
        """
        data = {
            "agent_id": request.agent_id,
            "session_id": session_id,
            "timestamp": request.timestamp.isoformat(),
            "nonce": request.nonce.hex(),
            "signature": request.signature.hex(),
            "ttl_seconds": ttl_seconds,
        }
        
        response = await self._http.post("/v1/leases", data)
        return LeaseResponse.from_dict(response)
    
    async def renew_lease(
        self,
        agent_id: str,
        session_id: str,
        current_token: str,
        ttl_seconds: int,
    ) -> LeaseResponse:
        """
        Renew an existing lease.
        
        Args:
            agent_id: Agent identifier
            session_id: Current session ID
            current_token: Current lease token
            ttl_seconds: New TTL
            
        Returns:
            LeaseResponse with renewed lease
        """
        data = {
            "session_id": session_id,
            "current_token": current_token,
            "ttl_seconds": ttl_seconds,
        }
        
        response = await self._http.put(f"/v1/leases/{agent_id}", data)
        return LeaseResponse.from_dict(response)
    
    async def release_lease(self, agent_id: str, session_id: str) -> None:
        """
        Release a lease before expiration.
        
        Args:
            agent_id: Agent identifier
            session_id: Current session ID
        """
        await self._http.delete(
            f"/v1/leases/{agent_id}",
            params={"session_id": session_id},
        )
    
    async def get_lease_status(self, agent_id: str) -> dict[str, Any]:
        """
        Get current lease status.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Lease status dict
        """
        return await self._http.get(f"/v1/leases/{agent_id}")
    
    # ========== State Operations ==========
    
    async def append_state(self, agent_id: str, entry: StateEntry) -> None:
        """
        Append state entry to agent's chain.
        
        Args:
            agent_id: Agent identifier
            entry: State entry to append
        """
        await self._http.post(f"/v1/state/{agent_id}", entry.to_dict())
    
    async def get_state_head(self, agent_id: str) -> StateEntry | None:
        """
        Get agent's current state head.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Latest StateEntry or None
        """
        try:
            response = await self._http.get(f"/v1/state/{agent_id}")
            if response.get("head"):
                return StateEntry.from_dict(response["head"])
            return None
        except AuthorityError as e:
            if "not found" in str(e).lower():
                return None
            raise
    
    async def get_state_history(
        self,
        agent_id: str,
        start_sequence: int = 0,
        end_sequence: int | None = None,
        limit: int = 100,
    ) -> list[StateEntry]:
        """
        Get agent's state history.
        
        Args:
            agent_id: Agent identifier
            start_sequence: Starting sequence (inclusive)
            end_sequence: Ending sequence (exclusive)
            limit: Maximum entries to return
            
        Returns:
            List of StateEntry
        """
        params = {
            "start": start_sequence,
            "limit": limit,
        }
        if end_sequence is not None:
            params["end"] = end_sequence
        
        response = await self._http.get(f"/v1/state/{agent_id}/history", params)
        return [StateEntry.from_dict(e) for e in response.get("entries", [])]
    
    # ========== Verification Operations ==========
    
    async def verify_proof(
        self,
        proof: ProofBundle,
        *,
        require_lease: bool = True,
    ) -> VerificationResult:
        """
        Verify a proof bundle via Authority.
        
        Args:
            proof: ProofBundle to verify
            require_lease: Require active lease
            
        Returns:
            VerificationResult
        """
        data = {
            "proof": proof.to_dict(),
            "require_lease": require_lease,
        }
        
        response = await self._http.post("/v1/verify", data)
        
        if response.get("valid"):
            return VerificationResult.success(
                agent_id=response["agent_id"],
                lease_expires_at=datetime.fromisoformat(response["lease_expires_at"]) if response.get("lease_expires_at") else datetime.now(),
                state_head_sequence=response.get("state_head_sequence"),
                state_head_hash=bytes.fromhex(response["state_head_hash"]) if response.get("state_head_hash") else None,
                reputation_score=response.get("reputation_score"),
            )
        else:
            return VerificationResult.failure(
                agent_id=response.get("agent_id", proof.agent_id),
                error_code=response.get("error_code", "unknown"),
                error_message=response.get("error_message", "Verification failed"),
            )
    
    async def close(self) -> None:
        """Close the client and release resources."""
        await self._http.close()
