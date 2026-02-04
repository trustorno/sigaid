"""LangChain integration for one-line SigAid wrapping."""

from __future__ import annotations

import asyncio
import functools
from typing import TYPE_CHECKING, Any, Callable, Dict, List

from sigaid.integrations.base import BaseIntegration
from sigaid.models.state import ActionType

if TYPE_CHECKING:
    from sigaid.client.agent import AgentClient


class SigAidCallbackHandler:
    """
    LangChain callback handler that records actions to SigAid.
    
    Auto-records:
    - Tool calls and results
    - LLM calls
    - Chain completions
    """
    
    def __init__(self, sigaid_client: AgentClient):
        """Initialize with SigAid client."""
        self._client = sigaid_client
    
    def _record_async(self, action_type: str, data: dict) -> None:
        """Record action asynchronously (fire and forget)."""
        try:
            if not self._client.is_holding_lease:
                return
            
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(
                    self._client.record_action(action_type, data, sync=False)
                )
        except Exception:
            pass
    
    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs,
    ) -> None:
        """Called when tool starts."""
        self._record_async(
            ActionType.TOOL_CALL.value,
            {
                "tool": serialized.get("name", "unknown"),
                "input": input_str[:500],
            },
        )
    
    def on_tool_end(self, output: str, **kwargs) -> None:
        """Called when tool ends."""
        self._record_async(
            "tool_result",
            {"output": str(output)[:500]},
        )
    
    def on_tool_error(self, error: Exception, **kwargs) -> None:
        """Called on tool error."""
        self._record_async(
            ActionType.ERROR.value,
            {"error": str(error)[:500]},
        )
    
    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs,
    ) -> None:
        """Called when LLM starts."""
        self._record_async(
            ActionType.LLM_REQUEST.value,
            {
                "model": serialized.get("name", "unknown"),
                "prompt_count": len(prompts),
            },
        )
    
    def on_llm_end(self, response, **kwargs) -> None:
        """Called when LLM ends."""
        pass  # Don't record - too verbose
    
    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Called on LLM error."""
        self._record_async(
            ActionType.ERROR.value,
            {"error": str(error)[:500]},
        )
    
    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs,
    ) -> None:
        """Called when chain starts."""
        self._record_async(
            ActionType.TASK_START.value,
            {
                "chain": serialized.get("name", "unknown"),
                "input_keys": list(inputs.keys()) if inputs else [],
            },
        )
    
    def on_chain_end(self, outputs: Dict[str, Any], **kwargs) -> None:
        """Called when chain ends."""
        self._record_async(
            ActionType.TASK_COMPLETE.value,
            {"output_keys": list(outputs.keys()) if outputs else []},
        )
    
    def on_chain_error(self, error: Exception, **kwargs) -> None:
        """Called on chain error."""
        self._record_async(
            ActionType.ERROR.value,
            {"error": str(error)[:500]},
        )
    
    def on_agent_action(self, action, **kwargs) -> None:
        """Called on agent action."""
        self._record_async(
            ActionType.DECISION.value,
            {
                "tool": getattr(action, "tool", "unknown"),
                "input": str(getattr(action, "tool_input", ""))[:500],
            },
        )
    
    def on_agent_finish(self, finish, **kwargs) -> None:
        """Called on agent finish."""
        self._record_async(
            ActionType.TASK_COMPLETE.value,
            {"output": str(getattr(finish, "return_values", {}))[:500]},
        )


class LangChainIntegration(BaseIntegration):
    """LangChain framework integration."""
    
    @classmethod
    def can_wrap(cls, agent: Any) -> bool:
        """Check if agent is a LangChain agent/chain."""
        type_name = type(agent).__module__ + "." + type(agent).__name__
        return "langchain" in type_name.lower()
    
    @classmethod
    def wrap(cls, agent: Any, sigaid_client: AgentClient) -> Any:
        """Wrap LangChain agent with SigAid identity."""
        callback = SigAidCallbackHandler(sigaid_client)
        
        # Try to add callback via different LangChain patterns
        if hasattr(agent, "callbacks"):
            # AgentExecutor, Chain, etc.
            existing = agent.callbacks or []
            agent.callbacks = list(existing) + [callback]
        elif hasattr(agent, "with_config"):
            # Runnable interface
            agent = agent.with_config(callbacks=[callback])
        
        # Wrap invoke methods
        cls._wrap_invoke_methods(agent, sigaid_client)
        
        # Attach SigAid client
        agent._sigaid = sigaid_client
        
        return agent
    
    @classmethod
    def _wrap_invoke_methods(cls, agent: Any, sigaid_client: AgentClient) -> None:
        """Wrap invoke/ainvoke to manage lease."""
        
        # Wrap sync invoke
        if hasattr(agent, "invoke"):
            original_invoke = agent.invoke
            
            @functools.wraps(original_invoke)
            def wrapped_invoke(*args, **kwargs):
                # If we have a running loop, use async version
                try:
                    loop = asyncio.get_running_loop()
                    # We're in async context
                    return asyncio.get_event_loop().run_until_complete(
                        _invoke_with_lease(original_invoke, sigaid_client, *args, **kwargs)
                    )
                except RuntimeError:
                    # No running loop - run sync
                    return asyncio.run(
                        _invoke_with_lease(original_invoke, sigaid_client, *args, **kwargs)
                    )
            
            agent.invoke = wrapped_invoke
        
        # Wrap async invoke
        if hasattr(agent, "ainvoke"):
            original_ainvoke = agent.ainvoke
            
            @functools.wraps(original_ainvoke)
            async def wrapped_ainvoke(*args, **kwargs):
                async with sigaid_client.lease():
                    return await original_ainvoke(*args, **kwargs)
            
            agent.ainvoke = wrapped_ainvoke


async def _invoke_with_lease(original_invoke: Callable, sigaid_client: AgentClient, *args, **kwargs):
    """Helper to invoke with lease context."""
    async with sigaid_client.lease():
        # Check if original is async
        result = original_invoke(*args, **kwargs)
        if asyncio.iscoroutine(result):
            return await result
        return result


def wrap_langchain(
    agent: Any,
    *,
    authority_url: str | None = None,
    api_key: str | None = None,
    agent_name: str | None = None,
) -> Any:
    """
    Wrap a LangChain agent/chain with SigAid identity.

    Supports:
    - AgentExecutor
    - RunnableSequence
    - Any Runnable with callbacks

    Args:
        agent: LangChain agent/chain to wrap
        authority_url: Authority service URL (or SIGAID_AUTHORITY_URL env var)
                      Defaults to https://api.sigaid.com
        api_key: SigAid API key (or SIGAID_API_KEY env var)
        agent_name: Optional name for this agent

    Returns:
        Wrapped agent with _sigaid attribute

    Example:
        from langchain.agents import AgentExecutor
        import sigaid

        # Using hosted service
        agent = AgentExecutor(...)
        agent = sigaid.wrap(agent, api_key="sk_xxx")

        # Using self-hosted authority
        agent = sigaid.wrap(
            agent,
            authority_url="https://my-authority.com",
            api_key="sk_xxx"
        )

        # Use as normal
        result = agent.invoke({"input": "Hello"})

        # Access SigAid
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
    return LangChainIntegration.wrap(agent, client)
