"""Liveness verification for agent face widgets.

Provides a simplified challenge-response protocol for verifying
that an agent is live and authentic. Used by embeddable widgets.

The protocol:
1. Widget requests a challenge from the verifier
2. Widget sends challenge to agent
3. Agent signs challenge with private key
4. Widget sends signature to verifier
5. Verifier confirms and returns agent profile + status
"""

from __future__ import annotations

import hashlib
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any

from sigaid.identity.agent_id import AgentID
from sigaid.identity.agent_profile import AgentProfile
from sigaid.constants import DOMAIN_LIVENESS, ED25519_SIGNATURE_SIZE
from sigaid.exceptions import VerificationError

if TYPE_CHECKING:
    from sigaid.crypto.keys import KeyPair


class LivenessStatus(str, Enum):
    """Status of liveness verification."""

    LIVE = "live"           # Verified in last 30 seconds
    FRESH = "fresh"         # Verified in last 5 minutes
    CACHED = "cached"       # Agent offline, showing cached data
    FAILED = "failed"       # Verification failed
    LOADING = "loading"     # Verification in progress
    UNAVAILABLE = "unavailable"  # Service unavailable


# Cache TTLs in seconds
LIVE_TTL = 30
FRESH_TTL = 300  # 5 minutes
CACHE_TTL = 3600  # 1 hour max cache


@dataclass
class LivenessChallenge:
    """Challenge for liveness verification."""

    challenge_id: str
    nonce: bytes
    timestamp: datetime
    expires_at: datetime
    agent_id: str | None = None  # Optional: lock to specific agent

    @classmethod
    def create(
        cls,
        agent_id: str | None = None,
        ttl_seconds: int = 60,
    ) -> LivenessChallenge:
        """Create a new challenge.

        Args:
            agent_id: Optional agent ID to lock challenge to
            ttl_seconds: Time until challenge expires

        Returns:
            New challenge
        """
        now = datetime.now(timezone.utc)
        nonce = secrets.token_bytes(32)
        challenge_id = hashlib.blake2b(nonce, digest_size=16).hexdigest()

        return cls(
            challenge_id=challenge_id,
            nonce=nonce,
            timestamp=now,
            expires_at=datetime.fromtimestamp(
                now.timestamp() + ttl_seconds,
                tz=timezone.utc
            ),
            agent_id=agent_id,
        )

    @property
    def is_expired(self) -> bool:
        """Check if challenge has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    def signing_data(self, agent_id: str) -> bytes:
        """Get the data that the agent should sign.

        Args:
            agent_id: Agent's ID

        Returns:
            Bytes to sign
        """
        # Include agent_id to prevent replay across agents
        return self.nonce + agent_id.encode('utf-8')

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        import base64
        return {
            "challenge_id": self.challenge_id,
            "nonce": base64.b64encode(self.nonce).decode('ascii'),
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "agent_id": self.agent_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LivenessChallenge:
        """Deserialize from dictionary."""
        import base64
        return cls(
            challenge_id=data["challenge_id"],
            nonce=base64.b64decode(data["nonce"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
            agent_id=data.get("agent_id"),
        )


@dataclass
class LivenessResponse:
    """Response to a liveness challenge (from agent)."""

    challenge_id: str
    agent_id: str
    signature: bytes
    profile: AgentProfile | None = None

    @classmethod
    def create(
        cls,
        challenge: LivenessChallenge,
        keypair: KeyPair,
        profile: AgentProfile | None = None,
    ) -> LivenessResponse:
        """Create a signed response to a challenge.

        Args:
            challenge: The challenge to respond to
            keypair: Agent's keypair for signing
            profile: Optional agent profile

        Returns:
            Signed response
        """
        agent_id = str(keypair.to_agent_id())
        signing_data = challenge.signing_data(agent_id)
        signature = keypair.sign(signing_data, domain=DOMAIN_LIVENESS)

        return cls(
            challenge_id=challenge.challenge_id,
            agent_id=agent_id,
            signature=signature,
            profile=profile,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        import base64
        result = {
            "challenge_id": self.challenge_id,
            "agent_id": self.agent_id,
            "signature": base64.b64encode(self.signature).decode('ascii'),
        }
        if self.profile:
            result["profile"] = self.profile.to_dict()
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LivenessResponse:
        """Deserialize from dictionary."""
        import base64
        profile = None
        if data.get("profile"):
            profile = AgentProfile.from_dict(data["profile"])
        return cls(
            challenge_id=data["challenge_id"],
            agent_id=data["agent_id"],
            signature=base64.b64decode(data["signature"]),
            profile=profile,
        )


@dataclass
class LivenessResult:
    """Result of liveness verification."""

    status: LivenessStatus
    agent_id: str
    profile: AgentProfile | None = None
    verified_at: datetime | None = None
    cache_until: datetime | None = None
    error: str | None = None

    @property
    def is_verified(self) -> bool:
        """Check if agent is verified (live or fresh)."""
        return self.status in (LivenessStatus.LIVE, LivenessStatus.FRESH)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        result = {
            "status": self.status.value,
            "agent_id": self.agent_id,
            "is_verified": self.is_verified,
        }
        if self.profile:
            result["profile"] = self.profile.to_dict()
        if self.verified_at:
            result["verified_at"] = self.verified_at.isoformat()
        if self.cache_until:
            result["cache_until"] = self.cache_until.isoformat()
        if self.error:
            result["error"] = self.error
        return result


class LivenessVerifier:
    """Verifies agent liveness for widgets.

    Manages challenge-response protocol and caching.

    Example:
        verifier = LivenessVerifier()

        # Create challenge
        challenge = verifier.create_challenge()

        # Agent signs challenge (on agent side)
        response = LivenessResponse.create(challenge, keypair, profile)

        # Verify response
        result = verifier.verify(challenge, response)
        if result.is_verified:
            print(f"Agent {result.profile.name} is live!")
    """

    def __init__(
        self,
        challenge_ttl_seconds: int = 60,
        cache_ttl_seconds: int = CACHE_TTL,
    ):
        """Initialize verifier.

        Args:
            challenge_ttl_seconds: How long challenges are valid
            cache_ttl_seconds: How long to cache verified results
        """
        self._challenge_ttl = challenge_ttl_seconds
        self._cache_ttl = cache_ttl_seconds
        self._pending_challenges: dict[str, LivenessChallenge] = {}
        self._verified_cache: dict[str, tuple[LivenessResult, float]] = {}

    def create_challenge(self, agent_id: str | None = None) -> LivenessChallenge:
        """Create a new liveness challenge.

        Args:
            agent_id: Optional agent ID to lock challenge to

        Returns:
            Challenge to send to agent
        """
        challenge = LivenessChallenge.create(
            agent_id=agent_id,
            ttl_seconds=self._challenge_ttl,
        )
        self._pending_challenges[challenge.challenge_id] = challenge
        self._cleanup_expired_challenges()
        return challenge

    def verify(
        self,
        challenge: LivenessChallenge,
        response: LivenessResponse,
    ) -> LivenessResult:
        """Verify a liveness response.

        Args:
            challenge: Original challenge
            response: Agent's response

        Returns:
            Verification result
        """
        now = datetime.now(timezone.utc)

        # Check challenge is valid
        if challenge.challenge_id != response.challenge_id:
            return LivenessResult(
                status=LivenessStatus.FAILED,
                agent_id=response.agent_id,
                error="Challenge ID mismatch",
            )

        if challenge.is_expired:
            return LivenessResult(
                status=LivenessStatus.FAILED,
                agent_id=response.agent_id,
                error="Challenge expired",
            )

        # Check agent_id matches if challenge was locked
        if challenge.agent_id and challenge.agent_id != response.agent_id:
            return LivenessResult(
                status=LivenessStatus.FAILED,
                agent_id=response.agent_id,
                error="Agent ID mismatch",
            )

        # Verify signature
        try:
            aid = AgentID(response.agent_id)
            public_key = aid.to_public_key()

            signing_data = challenge.signing_data(response.agent_id)

            # Add domain separation (matches KeyPair.sign)
            domain_bytes = DOMAIN_LIVENESS.encode('utf-8')
            prefixed_data = len(domain_bytes).to_bytes(2, 'big') + domain_bytes + signing_data

            public_key.verify(response.signature, prefixed_data)
        except Exception as e:
            return LivenessResult(
                status=LivenessStatus.FAILED,
                agent_id=response.agent_id,
                error=f"Signature verification failed: {e}",
            )

        # Remove used challenge
        self._pending_challenges.pop(challenge.challenge_id, None)

        # Get or create profile
        profile = response.profile
        if not profile:
            profile = AgentProfile.from_agent_id(response.agent_id)

        # Create successful result
        result = LivenessResult(
            status=LivenessStatus.LIVE,
            agent_id=response.agent_id,
            profile=profile,
            verified_at=now,
            cache_until=datetime.fromtimestamp(
                now.timestamp() + self._cache_ttl,
                tz=timezone.utc
            ),
        )

        # Cache result
        self._verified_cache[response.agent_id] = (result, time.time())

        return result

    def get_cached_status(self, agent_id: str) -> LivenessResult | None:
        """Get cached verification status for an agent.

        Args:
            agent_id: Agent ID to check

        Returns:
            Cached result with updated status, or None
        """
        if agent_id not in self._verified_cache:
            return None

        result, verified_time = self._verified_cache[agent_id]
        elapsed = time.time() - verified_time

        # Update status based on age
        if elapsed < LIVE_TTL:
            result.status = LivenessStatus.LIVE
        elif elapsed < FRESH_TTL:
            result.status = LivenessStatus.FRESH
        elif elapsed < self._cache_ttl:
            result.status = LivenessStatus.CACHED
        else:
            # Cache expired
            del self._verified_cache[agent_id]
            return None

        return result

    def _cleanup_expired_challenges(self) -> None:
        """Remove expired challenges."""
        now = datetime.now(timezone.utc)
        expired = [
            cid for cid, c in self._pending_challenges.items()
            if c.expires_at < now
        ]
        for cid in expired:
            del self._pending_challenges[cid]


class LivenessProver:
    """Creates liveness proofs for agents.

    Used by agents to respond to liveness challenges.

    Example:
        prover = LivenessProver(keypair, profile)

        # Respond to a challenge
        response = prover.respond(challenge)

        # Send response to verifier
    """

    def __init__(
        self,
        keypair: KeyPair,
        profile: AgentProfile | None = None,
    ):
        """Initialize prover.

        Args:
            keypair: Agent's keypair
            profile: Optional agent profile (will be created if not provided)
        """
        self._keypair = keypair
        self._profile = profile

    @property
    def agent_id(self) -> str:
        """Get agent ID."""
        return str(self._keypair.to_agent_id())

    @property
    def profile(self) -> AgentProfile:
        """Get or create agent profile."""
        if not self._profile:
            self._profile = AgentProfile.from_agent_id(self.agent_id)
        return self._profile

    def set_profile(self, profile: AgentProfile) -> None:
        """Set agent profile."""
        self._profile = profile

    def respond(self, challenge: LivenessChallenge) -> LivenessResponse:
        """Create a signed response to a liveness challenge.

        Args:
            challenge: Challenge from verifier

        Returns:
            Signed response
        """
        return LivenessResponse.create(
            challenge=challenge,
            keypair=self._keypair,
            profile=self.profile,
        )

    def sign_challenge_bytes(self, nonce: bytes) -> bytes:
        """Sign raw challenge bytes directly.

        Used for lower-level integrations.

        Args:
            nonce: Challenge nonce bytes

        Returns:
            Signature
        """
        signing_data = nonce + self.agent_id.encode('utf-8')
        return self._keypair.sign(signing_data, domain=DOMAIN_LIVENESS)
