"""Tests for runtimes/claude_code.py — ClaudeCodeRuntime adapter."""

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from runtimes.claude_code import ClaudeCodeRuntime, _log_event, _parse_worker_output


LOGGER_NAME = "runtimes.claude_code"


def _has_log(caplog, level: str, substring: str) -> bool:
    return any(
        rec.levelname == level and substring in rec.getMessage()
        for rec in caplog.records
    )


def _ndjson(events: list[dict]) -> list[str]:
    """Render a list of events as NDJSON lines (each ending with \\n)."""
    return [json.dumps(e) + "\n" for e in events]


def _default_events(inner_json: str = '{"ok": true}') -> list[dict]:
    """Minimal event stream: a system init then a result event."""
    return [
        {"type": "system", "subtype": "init"},
        {"type": "result", "subtype": "success", "result": inner_json},
    ]


def _mock_popen(
    events: list[dict] | None = None,
    returncode: int = 0,
    stderr: str = "",
) -> MagicMock:
    """Build a MagicMock that stands in for subprocess.Popen's return."""
    if events is None:
        events = _default_events()
    proc = MagicMock()
    proc.stdout = iter(_ndjson(events))
    proc.stderr = MagicMock()
    proc.stderr.read.return_value = stderr
    proc.returncode = returncode
    proc.wait.return_value = returncode
    return proc


class TestClaudeCodeRuntimeConstruction:
    def test_defaults(self):
        r = ClaudeCodeRuntime()
        assert r.claude_bin == "claude"
        assert r.timeout is None
        assert r.cwd is None
        assert r.add_dirs == []

    def test_custom_claude_bin(self):
        r = ClaudeCodeRuntime(claude_bin="/usr/local/bin/claude")
        assert r.claude_bin == "/usr/local/bin/claude"

    def test_add_dirs_defaults_to_empty_when_none(self):
        r = ClaudeCodeRuntime(add_dirs=None)
        assert r.add_dirs == []


class TestClaudeCodeRuntimeInvoke:
    @patch("runtimes.claude_code.subprocess.Popen")
    def test_serializes_packet_as_user_prompt(self, mock_popen):
        mock_popen.return_value = _mock_popen()
        r = ClaudeCodeRuntime()
        packet = {"objective": "test", "inputs": {"note_paths": ["A.md"]}}
        r.invoke(packet, system_prompt="role-prompt")
        cmd = mock_popen.call_args[0][0]
        p_idx = cmd.index("-p")
        assert json.loads(cmd[p_idx + 1]) == packet

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_passes_system_prompt(self, mock_popen):
        mock_popen.return_value = _mock_popen()
        r = ClaudeCodeRuntime()
        r.invoke({}, system_prompt="explorer-system-prompt")
        cmd = mock_popen.call_args[0][0]
        idx = cmd.index("--append-system-prompt")
        assert cmd[idx + 1] == "explorer-system-prompt"

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_uses_stream_json_output_format(self, mock_popen):
        mock_popen.return_value = _mock_popen()
        r = ClaudeCodeRuntime()
        r.invoke({}, "sys")
        cmd = mock_popen.call_args[0][0]
        idx = cmd.index("--output-format")
        assert cmd[idx + 1] == "stream-json"
        assert "--verbose" in cmd

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_tools_passed_when_provided(self, mock_popen):
        mock_popen.return_value = _mock_popen()
        r = ClaudeCodeRuntime()
        r.invoke({}, "sys", tools=["Read", "Grep"])
        cmd = mock_popen.call_args[0][0]
        idx = cmd.index("--allowed-tools")
        assert cmd[idx + 1] == "Read,Grep"

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_tools_omitted_when_none(self, mock_popen):
        mock_popen.return_value = _mock_popen()
        r = ClaudeCodeRuntime()
        r.invoke({}, "sys")
        cmd = mock_popen.call_args[0][0]
        assert "--allowed-tools" not in cmd

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_add_dirs_emitted_as_flags(self, mock_popen):
        mock_popen.return_value = _mock_popen()
        r = ClaudeCodeRuntime(add_dirs=["/path/one", "/path/two"])
        r.invoke({}, "sys")
        cmd = mock_popen.call_args[0][0]
        indices = [i for i, x in enumerate(cmd) if x == "--add-dir"]
        assert len(indices) == 2
        assert cmd[indices[0] + 1] == "/path/one"
        assert cmd[indices[1] + 1] == "/path/two"

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_no_add_dirs_by_default(self, mock_popen):
        mock_popen.return_value = _mock_popen()
        r = ClaudeCodeRuntime()
        r.invoke({}, "sys")
        cmd = mock_popen.call_args[0][0]
        assert "--add-dir" not in cmd

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_cwd_passed_to_subprocess(self, mock_popen):
        mock_popen.return_value = _mock_popen()
        r = ClaudeCodeRuntime(cwd="/some/where")
        r.invoke({}, "sys")
        assert mock_popen.call_args.kwargs["cwd"] == "/some/where"

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_cwd_defaults_to_none(self, mock_popen):
        mock_popen.return_value = _mock_popen()
        r = ClaudeCodeRuntime()
        r.invoke({}, "sys")
        assert mock_popen.call_args.kwargs["cwd"] is None

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_returns_parsed_inner_json(self, mock_popen):
        mock_popen.return_value = _mock_popen(
            events=_default_events(inner_json='{"recipe": {"artifact_name": "X"}}')
        )
        r = ClaudeCodeRuntime()
        result = r.invoke({}, "sys")
        assert result == {"recipe": {"artifact_name": "X"}}

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_extracts_result_from_final_event(self, mock_popen):
        events = [
            {"type": "system", "subtype": "init"},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "thinking"}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}},
            {"type": "result", "subtype": "success", "result": '{"final": true}'},
        ]
        mock_popen.return_value = _mock_popen(events=events)
        r = ClaudeCodeRuntime()
        result = r.invoke({}, "sys")
        assert result == {"final": True}

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_raises_on_nonzero_returncode(self, mock_popen):
        mock_popen.return_value = _mock_popen(returncode=1, stderr="boom")
        import subprocess as sp
        r = ClaudeCodeRuntime()
        with pytest.raises(sp.CalledProcessError) as exc_info:
            r.invoke({}, "sys")
        assert exc_info.value.returncode == 1
        assert exc_info.value.stderr == "boom"

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_raises_when_no_result_event(self, mock_popen):
        events = [
            {"type": "system", "subtype": "init"},
            {"type": "assistant", "message": {"content": []}},
        ]
        mock_popen.return_value = _mock_popen(events=events)
        r = ClaudeCodeRuntime()
        with pytest.raises(ValueError, match="no result event"):
            r.invoke({}, "sys")

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_skips_blank_lines_in_stream(self, mock_popen):
        proc = MagicMock()
        proc.stdout = iter([
            "\n",
            json.dumps({"type": "system", "subtype": "init"}) + "\n",
            "\n",
            json.dumps({"type": "result", "result": '{"ok": true}'}) + "\n",
        ])
        proc.stderr = MagicMock()
        proc.stderr.read.return_value = ""
        proc.returncode = 0
        mock_popen.return_value = proc
        r = ClaudeCodeRuntime()
        result = r.invoke({}, "sys")
        assert result == {"ok": True}

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_warns_on_non_json_lines_but_continues(self, mock_popen, caplog):
        proc = MagicMock()
        proc.stdout = iter([
            "not json at all\n",
            json.dumps({"type": "result", "result": '{"ok": true}'}) + "\n",
        ])
        proc.stderr = MagicMock()
        proc.stderr.read.return_value = ""
        proc.returncode = 0
        mock_popen.return_value = proc
        r = ClaudeCodeRuntime()
        with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
            result = r.invoke({}, "sys")
        assert result == {"ok": True}
        assert _has_log(caplog, "WARNING", "non-JSON line")


class TestClaudeCodeRuntimeEventLog:
    @patch("runtimes.claude_code.subprocess.Popen")
    def test_writes_event_log_when_path_provided(self, mock_popen, tmp_path):
        events = [
            {"type": "system", "subtype": "init"},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "hi"}]}},
            {"type": "result", "subtype": "success", "result": '{"ok": true}'},
        ]
        mock_popen.return_value = _mock_popen(events=events)
        log_path = tmp_path / "events.ndjson"
        r = ClaudeCodeRuntime()
        r.invoke({}, "sys", event_log=log_path)
        assert log_path.exists()
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 3
        assert json.loads(lines[0])["type"] == "system"
        assert json.loads(lines[1])["type"] == "assistant"
        assert json.loads(lines[2])["type"] == "result"

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_no_event_log_written_when_none(self, mock_popen, tmp_path):
        mock_popen.return_value = _mock_popen()
        r = ClaudeCodeRuntime()
        r.invoke({}, "sys")
        assert list(tmp_path.iterdir()) == []


class TestParseWorkerOutput:
    def test_plain_json(self):
        assert _parse_worker_output('{"a": 1}') == {"a": 1}

    def test_strips_markdown_fence_with_lang(self):
        text = '```json\n{"a": 1}\n```'
        assert _parse_worker_output(text) == {"a": 1}

    def test_strips_bare_fence(self):
        text = '```\n{"a": 1}\n```'
        assert _parse_worker_output(text) == {"a": 1}

    def test_recovers_from_prose_wrap(self):
        text = 'Sure, here is the result: {"a": 1} Hope that helps!'
        assert _parse_worker_output(text) == {"a": 1}

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            _parse_worker_output("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            _parse_worker_output("   \n  ")

    def test_no_json_raises(self):
        with pytest.raises(ValueError):
            _parse_worker_output("just some prose with no braces")


class TestClaudeCodeRuntimeLogging:
    @patch("runtimes.claude_code.subprocess.Popen")
    def test_logs_invocation_at_debug(self, mock_popen, caplog):
        mock_popen.return_value = _mock_popen()
        r = ClaudeCodeRuntime()
        with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
            r.invoke({"objective": "x"}, "sys", tools=["Read"])
        assert _has_log(caplog, "DEBUG", "invoking claude")

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_logs_worker_result_at_debug(self, mock_popen, caplog):
        mock_popen.return_value = _mock_popen(
            events=_default_events(inner_json='{"ok": true}')
        )
        r = ClaudeCodeRuntime()
        with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
            r.invoke({}, "sys")
        assert _has_log(caplog, "DEBUG", "worker result")

    @patch("runtimes.claude_code.subprocess.Popen")
    def test_logs_subprocess_error_before_reraise(self, mock_popen, caplog):
        import subprocess as sp
        mock_popen.return_value = _mock_popen(returncode=2, stderr="boom")
        r = ClaudeCodeRuntime()
        with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
            with pytest.raises(sp.CalledProcessError):
                r.invoke({}, "sys")
        assert _has_log(caplog, "ERROR", "claude subprocess failed")
        assert _has_log(caplog, "ERROR", "returncode=2")
        assert _has_log(caplog, "ERROR", "boom")


class TestParseWorkerOutputLogging:
    def test_empty_logs_error(self, caplog):
        with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
            with pytest.raises(ValueError):
                _parse_worker_output("")
        assert _has_log(caplog, "ERROR", "empty output")

    def test_fence_strip_logs_debug(self, caplog):
        with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
            _parse_worker_output('```json\n{"a": 1}\n```')
        assert _has_log(caplog, "DEBUG", "stripped markdown fence")

    def test_regex_fallback_logs_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
            _parse_worker_output('prose wrap {"a": 1} more prose')
        assert _has_log(caplog, "WARNING", "regex fallback")

    def test_no_json_logs_error(self, caplog):
        with caplog.at_level(logging.ERROR, logger=LOGGER_NAME):
            with pytest.raises(ValueError):
                _parse_worker_output("just prose no braces")
        assert _has_log(caplog, "ERROR", "no JSON object")


class TestLogEvent:
    """Translation of stream-json events into Python log lines."""

    def test_assistant_text_logs_at_info(self, caplog):
        event = {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "I will search now."}]},
        }
        with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
            _log_event(event)
        assert _has_log(caplog, "INFO", "worker text: I will search now.")

    def test_assistant_tool_use_logs_at_info_with_name(self, caplog):
        event = {
            "type": "assistant",
            "message": {
                "content": [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "grep -r foo Notes/"},
                    }
                ]
            },
        }
        with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
            _log_event(event)
        assert _has_log(caplog, "INFO", "worker tool_use Bash")
        assert _has_log(caplog, "INFO", "grep -r foo")

    def test_assistant_thinking_logs_at_info(self, caplog):
        event = {
            "type": "assistant",
            "message": {
                "content": [{"type": "thinking", "thinking": "Let me reason about this."}]
            },
        }
        with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
            _log_event(event)
        assert _has_log(caplog, "INFO", "worker thinking: Let me reason")

    def test_user_tool_result_logs_at_debug_with_byte_count(self, caplog):
        event = {
            "type": "user",
            "message": {
                "content": [
                    {"type": "tool_result", "content": "result text here"}
                ]
            },
        }
        with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
            _log_event(event)
        assert _has_log(caplog, "DEBUG", "worker tool_result bytes=16")

    def test_user_tool_result_handles_list_content(self, caplog):
        """Some tool_results have content as a list of {type: text, text: ...} blocks."""
        event = {
            "type": "user",
            "message": {
                "content": [
                    {
                        "type": "tool_result",
                        "content": [
                            {"type": "text", "text": "line one"},
                            {"type": "text", "text": "line two"},
                        ],
                    }
                ]
            },
        }
        with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
            _log_event(event)
        assert _has_log(caplog, "DEBUG", "worker tool_result")
        assert _has_log(caplog, "DEBUG", "line one")
        assert _has_log(caplog, "DEBUG", "line two")

    def test_api_retry_logs_at_warning(self, caplog):
        event = {
            "type": "system",
            "subtype": "api_retry",
            "attempt": 3,
            "max_retries": 10,
            "retry_delay_ms": 1500.5,
            "error_status": 529,
        }
        with caplog.at_level(logging.WARNING, logger=LOGGER_NAME):
            _log_event(event)
        assert _has_log(caplog, "WARNING", "api_retry attempt=3/10")
        assert _has_log(caplog, "WARNING", "status=529")

    def test_init_logs_at_debug(self, caplog):
        event = {
            "type": "system",
            "subtype": "init",
            "session_id": "abc-123",
            "model": "claude-opus-4-7",
        }
        with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
            _log_event(event)
        assert _has_log(caplog, "DEBUG", "worker init session=abc-123")
        assert _has_log(caplog, "DEBUG", "claude-opus-4-7")

    def test_result_logs_at_info_with_metadata(self, caplog):
        event = {
            "type": "result",
            "subtype": "success",
            "duration_ms": 18234,
            "num_turns": 12,
            "usage": {
                "input_tokens": 320,
                "output_tokens": 1450,
                "cache_read_input_tokens": 8000,
                "cache_creation_input_tokens": 200,
            },
            "total_cost_usd": 0.0234,
            "result": '{"ok": true}',
        }
        with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
            _log_event(event)
        assert _has_log(caplog, "INFO", "worker result")
        assert _has_log(caplog, "INFO", "ms=18234")
        assert _has_log(caplog, "INFO", "turns=12")
        assert _has_log(caplog, "INFO", "input_tokens=320")
        assert _has_log(caplog, "INFO", "output_tokens=1450")
        assert _has_log(caplog, "INFO", "cache_read_tokens=8000")
        assert _has_log(caplog, "INFO", "cache_creation_tokens=200")
        assert _has_log(caplog, "INFO", "cost_usd=0.0234")

    def test_result_logs_zero_when_usage_missing(self, caplog):
        """Older streams may not include usage; defaults to zeros."""
        event = {
            "type": "result",
            "subtype": "success",
            "duration_ms": 1000,
            "num_turns": 2,
            "result": '{"ok": true}',
        }
        with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
            _log_event(event)
        assert _has_log(caplog, "INFO", "input_tokens=0")
        assert _has_log(caplog, "INFO", "output_tokens=0")
        assert _has_log(caplog, "INFO", "cost_usd=0")

    def test_long_text_is_truncated(self, caplog):
        event = {
            "type": "assistant",
            "message": {"content": [{"type": "text", "text": "x" * 1000}]},
        }
        with caplog.at_level(logging.INFO, logger=LOGGER_NAME):
            _log_event(event)
        assert _has_log(caplog, "INFO", "+500 more chars")

    def test_unknown_event_type_logs_at_debug(self, caplog):
        event = {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed"}}
        with caplog.at_level(logging.DEBUG, logger=LOGGER_NAME):
            _log_event(event)
        assert _has_log(caplog, "DEBUG", "rate_limit status=allowed")
