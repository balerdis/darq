"""Composition root: the one place that knows which adapters exist.

Every other module works through the registry, so adding a CLI means writing a
directory here and adding one line below.
"""
from __future__ import annotations

from darq.adapters.claudecode import Adapter as ClaudeCodeAdapter
from darq.adapters.opencode import Adapter as OpenCodeAdapter
from darq.core.registry import Registry

ADAPTERS = (OpenCodeAdapter, ClaudeCodeAdapter)


def available() -> Registry:
    """A registry with every adapter this release ships, validated on the way in."""
    return Registry(*(adapter() for adapter in ADAPTERS))
