"""CrewAI integration for one-line SigAid wrapping."""

from __future__ import annotations

import asyncio
import functools
from typing import TYPE_CHECKING, Any

from sigaid.integrations.base import BaseIntegration
from sigaid.models.state import ActionType

if TYPE_CHECKING:
    from sigaid.client.agent import AgentClient


class CrewAIIntegration(BaseIntegration):
    """CrewAI framework integration."""
    
    @classmethod
    def can_wrap(cls, agent: Any) -> bool:
        """Check if agent is a CrewAI agent/crew."""
        type_name = type(agent).__module__ + "." + type(agent).__name__
        return "crewai" in type_name.lower()
    
    @classmethod
    def wrap(cls, agent: Any, sigaid_client: AgentClient) -> Any:
        """Wrap CrewAI agent/crew with SigAid identity."""
        type_name = type(agent).__name__
        
        if type_name == "Crew":
            return cls._wrap_crew(agent, sigaid_client)
        elif type_name == "Agent":
            return cls._wrap_agent(agent, sigaid_client)
        else:
            # Unknown type - attach client anyway
            agent._sigaid = sigaid_client
            return agent
    
    @classmethod
    def _wrap_crew(cls, crew: Any, sigaid_client: AgentClient) -> Any:
        """Wrap CrewAI Crew."""
        original_kickoff = crew.kickoff
        
        @functools.wraps(original_kickoff)
        def wrapped_kickoff(*args, **kwargs):
            async def _kickoff_with_lease():
                async with sigaid_client.lease():
                    # Record crew start
                    agents = [a.role for a in getattr(crew, "agents", [])]
                    tasks = len(getattr(crew, "tasks", []))
                    await sigaid_client.record_action(
                        ActionType.TASK_START.value,
                        {"agents": agents, "task_count": tasks},
                        sync=False,
                    )
                    
                    # Run original
                    result = original_kickoff(*args, **kwargs)
                    if asyncio.iscoroutine(result):
                        result = await result
                    
                    # Record completion
                    await sigaid_client.record_action(
                        ActionType.TASK_COMPLETE.value,
                        {"result_length": len(str(result))},
                        sync=False,
                    )
                    
                    return result
            
            return asyncio.run(_kickoff_with_lease())
        
        # Handle async kickoff if it exists
        if hasattr(crew, "kickoff_async"):
            original_kickoff_async = crew.kickoff_async
            
            @functools.wraps(original_kickoff_async)
            async def wrapped_kickoff_async(*args, **kwargs):
                async with sigaid_client.lease():
                    agents = [a.role for a in getattr(crew, "agents", [])]
                    await sigaid_client.record_action(
                        ActionType.TASK_START.value,
                        {"agents": agents},
                        sync=False,
                    )
                    
                    result = await original_kickoff_async(*args, **kwargs)
                    
                    await sigaid_client.record_action(
                        ActionType.TASK_COMPLETE.value,
                        {"result_length": len(str(result))},
                        sync=False,
                    )
                    
                    return result
            
            crew.kickoff_async = wrapped_kickoff_async
        
        crew.kickoff = wrapped_kickoff
        crew._sigaid = sigaid_client
        return crew
    
    @classmethod
    def _wrap_agent(cls, agent: Any, sigaid_client: AgentClient) -> Any:
        """Wrap CrewAI Agent."""
        # Wrap execute_task if present
        if hasattr(agent, "execute_task"):
            original_execute = agent.execute_task
            
            @functools.wraps(original_execute)
            def wrapped_execute(task, *args, **kwargs):
                async def _execute_with_record():
                    if sigaid_client.is_holding_lease:
                        await sigaid_client.record_action(
                            ActionType.TASK_START.value,
                            {
                                "task": str(task)[:200],
                                "agent_role": getattr(agent, "role", "unknown"),
                            },
                            sync=False,
                        )
                    
                    result = original_execute(task, *args, **kwargs)
                    if asyncio.iscoroutine(result):
                        result = await result
                    
                    if sigaid_client.is_holding_lease:
                        await sigaid_client.record_action(
                            ActionType.TASK_COMPLETE.value,
                            {"result_length": len(str(result))},
                            sync=False,
                        )
                    
                    return result
                
                try:
                    loop = asyncio.get_running_loop()
                    return asyncio.create_task(_execute_with_record())
                except RuntimeError:
                    return asyncio.run(_execute_with_record())
            
            agent.execute_task = wrapped_execute
        
        agent._sigaid = sigaid_client
        return agent


def wrap_crewai(
    agent: Any,
    *,
    api_key: str | None = None,
    agent_name: str | None = None,
) -> Any:
    """
    Wrap a CrewAI Agent or Crew with SigAid identity.
    
    Args:
        agent: CrewAI Agent or Crew to wrap
        api_key: SigAid API key (or SIGAID_API_KEY env var)
        agent_name: Optional name for this agent
        
    Returns:
        Wrapped agent/crew with _sigaid attribute
    
    Example:
        from crewai import Agent, Task, Crew
        import sigaid
        
        researcher = Agent(role="Researcher", ...)
        crew = Crew(agents=[researcher], tasks=[...])
        crew = sigaid.wrap(crew)
        
        result = crew.kickoff()
        print(crew._sigaid.agent_id)
    """
    from sigaid.client.agent import AgentClient
    
    client = AgentClient.create(api_key=api_key)
    return CrewAIIntegration.wrap(agent, client)
