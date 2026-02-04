"""Cryptographic primitives for SigAid protocol."""

from sigaid.crypto.keys import KeyPair
from sigaid.crypto.signing import sign, verify, sign_with_domain, verify_with_domain
from sigaid.crypto.hashing import (
    hash_bytes,
    hash_hex,
    hash_state_entry,
    verify_chain_integrity,
)
from sigaid.crypto.tokens import LeaseTokenManager

__all__ = [
    "KeyPair",
    "sign",
    "verify",
    "sign_with_domain",
    "verify_with_domain",
    "hash_bytes",
    "hash_hex",
    "hash_state_entry",
    "verify_chain_integrity",
    "LeaseTokenManager",
]
