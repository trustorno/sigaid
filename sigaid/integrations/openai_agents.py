"""OpenAI Agents SDK integration for one-line SigAid wrapping."""

from __future__ import annotations

import asyncio
import functools
from typing import TYPE_CHECKING, Any

from sigaid.integrations.base import BaseIntegration
from sigaid.models.state import ActionType

if TYPE_CHECKING:
    from sigaid.client.agent import AgentClient


class OpenAIAgentsIntegration(BaseIntegration):
    """OpenAI Agents SDK integration."""
    
    @classmethod
    def can_wrap(cls, agent: Any) -> bool:
        """Check if agent is an OpenAI Agents SDK agent."""
        type_name = type(agent).__module__ + "." + type(agent).__name__
        return "openai" in type_name.lower() and "agent" in type_name.lower()
    
    @classmethod
    def wrap(cls, agent: Any, sigaid_client: AgentClient) -> Any:
        """Wrap OpenAI Agents SDK agent with SigAid identity."""
        
        # Wrap run method
        if hasattr(agent, "run"):
            original_run = agent.run
            
            @functools.wraps(original_run)
            async def wrapped_run(*args, **kwargs):
                async with sigaid_client.lease():
                    await sigaid_client.record_action(
                        ActionType.TASK_START.value,
                        {
                            "agent_id": getattr(agent, "id", "unknown"),
                            "model": getattr(agent, "model", "unknown"),
                        },
                        sync=False,
                    )
                    
                    result = await original_run(*args, **kwargs)
                    
                    await sigaid_client.record_action(
                        ActionType.TASK_COMPLETE.value,
                        {
                            "status": getattr(result, "status", "complete") if result else "complete",
                        },
                        sync=False,
                    )
                    
                    return result
            
            agent.run = wrapped_run
        
        # Wrap stream method if present
        if hasattr(agent, "stream"):
            original_stream = agent.stream
            
            @functools.wraps(original_stream)
            async def wrapped_stream(*args, **kwargs):
                if sigaid_client.is_holding_lease:
                    await sigaid_client.record_action(
                        ActionType.TASK_START.value,
                        {"type": "stream"},
                        sync=False,
                    )
                
                async for chunk in original_stream(*args, **kwargs):
                    yield chunk
                
                if sigaid_client.is_holding_lease:
                    await sigaid_client.record_action(
                        ActionType.TASK_COMPLETE.value,
                        {"type": "stream_complete"},
                        sync=False,
                    )
            
            agent.stream = wrapped_stream
        
        agent._sigaid = sigaid_client
        return agent


def wrap_openai_agent(
    agent: Any,
    *,
    authority_url: str | None = None,
    api_key: str | None = None,
    agent_name: str | None = None,
) -> Any:
    """
    Wrap an OpenAI Agents SDK agent with SigAid identity.

    Args:
        agent: OpenAI agent to wrap
        authority_url: Authority service URL (or SIGAID_AUTHORITY_URL env var)
                      Defaults to https://api.sigaid.com
        api_key: SigAid API key (or SIGAID_API_KEY env var)
        agent_name: Optional name for this agent

    Returns:
        Wrapped agent with _sigaid attribute

    Example:
        from openai import Agent
        import sigaid

        agent = Agent(...)

        # Using hosted service
        agent = sigaid.wrap(agent, api_key="sk_xxx")

        # Using self-hosted authority
        agent = sigaid.wrap(
            agent,
            authority_url="https://my-authority.com",
            api_key="sk_xxx"
        )

        result = await agent.run("Hello!")
        print(agent._sigaid.agent_id)
    """
    import os
    from sigaid.client.agent import AgentClient
    from sigaid.constants import DEFAULT_AUTHORITY_URL

    authority_url = (
        authority_url
        or os.environ.get("SIGAID_AUTHORITY_URL")
        or DEFAULT_AUTHORITY_URL
    )
    api_key = api_key or os.environ.get("SIGAID_API_KEY")

    client = AgentClient.create(authority_url=authority_url, api_key=api_key)
    return OpenAIAgentsIntegration.wrap(agent, client)
