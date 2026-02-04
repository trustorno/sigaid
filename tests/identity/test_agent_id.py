"""Tests for identity/agent_id.py - AgentID generation and validation."""

import pytest

from sigaid.identity.agent_id import AgentID
from sigaid.crypto.keys import KeyPair
from sigaid.constants import AGENT_ID_PREFIX
from sigaid.exceptions import InvalidAgentID


class TestAgentID:
    """Tests for AgentID class."""
    
    def test_from_public_key_creates_valid_id(self, keypair):
        """from_public_key() should create valid AgentID."""
        agent_id = AgentID.from_public_key(keypair.public_key_bytes())
        
        assert str(agent_id).startswith(AGENT_ID_PREFIX)
        assert AgentID.is_valid(str(agent_id))
    
    def test_from_keypair_matches_from_public_key(self, keypair):
        """from_keypair() should match from_public_key()."""
        id1 = AgentID.from_keypair(keypair)
        id2 = AgentID.from_public_key(keypair.public_key_bytes())
        
        assert str(id1) == str(id2)
    
    def test_deterministic_for_same_key(self, keypair):
        """Same key should always produce same AgentID."""
        id1 = AgentID.from_public_key(keypair.public_key_bytes())
        id2 = AgentID.from_public_key(keypair.public_key_bytes())
        
        assert str(id1) == str(id2)
    
    def test_different_keys_different_ids(self):
        """Different keys should produce different AgentIDs."""
        kp1 = KeyPair.generate()
        kp2 = KeyPair.generate()
        
        id1 = AgentID.from_keypair(kp1)
        id2 = AgentID.from_keypair(kp2)
        
        assert str(id1) != str(id2)
    
    def test_public_key_property(self, keypair):
        """public_key property should return embedded key."""
        agent_id = AgentID.from_keypair(keypair)
        
        assert agent_id.public_key == keypair.public_key_bytes()
    
    def test_string_roundtrip(self, keypair):
        """AgentID should survive string roundtrip."""
        original = AgentID.from_keypair(keypair)
        restored = AgentID(str(original))
        
        assert str(original) == str(restored)
        assert original.public_key == restored.public_key
    
    def test_rejects_invalid_prefix(self):
        """Should reject IDs without correct prefix."""
        with pytest.raises(InvalidAgentID):
            AgentID("bad_7Xq9YkPzN3mWvR5tH8jL2cBfA4dE6gS1")
    
    def test_rejects_invalid_base58(self):
        """Should reject invalid Base58 encoding."""
        with pytest.raises(InvalidAgentID):
            AgentID("aid_0OIl")  # Contains invalid Base58 chars
    
    def test_rejects_bad_checksum(self):
        """Should reject IDs with invalid checksum."""
        keypair = KeyPair.generate()
        valid_id = str(AgentID.from_keypair(keypair))
        
        # Corrupt last character (checksum)
        corrupted = valid_id[:-1] + ("x" if valid_id[-1] != "x" else "y")
        
        with pytest.raises(InvalidAgentID):
            AgentID(corrupted)
    
    def test_is_valid_accepts_valid_id(self, keypair):
        """is_valid() should accept valid AgentID."""
        agent_id = AgentID.from_keypair(keypair)
        assert AgentID.is_valid(str(agent_id))
    
    def test_is_valid_rejects_invalid_id(self):
        """is_valid() should reject invalid IDs."""
        assert not AgentID.is_valid("invalid")
        assert not AgentID.is_valid("")
        assert not AgentID.is_valid("aid_")
    
    def test_is_valid_format_fast_check(self, keypair):
        """is_valid_format() should be fast format check."""
        agent_id = AgentID.from_keypair(keypair)
        assert AgentID.is_valid_format(str(agent_id))
        assert not AgentID.is_valid_format("invalid")
    
    def test_equality(self, keypair):
        """AgentIDs should support equality comparison."""
        id1 = AgentID.from_keypair(keypair)
        id2 = AgentID.from_keypair(keypair)
        id3 = AgentID.from_keypair(KeyPair.generate())
        
        assert id1 == id2
        assert id1 != id3
        assert id1 == str(id1)  # String comparison
    
    def test_hash(self, keypair):
        """AgentIDs should be hashable."""
        id1 = AgentID.from_keypair(keypair)
        id2 = AgentID.from_keypair(keypair)
        
        assert hash(id1) == hash(id2)
        
        # Can use in sets/dicts
        s = {id1}
        assert id2 in s
    
    def test_short(self, keypair):
        """short() should return truncated version."""
        agent_id = AgentID.from_keypair(keypair)
        
        short = agent_id.short(8)
        
        assert short.startswith(AGENT_ID_PREFIX)
        assert short.endswith("...")
        assert len(short) < len(str(agent_id))
    
    def test_repr(self, keypair):
        """repr() should be informative."""
        agent_id = AgentID.from_keypair(keypair)
        repr_str = repr(agent_id)
        
        assert "AgentID" in repr_str
        assert str(agent_id) in repr_str
