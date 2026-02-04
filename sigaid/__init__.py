"""
SigAid - Cryptographically secure agent identity protocol.

Usage:
    import sigaid
    
    # Create new agent
    client = sigaid.AgentClient.create()
    
    # Or wrap existing framework agent (one line!)
    agent = sigaid.wrap(my_langchain_agent)
"""

from sigaid.version import __version__
from sigaid.client.agent import AgentClient
from sigaid.identity.agent_id import AgentID
from sigaid.identity.keypair import KeyPair
from sigaid.verification.verifier import Verifier
from sigaid.verification.prover import ProofBundle
from sigaid.models.state import StateEntry
from sigaid.models.lease import Lease
from sigaid.exceptions import (
    SigAidError,
    LeaseError,
    LeaseHeldByAnotherInstance,
    LeaseExpired,
    StateChainError,
    ForkDetected,
    VerificationError,
    CryptoError,
)


def wrap(agent, *, api_key: str | None = None, agent_name: str | None = None):
    """
    Universal one-line wrapper. Auto-detects framework.
    
    Usage:
        import sigaid
        agent = sigaid.wrap(my_agent)
    
    Args:
        agent: Any supported agent (LangChain, CrewAI, AutoGen, etc.)
        api_key: SigAid API key (or use SIGAID_API_KEY env var)
        agent_name: Optional human-readable name for this agent
    
    Returns:
        Wrapped agent with same interface, now with SigAid identity
    """
    from sigaid.integrations.detect import detect_and_wrap
    return detect_and_wrap(agent, api_key=api_key, agent_name=agent_name)


__all__ = [
    "__version__",
    "AgentClient",
    "AgentID",
    "KeyPair",
    "Verifier",
    "ProofBundle",
    "StateEntry",
    "Lease",
    "wrap",
    # Exceptions
    "SigAidError",
    "LeaseError",
    "LeaseHeldByAnotherInstance",
    "LeaseExpired",
    "StateChainError",
    "ForkDetected",
    "VerificationError",
    "CryptoError",
]
