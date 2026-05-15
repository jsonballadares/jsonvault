"""Tests for subagents/miner.py — MinerSubagent + parser.

Covers: properties (system_prompt from file, tools list), composition
seam (runtime invoked with right packet/prompt/tools, packet contains
only the six expected keys — leakage prevention), parser paths (records,
missing-records, records-not-list, record-missing-kind, record-not-dict,
unknown-top-level-field).
"""

from __future__ import annotations

import pytest

from recipe import Bundle
from runtimes.base import SubagentRuntime
from subagents.miner import (
    MINER_SYSTEM_PROMPT,
    MINER_TOOLS,
    MinerSubagent,
    _parse_miner_output,
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


SAMPLE_BUNDLE = Bundle(
    paths=["Notes/Plex.md", "Notes/Sonarr.md"],
    description="Active services in the HomeLab.",
    expected_output="One per_note record per note. Capture purpose and status.",
)

SAMPLE_OBJECTIVE = "For each note, capture purpose and current status."
SAMPLE_SCHEMA = (
    'per_note: {"kind": "per_note", "path": str, "topic": str, "status": str}'
)

SAMPLE_RECORDS_RESPONSE = {
    "records": [
        {
            "kind": "per_note",
            "path": "Notes/Plex.md",
            "topic": "Plex",
            "status": "active",
        },
        {
            "kind": "per_note",
            "path": "Notes/Sonarr.md",
            "topic": "Sonarr",
            "status": "active",
        },
    ],
}


class TestProperties:
    def test_system_prompt_loaded_from_file(self):
        m = MinerSubagent(runtime=FakeRuntime(SAMPLE_RECORDS_RESPONSE))
        assert m.system_prompt == MINER_SYSTEM_PROMPT
        assert "You are the Miner" in m.system_prompt
        assert "records" in m.system_prompt

    def test_system_prompt_matches_module_constant(self):
        """The module constant is the file contents; properties return it."""
        assert isinstance(MINER_SYSTEM_PROMPT, str)
        assert len(MINER_SYSTEM_PROMPT) > 1000  # non-trivial

    def test_tools_include_read_grep_bash(self):
        m = MinerSubagent(runtime=FakeRuntime(SAMPLE_RECORDS_RESPONSE))
        assert m.tools == ["Read", "Grep", "Bash"]

    def test_tools_property_returns_fresh_list(self):
        """Mutating the returned list must not affect future calls."""
        m = MinerSubagent(runtime=FakeRuntime(SAMPLE_RECORDS_RESPONSE))
        t1 = m.tools
        t1.append("Write")
        t2 = m.tools
        assert t2 == ["Read", "Grep", "Bash"]


class TestCompositionSeam:
    def test_mine_invokes_runtime_with_correct_packet(self):
        rt = FakeRuntime(SAMPLE_RECORDS_RESPONSE)
        m = MinerSubagent(runtime=rt)

        m.mine(
            bundle=SAMPLE_BUNDLE,
            bundle_label="active-services",
            miner_objective=SAMPLE_OBJECTIVE,
            output_schema=SAMPLE_SCHEMA,
        )

        assert len(rt.calls) == 1
        packet = rt.calls[0]["packet"]
        assert packet == {
            "bundle_label": "active-services",
            "miner_objective": SAMPLE_OBJECTIVE,
            "output_schema": SAMPLE_SCHEMA,
            "bundle_description": SAMPLE_BUNDLE.description,
            "expected_output": SAMPLE_BUNDLE.expected_output,
            "paths": list(SAMPLE_BUNDLE.paths),
        }

    def test_packet_contains_only_six_expected_keys(self):
        """Leakage-prevention test — no Recipe-level fields can leak in."""
        rt = FakeRuntime(SAMPLE_RECORDS_RESPONSE)
        m = MinerSubagent(runtime=rt)

        m.mine(
            bundle=SAMPLE_BUNDLE,
            bundle_label="active-services",
            miner_objective="x",
            output_schema="y",
        )

        packet = rt.calls[0]["packet"]
        expected_keys = {
            "bundle_label",
            "miner_objective",
            "output_schema",
            "bundle_description",
            "expected_output",
            "paths",
        }
        assert set(packet.keys()) == expected_keys
        # Specifically verify that Recipe-level fields don't leak through.
        assert "artifact_description" not in packet
        assert "artifact_name" not in packet
        assert "notes_needed" not in packet

    def test_mine_passes_system_prompt(self):
        rt = FakeRuntime(SAMPLE_RECORDS_RESPONSE)
        m = MinerSubagent(runtime=rt)

        m.mine(SAMPLE_BUNDLE, "label", "obj", "schema")

        assert rt.calls[0]["system_prompt"] == MINER_SYSTEM_PROMPT

    def test_mine_passes_tools(self):
        rt = FakeRuntime(SAMPLE_RECORDS_RESPONSE)
        m = MinerSubagent(runtime=rt)

        m.mine(SAMPLE_BUNDLE, "label", "obj", "schema")

        assert rt.calls[0]["tools"] == ["Read", "Grep", "Bash"]

    def test_mine_forwards_event_log(self, tmp_path):
        rt = FakeRuntime(SAMPLE_RECORDS_RESPONSE)
        m = MinerSubagent(runtime=rt)

        log_path = tmp_path / "events.ndjson"
        m.mine(SAMPLE_BUNDLE, "label", "obj", "schema", event_log=log_path)

        assert rt.calls[0]["event_log"] == log_path

    def test_mine_event_log_defaults_to_none(self):
        rt = FakeRuntime(SAMPLE_RECORDS_RESPONSE)
        m = MinerSubagent(runtime=rt)

        m.mine(SAMPLE_BUNDLE, "label", "obj", "schema")

        assert rt.calls[0]["event_log"] is None

    def test_mine_returns_list_of_records(self):
        m = MinerSubagent(runtime=FakeRuntime(SAMPLE_RECORDS_RESPONSE))

        result = m.mine(SAMPLE_BUNDLE, "label", "obj", "schema")

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(r, dict) for r in result)
        assert result[0]["kind"] == "per_note"
        assert result[0]["path"] == "Notes/Plex.md"

    def test_mine_passes_paths_as_list_copy(self):
        """Packet's `paths` is a list copy — not a reference into the bundle."""
        rt = FakeRuntime(SAMPLE_RECORDS_RESPONSE)
        m = MinerSubagent(runtime=rt)

        m.mine(SAMPLE_BUNDLE, "label", "obj", "schema")

        packet_paths = rt.calls[0]["packet"]["paths"]
        assert packet_paths == list(SAMPLE_BUNDLE.paths)
        assert packet_paths is not SAMPLE_BUNDLE.paths


class TestParserHappyPath:
    def test_parses_records(self):
        result = _parse_miner_output(dict(SAMPLE_RECORDS_RESPONSE))
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["kind"] == "per_note"

    def test_parses_empty_records_list(self):
        """An empty records list is valid — bundle may produce no records."""
        result = _parse_miner_output({"records": []})
        assert result == []

    def test_records_pass_through_unchanged(self):
        """Parser is permissive on record shape — any dict with `kind` passes."""
        payload = {
            "records": [
                {
                    "kind": "custom_kind",
                    "anything": "goes",
                    "extra_field": [1, 2, 3],
                },
            ],
        }
        result = _parse_miner_output(payload)
        assert result == [
            {
                "kind": "custom_kind",
                "anything": "goes",
                "extra_field": [1, 2, 3],
            },
        ]


class TestParserErrors:
    def test_missing_records_key_raises(self):
        with pytest.raises(ValueError, match="missing 'records'"):
            _parse_miner_output({"something_else": []})

    def test_records_not_a_list_raises(self):
        with pytest.raises(ValueError, match="must be a list"):
            _parse_miner_output({"records": {"not": "a list"}})

    def test_records_string_raises(self):
        with pytest.raises(ValueError, match="must be a list"):
            _parse_miner_output({"records": "not a list"})

    def test_record_not_a_dict_raises(self):
        with pytest.raises(ValueError, match="record 0 must be a dict"):
            _parse_miner_output({"records": ["not a dict"]})

    def test_record_missing_kind_raises(self):
        with pytest.raises(ValueError, match="record 0 missing 'kind'"):
            _parse_miner_output({"records": [{"path": "Notes/X.md"}]})

    def test_record_kind_not_string_raises(self):
        with pytest.raises(ValueError, match="must be a string"):
            _parse_miner_output({"records": [{"kind": 42, "path": "x"}]})

    def test_records_non_first_invalid_raises(self):
        """Validation runs over every record, not just the first."""
        bad = {
            "records": [
                {"kind": "per_note", "path": "Notes/A.md"},
                {"path": "Notes/B.md"},  # missing kind
            ],
        }
        with pytest.raises(ValueError, match="record 1 missing 'kind'"):
            _parse_miner_output(bad)


class TestParserDefensive:
    def test_unknown_top_level_field_dropped_with_warning(self, caplog):
        import logging

        caplog.set_level(logging.WARNING, logger="subagents.miner")
        payload = {
            "records": [{"kind": "per_note", "path": "x"}],
            "extra_thoughts": "I think...",
        }
        result = _parse_miner_output(payload)
        assert isinstance(result, list)
        assert len(result) == 1
        assert any(
            "miner output" in r.message and "extra_thoughts" in r.message
            for r in caplog.records
        )

    def test_multiple_unknown_fields_all_logged(self, caplog):
        import logging

        caplog.set_level(logging.WARNING, logger="subagents.miner")
        payload = {
            "records": [],
            "warnings": [],
            "summary": "x",
        }
        _parse_miner_output(payload)
        warning_messages = " ".join(r.message for r in caplog.records)
        assert "warnings" in warning_messages
        assert "summary" in warning_messages


class TestParserLogging:
    def test_missing_records_logs_error(self, caplog):
        import logging

        caplog.set_level(logging.ERROR, logger="subagents.miner")
        with pytest.raises(ValueError):
            _parse_miner_output({"foo": "bar"})
        assert any("missing 'records'" in r.message for r in caplog.records)

    def test_records_not_list_logs_error(self, caplog):
        import logging

        caplog.set_level(logging.ERROR, logger="subagents.miner")
        with pytest.raises(ValueError):
            _parse_miner_output({"records": "x"})
        assert any("must be a list" in r.message for r in caplog.records)

    def test_mine_logs_at_debug(self, caplog):
        import logging

        caplog.set_level(logging.DEBUG, logger="subagents.miner")
        m = MinerSubagent(runtime=FakeRuntime(SAMPLE_RECORDS_RESPONSE))
        m.mine(SAMPLE_BUNDLE, "active-services", "obj", "schema")
        assert any(
            "mining bundle" in r.message and "active-services" in r.message
            for r in caplog.records
        )
