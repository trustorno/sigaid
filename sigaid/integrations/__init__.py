"""Framework integrations for one-line SigAid wrapping."""

from sigaid.integrations.detect import detect_and_wrap
from sigaid.integrations.base import BaseIntegration, WrappedAgent

__all__ = [
    "detect_and_wrap",
    "BaseIntegration",
    "WrappedAgent",
]
