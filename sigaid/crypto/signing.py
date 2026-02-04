"""Ed25519 signature operations with domain separation."""

from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from sigaid.constants import ED25519_PUBLIC_KEY_SIZE, ED25519_SIGNATURE_SIZE
from sigaid.exceptions import InvalidKey, InvalidSignature


def sign(private_key: bytes | Ed25519PrivateKey, message: bytes) -> bytes:
    """
    Sign message using Ed25519.
    
    Args:
        private_key: 32-byte private key or Ed25519PrivateKey instance
        message: Message to sign
        
    Returns:
        64-byte signature
    """
    if isinstance(private_key, bytes):
        private_key = Ed25519PrivateKey.from_private_bytes(private_key)
    return private_key.sign(message)


def verify(public_key: bytes | Ed25519PublicKey, signature: bytes, message: bytes) -> bool:
    """
    Verify Ed25519 signature.
    
    Args:
        public_key: 32-byte public key or Ed25519PublicKey instance
        signature: 64-byte signature
        message: Original message
        
    Returns:
        True if valid, False otherwise
    """
    if len(signature) != ED25519_SIGNATURE_SIZE:
        return False
    
    if isinstance(public_key, bytes):
        if len(public_key) != ED25519_PUBLIC_KEY_SIZE:
            return False
        try:
            public_key = Ed25519PublicKey.from_public_bytes(public_key)
        except Exception:
            return False
    
    try:
        public_key.verify(signature, message)
        return True
    except Exception:
        return False


def sign_with_domain(
    private_key: bytes | Ed25519PrivateKey, message: bytes, domain: str
) -> bytes:
    """
    Sign message with domain separation.
    
    Domain separation prevents cross-protocol signature replay attacks
    by prefixing messages with a domain-specific tag.
    
    Format: [2-byte domain length][domain bytes][message bytes]
    
    Args:
        private_key: 32-byte private key or Ed25519PrivateKey instance
        message: Message to sign
        domain: Domain string (e.g., "sigaid.identity.v1")
        
    Returns:
        64-byte signature
    """
    if isinstance(private_key, bytes):
        private_key = Ed25519PrivateKey.from_private_bytes(private_key)
    
    tagged_message = _create_tagged_message(message, domain)
    return private_key.sign(tagged_message)


def verify_with_domain(
    public_key: bytes | Ed25519PublicKey,
    signature: bytes,
    message: bytes,
    domain: str,
) -> bool:
    """
    Verify domain-separated signature.
    
    Args:
        public_key: 32-byte public key or Ed25519PublicKey instance
        signature: 64-byte signature
        message: Original message
        domain: Domain string used during signing
        
    Returns:
        True if valid, False otherwise
    """
    if len(signature) != ED25519_SIGNATURE_SIZE:
        return False
    
    if isinstance(public_key, bytes):
        if len(public_key) != ED25519_PUBLIC_KEY_SIZE:
            return False
        try:
            public_key = Ed25519PublicKey.from_public_bytes(public_key)
        except Exception:
            return False
    
    tagged_message = _create_tagged_message(message, domain)
    
    try:
        public_key.verify(signature, tagged_message)
        return True
    except Exception:
        return False


def _create_tagged_message(message: bytes, domain: str) -> bytes:
    """
    Create domain-tagged message for signing.
    
    Format: [2-byte domain length BE][domain bytes][message bytes]
    """
    domain_bytes = domain.encode("utf-8")
    if len(domain_bytes) > 65535:
        raise ValueError("Domain string too long (max 65535 bytes)")
    return len(domain_bytes).to_bytes(2, "big") + domain_bytes + message


def extract_public_key(private_key: bytes) -> bytes:
    """
    Extract public key from private key bytes.
    
    Args:
        private_key: 32-byte private key
        
    Returns:
        32-byte public key
    """
    from cryptography.hazmat.primitives import serialization
    
    pk = Ed25519PrivateKey.from_private_bytes(private_key)
    return pk.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
