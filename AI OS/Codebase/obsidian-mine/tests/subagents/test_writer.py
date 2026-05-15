"""Tests for subagents/writer.py — WriterSubagent + parser.

Covers: properties (system_prompt from file, tools = Read only),
composition seam (runtime invoked with right packet/prompt/tools, packet
carries exactly four keys — no Recipe-level leakage), parser paths
(markdown happy-path, missing-markdown, markdown-not-string,
unknown-top-level-field).
"""

from __future__ import annotations

import logging

import pytest

from recipe import BundleResult
from runtimes.base import SubagentRuntime
from subagents.writer import (
    WRITER_SYSTEM_PROMPT,
    WRITER_TOOLS,
    WriterSubagent,
    _parse_writer_output,
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


SAMPLE_BUNDLES = {
    "active-services": BundleResult(
        paths=["Notes/Plex.md", "Notes/Sonarr.md"],
        description="Active services in the HomeLab.",
        expected_output="One per_note record per note plus a bundle summary.",
        records=[
            {"kind": "per_note", "path": "Notes/Plex.md", "topic": "Plex"},
            {"kind": "per_note", "path": "Notes/Sonarr.md", "topic": "Sonarr"},
            {"kind": "bundle_summary", "summary": "Two media services."},
        ],
    ),
}

SAMPLE_ARTIFACT_NAME = "HomeLab Active Services Inventory"
SAMPLE_ARTIFACT_DESCRIPTION = (
    "A snapshot of services running in the HomeLab. Open with framing, "
    "then a table, then a section per service."
)
SAMPLE_OUTPUT_SCHEMA = (
    'per_note: {"kind": "per_note", "path": str, "topic": str}; '
    'bundle_summary: {"kind": "bundle_summary", "summary": str}'
)

SAMPLE_MARKDOWN = (
    "origin:: agent\n"
    "type:: #vault-mining\n"
    "tags:: #homelab\n\n"
    "---\n"
    "# HomeLab Active Services Inventory\n\n"
    "Two services are running.\n\n"
    "---\n"
    "# References\n\n"
    "- [[Plex]]\n"
    "- [[Sonarr]]\n"
)
SAMPLE_RESPONSE = {"markdown": SAMPLE_MARKDOWN}


class TestProperties:
    def test_system_prompt_loaded_from_file(self):
        w = WriterSubagent(runtime=FakeRuntime(SAMPLE_RESPONSE))
        assert w.system_prompt == WRITER_SYSTEM_PROMPT
        assert "You are the Writer" in w.system_prompt
        assert "markdown" in w.system_prompt

    def test_system_prompt_matches_module_constant(self):
        assert isinstance(WRITER_SYSTEM_PROMPT, str)
        assert len(WRITER_SYSTEM_PROMPT) > 1000

    def test_tools_are_read_only(self):
        w = WriterSubagent(runtime=FakeRuntime(SAMPLE_RESPONSE))
        assert w.tools == ["Read"]

    def test_tools_property_returns_fresh_list(self):
        """Mutating the returned list must not affect future calls."""
        w = WriterSubagent(runtime=FakeRuntime(SAMPLE_RESPONSE))
        t1 = w.tools
        t1.append("Bash")
        t2 = w.tools
        assert t2 == ["Read"]

    def test_tools_does_not_include_grep_or_bash(self):
        """W3 — Read only, no Grep, no Bash."""
        w = WriterSubagent(runtime=FakeRuntime(SAMPLE_RESPONSE))
        assert "Grep" not in w.tools
        assert "Bash" not in w.tools


class TestCompositionSeam:
    def test_write_invokes_runtime_with_correct_packet(self):
        rt = FakeRuntime(SAMPLE_RESPONSE)
        w = WriterSubagent(runtime=rt)

        w.write(
            artifact_name=SAMPLE_ARTIFACT_NAME,
            artifact_description=SAMPLE_ARTIFACT_DESCRIPTION,
            output_schema=SAMPLE_OUTPUT_SCHEMA,
            bundles=SAMPLE_BUNDLES,
        )

        assert len(rt.calls) == 1
        packet = rt.calls[0]["packet"]
        assert packet["artifact_name"] == SAMPLE_ARTIFACT_NAME
        assert packet["artifact_description"] == SAMPLE_ARTIFACT_DESCRIPTION
        assert packet["output_schema"] == SAMPLE_OUTPUT_SCHEMA
        # Bundles serialized as plain dicts (asdict over BundleResult).
        assert "active-services" in packet["bundles"]
        bundle = packet["bundles"]["active-services"]
        assert bundle["paths"] == ["Notes/Plex.md", "Notes/Sonarr.md"]
        assert bundle["description"] == "Active services in the HomeLab."
        assert (
            bundle["expected_output"]
            == "One per_note record per note plus a bundle summary."
        )
        assert len(bundle["records"]) == 3

    def test_packet_contains_only_four_expected_keys(self):
        """Leakage-prevention test — no Recipe-level fields can leak in."""
        rt = FakeRuntime(SAMPLE_RESPONSE)
        w = WriterSubagent(runtime=rt)

        w.write(
            artifact_name="X",
            artifact_description="y",
            output_schema="z",
            bundles={},
        )

        packet = rt.calls[0]["packet"]
        expected_keys = {
            "artifact_name",
            "artifact_description",
            "output_schema",
            "bundles",
        }
        assert set(packet.keys()) == expected_keys
        # Specifically verify Recipe-level / Miner-level fields don't leak.
        assert "miner_objective" not in packet
        assert "notes_needed" not in packet
        assert "bundle_label" not in packet

    def test_write_passes_system_prompt(self):
        rt = FakeRuntime(SAMPLE_RESPONSE)
        w = WriterSubagent(runtime=rt)

        w.write("X", "y", "z", {})

        assert rt.calls[0]["system_prompt"] == WRITER_SYSTEM_PROMPT

    def test_write_passes_tools(self):
        rt = FakeRuntime(SAMPLE_RESPONSE)
        w = WriterSubagent(runtime=rt)

        w.write("X", "y", "z", {})

        assert rt.calls[0]["tools"] == ["Read"]

    def test_write_forwards_event_log(self, tmp_path):
        rt = FakeRuntime(SAMPLE_RESPONSE)
        w = WriterSubagent(runtime=rt)

        log_path = tmp_path / "events.ndjson"
        w.write("X", "y", "z", {}, event_log=log_path)

        assert rt.calls[0]["event_log"] == log_path

    def test_write_event_log_defaults_to_none(self):
        rt = FakeRuntime(SAMPLE_RESPONSE)
        w = WriterSubagent(runtime=rt)

        w.write("X", "y", "z", {})

        assert rt.calls[0]["event_log"] is None

    def test_write_returns_markdown_string(self):
        w = WriterSubagent(runtime=FakeRuntime(SAMPLE_RESPONSE))

        result = w.write(
            SAMPLE_ARTIFACT_NAME, SAMPLE_ARTIFACT_DESCRIPTION,
            SAMPLE_OUTPUT_SCHEMA, SAMPLE_BUNDLES,
        )

        assert isinstance(result, str)
        assert result == SAMPLE_MARKDOWN
        assert result.startswith("origin:: agent")

    def test_empty_bundles_packet_serializes_cleanly(self):
        """Edge case: zero bundles still produces a valid packet."""
        rt = FakeRuntime(SAMPLE_RESPONSE)
        w = WriterSubagent(runtime=rt)

        w.write("X", "y", "z", {})

        packet = rt.calls[0]["packet"]
        assert packet["bundles"] == {}


class TestParserHappyPath:
    def test_parses_markdown_string(self):
        result = _parse_writer_output({"markdown": "# Hello"})
        assert result == "# Hello"

    def test_parses_empty_markdown_string(self):
        """An empty string is valid — degenerate but not malformed."""
        result = _parse_writer_output({"markdown": ""})
        assert result == ""

    def test_parses_markdown_with_newlines(self):
        body = "# H1\n\nbody\n\n## H2\n"
        result = _parse_writer_output({"markdown": body})
        assert result == body


class TestParserErrors:
    def test_missing_markdown_key_raises(self):
        with pytest.raises(ValueError, match="missing 'markdown'"):
            _parse_writer_output({"something_else": "x"})

    def test_markdown_not_a_string_raises(self):
        with pytest.raises(ValueError, match="must be a string"):
            _parse_writer_output({"markdown": ["a", "list"]})

    def test_markdown_dict_raises(self):
        with pytest.raises(ValueError, match="must be a string"):
            _parse_writer_output({"markdown": {"nested": "object"}})

    def test_markdown_int_raises(self):
        with pytest.raises(ValueError, match="must be a string"):
            _parse_writer_output({"markdown": 42})


class TestParserDefensive:
    def test_unknown_top_level_field_dropped_with_warning(self, caplog):
        caplog.set_level(logging.WARNING, logger="subagents.writer")
        payload = {
            "markdown": "# X",
            "extra_thoughts": "I think...",
        }
        result = _parse_writer_output(payload)
        assert result == "# X"
        assert any(
            "writer output" in r.message and "extra_thoughts" in r.message
            for r in caplog.records
        )

    def test_multiple_unknown_fields_all_logged(self, caplog):
        caplog.set_level(logging.WARNING, logger="subagents.writer")
        payload = {
            "markdown": "",
            "warnings": [],
            "summary": "x",
        }
        _parse_writer_output(payload)
        warning_messages = " ".join(r.message for r in caplog.records)
        assert "warnings" in warning_messages
        assert "summary" in warning_messages


class TestParserLogging:
    def test_missing_markdown_logs_error(self, caplog):
        caplog.set_level(logging.ERROR, logger="subagents.writer")
        with pytest.raises(ValueError):
            _parse_writer_output({"foo": "bar"})
        assert any("missing 'markdown'" in r.message for r in caplog.records)

    def test_markdown_not_string_logs_error(self, caplog):
        caplog.set_level(logging.ERROR, logger="subagents.writer")
        with pytest.raises(ValueError):
            _parse_writer_output({"markdown": 42})
        assert any("must be a string" in r.message for r in caplog.records)

    def test_write_logs_at_debug(self, caplog):
        caplog.set_level(logging.DEBUG, logger="subagents.writer")
        w = WriterSubagent(runtime=FakeRuntime(SAMPLE_RESPONSE))
        w.write(
            SAMPLE_ARTIFACT_NAME, SAMPLE_ARTIFACT_DESCRIPTION,
            SAMPLE_OUTPUT_SCHEMA, SAMPLE_BUNDLES,
        )
        assert any(
            "writing artifact" in r.message
            and SAMPLE_ARTIFACT_NAME in r.message
            for r in caplog.records
        )
