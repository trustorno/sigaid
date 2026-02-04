"""AgentID generation and validation."""

from __future__ import annotations

import hashlib
import re
from typing import TYPE_CHECKING

import base58

from sigaid.constants import AGENT_ID_PREFIX, ED25519_PUBLIC_KEY_SIZE
from sigaid.exceptions import InvalidAgentID

if TYPE_CHECKING:
    from sigaid.identity.keypair import KeyPair


# AgentID format: aid_<base58(public_key + checksum)>
# Checksum is first 4 bytes of SHA256(public_key)
# 36 bytes Base58-encoded = typically 48-50 characters
AGENT_ID_PATTERN = re.compile(r"^aid_[1-9A-HJ-NP-Za-km-z]{44,52}$")


class AgentID:
    """
    Cryptographically-derived agent identifier.
    
    AgentID is derived deterministically from an Ed25519 public key:
    1. Take the 32-byte public key
    2. Compute SHA256(public_key)
    3. Take first 4 bytes as checksum
    4. Concatenate: public_key + checksum (36 bytes)
    5. Base58 encode
    6. Prefix with "aid_"
    
    This ensures:
    - Every keypair has exactly one AgentID
    - AgentIDs are human-readable and URL-safe
    - Built-in checksum catches typos
    - No ambiguous characters (Base58)
    
    Example:
        # From keypair
        keypair = KeyPair.generate()
        agent_id = AgentID.from_keypair(keypair)
        
        # From public key bytes
        agent_id = AgentID.from_public_key(public_key_bytes)
        
        # Validate format
        if AgentID.is_valid("aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1xxx"):
            agent_id = AgentID("aid_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1xxx")
    """
    
    __slots__ = ("_value", "_public_key")
    
    def __init__(self, value: str):
        """
        Create AgentID from string value.
        
        Args:
            value: AgentID string (aid_xxx format)
            
        Raises:
            InvalidAgentID: If format is invalid or checksum fails
        """
        if not value.startswith(AGENT_ID_PREFIX):
            raise InvalidAgentID(f"AgentID must start with '{AGENT_ID_PREFIX}', got: {value[:10]}...")
        
        if not AGENT_ID_PATTERN.match(value):
            raise InvalidAgentID(f"Invalid AgentID format: {value}")
        
        # Decode and verify checksum
        try:
            encoded = value[len(AGENT_ID_PREFIX):]
            decoded = base58.b58decode(encoded)
        except Exception as e:
            raise InvalidAgentID(f"Invalid Base58 encoding: {e}") from e
        
        if len(decoded) != ED25519_PUBLIC_KEY_SIZE + 4:
            raise InvalidAgentID(
                f"Decoded AgentID has wrong length: {len(decoded)}, "
                f"expected {ED25519_PUBLIC_KEY_SIZE + 4}"
            )
        
        public_key = decoded[:ED25519_PUBLIC_KEY_SIZE]
        checksum = decoded[ED25519_PUBLIC_KEY_SIZE:]
        
        # Verify checksum
        expected_checksum = self._compute_checksum(public_key)
        if checksum != expected_checksum:
            raise InvalidAgentID("AgentID checksum verification failed")
        
        self._value = value
        self._public_key = public_key
    
    @classmethod
    def from_public_key(cls, public_key: bytes) -> AgentID:
        """
        Create AgentID from Ed25519 public key bytes.
        
        Args:
            public_key: 32-byte Ed25519 public key
            
        Returns:
            AgentID instance
            
        Raises:
            InvalidAgentID: If public key has wrong size
        """
        if len(public_key) != ED25519_PUBLIC_KEY_SIZE:
            raise InvalidAgentID(
                f"Public key must be {ED25519_PUBLIC_KEY_SIZE} bytes, got {len(public_key)}"
            )
        
        checksum = cls._compute_checksum(public_key)
        encoded = base58.b58encode(public_key + checksum).decode("ascii")
        value = AGENT_ID_PREFIX + encoded
        
        # Create instance directly (we know it's valid)
        instance = object.__new__(cls)
        instance._value = value
        instance._public_key = public_key
        return instance
    
    @classmethod
    def from_keypair(cls, keypair: KeyPair) -> AgentID:
        """
        Create AgentID from KeyPair.
        
        Args:
            keypair: KeyPair instance
            
        Returns:
            AgentID instance
        """
        return cls.from_public_key(keypair.public_key_bytes())
    
    @staticmethod
    def _compute_checksum(public_key: bytes) -> bytes:
        """Compute 4-byte checksum of public key."""
        return hashlib.sha256(public_key).digest()[:4]
    
    @staticmethod
    def is_valid(value: str) -> bool:
        """
        Check if string is a valid AgentID format.
        
        This performs full validation including checksum verification.
        
        Args:
            value: String to check
            
        Returns:
            True if valid AgentID, False otherwise
        """
        try:
            AgentID(value)
            return True
        except InvalidAgentID:
            return False
    
    @staticmethod
    def is_valid_format(value: str) -> bool:
        """
        Check if string matches AgentID format (without checksum verification).
        
        This is faster than full validation when you just need format check.
        
        Args:
            value: String to check
            
        Returns:
            True if format matches, False otherwise
        """
        return bool(AGENT_ID_PATTERN.match(value))
    
    @property
    def public_key(self) -> bytes:
        """Get the public key bytes embedded in this AgentID."""
        return self._public_key
    
    def __str__(self) -> str:
        return self._value
    
    def __repr__(self) -> str:
        return f"AgentID({self._value!r})"
    
    def __eq__(self, other: object) -> bool:
        if isinstance(other, AgentID):
            return self._value == other._value
        if isinstance(other, str):
            return self._value == other
        return NotImplemented
    
    def __hash__(self) -> int:
        return hash(self._value)
    
    def __len__(self) -> int:
        return len(self._value)
    
    def short(self, length: int = 8) -> str:
        """
        Get shortened AgentID for display.
        
        Args:
            length: Number of characters after prefix
            
        Returns:
            Shortened ID like "aid_7Xq9YkPz..."
        """
        encoded = self._value[len(AGENT_ID_PREFIX):]
        if len(encoded) <= length:
            return self._value
        return f"{AGENT_ID_PREFIX}{encoded[:length]}..."
