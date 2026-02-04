"""Exceptions for SigAid protocol."""


class SigAidError(Exception):
    """Base exception for all SigAid errors."""

    pass


# Crypto errors
class CryptoError(SigAidError):
    """Error in cryptographic operations."""

    pass


class InvalidSignature(CryptoError):
    """Signature verification failed."""

    pass


class InvalidKey(CryptoError):
    """Invalid key format or size."""

    pass


class TokenError(CryptoError):
    """Error with PASETO token."""

    pass


class TokenExpired(TokenError):
    """Token has expired."""

    pass


class TokenInvalid(TokenError):
    """Token is malformed or invalid."""

    pass


# Lease errors
class LeaseError(SigAidError):
    """Error related to lease operations."""

    pass


class LeaseHeldByAnotherInstance(LeaseError):
    """Another instance already holds the lease for this agent."""

    def __init__(self, agent_id: str, holder_session_id: str | None = None):
        self.agent_id = agent_id
        self.holder_session_id = holder_session_id
        msg = f"Lease for agent {agent_id} is held by another instance"
        if holder_session_id:
            msg += f" (session: {holder_session_id[:8]}...)"
        super().__init__(msg)


class LeaseExpired(LeaseError):
    """Lease has expired."""

    pass


class LeaseNotHeld(LeaseError):
    """Operation requires an active lease but none is held."""

    pass


class LeaseRenewalFailed(LeaseError):
    """Failed to renew the lease."""

    pass


# State chain errors
class StateChainError(SigAidError):
    """Error related to state chain operations."""

    pass


class ForkDetected(StateChainError):
    """Fork detected in state chain - indicates tampering or clone."""

    def __init__(self, agent_id: str, expected_seq: int, found_seq: int, message: str = ""):
        self.agent_id = agent_id
        self.expected_seq = expected_seq
        self.found_seq = found_seq
        msg = f"Fork detected for agent {agent_id}: expected seq {expected_seq}, found {found_seq}"
        if message:
            msg += f" - {message}"
        super().__init__(msg)


class InvalidStateEntry(StateChainError):
    """State entry is invalid (bad signature, hash, etc.)."""

    pass


class ChainIntegrityError(StateChainError):
    """State chain integrity check failed."""

    pass


# Verification errors
class VerificationError(SigAidError):
    """Error during verification."""

    pass


class ProofInvalid(VerificationError):
    """Proof bundle is invalid."""

    pass


class AgentRevoked(VerificationError):
    """Agent has been revoked."""

    pass


# Identity errors
class IdentityError(SigAidError):
    """Error related to agent identity."""

    pass


class InvalidAgentID(IdentityError):
    """Agent ID format is invalid."""

    pass


# Network errors
class NetworkError(SigAidError):
    """Network communication error."""

    pass


class AuthorityUnavailable(NetworkError):
    """Cannot reach the authority service."""

    pass
