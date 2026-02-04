"""Ed25519 signature operations with domain separation."""

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from sigaid.exceptions import InvalidSignature


def _apply_domain(message: bytes, domain: str) -> bytes:
    """Apply domain separation to a message.

    Format: [2-byte domain length][domain bytes][message]

    Args:
        message: Original message
        domain: Domain tag

    Returns:
        Domain-prefixed message
    """
    if not domain:
        return message
    domain_bytes = domain.encode("utf-8")
    return len(domain_bytes).to_bytes(2, "big") + domain_bytes + message


def sign(private_key: Ed25519PrivateKey, message: bytes) -> bytes:
    """Sign a message without domain separation.

    Args:
        private_key: Ed25519 private key
        message: Message to sign

    Returns:
        64-byte signature
    """
    return private_key.sign(message)


def verify(public_key: Ed25519PublicKey, signature: bytes, message: bytes) -> bool:
    """Verify a signature without domain separation.

    Args:
        public_key: Ed25519 public key
        signature: Signature to verify
        message: Original message

    Returns:
        True if valid

    Raises:
        InvalidSignature: If signature is invalid
    """
    try:
        public_key.verify(signature, message)
        return True
    except Exception as e:
        raise InvalidSignature(f"Signature verification failed: {e}") from e


def sign_with_domain(private_key: Ed25519PrivateKey, message: bytes, domain: str) -> bytes:
    """Sign a message with domain separation.

    Domain separation prevents cross-protocol signature reuse attacks.

    Args:
        private_key: Ed25519 private key
        message: Message to sign
        domain: Domain tag (e.g., "sigaid.lease.v1")

    Returns:
        64-byte signature
    """
    tagged_message = _apply_domain(message, domain)
    return private_key.sign(tagged_message)


def verify_with_domain(
    public_key: Ed25519PublicKey, signature: bytes, message: bytes, domain: str
) -> bool:
    """Verify a signature with domain separation.

    Args:
        public_key: Ed25519 public key
        signature: Signature to verify
        message: Original message (without domain prefix)
        domain: Domain tag used when signing

    Returns:
        True if valid

    Raises:
        InvalidSignature: If signature is invalid
    """
    tagged_message = _apply_domain(message, domain)
    try:
        public_key.verify(signature, tagged_message)
        return True
    except Exception as e:
        raise InvalidSignature(f"Signature verification failed: {e}") from e


def verify_with_domain_safe(
    public_key: Ed25519PublicKey, signature: bytes, message: bytes, domain: str
) -> bool:
    """Verify a signature with domain separation (no exception on failure).

    Args:
        public_key: Ed25519 public key
        signature: Signature to verify
        message: Original message
        domain: Domain tag

    Returns:
        True if valid, False otherwise
    """
    try:
        verify_with_domain(public_key, signature, message, domain)
        return True
    except InvalidSignature:
        return False
