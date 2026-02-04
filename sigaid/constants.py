"""Constants for SigAid protocol."""

# Domain separation tags for signatures
DOMAIN_IDENTITY = "sigaid.identity.v1"
DOMAIN_LEASE = "sigaid.lease.v1"
DOMAIN_STATE = "sigaid.state.v1"
DOMAIN_VERIFY = "sigaid.verify.v1"

# AgentID prefix
AGENT_ID_PREFIX = "aid_"

# Key sizes (bytes)
ED25519_SEED_SIZE = 32
ED25519_PUBLIC_KEY_SIZE = 32
ED25519_PRIVATE_KEY_SIZE = 32
ED25519_SIGNATURE_SIZE = 64
BLAKE3_HASH_SIZE = 32

# Lease defaults
DEFAULT_LEASE_TTL_SECONDS = 600  # 10 minutes
DEFAULT_LEASE_RENEWAL_BUFFER_SECONDS = 60  # Renew 1 minute before expiry
MAX_LEASE_TTL_SECONDS = 3600  # 1 hour max

# State chain
GENESIS_PREV_HASH = bytes(32)  # 32 zero bytes for genesis entry

# Rate limits (requests, window_seconds)
RATE_LIMITS = {
    "lease_acquire": (5, 60),
    "lease_renew": (60, 60),
    "state_append": (100, 60),
    "verify": (1000, 60),
}

# Default authority URL
DEFAULT_AUTHORITY_URL = "https://api.sigaid.com"

# Encrypted keyfile
KEYFILE_VERSION = 1
KEYFILE_SCRYPT_N = 2**20  # ~1 second on modern hardware
KEYFILE_SCRYPT_R = 8
KEYFILE_SCRYPT_P = 1
