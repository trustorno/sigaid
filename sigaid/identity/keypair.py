"""KeyPair re-export from crypto module for convenience."""

# Re-export KeyPair from crypto module
# This allows: from sigaid.identity import KeyPair
from sigaid.crypto.keys import KeyPair

__all__ = ["KeyPair"]
