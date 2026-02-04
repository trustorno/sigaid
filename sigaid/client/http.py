"""HTTP transport for API calls."""

from __future__ import annotations

import json
from typing import Any, TypeVar

import httpx

from sigaid.exceptions import AuthorityError, NetworkError, RateLimitExceeded

T = TypeVar("T")


class HTTPClient:
    """
    Async HTTP client for Authority API calls.
    
    Handles:
    - Request signing
    - Error handling
    - Rate limit responses
    - Retries
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize HTTP client.
        
        Args:
            base_url: Authority service base URL
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._max_retries = max_retries
        
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"
            
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=headers,
                timeout=self._timeout,
            )
        return self._client
    
    async def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make GET request.
        
        Args:
            path: API path (e.g., "/v1/agents/aid_xxx")
            params: Query parameters
            
        Returns:
            Response JSON as dict
        """
        client = await self._get_client()
        
        for attempt in range(self._max_retries):
            try:
                response = await client.get(path, params=params)
                return self._handle_response(response)
            except httpx.TimeoutException:
                if attempt == self._max_retries - 1:
                    raise NetworkError(f"Request timeout after {self._max_retries} attempts")
            except httpx.RequestError as e:
                if attempt == self._max_retries - 1:
                    raise NetworkError(f"Request failed: {e}") from e
    
    async def post(
        self,
        path: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make POST request.
        
        Args:
            path: API path
            data: Request body
            
        Returns:
            Response JSON as dict
        """
        client = await self._get_client()
        
        for attempt in range(self._max_retries):
            try:
                response = await client.post(path, json=data)
                return self._handle_response(response)
            except httpx.TimeoutException:
                if attempt == self._max_retries - 1:
                    raise NetworkError(f"Request timeout after {self._max_retries} attempts")
            except httpx.RequestError as e:
                if attempt == self._max_retries - 1:
                    raise NetworkError(f"Request failed: {e}") from e
    
    async def put(
        self,
        path: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make PUT request."""
        client = await self._get_client()
        
        for attempt in range(self._max_retries):
            try:
                response = await client.put(path, json=data)
                return self._handle_response(response)
            except httpx.TimeoutException:
                if attempt == self._max_retries - 1:
                    raise NetworkError(f"Request timeout after {self._max_retries} attempts")
            except httpx.RequestError as e:
                if attempt == self._max_retries - 1:
                    raise NetworkError(f"Request failed: {e}") from e
    
    async def delete(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make DELETE request."""
        client = await self._get_client()
        
        for attempt in range(self._max_retries):
            try:
                response = await client.delete(path, params=params)
                return self._handle_response(response)
            except httpx.TimeoutException:
                if attempt == self._max_retries - 1:
                    raise NetworkError(f"Request timeout after {self._max_retries} attempts")
            except httpx.RequestError as e:
                if attempt == self._max_retries - 1:
                    raise NetworkError(f"Request failed: {e}") from e
    
    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle API response."""
        # Rate limit
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After", "60")
            raise RateLimitExceeded(f"Rate limit exceeded. Retry after {retry_after}s")
        
        # Success
        if 200 <= response.status_code < 300:
            if response.content:
                return response.json()
            return {}
        
        # Error
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", response.text)
        except Exception:
            error_message = response.text
        
        raise AuthorityError(
            f"API error {response.status_code}: {error_message}"
        )
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
