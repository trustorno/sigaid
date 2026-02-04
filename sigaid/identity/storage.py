"""Secure key storage utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sigaid.crypto.keys import KeyPair


def get_default_keyfile_path() -> Path:
    """Get the default path for agent keyfile.

    Uses XDG_DATA_HOME on Linux, ~/Library/Application Support on macOS,
    and APPDATA on Windows.

    Returns:
        Path to default keyfile location
    """
    if os.name == "nt":
        # Windows
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif os.name == "posix":
        if "darwin" in os.uname().sysname.lower():
            # macOS
            base = Path.home() / "Library" / "Application Support"
        else:
            # Linux/Unix
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    else:
        base = Path.home()

    return base / "sigaid" / "agent.key"


def ensure_keyfile_dir(path: Path) -> None:
    """Ensure the directory for a keyfile exists with secure permissions.

    Args:
        path: Path to keyfile
    """
    directory = path.parent
    directory.mkdir(parents=True, exist_ok=True)

    # Set restrictive permissions on Unix
    if os.name == "posix":
        os.chmod(directory, 0o700)


def load_or_create_keypair(
    path: Path | None = None,
    password: str | None = None,
    create_if_missing: bool = True,
) -> KeyPair:
    """Load keypair from file, or create new one if missing.

    Args:
        path: Path to keyfile (uses default if None)
        password: Password for encryption/decryption
        create_if_missing: Whether to create a new keypair if file doesn't exist

    Returns:
        KeyPair instance

    Raises:
        FileNotFoundError: If file doesn't exist and create_if_missing is False
        ValueError: If password is required but not provided
    """
    from sigaid.crypto.keys import KeyPair

    if path is None:
        path = get_default_keyfile_path()

    if path.exists():
        if password is None:
            raise ValueError("Password required to decrypt existing keyfile")
        return KeyPair.from_encrypted_file(path, password)

    if not create_if_missing:
        raise FileNotFoundError(f"Keyfile not found: {path}")

    # Create new keypair
    keypair = KeyPair.generate()

    if password is not None:
        ensure_keyfile_dir(path)
        keypair.to_encrypted_file(path, password)

    return keypair


def delete_keyfile(path: Path | None = None) -> bool:
    """Securely delete a keyfile.

    Overwrites the file with random data before deletion.

    Args:
        path: Path to keyfile (uses default if None)

    Returns:
        True if file was deleted, False if it didn't exist
    """
    import secrets

    if path is None:
        path = get_default_keyfile_path()

    if not path.exists():
        return False

    # Overwrite with random data
    size = path.stat().st_size
    path.write_bytes(secrets.token_bytes(size))

    # Delete
    path.unlink()
    return True
