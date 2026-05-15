"""Subagent — the role axis of the Subagent class hierarchy.

A Subagent is a role (Explorer, Miner). It holds a SubagentRuntime via
composition and delegates the worker call through it. Each role declares
its own system prompt and read-only tool grants, and defines its own
typed method signature — there is no uniform `invoke` on the base. See
Component Map §2 *Subagent Class Hierarchy* and the Q5 decision in
P8 Working Notes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from runtimes.base import SubagentRuntime


class Subagent(ABC):
    """Base class for Subagent roles. Holds a runtime; declares prompt + tools."""

    def __init__(self, runtime: SubagentRuntime) -> None:
        self.runtime = runtime

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """The role's system prompt — passed to the runtime at call time."""

    @property
    @abstractmethod
    def tools(self) -> list[str]:
        """The role's read-only tool grants — passed to the runtime at call time."""
