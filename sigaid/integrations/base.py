"""Base integration class for framework wrappers."""

from __future__ import annotations

import asyncio
import functools
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Generic, TypeVar

if TYPE_CHECKING:
    from sigaid.client.agent import AgentClient

T = TypeVar("T")


class WrappedAgent(Generic[T]):
    """
    Wrapper that adds SigAid identity to any agent.
    
    Preserves the original agent's interface while adding:
    - _sigaid: AgentClient for direct access to SigAid functionality
    - Automatic lease management
    - Action recording
    """
    
    def __init__(self, agent: T, sigaid_client: AgentClient):
        """
        Initialize wrapped agent.
        
        Args:
            agent: Original agent instance
            sigaid_client: SigAid client for identity
        """
        self._agent = agent
        self._sigaid = sigaid_client
    
    @property
    def sigaid(self) -> AgentClient:
        """Get SigAid client for direct access."""
        return self._sigaid
    
    @property
    def agent_id(self) -> str:
        """Get agent ID."""
        return str(self._sigaid.agent_id)
    
    def __getattr__(self, name: str) -> Any:
        """Proxy attribute access to wrapped agent."""
        return getattr(self._agent, name)
    
    def __repr__(self) -> str:
        return f"WrappedAgent({self._agent!r}, sigaid={self._sigaid.agent_id})"


class BaseIntegration(ABC):
    """
    Abstract base class for framework integrations.
    
    Subclasses implement framework-specific wrapping logic.
    """
    
    @classmethod
    @abstractmethod
    def can_wrap(cls, agent: Any) -> bool:
        """
        Check if this integration can wrap the given agent.
        
        Args:
            agent: Agent to check
            
        Returns:
            True if this integration supports the agent type
        """
        pass
    
    @classmethod
    @abstractmethod
    def wrap(
        cls,
        agent: Any,
        sigaid_client: AgentClient,
    ) -> Any:
        """
        Wrap agent with SigAid identity.
        
        Args:
            agent: Agent to wrap
            sigaid_client: SigAid client
            
        Returns:
            Wrapped agent with SigAid integration
        """
        pass
    
    @staticmethod
    def wrap_sync_method(
        method: Callable,
        sigaid_client: AgentClient,
        action_type: str,
    ) -> Callable:
        """
        Wrap a sync method to record actions.
        
        Args:
            method: Original method
            sigaid_client: SigAid client
            action_type: Action type for recording
            
        Returns:
            Wrapped method
        """
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            # Record action (fire and forget)
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(
                        sigaid_client.record_action(action_type, {"args": str(args)[:200]})
                    )
            except Exception:
                pass
            
            return method(*args, **kwargs)
        
        return wrapper
    
    @staticmethod
    def wrap_async_method(
        method: Callable,
        sigaid_client: AgentClient,
        action_type: str,
    ) -> Callable:
        """
        Wrap an async method to record actions.
        
        Args:
            method: Original async method
            sigaid_client: SigAid client
            action_type: Action type for recording
            
        Returns:
            Wrapped async method
        """
        @functools.wraps(method)
        async def wrapper(*args, **kwargs):
            # Record action
            try:
                if sigaid_client.is_holding_lease:
                    await sigaid_client.record_action(
                        action_type,
                        {"args": str(args)[:200]},
                        sync=False,
                    )
            except Exception:
                pass
            
            return await method(*args, **kwargs)
        
        return wrapper
