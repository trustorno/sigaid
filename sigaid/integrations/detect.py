"""Auto-detection and wrapping for agent frameworks."""

from __future__ import annotations

import os
from typing import Any

from sigaid.exceptions import SigAidError


def detect_and_wrap(
    agent: Any,
    *,
    api_key: str | None = None,
    agent_name: str | None = None,
) -> Any:
    """
    Auto-detect framework and apply appropriate wrapper.
    
    This is the universal entry point for one-line integration.
    
    Args:
        agent: Any supported agent (LangChain, CrewAI, AutoGen, OpenAI, etc.)
        api_key: SigAid API key (or SIGAID_API_KEY env var)
        agent_name: Optional human-readable name for this agent
        
    Returns:
        Wrapped agent with same interface, now with SigAid identity
        
    Raises:
        TypeError: If agent type is not supported
    
    Example:
        import sigaid
        agent = sigaid.wrap(my_agent)
    """
    from sigaid.client.agent import AgentClient
    
    # Get API key
    api_key = api_key or os.environ.get("SIGAID_API_KEY")
    
    # Create SigAid client
    client = AgentClient.create(api_key=api_key)
    
    # Detect agent type
    agent_type = type(agent).__module__ + "." + type(agent).__name__
    agent_type_lower = agent_type.lower()
    
    # LangChain detection
    if "langchain" in agent_type_lower:
        from sigaid.integrations.langchain import LangChainIntegration
        return LangChainIntegration.wrap(agent, client)
    
    # CrewAI detection
    if "crewai" in agent_type_lower:
        from sigaid.integrations.crewai import CrewAIIntegration
        return CrewAIIntegration.wrap(agent, client)
    
    # AutoGen detection
    if "autogen" in agent_type_lower:
        from sigaid.integrations.autogen import AutoGenIntegration
        return AutoGenIntegration.wrap(agent, client)
    
    # OpenAI Agents detection
    if "openai" in agent_type_lower and "agent" in agent_type_lower:
        from sigaid.integrations.openai_agents import OpenAIAgentsIntegration
        return OpenAIAgentsIntegration.wrap(agent, client)
    
    # Unknown framework
    raise TypeError(
        f"Unknown agent type: {agent_type}. "
        f"Supported frameworks: LangChain, CrewAI, AutoGen, OpenAI Agents. "
        f"For manual wrapping, use sigaid.integrations.<framework>.wrap_<framework>() "
        f"or create an AgentClient directly with sigaid.AgentClient.create()."
    )


def get_supported_frameworks() -> list[str]:
    """
    Get list of supported framework names.
    
    Returns:
        List of framework names
    """
    return ["LangChain", "CrewAI", "AutoGen", "OpenAI Agents"]
