"""AutoGen integration for one-line SigAid wrapping."""

from __future__ import annotations

import asyncio
import functools
from typing import TYPE_CHECKING, Any

from sigaid.integrations.base import BaseIntegration
from sigaid.models.state import ActionType

if TYPE_CHECKING:
    from sigaid.client.agent import AgentClient


class AutoGenIntegration(BaseIntegration):
    """AutoGen framework integration."""
    
    @classmethod
    def can_wrap(cls, agent: Any) -> bool:
        """Check if agent is an AutoGen agent."""
        type_name = type(agent).__module__ + "." + type(agent).__name__
        return "autogen" in type_name.lower()
    
    @classmethod
    def wrap(cls, agent: Any, sigaid_client: AgentClient) -> Any:
        """Wrap AutoGen agent with SigAid identity."""
        type_name = type(agent).__name__
        
        if type_name == "GroupChat":
            return cls._wrap_groupchat(agent, sigaid_client)
        else:
            # ConversableAgent, AssistantAgent, UserProxyAgent, etc.
            return cls._wrap_agent(agent, sigaid_client)
    
    @classmethod
    def _wrap_agent(cls, agent: Any, sigaid_client: AgentClient) -> Any:
        """Wrap AutoGen ConversableAgent."""
        
        # Wrap receive method
        if hasattr(agent, "receive"):
            original_receive = agent.receive
            
            @functools.wraps(original_receive)
            async def wrapped_receive(message, sender, request_reply=None, silent=False):
                if sigaid_client.is_holding_lease:
                    await sigaid_client.record_action(
                        "message_received",
                        {
                            "from": getattr(sender, "name", str(sender)),
                            "content_length": len(str(message)),
                        },
                        sync=False,
                    )
                return await original_receive(message, sender, request_reply, silent)
            
            agent.receive = wrapped_receive
        
        # Wrap generate_reply method
        if hasattr(agent, "generate_reply"):
            original_generate = agent.generate_reply
            
            @functools.wraps(original_generate)
            def wrapped_generate(messages=None, sender=None, **kwargs):
                reply = original_generate(messages, sender, **kwargs)
                
                # Record async
                if sigaid_client.is_holding_lease:
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(
                                sigaid_client.record_action(
                                    "reply_generated",
                                    {
                                        "to": getattr(sender, "name", str(sender)) if sender else "unknown",
                                        "reply_length": len(str(reply)),
                                    },
                                    sync=False,
                                )
                            )
                    except Exception:
                        pass
                
                return reply
            
            agent.generate_reply = wrapped_generate
        
        # Wrap initiate_chat if present
        if hasattr(agent, "initiate_chat"):
            original_initiate = agent.initiate_chat
            
            @functools.wraps(original_initiate)
            def wrapped_initiate(recipient, *args, **kwargs):
                async def _initiate_with_lease():
                    async with sigaid_client.lease():
                        await sigaid_client.record_action(
                            ActionType.TASK_START.value,
                            {
                                "type": "initiate_chat",
                                "recipient": getattr(recipient, "name", str(recipient)),
                            },
                            sync=False,
                        )
                        
                        result = original_initiate(recipient, *args, **kwargs)
                        if asyncio.iscoroutine(result):
                            result = await result
                        
                        await sigaid_client.record_action(
                            ActionType.TASK_COMPLETE.value,
                            {"type": "chat_complete"},
                            sync=False,
                        )
                        
                        return result
                
                return asyncio.run(_initiate_with_lease())
            
            agent.initiate_chat = wrapped_initiate
        
        agent._sigaid = sigaid_client
        return agent
    
    @classmethod
    def _wrap_groupchat(cls, groupchat: Any, sigaid_client: AgentClient) -> Any:
        """Wrap AutoGen GroupChat."""
        # GroupChat doesn't have execution methods - wrap the manager instead
        # For now, just attach the client
        groupchat._sigaid = sigaid_client
        return groupchat


def wrap_autogen(
    agent: Any,
    *,
    authority_url: str | None = None,
    api_key: str | None = None,
    agent_name: str | None = None,
) -> Any:
    """
    Wrap an AutoGen agent with SigAid identity.

    Supports:
    - ConversableAgent
    - AssistantAgent
    - UserProxyAgent
    - GroupChat

    Args:
        agent: AutoGen agent to wrap
        authority_url: Authority service URL (or SIGAID_AUTHORITY_URL env var)
                      Defaults to https://api.sigaid.com
        api_key: SigAid API key (or SIGAID_API_KEY env var)
        agent_name: Optional name for this agent

    Returns:
        Wrapped agent with _sigaid attribute

    Example:
        from autogen import AssistantAgent, UserProxyAgent
        import sigaid

        assistant = AssistantAgent("assistant", llm_config={...})

        # Using hosted service
        assistant = sigaid.wrap(assistant, api_key="sk_xxx")

        # Using self-hosted authority
        assistant = sigaid.wrap(
            assistant,
            authority_url="https://my-authority.com",
            api_key="sk_xxx"
        )

        user_proxy.initiate_chat(assistant, message="Hello!")
        print(assistant._sigaid.agent_id)
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
    return AutoGenIntegration.wrap(agent, client)
