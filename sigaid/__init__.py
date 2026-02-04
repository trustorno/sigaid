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


def wrap(
    agent,
    *,
    authority_url: str | None = None,
    api_key: str | None = None,
    agent_name: str | None = None,
):
    """
    Universal one-line wrapper. Auto-detects framework.

    Usage:
        import sigaid

        # Using hosted service (default)
        agent = sigaid.wrap(my_agent, api_key="sk_xxx")

        # Using self-hosted authority
        agent = sigaid.wrap(
            my_agent,
            authority_url="https://my-authority.com",
            api_key="sk_xxx"
        )

        # Using environment variables
        # SIGAID_AUTHORITY_URL=https://my-authority.com
        # SIGAID_API_KEY=sk_xxx
        agent = sigaid.wrap(my_agent)

    Args:
        agent: Any supported agent (LangChain, CrewAI, AutoGen, etc.)
        authority_url: Authority service URL (or SIGAID_AUTHORITY_URL env var)
                      Defaults to https://api.sigaid.com
        api_key: SigAid API key (or SIGAID_API_KEY env var)
        agent_name: Optional human-readable name for this agent

    Returns:
        Wrapped agent with same interface, now with SigAid identity
    """
    from sigaid.integrations.detect import detect_and_wrap
    return detect_and_wrap(
        agent,
        authority_url=authority_url,
        api_key=api_key,
        agent_name=agent_name,
    )


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
