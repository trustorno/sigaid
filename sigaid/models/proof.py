"""Proof bundle model for verification."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from sigaid.models.state import StateEntry
    from sigaid.crypto.keys import KeyPair


@dataclass
class ProofBundle:
    """Complete proof bundle for verification.

    A proof bundle contains everything needed for a third party
    to verify an agent's identity, current lease, and state history.

    Example:
        # Agent creates proof
        proof = ProofBundle.create(
            agent_id="aid_xxx",
            lease_token="v4.local.xxx",
            state_head=current_state,
            challenge=b"random_bytes",
            keypair=my_keypair,
        )

        # Service verifies proof
        verifier = Verifier(api_key="...")
        result = await verifier.verify(proof)
    """

    agent_id: str
    lease_token: str
    state_head: StateEntry | None
    challenge_response: bytes  # Signature over challenge
    timestamp: datetime
    signature: bytes  # Signature over entire bundle

    # Optional attestations
    user_attestation: bytes | None = None
    third_party_attestations: list[bytes] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        agent_id: str,
        lease_token: str,
        state_head: StateEntry | None,
        challenge: bytes,
        keypair: KeyPair,
        user_attestation: bytes | None = None,
        third_party_attestations: list[bytes] | None = None,
    ) -> ProofBundle:
        """Create a proof bundle with automatic signing.

        Args:
            agent_id: Agent identifier
            lease_token: Current lease token
            state_head: Current state chain head (or None if no history)
            challenge: Challenge bytes to sign
            keypair: Agent's keypair for signing
            user_attestation: Optional user authorization
            third_party_attestations: Optional third-party attestations

        Returns:
            Signed ProofBundle
        """
        from sigaid.constants import DOMAIN_VERIFY
        from sigaid.crypto.hashing import hash_bytes

        timestamp = datetime.now(timezone.utc)

        # Sign the challenge
        challenge_response = keypair.sign(challenge, domain=DOMAIN_VERIFY)

        # Create bundle content for signing
        bundle_content = cls._create_signable(
            agent_id=agent_id,
            lease_token=lease_token,
            state_head=state_head,
            challenge_response=challenge_response,
            timestamp=timestamp,
        )

        # Sign the entire bundle
        signature = keypair.sign(bundle_content, domain=DOMAIN_VERIFY)

        return cls(
            agent_id=agent_id,
            lease_token=lease_token,
            state_head=state_head,
            challenge_response=challenge_response,
            timestamp=timestamp,
            signature=signature,
            user_attestation=user_attestation,
            third_party_attestations=third_party_attestations or [],
        )

    @staticmethod
    def _create_signable(
        agent_id: str,
        lease_token: str,
        state_head: StateEntry | None,
        challenge_response: bytes,
        timestamp: datetime,
    ) -> bytes:
        """Create signable content for the bundle."""
        parts = [
            agent_id.encode("utf-8"),
            lease_token.encode("utf-8"),
            state_head.entry_hash if state_head else bytes(32),
            challenge_response,
            timestamp.isoformat().encode("utf-8"),
        ]
        return b"".join(parts)

    def to_signable_bytes(self) -> bytes:
        """Get canonical bytes for verification.

        Returns:
            Signable byte representation
        """
        return self._create_signable(
            agent_id=self.agent_id,
            lease_token=self.lease_token,
            state_head=self.state_head,
            challenge_response=self.challenge_response,
            timestamp=self.timestamp,
        )

    def verify_signature(self, public_key: bytes) -> bool:
        """Verify bundle signature.

        Args:
            public_key: 32-byte Ed25519 public key

        Returns:
            True if signature is valid
        """
        from sigaid.crypto.keys import public_key_from_bytes
        from sigaid.crypto.signing import verify_with_domain_safe
        from sigaid.constants import DOMAIN_VERIFY

        pk = public_key_from_bytes(public_key)
        signable = self.to_signable_bytes()
        return verify_with_domain_safe(pk, self.signature, signable, DOMAIN_VERIFY)

    def verify_challenge_response(self, public_key: bytes, challenge: bytes) -> bool:
        """Verify the challenge response.

        Args:
            public_key: 32-byte Ed25519 public key
            challenge: Original challenge bytes

        Returns:
            True if challenge response is valid
        """
        from sigaid.crypto.keys import public_key_from_bytes
        from sigaid.crypto.signing import verify_with_domain_safe
        from sigaid.constants import DOMAIN_VERIFY

        pk = public_key_from_bytes(public_key)
        return verify_with_domain_safe(pk, self.challenge_response, challenge, DOMAIN_VERIFY)

    def to_bytes(self) -> bytes:
        """Serialize to bytes.

        Returns:
            Serialized proof bundle
        """
        return json.dumps(self.to_dict()).encode("utf-8")

    @classmethod
    def from_bytes(cls, data: bytes) -> ProofBundle:
        """Deserialize from bytes.

        Args:
            data: Serialized proof bundle

        Returns:
            ProofBundle instance
        """
        return cls.from_dict(json.loads(data.decode("utf-8")))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        result = {
            "agent_id": self.agent_id,
            "lease_token": self.lease_token,
            "state_head": self.state_head.to_dict() if self.state_head else None,
            "challenge_response": base64.b64encode(self.challenge_response).decode("ascii"),
            "timestamp": self.timestamp.isoformat(),
            "signature": base64.b64encode(self.signature).decode("ascii"),
        }

        if self.user_attestation:
            result["user_attestation"] = base64.b64encode(self.user_attestation).decode("ascii")

        if self.third_party_attestations:
            result["third_party_attestations"] = [
                base64.b64encode(a).decode("ascii") for a in self.third_party_attestations
            ]

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProofBundle:
        """Create from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            ProofBundle instance
        """
        from sigaid.models.state import StateEntry

        state_head = None
        if data.get("state_head"):
            state_head = StateEntry.from_dict(data["state_head"])

        user_attestation = None
        if data.get("user_attestation"):
            user_attestation = base64.b64decode(data["user_attestation"])

        third_party_attestations = []
        if data.get("third_party_attestations"):
            third_party_attestations = [
                base64.b64decode(a) for a in data["third_party_attestations"]
            ]

        return cls(
            agent_id=data["agent_id"],
            lease_token=data["lease_token"],
            state_head=state_head,
            challenge_response=base64.b64decode(data["challenge_response"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            signature=base64.b64decode(data["signature"]),
            user_attestation=user_attestation,
            third_party_attestations=third_party_attestations,
        )

    def __repr__(self) -> str:
        """Debug representation."""
        return (
            f"ProofBundle(agent_id={self.agent_id!r}, "
            f"has_state={'yes' if self.state_head else 'no'}, "
            f"timestamp={self.timestamp.isoformat()})"
        )
