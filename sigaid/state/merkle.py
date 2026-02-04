"""Merkle tree implementation for efficient state chain proofs.

Provides:
- Compact inclusion proofs (O(log n) size vs O(n) for full chain)
- Efficient verification without downloading entire history
- Tamper detection with merkle root commitment

The merkle tree is built from state entry hashes, allowing third parties
to verify that a specific entry exists in the chain without needing
the full chain history.

Example:
    # Build tree from state chain
    tree = MerkleTree.from_entries(entries)

    # Get merkle root (can be published/committed)
    root = tree.root

    # Generate proof for a specific entry
    proof = tree.get_proof(entry_index)

    # Verify proof (can be done by anyone with root + entry hash)
    valid = MerkleTree.verify_proof(entry_hash, proof, root)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, TYPE_CHECKING

from sigaid.crypto.hashing import hash_bytes, hash_multiple

if TYPE_CHECKING:
    from sigaid.models.state import StateEntry


@dataclass
class MerkleProof:
    """Proof of inclusion in a merkle tree.

    Contains the sibling hashes needed to reconstruct
    the path from a leaf to the root.
    """
    leaf_index: int
    leaf_hash: bytes  # 32 bytes
    siblings: List[bytes]  # List of 32-byte hashes
    directions: List[bool]  # True = sibling is on right, False = left

    def to_bytes(self) -> bytes:
        """Serialize proof to bytes."""
        import struct

        # Format: [4-byte index][32-byte leaf][1-byte count][siblings + directions]
        result = struct.pack(">I", self.leaf_index)
        result += self.leaf_hash

        result += struct.pack("B", len(self.siblings))
        for sibling, direction in zip(self.siblings, self.directions):
            result += sibling
            result += struct.pack("?", direction)

        return result

    @classmethod
    def from_bytes(cls, data: bytes) -> MerkleProof:
        """Deserialize proof from bytes."""
        import struct

        offset = 0

        # Read index
        leaf_index = struct.unpack_from(">I", data, offset)[0]
        offset += 4

        # Read leaf hash
        leaf_hash = data[offset:offset + 32]
        offset += 32

        # Read siblings
        count = data[offset]
        offset += 1

        siblings = []
        directions = []
        for _ in range(count):
            siblings.append(data[offset:offset + 32])
            offset += 32
            directions.append(struct.unpack_from("?", data, offset)[0])
            offset += 1

        return cls(
            leaf_index=leaf_index,
            leaf_hash=leaf_hash,
            siblings=siblings,
            directions=directions,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        import base64
        return {
            "leaf_index": self.leaf_index,
            "leaf_hash": base64.b64encode(self.leaf_hash).decode("ascii"),
            "siblings": [base64.b64encode(s).decode("ascii") for s in self.siblings],
            "directions": self.directions,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MerkleProof:
        """Create from dictionary."""
        import base64
        return cls(
            leaf_index=data["leaf_index"],
            leaf_hash=base64.b64decode(data["leaf_hash"]),
            siblings=[base64.b64decode(s) for s in data["siblings"]],
            directions=data["directions"],
        )


class MerkleTree:
    """Binary merkle tree for state chain entries.

    Builds a complete binary tree where:
    - Leaves are hashes of state entries
    - Internal nodes are H(left || right)
    - Tree is padded to power of 2 with empty hashes
    """

    # Empty hash for padding (hash of empty bytes)
    EMPTY_HASH = hash_bytes(b"")

    def __init__(self, leaf_hashes: List[bytes]):
        """Build merkle tree from leaf hashes.

        Args:
            leaf_hashes: List of 32-byte hashes (state entry hashes)
        """
        self._leaves = leaf_hashes.copy()
        self._tree = self._build_tree(leaf_hashes)

    @classmethod
    def from_entries(cls, entries: List[StateEntry]) -> MerkleTree:
        """Build tree from state chain entries.

        Args:
            entries: List of StateEntry objects

        Returns:
            MerkleTree built from entry hashes
        """
        leaf_hashes = [entry.entry_hash for entry in entries]
        return cls(leaf_hashes)

    def _build_tree(self, leaves: List[bytes]) -> List[List[bytes]]:
        """Build the complete merkle tree.

        Returns list of levels, where level[0] are leaves
        and level[-1] is the root.
        """
        if not leaves:
            # Empty tree has just the empty hash as root
            return [[self.EMPTY_HASH]]

        # Pad to power of 2
        n = len(leaves)
        padded_size = 1
        while padded_size < n:
            padded_size *= 2

        padded_leaves = leaves + [self.EMPTY_HASH] * (padded_size - n)

        # Build tree bottom-up
        tree = [padded_leaves]
        current_level = padded_leaves

        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                right = current_level[i + 1]
                parent = hash_multiple(left, right)
                next_level.append(parent)
            tree.append(next_level)
            current_level = next_level

        return tree

    @property
    def root(self) -> bytes:
        """Get the merkle root (32 bytes)."""
        return self._tree[-1][0]

    @property
    def leaf_count(self) -> int:
        """Number of actual leaves (excluding padding)."""
        return len(self._leaves)

    @property
    def height(self) -> int:
        """Height of the tree (number of levels)."""
        return len(self._tree)

    def get_leaf(self, index: int) -> bytes:
        """Get leaf hash at index."""
        if index < 0 or index >= len(self._leaves):
            raise IndexError(f"Leaf index {index} out of range")
        return self._leaves[index]

    def get_proof(self, leaf_index: int) -> MerkleProof:
        """Generate inclusion proof for a leaf.

        Args:
            leaf_index: Index of the leaf to prove

        Returns:
            MerkleProof that can verify inclusion

        Raises:
            IndexError: If leaf_index is out of range
        """
        if leaf_index < 0 or leaf_index >= len(self._leaves):
            raise IndexError(f"Leaf index {leaf_index} out of range")

        siblings = []
        directions = []

        current_index = leaf_index

        # Walk up the tree collecting siblings
        for level in range(len(self._tree) - 1):
            # Determine sibling index
            if current_index % 2 == 0:
                # Current is left child, sibling is right
                sibling_index = current_index + 1
                directions.append(True)  # Sibling on right
            else:
                # Current is right child, sibling is left
                sibling_index = current_index - 1
                directions.append(False)  # Sibling on left

            siblings.append(self._tree[level][sibling_index])
            current_index //= 2

        return MerkleProof(
            leaf_index=leaf_index,
            leaf_hash=self._leaves[leaf_index],
            siblings=siblings,
            directions=directions,
        )

    @staticmethod
    def verify_proof(
        leaf_hash: bytes,
        proof: MerkleProof,
        expected_root: bytes,
    ) -> bool:
        """Verify a merkle proof.

        Args:
            leaf_hash: Hash of the leaf being verified
            proof: MerkleProof from get_proof()
            expected_root: Expected merkle root

        Returns:
            True if proof is valid and leads to expected root
        """
        if leaf_hash != proof.leaf_hash:
            return False

        current_hash = leaf_hash

        for sibling, is_right in zip(proof.siblings, proof.directions):
            if is_right:
                # Sibling is on right
                current_hash = hash_multiple(current_hash, sibling)
            else:
                # Sibling is on left
                current_hash = hash_multiple(sibling, current_hash)

        return current_hash == expected_root

    def verify_entry(self, entry: StateEntry, expected_root: Optional[bytes] = None) -> bool:
        """Verify a state entry is in the tree.

        Args:
            entry: StateEntry to verify
            expected_root: Optional root to verify against (uses self.root if None)

        Returns:
            True if entry is in the tree
        """
        # Find the entry in leaves
        try:
            index = self._leaves.index(entry.entry_hash)
        except ValueError:
            return False

        proof = self.get_proof(index)
        root = expected_root or self.root
        return self.verify_proof(entry.entry_hash, proof, root)


class MerkleChainCommitment:
    """Combines state chain with merkle tree for efficient proofs.

    Maintains both the linear chain (for ordering/signatures) and
    a merkle tree (for efficient inclusion proofs).
    """

    def __init__(self, entries: Optional[List[StateEntry]] = None):
        """Initialize with optional entries.

        Args:
            entries: Initial state entries
        """
        self._entries: List[StateEntry] = entries.copy() if entries else []
        self._tree: Optional[MerkleTree] = None
        if self._entries:
            self._rebuild_tree()

    def _rebuild_tree(self) -> None:
        """Rebuild merkle tree from entries."""
        self._tree = MerkleTree.from_entries(self._entries)

    def append(self, entry: StateEntry) -> None:
        """Append a new entry.

        Args:
            entry: State entry to append
        """
        # Verify chain integrity
        if self._entries:
            last_entry = self._entries[-1]
            if entry.prev_hash != last_entry.entry_hash:
                raise ValueError("Entry prev_hash doesn't match chain head")
            if entry.sequence != last_entry.sequence + 1:
                raise ValueError("Entry sequence must be prev + 1")
        else:
            from sigaid.constants import GENESIS_PREV_HASH
            if entry.prev_hash != GENESIS_PREV_HASH:
                raise ValueError("First entry must have genesis prev_hash")
            if entry.sequence != 0:
                raise ValueError("First entry must have sequence 0")

        self._entries.append(entry)
        self._rebuild_tree()

    @property
    def root(self) -> Optional[bytes]:
        """Get merkle root of the chain."""
        return self._tree.root if self._tree else None

    @property
    def head(self) -> Optional[StateEntry]:
        """Get the latest entry."""
        return self._entries[-1] if self._entries else None

    @property
    def length(self) -> int:
        """Number of entries in the chain."""
        return len(self._entries)

    def get_proof(self, sequence: int) -> MerkleProof:
        """Get proof for entry at sequence number.

        Args:
            sequence: Sequence number of entry

        Returns:
            MerkleProof for the entry
        """
        if not self._tree:
            raise ValueError("Chain is empty")
        if sequence < 0 or sequence >= len(self._entries):
            raise IndexError(f"Sequence {sequence} out of range")
        return self._tree.get_proof(sequence)

    def verify_proof(self, entry_hash: bytes, proof: MerkleProof) -> bool:
        """Verify an inclusion proof against current root.

        Args:
            entry_hash: Hash of entry being verified
            proof: Merkle proof

        Returns:
            True if proof is valid
        """
        if not self._tree:
            return False
        return MerkleTree.verify_proof(entry_hash, proof, self._tree.root)

    def to_commitment(self) -> dict:
        """Export commitment data for publishing.

        Returns:
            Dictionary with root, head hash, and length
        """
        import base64
        return {
            "merkle_root": base64.b64encode(self.root).decode("ascii") if self.root else None,
            "head_hash": base64.b64encode(self.head.entry_hash).decode("ascii") if self.head else None,
            "head_sequence": self.head.sequence if self.head else None,
            "length": self.length,
        }
