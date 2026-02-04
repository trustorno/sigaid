#!/usr/bin/env python3
"""
Framework integration demo for SigAid SDK.

This demo shows how to integrate SigAid with popular AI frameworks
using just one line of code.

Note: This is a conceptual demo - actual framework imports are commented
out since they may not be installed.
"""

import asyncio


def demo_langchain():
    """Show LangChain integration."""
    print("\n" + "=" * 50)
    print("LangChain Integration")
    print("=" * 50)
    
    print("""
# Installation:
pip install sigaid[langchain]

# Usage (ONE LINE!):
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
import sigaid

# Create your LangChain agent as usual
llm = ChatOpenAI(model="gpt-4")
tools = [...]  # Your tools
agent = create_openai_tools_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)

# Add SigAid identity - ONE LINE
executor = sigaid.wrap(executor)

# Use exactly as before
result = executor.invoke({"input": "Book a hotel"})

# SigAid automatically:
# - Creates unique agent identity
# - Manages lease acquisition
# - Records all tool calls and LLM interactions
# - Enables verification by services

# Access SigAid features
print(f"Agent ID: {executor._sigaid.agent_id}")
proof = executor._sigaid.create_proof(challenge=b"nonce")
""")


def demo_crewai():
    """Show CrewAI integration."""
    print("\n" + "=" * 50)
    print("CrewAI Integration")
    print("=" * 50)
    
    print("""
# Installation:
pip install sigaid[crewai]

# Usage (ONE LINE!):
from crewai import Agent, Task, Crew
import sigaid

# Create your CrewAI setup as usual
researcher = Agent(
    role="Researcher",
    goal="Research AI trends",
    backstory="Expert researcher..."
)
writer = Agent(
    role="Writer",
    goal="Write reports",
    backstory="Technical writer..."
)
task = Task(description="Research and write about AI")
crew = Crew(agents=[researcher, writer], tasks=[task])

# Add SigAid identity - ONE LINE
crew = sigaid.wrap(crew)

# Use exactly as before
result = crew.kickoff()

# SigAid automatically:
# - Tracks all agent tasks
# - Records decisions and completions
# - Provides verifiable audit trail
""")


def demo_autogen():
    """Show AutoGen integration."""
    print("\n" + "=" * 50)
    print("AutoGen Integration")
    print("=" * 50)
    
    print("""
# Installation:
pip install sigaid[autogen]

# Usage (ONE LINE!):
from autogen import AssistantAgent, UserProxyAgent
import sigaid

# Create your AutoGen agents as usual
assistant = AssistantAgent(
    "assistant",
    llm_config={"model": "gpt-4"}
)
user_proxy = UserProxyAgent("user_proxy")

# Add SigAid identity - ONE LINE
assistant = sigaid.wrap(assistant)

# Use exactly as before
user_proxy.initiate_chat(assistant, message="Hello!")

# SigAid automatically:
# - Records all messages received/sent
# - Tracks replies generated
# - Creates verifiable interaction log
""")


def demo_verification():
    """Show how services verify agents."""
    print("\n" + "=" * 50)
    print("Service-Side Verification")
    print("=" * 50)
    
    print("""
# Services can verify agents before trusting them
from sigaid import Verifier

# Initialize verifier with API key
verifier = Verifier(api_key="...")

# When agent connects, verify their proof
async def handle_agent_request(proof_bundle):
    result = await verifier.verify(
        proof_bundle,
        require_lease=True,            # Must have active lease
        min_reputation_score=0.7,      # Minimum reputation
        max_state_age=timedelta(hours=1),  # Recent state required
    )
    
    if result.valid:
        print(f"Agent {result.agent_id} verified!")
        print(f"Reputation: {result.reputation_score}")
        print(f"State entries: {result.state_head_sequence}")
        # Proceed with request
    else:
        print(f"Verification failed: {result.error_message}")
        # Reject request
""")


def main():
    print("=" * 60)
    print("SigAid Framework Integration Demo")
    print("=" * 60)
    print("\nSigAid enables 'one line of code' integration with")
    print("popular AI agent frameworks. Just add sigaid.wrap()!")
    
    demo_langchain()
    demo_crewai()
    demo_autogen()
    demo_verification()
    
    print("\n" + "=" * 60)
    print("Summary: What SigAid Provides")
    print("=" * 60)
    print("""
For Agents:
  - Cryptographic identity (Ed25519 keypair)
  - Exclusive operation (lease prevents clones)
  - Verifiable history (state chain)
  - Simple integration (one line!)

For Services:
  - Verify agent identity
  - Check lease status
  - Validate state chain
  - Query reputation

Security:
  - No clone attacks (exclusive leases)
  - No tampering (hash-linked chain)
  - No impersonation (cryptographic signatures)
  - No replay attacks (nonces, timestamps)
""")


if __name__ == "__main__":
    main()
