"""Tests for runtimes/base.py — SubagentRuntime ABC contract."""

import pytest

from runtimes.base import SubagentRuntime


class TestSubagentRuntimeBase:
    def test_base_class_is_abstract(self):
        with pytest.raises(TypeError):
            SubagentRuntime()  # type: ignore[abstract]

    def test_subclass_without_invoke_is_abstract(self):
        class Incomplete(SubagentRuntime):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_concrete_subclass_can_instantiate_and_invoke(self):
        class Concrete(SubagentRuntime):
            def invoke(
                self, packet, system_prompt, tools=None, event_log=None,
                logger=None,
            ):
                return {
                    "received": packet,
                    "prompt": system_prompt,
                    "tools": tools,
                    "event_log": event_log,
                    "logger": logger,
                }

        r = Concrete()
        out = r.invoke({"objective": "x"}, "sys", tools=["Read"])
        assert out == {
            "received": {"objective": "x"},
            "prompt": "sys",
            "tools": ["Read"],
            "event_log": None,
            "logger": None,
        }
