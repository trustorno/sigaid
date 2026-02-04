"""Pytest configuration and fixtures for SigAid tests."""

import pytest
import asyncio
from pathlib import Path
import tempfile

from sigaid.crypto.keys import KeyPair
from sigaid.identity.agent_id import AgentID


@pytest.fixture
def keypair():
    """Generate a fresh keypair for testing."""
    return KeyPair.generate()


@pytest.fixture
def agent_id(keypair):
    """Get agent ID from keypair."""
    return keypair.to_agent_id()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for file-based tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
