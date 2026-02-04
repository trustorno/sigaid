"""Secure key storage utilities."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

from sigaid.constants import KEYFILE_VERSION
from sigaid.exceptions import CryptoError, InvalidKey

if TYPE_CHECKING:
    from sigaid.crypto.keys import KeyPair


class SecureKeyStorage:
    """
    Secure storage manager for agent keypairs.
    
    Provides a simple interface for storing and loading encrypted
    keypairs from disk.
    
    Example:
        storage = SecureKeyStorage(Path("~/.sigaid/keys"))
        
        # Store keypair
        storage.save("my-agent", keypair, "password123")
        
        # Load keypair
        keypair = storage.load("my-agent", "password123")
        
        # List stored agents
        for name in storage.list_agents():
            print(name)
    """
    
    def __init__(self, base_path: Path | str):
        """
        Initialize storage with base directory.
        
        Args:
            base_path: Directory for storing key files
        """
        self._base_path = Path(base_path).expanduser()
        self._base_path.mkdir(parents=True, exist_ok=True)
        
        # Set restrictive permissions on the directory
        try:
            os.chmod(self._base_path, 0o700)
        except OSError:
            pass  # May fail on Windows
    
    def _key_path(self, name: str) -> Path:
        """Get path for a named keypair."""
        # Sanitize name
        safe_name = "".join(c for c in name if c.isalnum() or c in "-_")
        if not safe_name:
            raise ValueError("Invalid key name")
        return self._base_path / f"{safe_name}.key"
    
    def save(self, name: str, keypair: KeyPair, password: str) -> Path:
        """
        Save keypair to encrypted file.
        
        Args:
            name: Human-readable name for this keypair
            keypair: KeyPair to store
            password: Encryption password
            
        Returns:
            Path to saved file
        """
        path = self._key_path(name)
        keypair.to_encrypted_file(path, password)
        
        # Set restrictive permissions
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        
        return path
    
    def load(self, name: str, password: str) -> KeyPair:
        """
        Load keypair from encrypted file.
        
        Args:
            name: Name of stored keypair
            password: Decryption password
            
        Returns:
            KeyPair instance
            
        Raises:
            FileNotFoundError: If keypair doesn't exist
            CryptoError: If decryption fails
        """
        from sigaid.crypto.keys import KeyPair
        
        path = self._key_path(name)
        if not path.exists():
            raise FileNotFoundError(f"No keypair found with name: {name}")
        
        return KeyPair.from_encrypted_file(path, password)
    
    def exists(self, name: str) -> bool:
        """Check if a named keypair exists."""
        return self._key_path(name).exists()
    
    def delete(self, name: str) -> bool:
        """
        Delete a stored keypair.
        
        Args:
            name: Name of keypair to delete
            
        Returns:
            True if deleted, False if didn't exist
        """
        path = self._key_path(name)
        if path.exists():
            path.unlink()
            return True
        return False
    
    def list_agents(self) -> list[str]:
        """
        List all stored agent names.
        
        Returns:
            List of agent names (without .key extension)
        """
        return [
            p.stem for p in self._base_path.glob("*.key")
            if p.is_file()
        ]
    
    def get_agent_id(self, name: str, password: str) -> str:
        """
        Get AgentID for a stored keypair without fully loading it.
        
        Args:
            name: Name of stored keypair
            password: Decryption password
            
        Returns:
            AgentID string
        """
        keypair = self.load(name, password)
        return str(keypair.to_agent_id())
    
    @property
    def base_path(self) -> Path:
        """Get the base storage path."""
        return self._base_path


def get_default_storage() -> SecureKeyStorage:
    """
    Get the default key storage location.
    
    Default is ~/.sigaid/keys
    
    Returns:
        SecureKeyStorage instance
    """
    return SecureKeyStorage(Path.home() / ".sigaid" / "keys")
