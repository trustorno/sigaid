"""State chain operations."""

from __future__ import annotations

import fcntl
import json
import logging
import os
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterator

from sigaid.crypto.hashing import ZERO_HASH, hash_bytes, verify_chain_integrity
from sigaid.exceptions import (
    ForkDetected,
    InvalidStateEntry,
    StateChainBroken,
    StateChainError,
)
from sigaid.models.state import ActionType, StateEntry, StateEntryBuilder

if TYPE_CHECKING:
    from sigaid.crypto.keys import KeyPair
    from sigaid.client.authority import AuthorityClient

logger = logging.getLogger(__name__)


class StateChain:
    """
    Agent's state chain - an immutable log of actions.
    
    The state chain provides:
    - Tamper-evident history via hash linking
    - Cryptographic signatures for authenticity
    - Fork detection for clone prevention
    
    Example:
        chain = StateChain(agent_id, keypair)
        
        # Record actions
        entry = await chain.append(
            ActionType.TRANSACTION,
            "Booked hotel for $180",
            {"hotel_id": "123", "amount": 180}
        )
        
        # Get chain head
        head = chain.head
        print(f"Chain has {chain.length} entries")
        
        # Verify integrity
        if chain.verify():
            print("Chain is valid")
    """
    
    def __init__(
        self,
        agent_id: str,
        keypair: KeyPair,
        *,
        authority: AuthorityClient | None = None,
        persistence_path: Path | None = None,
        sync_on_startup: bool = True,
    ):
        """
        Initialize state chain.

        Args:
            agent_id: Agent identifier
            keypair: Agent's keypair for signing entries
            authority: Optional Authority client for remote persistence
            persistence_path: Optional local file path for persistence
            sync_on_startup: Whether to sync with Authority on first async operation
        """
        self._agent_id = agent_id
        self._keypair = keypair
        self._authority = authority
        self._persistence_path = persistence_path
        self._sync_on_startup = sync_on_startup
        self._startup_synced = False

        self._entries: list[StateEntry] = []
        self._builder = StateEntryBuilder(agent_id, keypair)

        # Load from persistence if available (with locking and WAL recovery)
        if persistence_path and persistence_path.exists():
            self._load_from_file_with_lock(persistence_path)
        elif persistence_path:
            # Check for WAL recovery even if main file doesn't exist
            wal_path = persistence_path.with_suffix(".wal")
            if wal_path.exists():
                self._recover_from_wal(persistence_path, wal_path)
                if persistence_path.exists():
                    self._load_from_file_with_lock(persistence_path)
    
    @property
    def agent_id(self) -> str:
        """Get agent ID."""
        return self._agent_id
    
    @property
    def head(self) -> StateEntry | None:
        """Get the most recent state entry (chain head)."""
        return self._entries[-1] if self._entries else None
    
    @property
    def length(self) -> int:
        """Get number of entries in chain."""
        return len(self._entries)
    
    @property
    def sequence(self) -> int:
        """Get current sequence number (next entry will have sequence + 1)."""
        return self._entries[-1].sequence if self._entries else -1
    
    @property
    def is_empty(self) -> bool:
        """Check if chain is empty."""
        return len(self._entries) == 0
    
    def append(
        self,
        action_type: ActionType,
        action_summary: str,
        action_data: dict[str, Any] | None = None,
    ) -> StateEntry:
        """
        Append new entry to the state chain.

        Args:
            action_type: Type of action
            action_summary: Human-readable summary
            action_data: Optional structured data (will be hashed)

        Returns:
            The new StateEntry
        """
        entry = self._builder.build(
            prev_entry=self.head,
            action_type=action_type,
            action_summary=action_summary,
            action_data=action_data,
        )

        self._entries.append(entry)

        # Persist locally if configured (with WAL for crash safety)
        if self._persistence_path:
            self._save_to_file_with_wal(self._persistence_path)

        return entry
    
    async def append_and_sync(
        self,
        action_type: ActionType,
        action_summary: str,
        action_data: dict[str, Any] | None = None,
    ) -> StateEntry:
        """
        Append entry and sync with Authority.
        
        This ensures the entry is recorded remotely for verification.
        
        Args:
            action_type: Type of action
            action_summary: Human-readable summary
            action_data: Optional structured data
            
        Returns:
            The new StateEntry
            
        Raises:
            StateChainError: If sync fails
        """
        entry = self.append(action_type, action_summary, action_data)
        
        if self._authority:
            try:
                await self._authority.append_state(self._agent_id, entry)
            except Exception as e:
                # Remove local entry on failure
                self._entries.pop()
                raise StateChainError(f"Failed to sync state entry: {e}") from e
        
        return entry
    
    def verify(self) -> bool:
        """
        Verify the entire chain integrity.
        
        Checks:
        - Hash linking between entries
        - Entry hashes are correct
        - Sequences are monotonic
        - Signatures are valid
        
        Returns:
            True if chain is valid
        """
        if not self._entries:
            return True
        
        # Verify chain integrity
        if not verify_chain_integrity(self._entries):
            return False
        
        # Verify all signatures
        public_key = self._keypair.public_key_bytes()
        for entry in self._entries:
            if not entry.verify_signature(public_key):
                return False
        
        return True
    
    def verify_against_remote(self, remote_head: StateEntry) -> bool:
        """
        Verify local chain is consistent with remote head.
        
        Detects forks where local and remote chains diverge.
        
        Args:
            remote_head: The Authority's recorded head entry
            
        Returns:
            True if consistent
            
        Raises:
            ForkDetected: If chains have diverged
        """
        if self.is_empty:
            return True
        
        local_head = self.head
        
        # Same sequence - check same hash
        if local_head.sequence == remote_head.sequence:
            if local_head.entry_hash != remote_head.entry_hash:
                raise ForkDetected(
                    self._agent_id,
                    expected_hash=remote_head.entry_hash,
                    actual_hash=local_head.entry_hash,
                    sequence=local_head.sequence,
                )
            return True
        
        # Local is ahead - remote should match an earlier entry
        if local_head.sequence > remote_head.sequence:
            local_at_remote_seq = self.get_entry(remote_head.sequence)
            if local_at_remote_seq and local_at_remote_seq.entry_hash != remote_head.entry_hash:
                raise ForkDetected(
                    self._agent_id,
                    expected_hash=remote_head.entry_hash,
                    actual_hash=local_at_remote_seq.entry_hash,
                    sequence=remote_head.sequence,
                )
            return True
        
        # Local is behind - OK, we might need to sync
        return True
    
    def get_entry(self, sequence: int) -> StateEntry | None:
        """
        Get entry by sequence number.
        
        Args:
            sequence: Entry sequence number
            
        Returns:
            StateEntry or None if not found
        """
        if sequence < 0 or sequence >= len(self._entries):
            return None
        return self._entries[sequence]
    
    def get_entries(
        self,
        start_sequence: int = 0,
        end_sequence: int | None = None,
    ) -> list[StateEntry]:
        """
        Get range of entries.
        
        Args:
            start_sequence: First entry sequence (inclusive)
            end_sequence: Last entry sequence (exclusive), None for all
            
        Returns:
            List of StateEntry
        """
        end = end_sequence if end_sequence is not None else len(self._entries)
        return self._entries[start_sequence:end]
    
    def __iter__(self) -> Iterator[StateEntry]:
        """Iterate over all entries."""
        return iter(self._entries)
    
    def __len__(self) -> int:
        """Get chain length."""
        return len(self._entries)
    
    def __getitem__(self, index: int) -> StateEntry:
        """Get entry by index."""
        return self._entries[index]
    
    # ========== File Locking ==========

    def _acquire_file_lock(self, path: Path, exclusive: bool = True) -> int:
        """
        Acquire file lock for safe concurrent access.

        Args:
            path: Path to the file being protected
            exclusive: True for write lock, False for read lock

        Returns:
            File descriptor for the lock file
        """
        lock_path = path.with_suffix(".lock")
        fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)

        try:
            if platform.system() == "Windows":
                # Windows doesn't have fcntl, use msvcrt
                import msvcrt
                if exclusive:
                    msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                else:
                    msvcrt.locking(fd, msvcrt.LK_NBRLCK, 1)
            else:
                # Unix-like systems use fcntl
                lock_type = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
                fcntl.flock(fd, lock_type)
            return fd
        except Exception:
            os.close(fd)
            raise

    def _release_file_lock(self, fd: int) -> None:
        """Release file lock."""
        try:
            if platform.system() == "Windows":
                import msvcrt
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    # ========== Write-Ahead Logging ==========

    def _save_to_file_with_wal(self, path: Path) -> None:
        """
        Save chain with write-ahead logging for crash recovery.

        Steps:
        1. Acquire exclusive file lock
        2. Write to WAL file
        3. Sync WAL to disk
        4. Write to temp file
        5. Sync temp to disk
        6. Atomic rename temp -> final
        7. Delete WAL
        8. Release lock
        """
        lock_fd = self._acquire_file_lock(path, exclusive=True)

        try:
            data = {
                "agent_id": self._agent_id,
                "entries": [e.to_dict() for e in self._entries],
                "version": 1,
            }

            wal_path = path.with_suffix(".wal")
            temp_path = path.with_suffix(".tmp")

            # Step 2-3: Write and sync WAL
            with open(wal_path, "w") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # Step 4-5: Write and sync temp file
            with open(temp_path, "w") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            # Step 6: Atomic rename
            temp_path.rename(path)

            # Sync directory to ensure rename is durable
            try:
                dir_fd = os.open(str(path.parent), os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except (OSError, PermissionError):
                # Directory sync may fail on some systems, not critical
                pass

            # Step 7: Delete WAL
            if wal_path.exists():
                wal_path.unlink()

        finally:
            self._release_file_lock(lock_fd)

    def _save_to_file(self, path: Path) -> None:
        """Save chain to local file (wrapper for backward compatibility)."""
        self._save_to_file_with_wal(path)

    def _load_from_file_with_lock(self, path: Path) -> None:
        """Load chain with file locking and WAL recovery."""
        lock_fd = self._acquire_file_lock(path, exclusive=False)

        try:
            # Check for WAL recovery (crash during previous write)
            wal_path = path.with_suffix(".wal")
            if wal_path.exists():
                # Need exclusive lock for recovery
                self._release_file_lock(lock_fd)
                lock_fd = self._acquire_file_lock(path, exclusive=True)
                self._recover_from_wal(path, wal_path)
                # Downgrade to shared lock for reading
                self._release_file_lock(lock_fd)
                lock_fd = self._acquire_file_lock(path, exclusive=False)

            # Load main file
            with open(path) as f:
                data = json.load(f)

            if data.get("agent_id") != self._agent_id:
                raise StateChainError(
                    f"Chain file agent_id mismatch: {data.get('agent_id')} != {self._agent_id}"
                )

            self._entries = [StateEntry.from_dict(e) for e in data.get("entries", [])]

        finally:
            self._release_file_lock(lock_fd)

    def _load_from_file(self, path: Path) -> None:
        """Load chain from local file (wrapper for backward compatibility)."""
        self._load_from_file_with_lock(path)

    def _recover_from_wal(self, main_path: Path, wal_path: Path) -> None:
        """
        Recover from WAL after crash.

        If WAL exists, it means a write was interrupted. We complete it.
        """
        logger.info(f"Recovering state chain from WAL: {wal_path}")

        try:
            with open(wal_path) as f:
                wal_data = json.load(f)

            # WAL is valid, complete the write
            temp_path = main_path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                json.dump(wal_data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())

            temp_path.rename(main_path)

            # Sync directory
            try:
                dir_fd = os.open(str(main_path.parent), os.O_RDONLY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except (OSError, PermissionError):
                pass

            wal_path.unlink()
            logger.info("WAL recovery completed successfully")

        except (json.JSONDecodeError, IOError) as e:
            # WAL is corrupted, just delete it
            logger.warning(f"WAL recovery failed, deleting corrupted WAL: {e}")
            try:
                wal_path.unlink()
            except OSError:
                pass
    
    async def sync_from_authority(self) -> int:
        """
        Sync local chain with Authority's version.
        
        Fetches any entries we're missing from the Authority.
        
        Returns:
            Number of entries synced
            
        Raises:
            ForkDetected: If chains have diverged
            StateChainError: If sync fails
        """
        if not self._authority:
            raise StateChainError("No authority configured for sync")
        
        # Get remote head
        remote_head = await self._authority.get_state_head(self._agent_id)
        
        if remote_head is None:
            return 0  # No remote state
        
        # Check for fork
        self.verify_against_remote(remote_head)
        
        # If we're behind, fetch missing entries
        local_seq = self.sequence
        remote_seq = remote_head.sequence
        
        if local_seq >= remote_seq:
            return 0  # Up to date
        
        # Fetch missing entries
        entries = await self._authority.get_state_history(
            self._agent_id,
            start_sequence=local_seq + 1,
            end_sequence=remote_seq + 1,
        )
        
        # Verify and append
        public_key = self._keypair.public_key_bytes()
        for entry in entries:
            # Verify signature
            if not entry.verify_signature(public_key):
                raise InvalidStateEntry(f"Invalid signature on entry {entry.sequence}")
            
            # Verify linkage
            if entry.sequence > 0:
                expected_prev = self.head.entry_hash if self.head else ZERO_HASH
                if entry.prev_hash != expected_prev:
                    raise StateChainBroken(
                        f"Chain broken at entry {entry.sequence}: "
                        f"prev_hash mismatch"
                    )
            
            self._entries.append(entry)
        
        # Save locally
        if self._persistence_path:
            self._save_to_file(self._persistence_path)
        
        return len(entries)

    async def ensure_synced(self) -> None:
        """
        Ensure local chain is synced with Authority on startup.

        Call this after initialization to detect local/remote divergence
        and fetch any missing entries.

        This method is idempotent - calling it multiple times has no effect
        after the first successful sync.

        Raises:
            ForkDetected: If local and remote chains have diverged
        """
        if self._startup_synced:
            return

        if not self._sync_on_startup:
            self._startup_synced = True
            return

        if not self._authority:
            self._startup_synced = True
            return

        try:
            # Get remote head
            remote_head = await self._authority.get_state_head(self._agent_id)

            if remote_head is None:
                # No remote state, local chain is authoritative
                self._startup_synced = True
                logger.debug(f"No remote state for {self._agent_id}, local chain is authoritative")
                return

            # Check for fork (raises ForkDetected if diverged)
            self.verify_against_remote(remote_head)

            # Sync missing entries if we're behind
            synced = await self.sync_from_authority()
            if synced > 0:
                logger.info(f"Synced {synced} entries from Authority for {self._agent_id}")

            self._startup_synced = True

        except ForkDetected:
            # Re-raise - caller must handle fork resolution
            logger.error(f"Fork detected for {self._agent_id} during startup sync")
            raise
        except Exception as e:
            # Log warning but don't fail startup for transient errors
            # (network issues, Authority temporarily down, etc.)
            logger.warning(f"Failed to sync with Authority on startup: {e}")
            # Don't mark as synced - will retry on next call

    @property
    def is_synced(self) -> bool:
        """Check if startup sync has been completed."""
        return self._startup_synced

    def to_dict(self) -> dict[str, Any]:
        """Convert chain to dictionary."""
        return {
            "agent_id": self._agent_id,
            "length": len(self._entries),
            "head": self.head.to_dict() if self.head else None,
            "entries": [e.to_dict() for e in self._entries],
        }
