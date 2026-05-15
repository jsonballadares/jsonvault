"""ClaudeCodeRuntime — runs a Subagent call via `claude -p`.

Ported from `mining-report/subagent.py`'s `ClaudeCodeSubagent`. The role-vs-
runtime split (Component Map §2) moves the system prompt and tool grants
out of the adapter — Subagent passes them at call time.

Uses `--output-format stream-json --verbose` so every event Claude emits
during the call (system init, assistant messages, tool_use blocks,
tool_result blocks, the final result) lands as one NDJSON line on stdout.

Each event is also translated into a tidy Python log line as it arrives:
assistant text and tool_use at INFO, tool_result and operational events
(init, rate_limit) at DEBUG, api_retry at WARNING, the final result at
INFO. Long content is truncated to keep logs scannable.

Callers can additionally capture the raw NDJSON stream to disk via the
per-call `event_log` parameter — useful for forensic debugging when the
log narrative isn't enough.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
import threading
from pathlib import Path

from .base import SubagentRuntime


logger = logging.getLogger(__name__)


_TRUNCATE = 500


def _trunc(s: str) -> str:
    if len(s) <= _TRUNCATE:
        return s
    return s[:_TRUNCATE] + f"... [+{len(s) - _TRUNCATE} more chars]"


def _log_event(event: dict, log: logging.Logger | None = None) -> None:
    """Translate a stream-json event into a Python log line.

    `log` defaults to the module logger; the orchestrator passes a
    per-bundle logger so events for that bundle land in its log file.
    """
    log = log or logger
    et = event.get("type")
    if et == "system":
        subtype = event.get("subtype")
        if subtype == "api_retry":
            log.warning(
                "worker api_retry attempt=%s/%s delay_ms=%.0f status=%s",
                event.get("attempt"),
                event.get("max_retries"),
                event.get("retry_delay_ms", 0),
                event.get("error_status"),
            )
        elif subtype == "init":
            log.debug(
                "worker init session=%s model=%s",
                event.get("session_id"),
                event.get("model"),
            )
        else:
            log.debug("worker system/%s", subtype)
    elif et == "assistant":
        message = event.get("message", {})
        for block in message.get("content", []) or []:
            btype = block.get("type")
            if btype == "text":
                log.info("worker text: %s", _trunc(block.get("text", "")))
            elif btype == "tool_use":
                log.info(
                    "worker tool_use %s input=%s",
                    block.get("name"),
                    _trunc(json.dumps(block.get("input", {}))),
                )
            elif btype == "thinking":
                log.info(
                    "worker thinking: %s", _trunc(block.get("thinking", ""))
                )
            else:
                log.debug("worker assistant block %s", btype)
    elif et == "user":
        message = event.get("message", {})
        for block in message.get("content", []) or []:
            if block.get("type") != "tool_result":
                continue
            content = block.get("content", "")
            if isinstance(content, list):
                parts = [
                    sub.get("text", "")
                    for sub in content
                    if isinstance(sub, dict) and sub.get("type") == "text"
                ]
                content = "\n".join(parts)
            content = str(content)
            log.debug(
                "worker tool_result bytes=%d: %s",
                len(content),
                _trunc(content),
            )
    elif et == "rate_limit_event":
        info = event.get("rate_limit_info", {})
        log.debug("worker rate_limit status=%s", info.get("status"))
    elif et == "result":
        usage = event.get("usage") or {}
        log.info(
            "worker result subtype=%s ms=%s turns=%s "
            "input_tokens=%s output_tokens=%s "
            "cache_read_tokens=%s cache_creation_tokens=%s "
            "cost_usd=%s",
            event.get("subtype"),
            event.get("duration_ms"),
            event.get("num_turns"),
            usage.get("input_tokens", 0),
            usage.get("output_tokens", 0),
            usage.get("cache_read_input_tokens", 0),
            usage.get("cache_creation_input_tokens", 0),
            event.get("total_cost_usd", 0),
        )
    else:
        log.debug("worker event type=%s", et)


class ClaudeCodeRuntime(SubagentRuntime):
    def __init__(
        self,
        claude_bin: str = "claude",
        timeout: int | None = None,
        cwd: str | None = None,
        add_dirs: list[str] | None = None,
    ) -> None:
        self.claude_bin = claude_bin
        self.timeout = timeout
        self.cwd = cwd
        self.add_dirs = add_dirs or []

    def invoke(
        self,
        packet: dict,
        system_prompt: str,
        tools: list[str] | None = None,
        event_log: Path | None = None,
        logger: logging.Logger | None = None,
    ) -> dict:
        log = logger or globals()["logger"]
        prompt = json.dumps(packet)
        cmd = [
            self.claude_bin,
            "-p", prompt,
            "--output-format", "stream-json",
            "--verbose",
            "--append-system-prompt", system_prompt,
        ]
        if tools is not None:
            cmd.extend(["--allowed-tools", ",".join(tools)])
        for d in self.add_dirs:
            cmd.extend(["--add-dir", d])
        log.debug(
            "invoking claude: bin=%s tools=%s cwd=%s timeout=%s "
            "event_log=%s packet=%s",
            self.claude_bin, tools, self.cwd, self.timeout, event_log, prompt,
        )

        log_file = open(event_log, "w", encoding="utf-8") if event_log else None
        stderr_buf: list[str] = []
        final_result: str | None = None
        timed_out = False

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=self.cwd,
        )

        # Drain stderr in a background thread to avoid pipe-buffer deadlock.
        stderr_thread = threading.Thread(
            target=lambda: stderr_buf.append(proc.stderr.read() or ""),
            daemon=True,
        )
        stderr_thread.start()

        # Watchdog kills the process if self.timeout elapses without completion.
        done = threading.Event()
        if self.timeout is not None:
            def _watchdog() -> None:
                nonlocal timed_out
                if not done.wait(self.timeout):
                    timed_out = True
                    proc.kill()
            threading.Thread(target=_watchdog, daemon=True).start()

        try:
            for line in proc.stdout:
                if log_file:
                    log_file.write(line)
                    log_file.flush()
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    event = json.loads(stripped)
                except json.JSONDecodeError:
                    log.warning("non-JSON line from claude: %s", stripped)
                    continue
                _log_event(event, log)
                if event.get("type") == "result":
                    final_result = event.get("result", "")
            proc.wait()
        finally:
            done.set()
            stderr_thread.join(timeout=5)
            if log_file:
                log_file.close()

        stderr = "".join(stderr_buf)

        if timed_out:
            log.error(
                "claude subprocess timed out after %ss (killed)", self.timeout,
            )
            raise subprocess.TimeoutExpired(cmd, self.timeout, stderr=stderr)

        if proc.returncode != 0:
            log.error(
                "claude subprocess failed: returncode=%s stderr=%s",
                proc.returncode, stderr,
            )
            raise subprocess.CalledProcessError(
                proc.returncode, cmd, stderr=stderr,
            )

        log.debug("worker result: %s", final_result)
        if final_result is None:
            log.error("claude stream produced no result event")
            raise ValueError("Claude stream produced no result event")
        return _parse_worker_output(final_result, log)


def _parse_worker_output(text: str, log: logging.Logger | None = None) -> dict:
    """Recover a JSON object from the worker's `result` string.

    Strips an optional markdown code fence; falls back to scanning for the
    first `{...}` block if the unwrapped text isn't valid JSON.
    """
    log = log or logger
    s = (text or "").strip()
    if not s:
        log.error("worker returned empty output")
        raise ValueError("Worker returned empty output")

    if s.startswith("```"):
        first_newline = s.find("\n")
        if first_newline != -1:
            s = s[first_newline + 1:]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()
        log.debug("stripped markdown fence from worker output")

    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", s, re.DOTALL)
    if match:
        try:
            obj = json.loads(match.group(0))
            log.warning(
                "recovered JSON via regex fallback — worker did not emit pure JSON"
            )
            return obj
        except json.JSONDecodeError as e:
            log.error(
                "worker output contains JSON-looking block but parsing failed: %s", s
            )
            raise ValueError(f"Worker output is not valid JSON: {e}") from e
    log.error("worker output contains no JSON object: %s", s)
    raise ValueError("Worker output contains no JSON object")
