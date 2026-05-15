"""Tests for subagents/explorer.py — ExplorerSubagent + parser.

Covers: properties (system_prompt from file, tools list), composition
seam (runtime is called with the right packet/prompt/tools), parser paths
(recipe, denial, missing-kind, unknown-kind, malformed-payload).
"""

from __future__ import annotations

import pytest

from recipe import Bundle, Recipe, Denial
from runtimes.base import SubagentRuntime
from subagents.explorer import (
    EXPLORER_SYSTEM_PROMPT,
    EXPLORER_TOOLS,
    ExplorerSubagent,
    _parse_explorer_output,
)


class FakeRuntime(SubagentRuntime):
    """Records invocations and returns a canned response."""

    def __init__(self, response: dict) -> None:
        self.response = response
        self.calls: list[dict] = []

    def invoke(
        self, packet, system_prompt, tools=None, event_log=None, logger=None,
    ):
        self.calls.append(
            {
                "packet": packet,
                "system_prompt": system_prompt,
                "tools": tools,
                "event_log": event_log,
                "logger": logger,
            }
        )
        return self.response


RECIPE_RESPONSE = {
    "kind": "recipe",
    "artifact_name": "What I Know About Data Engineering — Inventory",
    "notes_needed": {
        "foundations": {
            "paths": ["Notes/Data Engineering.md"],
            "description": "The core concept note.",
            "expected_output": "One per-note record.",
        },
        "pipelines": {
            "paths": ["Notes/ETL Pipelines.md"],
            "description": "Pipeline-focused notes.",
            "expected_output": "One per-note record.",
        },
    },
    "miner_objective": "For each note, extract the core claims about data engineering.",
    "output_schema": (
        '{"kind": "per-note-record", '
        '"path": str, "claims": [str]}'
    ),
    "artifact_description": "A practical overview anchored to source notes, grouped by the bundle themes.",
}

DENIAL_RESPONSE = {
    "kind": "denial",
    "reason": "No notes on kombucha brewing; provide vault notes first.",
}


class TestProperties:
    def test_system_prompt_loaded_from_file(self):
        ex = ExplorerSubagent(runtime=FakeRuntime(RECIPE_RESPONSE))
        assert ex.system_prompt == EXPLORER_SYSTEM_PROMPT
        assert "You are the Explorer" in ex.system_prompt
        assert "kind" in ex.system_prompt

    def test_system_prompt_matches_module_constant(self):
        """The module constant is the file contents; properties return it."""
        assert isinstance(EXPLORER_SYSTEM_PROMPT, str)
        assert len(EXPLORER_SYSTEM_PROMPT) > 1000  # non-trivial

    def test_tools_include_read_grep_bash(self):
        ex = ExplorerSubagent(runtime=FakeRuntime(RECIPE_RESPONSE))
        assert ex.tools == ["Read", "Grep", "Bash"]

    def test_tools_property_returns_fresh_list(self):
        """Mutating the returned list must not affect future calls."""
        ex = ExplorerSubagent(runtime=FakeRuntime(RECIPE_RESPONSE))
        t1 = ex.tools
        t1.append("Write")
        t2 = ex.tools
        assert t2 == ["Read", "Grep", "Bash"]


class TestCompositionSeam:
    def test_explore_invokes_runtime_with_correct_packet(self):
        rt = FakeRuntime(RECIPE_RESPONSE)
        ex = ExplorerSubagent(runtime=rt)

        ex.explore("What do I know about data engineering?")

        assert len(rt.calls) == 1
        call = rt.calls[0]
        assert call["packet"] == {
            "direction": "What do I know about data engineering?"
        }

    def test_explore_passes_system_prompt(self):
        rt = FakeRuntime(RECIPE_RESPONSE)
        ex = ExplorerSubagent(runtime=rt)

        ex.explore("anything")

        assert rt.calls[0]["system_prompt"] == EXPLORER_SYSTEM_PROMPT

    def test_explore_passes_tools(self):
        rt = FakeRuntime(RECIPE_RESPONSE)
        ex = ExplorerSubagent(runtime=rt)

        ex.explore("anything")

        assert rt.calls[0]["tools"] == ["Read", "Grep", "Bash"]

    def test_explore_forwards_event_log(self, tmp_path):
        rt = FakeRuntime(RECIPE_RESPONSE)
        ex = ExplorerSubagent(runtime=rt)

        log_path = tmp_path / "events.ndjson"
        ex.explore("anything", event_log=log_path)

        assert rt.calls[0]["event_log"] == log_path

    def test_explore_event_log_defaults_to_none(self):
        rt = FakeRuntime(RECIPE_RESPONSE)
        ex = ExplorerSubagent(runtime=rt)

        ex.explore("anything")

        assert rt.calls[0]["event_log"] is None

    def test_explore_returns_recipe(self):
        ex = ExplorerSubagent(runtime=FakeRuntime(RECIPE_RESPONSE))

        result = ex.explore("data engineering")

        assert isinstance(result, Recipe)
        assert result.artifact_name == RECIPE_RESPONSE["artifact_name"]
        assert set(result.notes_needed.keys()) == set(
            RECIPE_RESPONSE["notes_needed"].keys()
        )
        for label, bundle in result.notes_needed.items():
            wire = RECIPE_RESPONSE["notes_needed"][label]
            assert isinstance(bundle, Bundle)
            assert bundle.paths == wire["paths"]
            assert bundle.description == wire["description"]
            assert bundle.expected_output == wire["expected_output"]
        assert result.miner_objective == RECIPE_RESPONSE["miner_objective"]
        assert result.output_schema == RECIPE_RESPONSE["output_schema"]
        assert result.artifact_description == RECIPE_RESPONSE["artifact_description"]

    def test_explore_returns_denial(self):
        ex = ExplorerSubagent(runtime=FakeRuntime(DENIAL_RESPONSE))

        result = ex.explore("kombucha brewing")

        assert isinstance(result, Denial)
        assert result.reason == DENIAL_RESPONSE["reason"]


class TestParserHappyPath:
    def test_parses_recipe(self):
        result = _parse_explorer_output(dict(RECIPE_RESPONSE))
        assert isinstance(result, Recipe)
        assert result.artifact_name == RECIPE_RESPONSE["artifact_name"]

    def test_parses_denial(self):
        result = _parse_explorer_output(dict(DENIAL_RESPONSE))
        assert isinstance(result, Denial)
        assert result.reason == DENIAL_RESPONSE["reason"]

    def test_strips_kind_discriminator_from_dataclass(self):
        """kind is wire-level; it must not end up as a dataclass attr."""
        result = _parse_explorer_output(dict(RECIPE_RESPONSE))
        assert not hasattr(result, "kind")


class TestParserErrors:
    def test_missing_kind_raises(self):
        payload = {k: v for k, v in RECIPE_RESPONSE.items() if k != "kind"}
        with pytest.raises(ValueError, match="missing 'kind'"):
            _parse_explorer_output(payload)

    def test_unknown_kind_raises(self):
        bad = dict(RECIPE_RESPONSE, kind="proposal")
        with pytest.raises(ValueError, match="must be 'recipe' or 'denial'"):
            _parse_explorer_output(bad)

    def test_recipe_missing_required_field_raises(self):
        bad = dict(RECIPE_RESPONSE)
        del bad["miner_objective"]
        with pytest.raises(ValueError, match="recipe payload invalid"):
            _parse_explorer_output(bad)

    def test_recipe_extra_field_dropped_with_warning(self, caplog):
        import logging

        caplog.set_level(logging.WARNING, logger="subagents.explorer")
        bad = dict(RECIPE_RESPONSE, artifact_description_continued="")
        result = _parse_explorer_output(bad)
        assert isinstance(result, Recipe)
        assert result.artifact_name == RECIPE_RESPONSE["artifact_name"]
        assert not hasattr(result, "artifact_description_continued")
        assert any(
            "recipe" in r.message
            and "artifact_description_continued" in r.message
            for r in caplog.records
        )

    def test_denial_missing_reason_raises(self):
        bad = {"kind": "denial"}
        with pytest.raises(ValueError, match="denial payload invalid"):
            _parse_explorer_output(bad)

    def test_denial_extra_field_dropped_with_warning(self, caplog):
        import logging

        caplog.set_level(logging.WARNING, logger="subagents.explorer")
        bad = {"kind": "denial", "reason": "x", "extra": "y"}
        result = _parse_explorer_output(bad)
        assert isinstance(result, Denial)
        assert result.reason == "x"
        assert not hasattr(result, "extra")
        assert any(
            "denial" in r.message and "extra" in r.message
            for r in caplog.records
        )

    def test_notes_needed_as_list_raises(self):
        """Legacy shape (list of paths) must be rejected — bundles are required."""
        bad = dict(RECIPE_RESPONSE)
        bad["notes_needed"] = ["Notes/A.md", "Notes/B.md"]
        with pytest.raises(ValueError, match="must be a dict of bundles"):
            _parse_explorer_output(bad)

    def test_bundle_missing_field_raises(self):
        bad = dict(RECIPE_RESPONSE)
        bad["notes_needed"] = {
            "foundations": {
                "paths": ["Notes/Data Engineering.md"],
                "description": "x",
                # expected_output missing
            },
        }
        with pytest.raises(ValueError, match="recipe payload invalid"):
            _parse_explorer_output(bad)

    def test_bundle_extra_field_dropped_with_warning(self, caplog):
        import logging

        caplog.set_level(logging.WARNING, logger="subagents.explorer")
        bad = dict(RECIPE_RESPONSE)
        bad["notes_needed"] = {
            "foundations": {
                "paths": ["Notes/Data Engineering.md"],
                "description": "x",
                "expected_output": "y",
                "bogus": "z",
            },
        }
        result = _parse_explorer_output(bad)
        assert isinstance(result, Recipe)
        bundle = result.notes_needed["foundations"]
        assert bundle.paths == ["Notes/Data Engineering.md"]
        assert not hasattr(bundle, "bogus")
        assert any(
            "bundle" in r.message
            and "foundations" in r.message
            and "bogus" in r.message
            for r in caplog.records
        )


class TestParserLogging:
    def test_missing_kind_logs_error(self, caplog):
        import logging

        caplog.set_level(logging.ERROR, logger="subagents.explorer")
        with pytest.raises(ValueError):
            _parse_explorer_output({"artifact_name": "x"})
        assert any("missing 'kind'" in r.message for r in caplog.records)

    def test_unknown_kind_logs_error(self, caplog):
        import logging

        caplog.set_level(logging.ERROR, logger="subagents.explorer")
        with pytest.raises(ValueError):
            _parse_explorer_output({"kind": "proposal", "reason": "x"})
        assert any("unknown kind" in r.message for r in caplog.records)

    def test_explore_logs_direction_at_debug(self, caplog):
        import logging

        caplog.set_level(logging.DEBUG, logger="subagents.explorer")
        ex = ExplorerSubagent(runtime=FakeRuntime(RECIPE_RESPONSE))
        ex.explore("test direction")
        assert any(
            "exploring direction" in r.message and "test direction" in r.message
            for r in caplog.records
        )
