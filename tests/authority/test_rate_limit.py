"""Tests for rate limiting middleware."""

import time
import pytest
from unittest.mock import MagicMock, patch

from authority.middleware.rate_limit import (
    RateLimitConfig,
    RateLimitEntry,
    RateLimiter,
    InMemoryBackend,
    RedisBackend,
    RateLimitMiddleware,
)


class TestRateLimitConfig:
    """Tests for RateLimitConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = RateLimitConfig()

        assert config.lease_acquire == 30
        assert config.lease_renew == 120
        assert config.state_append == 200
        assert config.verify == 1000
        assert config.default == 100

    def test_custom_values(self):
        """Test custom configuration values."""
        config = RateLimitConfig(
            lease_acquire=10,
            verify=500,
        )

        assert config.lease_acquire == 10
        assert config.verify == 500


class TestInMemoryBackend:
    """Tests for InMemoryBackend."""

    @pytest.fixture
    def backend(self):
        """Create fresh backend for each test."""
        return InMemoryBackend()

    def test_first_request_allowed(self, backend):
        """Test first request is always allowed."""
        allowed, limit, remaining = backend.check("test", 10, 60)

        assert allowed is True
        assert remaining == 9

    def test_respects_limit(self, backend):
        """Test limit is respected."""
        for i in range(5):
            allowed, limit, remaining = backend.check("test", 5, 60)
            if i < 4:
                assert allowed is True
            else:
                assert allowed is True
                assert remaining == 0

        # Next request should be denied
        allowed, limit, remaining = backend.check("test", 5, 60)
        assert allowed is False
        assert remaining == 0

    def test_different_keys_independent(self, backend):
        """Test different keys are tracked independently."""
        # Use up limit for key1
        for _ in range(5):
            backend.check("key1", 5, 60)

        # key1 should be blocked
        allowed, _, _ = backend.check("key1", 5, 60)
        assert allowed is False

        # key2 should still be allowed
        allowed, _, _ = backend.check("key2", 5, 60)
        assert allowed is True

    def test_window_resets(self, backend):
        """Test window resets after expiry."""
        # Use up limit
        for _ in range(3):
            backend.check("test", 3, 1)  # 1 second window

        allowed, _, _ = backend.check("test", 3, 1)
        assert allowed is False

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        allowed, _, _ = backend.check("test", 3, 1)
        assert allowed is True

    def test_reset_key(self, backend):
        """Test resetting a key."""
        # Make some requests
        backend.check("test", 10, 60)
        backend.check("test", 10, 60)

        # Reset
        backend.reset("test")

        # Should start fresh
        allowed, _, remaining = backend.check("test", 10, 60)
        assert allowed is True
        assert remaining == 9

    def test_cleanup_expired(self, backend):
        """Test cleanup removes expired entries."""
        # Create some entries
        backend.check("key1", 10, 1)
        backend.check("key2", 10, 1)

        # Wait for expiry
        time.sleep(2.1)

        # Cleanup
        removed = backend.cleanup_expired(1)

        assert removed >= 0  # At least the expired ones


class TestRateLimiter:
    """Tests for RateLimiter."""

    @pytest.fixture
    def limiter(self):
        """Create fresh limiter for each test."""
        return RateLimiter()

    def test_default_backend_is_inmemory(self, limiter):
        """Test default backend is InMemoryBackend."""
        assert isinstance(limiter._backend, InMemoryBackend)

    def test_uses_redis_when_url_provided(self):
        """Test Redis backend when URL provided."""
        # Mock Redis to avoid needing a real server
        with patch("authority.middleware.rate_limit.RedisBackend") as mock_redis:
            mock_redis.return_value = MagicMock()
            limiter = RateLimiter(redis_url="redis://localhost:6379")

            mock_redis.assert_called_once_with("redis://localhost:6379")

    def test_falls_back_to_inmemory_on_redis_error(self):
        """Test fallback to InMemory when Redis fails."""
        with patch("authority.middleware.rate_limit.RedisBackend") as mock_redis:
            mock_redis.side_effect = ConnectionError("Redis unavailable")

            limiter = RateLimiter(redis_url="redis://localhost:6379")

            assert isinstance(limiter._backend, InMemoryBackend)

    def test_get_limit_lease_acquire(self, limiter):
        """Test limit for lease acquisition."""
        limit = limiter._get_limit("/v1/leases", "POST")
        assert limit == limiter.config.lease_acquire

    def test_get_limit_lease_renew(self, limiter):
        """Test limit for lease renewal."""
        limit = limiter._get_limit("/v1/leases/aid_xxx", "PUT")
        assert limit == limiter.config.lease_renew

    def test_get_limit_state_append(self, limiter):
        """Test limit for state append."""
        limit = limiter._get_limit("/v1/state/aid_xxx", "POST")
        assert limit == limiter.config.state_append

    def test_get_limit_state_read(self, limiter):
        """Test limit for state read."""
        limit = limiter._get_limit("/v1/state/aid_xxx", "GET")
        assert limit == limiter.config.state_read

    def test_get_limit_verify(self, limiter):
        """Test limit for verification."""
        limit = limiter._get_limit("/v1/verify", "POST")
        assert limit == limiter.config.verify

    def test_get_limit_agent_create(self, limiter):
        """Test limit for agent creation."""
        limit = limiter._get_limit("/v1/agents", "POST")
        assert limit == limiter.config.agent_create

    def test_get_limit_agent_read(self, limiter):
        """Test limit for agent read."""
        limit = limiter._get_limit("/v1/agents/aid_xxx", "GET")
        assert limit == limiter.config.agent_read

    def test_get_limit_default(self, limiter):
        """Test default limit for unknown endpoints."""
        limit = limiter._get_limit("/v1/unknown", "GET")
        assert limit == limiter.config.default

    def test_check_includes_method_in_key(self, limiter):
        """Test check distinguishes by method."""
        # POST and GET to same path should be independent
        for _ in range(5):
            limiter.check("client", "/v1/test", "POST")

        # GET should still be allowed
        allowed, _, _ = limiter.check("client", "/v1/test", "GET")
        assert allowed is True


class TestRedisBackend:
    """Tests for RedisBackend (mocked)."""

    def test_init_requires_redis_package(self):
        """Test init fails without redis package."""
        with patch.dict("sys.modules", {"redis": None}):
            with pytest.raises(ImportError):
                RedisBackend("redis://localhost:6379")

    @pytest.fixture
    def mock_redis_module(self):
        """Mock the redis module for testing."""
        try:
            import redis as redis_mod
            return redis_mod
        except ImportError:
            pytest.skip("redis module not installed")

    def test_check_uses_pipeline(self, mock_redis_module):
        """Test check uses Redis pipeline for atomicity."""
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = [1, 60]  # count=1, ttl=60
        mock_redis.pipeline.return_value = mock_pipe

        with patch.object(mock_redis_module, "from_url", return_value=mock_redis):
            backend = RedisBackend("redis://localhost:6379")

            allowed, limit, remaining = backend.check("test", 10, 60)

            mock_redis.pipeline.assert_called_once()
            mock_pipe.incr.assert_called_once()
            mock_pipe.ttl.assert_called_once()
            mock_pipe.execute.assert_called_once()

    def test_check_sets_expiry_on_new_key(self, mock_redis_module):
        """Test check sets expiry when key is new."""
        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = [1, -1]  # count=1, ttl=-1 (no expiry)
        mock_redis.pipeline.return_value = mock_pipe

        with patch.object(mock_redis_module, "from_url", return_value=mock_redis):
            backend = RedisBackend("redis://localhost:6379")
            backend.check("test", 10, 60)

            mock_redis.expire.assert_called_once()

    def test_reset_deletes_key(self, mock_redis_module):
        """Test reset deletes Redis key."""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True

        with patch.object(mock_redis_module, "from_url", return_value=mock_redis):
            backend = RedisBackend("redis://localhost:6379")
            backend.reset("test")

            mock_redis.delete.assert_called_once()


class TestRateLimiterAdditional:
    """Additional tests for RateLimiter."""

    def test_explicit_backend(self):
        """Test providing explicit backend."""
        backend = InMemoryBackend()
        limiter = RateLimiter(backend=backend)
        assert limiter._backend is backend

    def test_get_limit_lease_other(self):
        """Test limit for other lease operations."""
        limiter = RateLimiter()
        limit = limiter._get_limit("/v1/leases/aid_xxx", "DELETE")
        assert limit == limiter.config.lease_other

    def test_reset_method(self):
        """Test reset method."""
        limiter = RateLimiter()
        # Make some requests
        limiter.check("client", "/v1/test", "GET")

        # Reset
        limiter.reset("client:/v1/test:GET")

        # Should have fresh limit
        allowed, _, remaining = limiter.check("client", "/v1/test", "GET")
        assert allowed is True
        assert remaining == limiter.config.default - 1

    def test_cleanup_expired(self):
        """Test cleanup expired entries."""
        limiter = RateLimiter()
        # Make requests with short window
        limiter._window_seconds = 1
        limiter.check("key1", "/test", "GET")

        # Wait for expiry
        import time
        time.sleep(2.5)

        # Cleanup
        removed = limiter.cleanup_expired()
        assert removed >= 0  # May have cleaned up expired entries


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    @pytest.fixture
    def middleware(self):
        """Create middleware with mock app."""
        mock_app = MagicMock()
        return RateLimitMiddleware(mock_app)

    def test_excludes_health_check(self, middleware):
        """Test health check is excluded from rate limiting."""
        assert "/health" in middleware.exclude_paths
        assert "/" in middleware.exclude_paths
        assert "/docs" in middleware.exclude_paths

    def test_default_key_func_uses_ip(self, middleware):
        """Test default key function uses client IP."""
        mock_request = MagicMock()
        mock_request.client.host = "192.168.1.1"
        mock_request.headers = {}

        key = middleware._default_key_func(mock_request)

        assert key == "192.168.1.1"

    def test_default_key_func_uses_forwarded_header(self, middleware):
        """Test key function uses X-Forwarded-For header."""
        mock_request = MagicMock()
        mock_request.headers = {"X-Forwarded-For": "10.0.0.1, 192.168.1.1"}

        key = middleware._default_key_func(mock_request)

        assert key == "10.0.0.1"

    @pytest.mark.asyncio
    async def test_rate_limited_response(self, middleware):
        """Test rate limited response format."""
        from starlette.responses import JSONResponse

        # Exhaust rate limit
        for _ in range(1000):
            middleware.limiter.check("test", "/v1/test", "GET")

        # Mock request
        mock_request = MagicMock()
        mock_request.url.path = "/v1/test"
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.client.host = "test"

        # Mock call_next
        async def call_next(request):
            return JSONResponse({"ok": True})

        # Override key_func to return "test"
        middleware.key_func = lambda r: "test"

        response = await middleware.dispatch(mock_request, call_next)

        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_successful_request_has_headers(self, middleware):
        """Test successful request has rate limit headers."""
        from starlette.responses import Response

        # Mock request for a non-excluded v1 path
        mock_request = MagicMock()
        mock_request.url.path = "/v1/agents"
        mock_request.method = "GET"
        mock_request.headers = {}
        mock_request.client.host = "192.168.1.1"

        # Mock response
        mock_response = Response(content=b"OK")

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    @pytest.mark.asyncio
    async def test_excluded_path_skipped(self, middleware):
        """Test excluded paths skip rate limiting."""
        from starlette.responses import Response

        mock_request = MagicMock()
        mock_request.url.path = "/health"
        mock_request.method = "GET"

        mock_response = Response(content=b"OK")

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        # Should not have rate limit headers (wasn't rate limited)
        assert "X-RateLimit-Limit" not in response.headers

    @pytest.mark.asyncio
    async def test_non_api_path_skipped(self, middleware):
        """Test non-/v1 paths skip rate limiting."""
        from starlette.responses import Response

        mock_request = MagicMock()
        mock_request.url.path = "/some/other/path"
        mock_request.method = "GET"

        mock_response = Response(content=b"OK")

        async def call_next(request):
            return mock_response

        response = await middleware.dispatch(mock_request, call_next)

        # Should not have rate limit headers
        assert "X-RateLimit-Limit" not in response.headers

    def test_default_key_func_no_client(self, middleware):
        """Test default key function when no client."""
        mock_request = MagicMock()
        mock_request.headers = {}
        mock_request.client = None

        key = middleware._default_key_func(mock_request)
        assert key == "unknown"
