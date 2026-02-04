"""Ed25519 key generation and management."""

from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from sigaid.constants import (
    ED25519_SEED_SIZE,
    KEYFILE_VERSION,
    KEYFILE_SCRYPT_N,
    KEYFILE_SCRYPT_R,
    KEYFILE_SCRYPT_P,
)
from sigaid.exceptions import InvalidKey, CryptoError

if TYPE_CHECKING:
    from sigaid.identity.agent_id import AgentID


class KeyPair:
    """Ed25519 keypair for agent identity.

    Example:
        # Generate new keypair
        keypair = KeyPair.generate()

        # Get agent ID
        agent_id = keypair.to_agent_id()

        # Sign a message
        signature = keypair.sign(b"hello world", domain="myapp.v1")

        # Save to encrypted file
        keypair.to_encrypted_file(Path("agent.key"), "mypassword")

        # Load from encrypted file
        keypair = KeyPair.from_encrypted_file(Path("agent.key"), "mypassword")
    """

    def __init__(self, private_key: Ed25519PrivateKey):
        """Initialize with an Ed25519 private key.

        Args:
            private_key: Ed25519 private key instance
        """
        self._private_key = private_key
        self._public_key = private_key.public_key()

    @classmethod
    def generate(cls) -> KeyPair:
        """Generate a new random keypair.

        Returns:
            New KeyPair instance with randomly generated keys
        """
        private_key = Ed25519PrivateKey.generate()
        return cls(private_key)

    @classmethod
    def from_seed(cls, seed: bytes) -> KeyPair:
        """Derive keypair from 32-byte seed (deterministic).

        Args:
            seed: 32-byte seed value

        Returns:
            KeyPair derived from the seed

        Raises:
            InvalidKey: If seed is not exactly 32 bytes
        """
        if len(seed) != ED25519_SEED_SIZE:
            raise InvalidKey(f"Seed must be {ED25519_SEED_SIZE} bytes, got {len(seed)}")
        private_key = Ed25519PrivateKey.from_private_bytes(seed)
        return cls(private_key)

    @classmethod
    def from_private_bytes(cls, data: bytes) -> KeyPair:
        """Load from raw private key bytes.

        Args:
            data: 32-byte raw private key

        Returns:
            KeyPair instance

        Raises:
            InvalidKey: If data is invalid
        """
        if len(data) != ED25519_SEED_SIZE:
            raise InvalidKey(f"Private key must be {ED25519_SEED_SIZE} bytes, got {len(data)}")
        try:
            private_key = Ed25519PrivateKey.from_private_bytes(data)
            return cls(private_key)
        except Exception as e:
            raise InvalidKey(f"Invalid private key bytes: {e}") from e

    def sign(self, message: bytes, domain: str = "") -> bytes:
        """Sign message with optional domain separation.

        Domain separation prevents cross-protocol signature attacks by
        prefixing messages with a domain tag.

        Args:
            message: The message to sign
            domain: Optional domain tag for separation (e.g., "sigaid.lease.v1")

        Returns:
            64-byte Ed25519 signature
        """
        if domain:
            domain_bytes = domain.encode("utf-8")
            message = len(domain_bytes).to_bytes(2, "big") + domain_bytes + message
        return self._private_key.sign(message)

    def verify(self, signature: bytes, message: bytes, domain: str = "") -> bool:
        """Verify a signature against this keypair's public key.

        Args:
            signature: The signature to verify
            message: The original message
            domain: Domain tag used when signing (must match)

        Returns:
            True if valid, False otherwise
        """
        if domain:
            domain_bytes = domain.encode("utf-8")
            message = len(domain_bytes).to_bytes(2, "big") + domain_bytes + message
        try:
            self._public_key.verify(signature, message)
            return True
        except Exception:
            return False

    def public_key_bytes(self) -> bytes:
        """Get raw public key bytes (32 bytes).

        Returns:
            32-byte public key
        """
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def private_key_bytes(self) -> bytes:
        """Get raw private key bytes (32 bytes).

        WARNING: Handle with extreme care! Never log or transmit.

        Returns:
            32-byte private key
        """
        return self._private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def to_agent_id(self) -> AgentID:
        """Derive AgentID from public key.

        Returns:
            AgentID instance
        """
        from sigaid.identity.agent_id import AgentID

        return AgentID.from_public_key(self.public_key_bytes())

    def to_encrypted_file(self, path: Path, password: str) -> None:
        """Save keypair to encrypted file.

        Uses scrypt for key derivation and ChaCha20-Poly1305 for encryption.

        Args:
            path: File path to write
            password: Encryption password
        """
        # Generate salt and nonce
        salt = secrets.token_bytes(32)
        nonce = secrets.token_bytes(12)  # ChaCha20-Poly1305 uses 12-byte nonce

        # Derive encryption key using scrypt
        kdf = Scrypt(
            salt=salt,
            length=32,
            n=KEYFILE_SCRYPT_N,
            r=KEYFILE_SCRYPT_R,
            p=KEYFILE_SCRYPT_P,
        )
        key = kdf.derive(password.encode("utf-8"))

        # Encrypt private key
        cipher = ChaCha20Poly1305(key)
        ciphertext = cipher.encrypt(nonce, self.private_key_bytes(), None)

        # Build keyfile
        import base64

        keyfile = {
            "version": KEYFILE_VERSION,
            "algorithm": "scrypt-chacha20poly1305",
            "scrypt_params": {
                "n": KEYFILE_SCRYPT_N,
                "r": KEYFILE_SCRYPT_R,
                "p": KEYFILE_SCRYPT_P,
            },
            "salt": base64.b64encode(salt).decode("ascii"),
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
        }

        path.write_text(json.dumps(keyfile, indent=2))

    @classmethod
    def from_encrypted_file(cls, path: Path, password: str) -> KeyPair:
        """Load keypair from encrypted file.

        Args:
            path: File path to read
            password: Decryption password

        Returns:
            Decrypted KeyPair

        Raises:
            CryptoError: If decryption fails
        """
        import base64

        keyfile = json.loads(path.read_text())

        if keyfile.get("version") != KEYFILE_VERSION:
            raise CryptoError(f"Unsupported keyfile version: {keyfile.get('version')}")

        # Extract parameters
        salt = base64.b64decode(keyfile["salt"])
        nonce = base64.b64decode(keyfile["nonce"])
        ciphertext = base64.b64decode(keyfile["ciphertext"])
        scrypt_params = keyfile["scrypt_params"]

        # Derive key
        kdf = Scrypt(
            salt=salt,
            length=32,
            n=scrypt_params["n"],
            r=scrypt_params["r"],
            p=scrypt_params["p"],
        )
        key = kdf.derive(password.encode("utf-8"))

        # Decrypt
        try:
            cipher = ChaCha20Poly1305(key)
            private_key_bytes = cipher.decrypt(nonce, ciphertext, None)
        except Exception as e:
            raise CryptoError(f"Decryption failed (wrong password?): {e}") from e

        return cls.from_private_bytes(private_key_bytes)

    def __repr__(self) -> str:
        """String representation (safe, shows only agent ID)."""
        return f"KeyPair(agent_id={self.to_agent_id()})"


def public_key_from_bytes(data: bytes) -> Ed25519PublicKey:
    """Create public key from raw bytes.

    Args:
        data: 32-byte raw public key

    Returns:
        Ed25519PublicKey instance

    Raises:
        InvalidKey: If data is invalid
    """
    from sigaid.constants import ED25519_PUBLIC_KEY_SIZE

    if len(data) != ED25519_PUBLIC_KEY_SIZE:
        raise InvalidKey(f"Public key must be {ED25519_PUBLIC_KEY_SIZE} bytes, got {len(data)}")
    try:
        return Ed25519PublicKey.from_public_bytes(data)
    except Exception as e:
        raise InvalidKey(f"Invalid public key bytes: {e}") from e
