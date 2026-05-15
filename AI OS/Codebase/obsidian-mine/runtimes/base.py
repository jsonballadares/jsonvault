"""SubagentRuntime — the runtime axis of the Subagent class hierarchy.

A runtime is a pure adapter: it knows how to invoke a worker call and parse
the response, but holds no role-specific state. The Subagent (role) passes
its own system prompt and tool grants at call time — see Component Map §2
*Subagent Class Hierarchy* for the role/runtime split.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path


class SubagentRuntime(ABC):
    """Executes one Subagent call. One concrete adapter per execution path."""

    @abstractmethod
    def invoke(
        self,
        packet: dict,
        system_prompt: str,
        tools: list[str] | None = None,
        event_log: Path | None = None,
        logger: logging.Logger | None = None,
    ) -> dict:
        """Run the worker with the given packet, system prompt, and tool grants.

        If `event_log` is set, the runtime writes its event stream (every
        message, tool call, and tool result Claude emits during the call)
        to that path as NDJSON. Caller owns the path; runtime overwrites.

        If `logger` is set, the runtime emits its translated event lines and
        lifecycle logs to that logger instead of its module-level default —
        used by the orchestrator to route per-call output to a per-bundle
        log file.

        Returns the parsed JSON object the worker emitted.
        """
