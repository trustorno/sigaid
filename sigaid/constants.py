"""Constants for SigAid protocol."""

# Domain separation strings for signatures
DOMAIN_IDENTITY = "sigaid.identity.v1"
DOMAIN_LEASE = "sigaid.lease.v1"
DOMAIN_STATE = "sigaid.state.v1"
DOMAIN_VERIFY = "sigaid.verify.v1"

# AgentID prefix
AGENT_ID_PREFIX = "aid_"

# Session ID prefix
SESSION_ID_PREFIX = "sid_"

# Default authority URL
DEFAULT_AUTHORITY_URL = "https://api.sigaid.com"

# Lease defaults
DEFAULT_LEASE_TTL_SECONDS = 600  # 10 minutes
DEFAULT_LEASE_RENEWAL_BUFFER_SECONDS = 60  # Renew 1 minute before expiry

# Rate limits (requests, seconds)
RATE_LIMITS = {
    "lease_acquire": (5, 60),    # 5 per minute
    "lease_renew": (60, 60),     # 60 per minute
    "state_append": (100, 60),   # 100 per minute
    "verify": (1000, 60),        # 1000 per minute
}

# Key sizes
ED25519_PRIVATE_KEY_SIZE = 32
ED25519_PUBLIC_KEY_SIZE = 32
ED25519_SIGNATURE_SIZE = 64
BLAKE3_HASH_SIZE = 32
PASETO_KEY_SIZE = 32

# Encrypted keyfile
KEYFILE_VERSION = 1
KEYFILE_ALGORITHM = "scrypt-chacha20poly1305"
SCRYPT_N = 2**20  # ~1 second on modern hardware
SCRYPT_R = 8
SCRYPT_P = 1
