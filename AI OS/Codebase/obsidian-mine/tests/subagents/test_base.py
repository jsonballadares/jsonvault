"""Tests for subagents/base.py — Subagent ABC contract."""

import pytest

from runtimes.base import SubagentRuntime
from subagents.base import Subagent


class _StubRuntime(SubagentRuntime):
    def invoke(self, packet, system_prompt, tools=None):
        return {"packet": packet, "system_prompt": system_prompt, "tools": tools}


class TestSubagentBase:
    def test_base_class_is_abstract(self):
        with pytest.raises(TypeError):
            Subagent(_StubRuntime())  # type: ignore[abstract]

    def test_subclass_missing_system_prompt_is_abstract(self):
        class NoPrompt(Subagent):
            @property
            def tools(self):
                return ["Read"]

        with pytest.raises(TypeError):
            NoPrompt(_StubRuntime())  # type: ignore[abstract]

    def test_subclass_missing_tools_is_abstract(self):
        class NoTools(Subagent):
            @property
            def system_prompt(self):
                return "sys"

        with pytest.raises(TypeError):
            NoTools(_StubRuntime())  # type: ignore[abstract]

    def test_concrete_subclass_instantiates_and_exposes_runtime(self):
        class Concrete(Subagent):
            @property
            def system_prompt(self):
                return "sys"

            @property
            def tools(self):
                return ["Read", "Grep"]

        runtime = _StubRuntime()
        agent = Concrete(runtime)
        assert agent.runtime is runtime
        assert agent.system_prompt == "sys"
        assert agent.tools == ["Read", "Grep"]

    def test_runtime_is_passed_through_composition(self):
        """Role delegates the worker call through its runtime instance."""

        class Concrete(Subagent):
            @property
            def system_prompt(self):
                return "sys"

            @property
            def tools(self):
                return ["Read"]

            def call(self, packet):
                return self.runtime.invoke(packet, self.system_prompt, self.tools)

        agent = Concrete(_StubRuntime())
        out = agent.call({"objective": "x"})
        assert out == {
            "packet": {"objective": "x"},
            "system_prompt": "sys",
            "tools": ["Read"],
        }
