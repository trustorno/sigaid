"""HTTP client for Authority API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from sigaid.exceptions import (
    NetworkError,
    AuthorityUnavailable,
    RateLimitExceeded,
    RequestTimeout,
    ServerError,
    ClientError,
)
from sigaid.client.retry import with_retry, RetryConfig

logger = logging.getLogger(__name__)


class HttpClient:
    """Async HTTP client for Authority API communication.

    Example:
        client = HttpClient("https://api.sigaid.com")

        response = await client.get("/v1/agents/aid_xxx")
        print(response)

        await client.close()
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        api_key: str | None = None,
    ):
        """Initialize HTTP client.

        Args:
            base_url: Base URL for API
            timeout: Request timeout in seconds
            api_key: Optional API key for authentication
        """
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            headers = {}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"

            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers=headers,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make GET request.

        Args:
            path: API path
            params: Query parameters
            headers: Additional headers

        Returns:
            JSON response

        Raises:
            NetworkError: On request failure
        """
        return await self._request("GET", path, params=params, headers=headers)

    async def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make POST request.

        Args:
            path: API path
            json: JSON body
            headers: Additional headers

        Returns:
            JSON response

        Raises:
            NetworkError: On request failure
        """
        return await self._request("POST", path, json=json, headers=headers)

    async def put(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make PUT request.

        Args:
            path: API path
            json: JSON body
            headers: Additional headers

        Returns:
            JSON response

        Raises:
            NetworkError: On request failure
        """
        return await self._request("PUT", path, json=json, headers=headers)

    async def delete(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make DELETE request.

        Args:
            path: API path
            json: JSON body
            headers: Additional headers

        Returns:
            JSON response

        Raises:
            NetworkError: On request failure
        """
        return await self._request("DELETE", path, json=json, headers=headers)

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request.

        Args:
            method: HTTP method
            path: API path
            params: Query parameters
            json: JSON body
            headers: Additional headers

        Returns:
            JSON response

        Raises:
            NetworkError: On request failure
            AuthorityUnavailable: If server is unreachable
            RateLimitExceeded: If rate limit is hit
            ServerError: If server returns 5xx
        """
        client = await self._get_client()

        try:
            response = await client.request(
                method=method,
                url=path,
                params=params,
                json=json,
                headers=headers,
            )

            # Log rate limit headers if present
            limit = response.headers.get("X-RateLimit-Limit")
            remaining = response.headers.get("X-RateLimit-Remaining")
            if limit and remaining:
                logger.debug(f"Rate limit: {remaining}/{limit} remaining")

            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 60))
                raise RateLimitExceeded(retry_after=retry_after)

            # Handle server errors (retryable)
            if response.status_code >= 500:
                try:
                    error_data = response.json()
                    message = error_data.get("detail", str(error_data))
                except Exception:
                    message = response.text
                raise ServerError(response.status_code, message)

            # Handle client errors
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    message = error_data.get("detail", str(error_data))
                    if isinstance(message, dict):
                        message = message.get("message", str(message))
                except Exception:
                    error_data = {"error": response.text}
                    message = response.text
                raise ClientError(response.status_code, message, response_data=error_data)

            # Return JSON response
            if response.status_code == 204:
                return {}

            return response.json()

        except httpx.ConnectError as e:
            logger.warning(f"Connection error to {self._base_url}: {e}")
            raise AuthorityUnavailable(f"Cannot connect to Authority: {e}") from e
        except httpx.TimeoutException as e:
            logger.warning(f"Request timeout to {self._base_url}: {e}")
            raise RequestTimeout(f"Request timed out: {e}") from e
        except httpx.HTTPError as e:
            logger.error(f"HTTP error: {e}")
            raise NetworkError(f"HTTP error: {e}") from e

    async def __aenter__(self) -> HttpClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
