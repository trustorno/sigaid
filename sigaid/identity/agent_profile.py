"""Agent profile with naming and visual identity.

Extends AgentID with human-readable names and visual faces.
Names are signed by the agent's private key to prove ownership.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sigaid.identity.agent_id import AgentID
from sigaid.identity.agent_face import AgentFace
from sigaid.constants import ED25519_SIGNATURE_SIZE, DOMAIN_PROFILE
from sigaid.exceptions import InvalidSignature, ValidationError

if TYPE_CHECKING:
    from sigaid.crypto.keys import KeyPair

# Name constraints
MIN_NAME_LENGTH = 1
MAX_NAME_LENGTH = 50
NAME_PATTERN = re.compile(r'^[\w\s\-\.]+$', re.UNICODE)


@dataclass
class AgentProfile:
    """Agent identity with human-readable name and visual face.

    The profile extends the cryptographic AgentID with:
    - A display name (e.g., "Alex", "Support Bot")
    - A visual face derived from the public key
    - A signature proving the agent owns this name

    Names are NOT globally unique - the agent_id/fingerprint is the
    true unique identifier. The name is for human convenience.

    Example:
        # Create profile from keypair
        keypair = KeyPair.generate()
        profile = AgentProfile.create(keypair, "My Agent")

        # Get face
        svg = profile.face.to_svg()

        # Display format
        print(profile.display_name)  # "My Agent"
        print(profile.short_display)  # "My Agent (a3f8b2c1)"

        # Verify profile authenticity
        is_valid = profile.verify()
    """

    agent_id: str
    name: str
    name_signature: bytes
    created_at: datetime
    face: AgentFace = field(repr=False)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Optional verified domain (e.g., "acme.com")
    verified_domain: str | None = None
    domain_proof: bytes | None = None

    @classmethod
    def create(
        cls,
        keypair: KeyPair,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> AgentProfile:
        """Create a new profile with a signed name.

        Args:
            keypair: Agent's keypair for signing
            name: Display name (1-50 characters)
            metadata: Optional additional metadata

        Returns:
            New AgentProfile with signed name

        Raises:
            ValidationError: If name is invalid
        """
        # Validate name
        cls._validate_name(name)

        # Get agent ID
        agent_id = str(keypair.to_agent_id())

        # Create timestamp
        created_at = datetime.now(timezone.utc)

        # Sign the name binding
        name_data = cls._name_signing_data(agent_id, name, created_at)
        name_signature = keypair.sign(name_data, domain=DOMAIN_PROFILE)

        # Generate face from public key
        face = AgentFace.from_public_key(keypair.public_key_bytes())

        return cls(
            agent_id=agent_id,
            name=name,
            name_signature=name_signature,
            created_at=created_at,
            face=face,
            metadata=metadata or {},
        )

    @classmethod
    def from_agent_id(cls, agent_id: str | AgentID, name: str = "Anonymous") -> AgentProfile:
        """Create an unsigned profile from just an agent ID.

        This creates a profile without name signature - useful for
        displaying unknown agents. The name will not be verified.

        Args:
            agent_id: Agent ID string or object
            name: Optional display name (defaults to "Anonymous")

        Returns:
            AgentProfile (unverified name)
        """
        if isinstance(agent_id, AgentID):
            agent_id_str = str(agent_id)
            public_key = agent_id.to_public_key_bytes()
        else:
            aid = AgentID(agent_id)
            agent_id_str = agent_id
            public_key = aid.to_public_key_bytes()

        return cls(
            agent_id=agent_id_str,
            name=name,
            name_signature=b'',  # Empty = unsigned
            created_at=datetime.now(timezone.utc),
            face=AgentFace.from_public_key(public_key),
            metadata={},
        )

    @staticmethod
    def _validate_name(name: str) -> None:
        """Validate name format."""
        if len(name) < MIN_NAME_LENGTH:
            raise ValidationError(f"Name must be at least {MIN_NAME_LENGTH} character")
        if len(name) > MAX_NAME_LENGTH:
            raise ValidationError(f"Name must be at most {MAX_NAME_LENGTH} characters")
        if not NAME_PATTERN.match(name):
            raise ValidationError("Name contains invalid characters")

    @staticmethod
    def _name_signing_data(agent_id: str, name: str, created_at: datetime) -> bytes:
        """Create the data that gets signed for name binding."""
        return f"{agent_id}:{name}:{created_at.isoformat()}".encode('utf-8')

    def verify(self) -> bool:
        """Verify the name signature is valid.

        Returns:
            True if signature is valid, False otherwise
        """
        if not self.name_signature:
            return False  # Unsigned profile

        try:
            # Get public key from agent ID
            aid = AgentID(self.agent_id)
            public_key = aid.to_public_key()

            # Reconstruct signed data
            name_data = self._name_signing_data(
                self.agent_id, self.name, self.created_at
            )

            # Add domain separation
            domain_bytes = DOMAIN_PROFILE.encode('utf-8')
            prefixed_data = len(domain_bytes).to_bytes(2, 'big') + domain_bytes + name_data

            # Verify
            public_key.verify(self.name_signature, prefixed_data)
            return True
        except Exception:
            return False

    def update_name(self, keypair: KeyPair, new_name: str) -> AgentProfile:
        """Create a new profile with updated name.

        Args:
            keypair: Agent's keypair for signing
            new_name: New display name

        Returns:
            New AgentProfile with updated name
        """
        return AgentProfile.create(keypair, new_name, self.metadata)

    @property
    def fingerprint(self) -> str:
        """8-character fingerprint from face."""
        return self.face.fingerprint()

    @property
    def display_name(self) -> str:
        """Human-readable display name."""
        return self.name

    @property
    def short_display(self) -> str:
        """Name with fingerprint: 'Alex (a3f8b2c1)'"""
        return f"{self.name} ({self.fingerprint})"

    @property
    def full_display(self) -> str:
        """Full display with verification status."""
        verified = self.verify()
        status = "verified" if verified else "unverified"
        domain = f" @ {self.verified_domain}" if self.verified_domain else ""
        return f"{self.name}{domain} ({self.fingerprint}) [{status}]"

    @property
    def is_signed(self) -> bool:
        """Check if profile has a name signature."""
        return bool(self.name_signature)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        import base64

        result = {
            "agent_id": self.agent_id,
            "name": self.name,
            "name_signature": base64.b64encode(self.name_signature).decode('ascii'),
            "created_at": self.created_at.isoformat(),
            "fingerprint": self.fingerprint,
            "metadata": self.metadata,
        }

        if self.verified_domain:
            result["verified_domain"] = self.verified_domain
            if self.domain_proof:
                result["domain_proof"] = base64.b64encode(self.domain_proof).decode('ascii')

        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentProfile:
        """Deserialize from dictionary."""
        import base64

        agent_id = data["agent_id"]
        aid = AgentID(agent_id)

        name_sig = data.get("name_signature", "")
        name_signature = base64.b64decode(name_sig) if name_sig else b''

        domain_proof = None
        if data.get("domain_proof"):
            domain_proof = base64.b64decode(data["domain_proof"])

        return cls(
            agent_id=agent_id,
            name=data["name"],
            name_signature=name_signature,
            created_at=datetime.fromisoformat(data["created_at"]),
            face=AgentFace.from_public_key(aid.to_public_key_bytes()),
            metadata=data.get("metadata", {}),
            verified_domain=data.get("verified_domain"),
            domain_proof=domain_proof,
        )

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> AgentProfile:
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AgentProfile):
            return False
        return self.agent_id == other.agent_id and self.name == other.name

    def __hash__(self) -> int:
        return hash((self.agent_id, self.name))

    def __repr__(self) -> str:
        return f"AgentProfile({self.short_display})"
