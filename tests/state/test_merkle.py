"""Tests for Merkle tree implementation."""

import pytest

from sigaid.state.merkle import (
    MerkleTree,
    MerkleProof,
    MerkleChainCommitment,
)
from sigaid.crypto.hashing import hash_bytes
from sigaid.constants import GENESIS_PREV_HASH


class TestMerkleProof:
    """Tests for MerkleProof class."""

    def test_to_bytes_from_bytes_roundtrip(self):
        """Test serialization roundtrip."""
        proof = MerkleProof(
            leaf_index=5,
            leaf_hash=b"a" * 32,
            siblings=[b"b" * 32, b"c" * 32, b"d" * 32],
            directions=[True, False, True],
        )

        serialized = proof.to_bytes()
        restored = MerkleProof.from_bytes(serialized)

        assert restored.leaf_index == proof.leaf_index
        assert restored.leaf_hash == proof.leaf_hash
        assert restored.siblings == proof.siblings
        assert restored.directions == proof.directions

    def test_to_dict_from_dict_roundtrip(self):
        """Test JSON-friendly serialization roundtrip."""
        proof = MerkleProof(
            leaf_index=3,
            leaf_hash=b"x" * 32,
            siblings=[b"y" * 32, b"z" * 32],
            directions=[False, True],
        )

        as_dict = proof.to_dict()
        restored = MerkleProof.from_dict(as_dict)

        assert restored.leaf_index == proof.leaf_index
        assert restored.leaf_hash == proof.leaf_hash
        assert restored.siblings == proof.siblings
        assert restored.directions == proof.directions

    def test_to_dict_json_serializable(self):
        """Test to_dict produces JSON-serializable output."""
        import json

        proof = MerkleProof(
            leaf_index=0,
            leaf_hash=b"a" * 32,
            siblings=[b"b" * 32],
            directions=[True],
        )

        as_dict = proof.to_dict()
        json_str = json.dumps(as_dict)  # Should not raise
        assert json_str is not None


class TestMerkleTree:
    """Tests for MerkleTree class."""

    def test_empty_tree(self):
        """Test creating empty tree."""
        tree = MerkleTree([])

        assert tree.leaf_count == 0
        assert tree.root == MerkleTree.EMPTY_HASH

    def test_single_leaf(self):
        """Test tree with single leaf."""
        leaf = hash_bytes(b"single")
        tree = MerkleTree([leaf])

        assert tree.leaf_count == 1
        assert tree.root is not None
        assert len(tree.root) == 32

    def test_power_of_two_leaves(self):
        """Test tree with power-of-2 leaves."""
        leaves = [hash_bytes(f"leaf{i}".encode()) for i in range(4)]
        tree = MerkleTree(leaves)

        assert tree.leaf_count == 4
        assert tree.height > 1

    def test_non_power_of_two_leaves(self):
        """Test tree with non-power-of-2 leaves (padded)."""
        leaves = [hash_bytes(f"leaf{i}".encode()) for i in range(5)]
        tree = MerkleTree(leaves)

        assert tree.leaf_count == 5
        # Should be padded to 8

    def test_get_leaf(self):
        """Test getting leaf by index."""
        leaves = [hash_bytes(f"leaf{i}".encode()) for i in range(3)]
        tree = MerkleTree(leaves)

        assert tree.get_leaf(0) == leaves[0]
        assert tree.get_leaf(1) == leaves[1]
        assert tree.get_leaf(2) == leaves[2]

    def test_get_leaf_out_of_range(self):
        """Test getting leaf out of range raises."""
        tree = MerkleTree([hash_bytes(b"only")])

        with pytest.raises(IndexError):
            tree.get_leaf(1)

        with pytest.raises(IndexError):
            tree.get_leaf(-1)

    def test_get_proof(self):
        """Test generating inclusion proof."""
        leaves = [hash_bytes(f"leaf{i}".encode()) for i in range(4)]
        tree = MerkleTree(leaves)

        proof = tree.get_proof(2)

        assert isinstance(proof, MerkleProof)
        assert proof.leaf_index == 2
        assert proof.leaf_hash == leaves[2]
        assert len(proof.siblings) == 2  # log2(4) = 2
        assert len(proof.directions) == 2

    def test_get_proof_out_of_range(self):
        """Test getting proof for out-of-range index raises."""
        tree = MerkleTree([hash_bytes(b"only")])

        with pytest.raises(IndexError):
            tree.get_proof(5)

    def test_verify_proof_valid(self):
        """Test verifying valid proof."""
        leaves = [hash_bytes(f"leaf{i}".encode()) for i in range(8)]
        tree = MerkleTree(leaves)

        for i in range(len(leaves)):
            proof = tree.get_proof(i)
            result = MerkleTree.verify_proof(leaves[i], proof, tree.root)
            assert result is True

    def test_verify_proof_wrong_leaf(self):
        """Test verifying proof with wrong leaf fails."""
        leaves = [hash_bytes(f"leaf{i}".encode()) for i in range(4)]
        tree = MerkleTree(leaves)

        proof = tree.get_proof(0)
        wrong_leaf = hash_bytes(b"wrong")

        result = MerkleTree.verify_proof(wrong_leaf, proof, tree.root)
        assert result is False

    def test_verify_proof_wrong_root(self):
        """Test verifying proof against wrong root fails."""
        leaves = [hash_bytes(f"leaf{i}".encode()) for i in range(4)]
        tree = MerkleTree(leaves)

        proof = tree.get_proof(0)
        wrong_root = hash_bytes(b"fake root")

        result = MerkleTree.verify_proof(leaves[0], proof, wrong_root)
        assert result is False

    def test_verify_proof_tampered_sibling(self):
        """Test verifying proof with tampered sibling fails."""
        leaves = [hash_bytes(f"leaf{i}".encode()) for i in range(4)]
        tree = MerkleTree(leaves)

        proof = tree.get_proof(0)
        # Tamper with a sibling
        proof.siblings[0] = hash_bytes(b"tampered")

        result = MerkleTree.verify_proof(leaves[0], proof, tree.root)
        assert result is False

    def test_different_trees_different_roots(self):
        """Test different data produces different roots."""
        tree1 = MerkleTree([hash_bytes(b"data1")])
        tree2 = MerkleTree([hash_bytes(b"data2")])

        assert tree1.root != tree2.root

    def test_same_data_same_root(self):
        """Test same data produces same root."""
        leaves = [hash_bytes(f"leaf{i}".encode()) for i in range(4)]
        tree1 = MerkleTree(leaves)
        tree2 = MerkleTree(leaves)

        assert tree1.root == tree2.root

    def test_from_entries(self):
        """Test creating tree from state entries."""
        from sigaid.models.state import StateEntry, ActionType
        from sigaid.crypto.keys import KeyPair
        from datetime import datetime, timezone

        keypair = KeyPair.generate()

        entries = []
        prev_hash = GENESIS_PREV_HASH

        for i in range(3):
            entry = StateEntry.create(
                agent_id="aid_test",
                sequence=i,
                prev_hash=prev_hash,
                action_type=ActionType.TRANSACTION,
                action_summary=f"Action {i}",
                action_data={"index": i},
                keypair=keypair,
            )
            entries.append(entry)
            prev_hash = entry.entry_hash

        tree = MerkleTree.from_entries(entries)

        assert tree.leaf_count == 3
        assert tree.get_leaf(0) == entries[0].entry_hash
        assert tree.get_leaf(1) == entries[1].entry_hash
        assert tree.get_leaf(2) == entries[2].entry_hash

        keypair.clear()


class TestMerkleChainCommitment:
    """Tests for MerkleChainCommitment class."""

    @pytest.fixture
    def keypair(self):
        """Create test keypair."""
        kp = KeyPair.generate()
        yield kp
        kp.clear()

    def _create_entry(self, keypair, sequence, prev_hash):
        """Helper to create state entry."""
        from sigaid.models.state import StateEntry, ActionType

        return StateEntry.create(
            agent_id=str(keypair.to_agent_id()),
            sequence=sequence,
            prev_hash=prev_hash,
            action_type=ActionType.TRANSACTION,
            action_summary=f"Action {sequence}",
            action_data={"seq": sequence},
            keypair=keypair,
        )

    def test_empty_commitment(self):
        """Test empty commitment."""
        commit = MerkleChainCommitment()

        assert commit.length == 0
        assert commit.root is None
        assert commit.head is None

    def test_append_genesis(self, keypair):
        """Test appending genesis entry."""
        from sigaid.models.state import create_genesis_entry

        commit = MerkleChainCommitment()
        entry = create_genesis_entry(str(keypair.to_agent_id()), keypair)

        commit.append(entry)

        assert commit.length == 1
        assert commit.head == entry
        assert commit.root is not None

    def test_append_chain(self, keypair):
        """Test appending multiple entries."""
        commit = MerkleChainCommitment()

        entry0 = self._create_entry(keypair, 0, GENESIS_PREV_HASH)
        commit.append(entry0)

        entry1 = self._create_entry(keypair, 1, entry0.entry_hash)
        commit.append(entry1)

        entry2 = self._create_entry(keypair, 2, entry1.entry_hash)
        commit.append(entry2)

        assert commit.length == 3
        assert commit.head == entry2

    def test_append_wrong_prev_hash_fails(self, keypair):
        """Test appending with wrong prev_hash fails."""
        commit = MerkleChainCommitment()

        entry0 = self._create_entry(keypair, 0, GENESIS_PREV_HASH)
        commit.append(entry0)

        # Create entry with wrong prev_hash
        entry1 = self._create_entry(keypair, 1, GENESIS_PREV_HASH)  # Wrong!

        with pytest.raises(ValueError, match="prev_hash"):
            commit.append(entry1)

    def test_append_wrong_sequence_fails(self, keypair):
        """Test appending with wrong sequence fails."""
        commit = MerkleChainCommitment()

        entry0 = self._create_entry(keypair, 0, GENESIS_PREV_HASH)
        commit.append(entry0)

        # Create entry with wrong sequence
        entry2 = self._create_entry(keypair, 2, entry0.entry_hash)  # Should be 1

        with pytest.raises(ValueError, match="sequence"):
            commit.append(entry2)

    def test_get_proof(self, keypair):
        """Test getting proof for entry."""
        commit = MerkleChainCommitment()

        entry0 = self._create_entry(keypair, 0, GENESIS_PREV_HASH)
        commit.append(entry0)

        entry1 = self._create_entry(keypair, 1, entry0.entry_hash)
        commit.append(entry1)

        proof = commit.get_proof(0)

        assert proof.leaf_hash == entry0.entry_hash
        assert commit.verify_proof(entry0.entry_hash, proof)

    def test_verify_proof(self, keypair):
        """Test verifying inclusion proof."""
        commit = MerkleChainCommitment()

        entries = []
        prev_hash = GENESIS_PREV_HASH
        for i in range(5):
            entry = self._create_entry(keypair, i, prev_hash)
            commit.append(entry)
            entries.append(entry)
            prev_hash = entry.entry_hash

        # Verify each entry
        for i, entry in enumerate(entries):
            proof = commit.get_proof(i)
            assert commit.verify_proof(entry.entry_hash, proof)

    def test_to_commitment(self, keypair):
        """Test exporting commitment data."""
        commit = MerkleChainCommitment()

        entry0 = self._create_entry(keypair, 0, GENESIS_PREV_HASH)
        commit.append(entry0)

        data = commit.to_commitment()

        assert "merkle_root" in data
        assert "head_hash" in data
        assert "head_sequence" in data
        assert "length" in data

        assert data["head_sequence"] == 0
        assert data["length"] == 1

    def test_commitment_from_entries(self, keypair):
        """Test creating commitment with initial entries."""
        entries = []
        prev_hash = GENESIS_PREV_HASH
        for i in range(3):
            entry = self._create_entry(keypair, i, prev_hash)
            entries.append(entry)
            prev_hash = entry.entry_hash

        commit = MerkleChainCommitment(entries)

        assert commit.length == 3
        assert commit.head == entries[-1]


# Import at module level for fixtures
from sigaid.crypto.keys import KeyPair
