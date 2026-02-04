"""Retry logic for SDK operations."""

import asyncio
import logging
import random
from functools import wraps
from typing import Callable, TypeVar, Awaitable, Type

from sigaid.exceptions import (
    NetworkError,
    AuthorityUnavailable,
    RateLimitExceeded,
    RetryableError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryConfig:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: tuple[Type[Exception], ...] | None = None,
    ):
        """Initialize retry configuration.

        Args:
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay between retries in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential backoff
            jitter: Whether to add random jitter to delays
            retryable_exceptions: Exceptions that should trigger retry
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or (
            NetworkError,
            AuthorityUnavailable,
            RateLimitExceeded,
            RetryableError,
            ConnectionError,
            TimeoutError,
        )

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt number.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        delay = self.base_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add up to 25% jitter
            delay = delay * (0.75 + random.random() * 0.5)

        return delay


# Default configuration
DEFAULT_RETRY_CONFIG = RetryConfig()


def with_retry(
    config: RetryConfig | None = None,
    on_retry: Callable[[int, Exception, float], None] | None = None,
):
    """Decorator to add retry logic to async functions.

    Args:
        config: Retry configuration
        on_retry: Callback called before each retry (attempt, exception, delay)

    Example:
        @with_retry()
        async def make_request():
            ...

        @with_retry(RetryConfig(max_retries=5))
        async def important_operation():
            ...
    """
    config = config or DEFAULT_RETRY_CONFIG

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception: Exception | None = None

            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e

                    if attempt < config.max_retries:
                        delay = config.calculate_delay(attempt)

                        if on_retry:
                            on_retry(attempt, e, delay)
                        else:
                            logger.warning(
                                f"Retry {attempt + 1}/{config.max_retries} for "
                                f"{func.__name__} after {delay:.2f}s: {e}"
                            )

                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {config.max_retries} retries failed for "
                            f"{func.__name__}: {e}"
                        )

            raise last_exception

        return wrapper

    return decorator


async def retry_operation(
    operation: Callable[..., Awaitable[T]],
    *args,
    config: RetryConfig | None = None,
    **kwargs,
) -> T:
    """Execute an operation with retry logic.

    Args:
        operation: Async function to execute
        *args: Positional arguments for the operation
        config: Retry configuration
        **kwargs: Keyword arguments for the operation

    Returns:
        Result of the operation

    Example:
        result = await retry_operation(
            client.post,
            "/v1/leases",
            json=data,
            config=RetryConfig(max_retries=5)
        )
    """
    config = config or DEFAULT_RETRY_CONFIG
    last_exception: Exception | None = None

    for attempt in range(config.max_retries + 1):
        try:
            return await operation(*args, **kwargs)
        except config.retryable_exceptions as e:
            last_exception = e

            if attempt < config.max_retries:
                delay = config.calculate_delay(attempt)
                logger.warning(
                    f"Retry {attempt + 1}/{config.max_retries} after "
                    f"{delay:.2f}s: {e}"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {config.max_retries} retries failed: {e}")

    raise last_exception
