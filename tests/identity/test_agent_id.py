"""Tests for AgentID generation and validation."""

import pytest

from sigaid.identity.agent_id import AgentID
from sigaid.crypto.keys import KeyPair
from sigaid.exceptions import InvalidAgentID


class TestAgentID:
    """Tests for AgentID class."""

    def test_from_public_key(self):
        """Test creating AgentID from public key."""
        keypair = KeyPair.generate()
        agent_id = AgentID.from_public_key(keypair.public_key_bytes())

        assert str(agent_id).startswith("aid_")

    def test_from_keypair_method(self):
        """Test creating AgentID via keypair method."""
        keypair = KeyPair.generate()
        agent_id = keypair.to_agent_id()

        assert str(agent_id).startswith("aid_")

    def test_deterministic(self):
        """Test that same public key produces same AgentID."""
        keypair = KeyPair.generate()
        agent_id1 = AgentID.from_public_key(keypair.public_key_bytes())
        agent_id2 = AgentID.from_public_key(keypair.public_key_bytes())

        assert agent_id1 == agent_id2

    def test_validate_valid_id(self):
        """Test validating a valid AgentID."""
        keypair = KeyPair.generate()
        agent_id = keypair.to_agent_id()

        # Should not raise
        AgentID.validate(str(agent_id))

    def test_validate_missing_prefix(self):
        """Test that missing prefix is rejected."""
        with pytest.raises(InvalidAgentID):
            AgentID.validate("invalid_id_without_prefix")

    def test_validate_invalid_base58(self):
        """Test that invalid base58 is rejected."""
        with pytest.raises(InvalidAgentID):
            AgentID.validate("aid_0OIl")  # Contains invalid chars

    def test_validate_bad_checksum(self):
        """Test that bad checksum is rejected."""
        keypair = KeyPair.generate()
        agent_id_str = str(keypair.to_agent_id())

        # Corrupt the last character
        corrupted = agent_id_str[:-1] + ("A" if agent_id_str[-1] != "A" else "B")

        with pytest.raises(InvalidAgentID):
            AgentID.validate(corrupted)

    def test_to_public_key_bytes_roundtrip(self):
        """Test extracting public key from AgentID."""
        keypair = KeyPair.generate()
        original_pk = keypair.public_key_bytes()

        agent_id = AgentID.from_public_key(original_pk)
        recovered_pk = agent_id.to_public_key_bytes()

        assert original_pk == recovered_pk

    def test_short_representation(self):
        """Test short form of AgentID."""
        keypair = KeyPair.generate()
        agent_id = keypair.to_agent_id()

        short = agent_id.short
        assert short.startswith("aid_")
        assert short.endswith("...")
        assert len(short) < len(str(agent_id))

    def test_equality_with_string(self):
        """Test equality comparison with string."""
        keypair = KeyPair.generate()
        agent_id = keypair.to_agent_id()

        assert agent_id == str(agent_id)

    def test_equality_with_agent_id(self):
        """Test equality comparison with another AgentID."""
        keypair = KeyPair.generate()
        agent_id1 = keypair.to_agent_id()
        agent_id2 = AgentID(str(agent_id1))

        assert agent_id1 == agent_id2

    def test_hash_for_dict_key(self):
        """Test that AgentID can be used as dict key."""
        keypair = KeyPair.generate()
        agent_id = keypair.to_agent_id()

        d = {agent_id: "value"}
        assert d[agent_id] == "value"

    def test_invalid_public_key_length(self):
        """Test that invalid public key length is rejected."""
        with pytest.raises(InvalidAgentID):
            AgentID.from_public_key(b"too_short")
