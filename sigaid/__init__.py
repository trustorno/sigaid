"""
SigAid - Cryptographically secure agent identity protocol.

Provides:
- Ed25519-based agent identity
- Exclusive leasing (prevents clone attacks)
- State chain continuity (tamper-evident history)
- Verification for third-party services
"""

from sigaid.version import __version__
from sigaid.identity.agent_id import AgentID
from sigaid.identity.keypair import KeyPair
from sigaid.client.agent import AgentClient
from sigaid.verification.verifier import Verifier
from sigaid.models.state import StateEntry, ActionType
from sigaid.models.proof import ProofBundle
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

__all__ = [
    "__version__",
    # Identity
    "AgentID",
    "KeyPair",
    # Client
    "AgentClient",
    "Verifier",
    # Models
    "StateEntry",
    "ActionType",
    "ProofBundle",
    "Lease",
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
