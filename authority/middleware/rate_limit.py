"""Rate limiting middleware for Authority API.

Supports two backends:
- In-memory: Simple, single-instance (default)
- Redis: Distributed, multi-instance (recommended for production)

Enable Redis by setting REDIS_URL in environment.
"""

import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limits per endpoint category."""

    # Requests per minute by endpoint pattern
    lease_acquire: int = 30       # Lease acquisition
    lease_renew: int = 120        # Lease renewal
    lease_other: int = 60         # Other lease operations
    state_append: int = 200       # State chain append
    state_read: int = 500         # State chain read
    verify: int = 1000            # Verification requests
    agent_create: int = 30        # Agent registration
    agent_read: int = 200         # Agent info
    default: int = 100            # Default limit


@dataclass
class RateLimitEntry:
    """Tracking entry for rate limiting."""

    count: int = 0
    window_start: float = field(default_factory=time.time)


class RateLimitBackend(ABC):
    """Abstract base for rate limit backends."""

    @abstractmethod
    def check(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
        """Check if request is allowed.

        Args:
            key: Rate limit key
            limit: Maximum requests per window
            window_seconds: Window duration

        Returns:
            Tuple of (allowed, limit, remaining)
        """
        pass

    @abstractmethod
    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        pass


class InMemoryBackend(RateLimitBackend):
    """In-memory rate limit backend (single instance only)."""

    def __init__(self):
        self._buckets: dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)

    def check(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
        now = time.time()
        entry = self._buckets[key]

        # Reset window if expired
        if now - entry.window_start >= window_seconds:
            entry.count = 0
            entry.window_start = now

        # Check limit
        if entry.count >= limit:
            return False, limit, 0

        # Increment and allow
        entry.count += 1
        remaining = limit - entry.count

        return True, limit, remaining

    def reset(self, key: str) -> None:
        if key in self._buckets:
            del self._buckets[key]

    def cleanup_expired(self, window_seconds: int = 60) -> int:
        """Remove expired entries."""
        now = time.time()
        to_remove = [
            k for k, v in self._buckets.items()
            if now - v.window_start >= window_seconds * 2
        ]
        for k in to_remove:
            del self._buckets[k]
        return len(to_remove)


class RedisBackend(RateLimitBackend):
    """Redis-based rate limit backend (distributed).

    Uses Redis INCR with expiration for atomic rate limiting.
    Suitable for multi-instance deployments.
    """

    def __init__(self, redis_url: str, key_prefix: str = "sigaid:ratelimit:"):
        """Initialize Redis backend.

        Args:
            redis_url: Redis connection URL (e.g., redis://localhost:6379/0)
            key_prefix: Prefix for rate limit keys
        """
        try:
            import redis
            self._redis = redis.from_url(redis_url, decode_responses=True)
            self._key_prefix = key_prefix
            # Test connection
            self._redis.ping()
            logger.info("Redis rate limiting enabled")
        except ImportError:
            raise ImportError("redis package required for Redis rate limiting. Install with: pip install redis")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Redis: {e}")

    def _make_key(self, key: str) -> str:
        """Create Redis key with prefix."""
        return f"{self._key_prefix}{key}"

    def check(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int, int]:
        redis_key = self._make_key(key)

        # Use Redis pipeline for atomic operations
        pipe = self._redis.pipeline()
        pipe.incr(redis_key)
        pipe.ttl(redis_key)
        results = pipe.execute()

        current_count = results[0]
        ttl = results[1]

        # Set expiration if this is a new key
        if ttl == -1:
            self._redis.expire(redis_key, window_seconds)

        # Check limit
        if current_count > limit:
            return False, limit, 0

        remaining = limit - current_count
        return True, limit, remaining

    def reset(self, key: str) -> None:
        redis_key = self._make_key(key)
        self._redis.delete(redis_key)


class RateLimiter:
    """Rate limiter with pluggable backend.

    Automatically uses Redis if REDIS_URL is configured,
    otherwise falls back to in-memory storage.
    """

    def __init__(
        self,
        config: RateLimitConfig | None = None,
        backend: RateLimitBackend | None = None,
        redis_url: Optional[str] = None,
    ):
        """Initialize rate limiter.

        Args:
            config: Rate limit configuration
            backend: Explicit backend to use (overrides redis_url)
            redis_url: Redis URL for distributed rate limiting
        """
        self.config = config or RateLimitConfig()
        self._window_seconds = 60

        # Determine backend
        if backend:
            self._backend = backend
        elif redis_url:
            try:
                self._backend = RedisBackend(redis_url)
            except (ImportError, ConnectionError) as e:
                logger.warning(f"Redis unavailable, falling back to in-memory: {e}")
                self._backend = InMemoryBackend()
        else:
            self._backend = InMemoryBackend()

    def _get_limit(self, path: str, method: str) -> int:
        """Get rate limit for a given endpoint.

        Args:
            path: Request path
            method: HTTP method

        Returns:
            Requests per minute limit
        """
        # Lease endpoints
        if "/leases" in path:
            if method == "POST":
                return self.config.lease_acquire
            elif method == "PUT":
                return self.config.lease_renew
            else:
                return self.config.lease_other

        # State endpoints
        if "/state" in path:
            if method == "POST":
                return self.config.state_append
            else:
                return self.config.state_read

        # Verification
        if "/verify" in path:
            return self.config.verify

        # Agent endpoints
        if "/agents" in path:
            if method == "POST":
                return self.config.agent_create
            else:
                return self.config.agent_read

        return self.config.default

    def check(self, key: str, path: str, method: str) -> tuple[bool, int, int]:
        """Check if request is allowed.

        Args:
            key: Rate limit key (e.g., IP or agent_id)
            path: Request path
            method: HTTP method

        Returns:
            Tuple of (allowed, limit, remaining)
        """
        limit = self._get_limit(path, method)
        bucket_key = f"{key}:{path}:{method}"

        return self._backend.check(bucket_key, limit, self._window_seconds)

    def reset(self, key: str) -> None:
        """Reset rate limit for a key.

        Args:
            key: Rate limit key to reset
        """
        self._backend.reset(key)

    def cleanup_expired(self) -> int:
        """Remove expired entries (in-memory backend only).

        Returns:
            Number of entries removed
        """
        if isinstance(self._backend, InMemoryBackend):
            return self._backend.cleanup_expired(self._window_seconds)
        return 0  # Redis handles expiration automatically


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(
        self,
        app,
        rate_limiter: RateLimiter | None = None,
        key_func: Callable[[Request], str] | None = None,
        exclude_paths: list[str] | None = None,
    ):
        """Initialize middleware.

        Args:
            app: FastAPI application
            rate_limiter: RateLimiter instance (creates default if None)
            key_func: Function to extract rate limit key from request
            exclude_paths: Paths to exclude from rate limiting
        """
        super().__init__(app)
        self.limiter = rate_limiter or RateLimiter()
        self.key_func = key_func or self._default_key_func
        self.exclude_paths = set(exclude_paths or ["/health", "/", "/docs", "/openapi.json"])

    @staticmethod
    def _default_key_func(request: Request) -> str:
        """Default key extraction (uses client IP)."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with rate limiting."""
        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Skip non-API paths
        if not request.url.path.startswith("/v1"):
            return await call_next(request)

        # Get rate limit key
        key = self.key_func(request)

        # Check rate limit
        allowed, limit, remaining = self.limiter.check(
            key, request.url.path, request.method
        )

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Rate limit exceeded",
                    "retry_after": 60,
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + 60),
                    "Retry-After": "60",
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response
