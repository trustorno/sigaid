"""Exceptions for SigAid protocol."""


class SigAidError(Exception):
    """Base exception for all SigAid errors."""
    pass


# Crypto errors
class CryptoError(SigAidError):
    """Cryptographic operation failed."""
    pass


class InvalidSignature(CryptoError):
    """Signature verification failed."""
    pass


class InvalidKey(CryptoError):
    """Invalid key format or size."""
    pass


class KeyDerivationError(CryptoError):
    """Key derivation failed."""
    pass


# Lease errors
class LeaseError(SigAidError):
    """Lease operation failed."""
    pass


class LeaseHeldByAnotherInstance(LeaseError):
    """Another instance already holds the lease for this agent."""
    
    def __init__(self, agent_id: str, message: str | None = None):
        self.agent_id = agent_id
        super().__init__(
            message or f"Lease for agent {agent_id} is held by another instance"
        )


class LeaseExpired(LeaseError):
    """Lease has expired."""
    pass


class LeaseNotHeld(LeaseError):
    """Operation requires holding a lease, but no lease is held."""
    pass


class LeaseRenewalFailed(LeaseError):
    """Failed to renew lease."""
    pass


# Token errors
class TokenError(SigAidError):
    """Token operation failed."""
    pass


class TokenExpired(TokenError):
    """Token has expired."""
    pass


class TokenInvalid(TokenError):
    """Token is invalid or corrupted."""
    pass


# State chain errors
class StateChainError(SigAidError):
    """State chain operation failed."""
    pass


class ForkDetected(StateChainError):
    """State chain fork detected - potential clone or tampering."""
    
    def __init__(self, agent_id: str, expected_hash: bytes, actual_hash: bytes, sequence: int):
        self.agent_id = agent_id
        self.expected_hash = expected_hash
        self.actual_hash = actual_hash
        self.sequence = sequence
        super().__init__(
            f"Fork detected for agent {agent_id} at sequence {sequence}: "
            f"expected {expected_hash.hex()[:16]}..., got {actual_hash.hex()[:16]}..."
        )


class InvalidStateEntry(StateChainError):
    """State entry is invalid."""
    pass


class StateChainBroken(StateChainError):
    """State chain integrity is broken."""
    pass


# Verification errors
class VerificationError(SigAidError):
    """Verification failed."""
    pass


class ProofInvalid(VerificationError):
    """Proof bundle is invalid."""
    pass


class AgentNotFound(VerificationError):
    """Agent not found in registry."""
    pass


class AgentRevoked(VerificationError):
    """Agent has been revoked."""
    pass


# Identity errors
class IdentityError(SigAidError):
    """Identity operation failed."""
    pass


class InvalidAgentID(IdentityError):
    """Invalid AgentID format."""
    pass


# Network/API errors
class NetworkError(SigAidError):
    """Network communication error."""
    pass


class AuthorityError(NetworkError):
    """Error communicating with Authority service."""
    pass


class RateLimitExceeded(AuthorityError):
    """Rate limit exceeded."""
    pass
