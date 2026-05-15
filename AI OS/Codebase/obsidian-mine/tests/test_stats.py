"""Tests for stats.py — log-driven stats collection."""
from __future__ import annotations

from pathlib import Path

import pytest

from stats import (
    CallStats,
    RunStats,
    StageStats,
    _parse_call_stats,
    collect_stats,
)


# --- Fixture builders -----------------------------------------------------

def _ts(seq: int) -> str:
    """Synthetic timestamp prefix; only the trailing logger:message matters."""
    return f"2026-04-28 09:00:{seq:02d},000 INFO obsidian-mine.run.x:"


def _explorer_phase(
    *,
    tool_uses: list[str],
    duration_ms: int = 100000,
    turns: int = 10,
    input_tokens: int = 500,
    output_tokens: int = 1000,
    cache_read: int = 5000,
    cache_creation: int = 100,
    cost: float = 0.05,
    attempts: int = 1,
    end_marker: str = "explorer produced Recipe: artifact_name='X' bundles=3",
) -> list[str]:
    lines = [f"{_ts(0)} explorer stage starting: direction='test'"]
    for n in range(1, attempts + 1):
        lines.append(f"{_ts(n)} explorer attempt {n}")
    for tool in tool_uses:
        lines.append(f"{_ts(2)} worker tool_use {tool} input={{}}")
    lines.append(
        f"{_ts(3)} worker result subtype=success ms={duration_ms} turns={turns} "
        f"input_tokens={input_tokens} output_tokens={output_tokens} "
        f"cache_read_tokens={cache_read} cache_creation_tokens={cache_creation} "
        f"cost_usd={cost}"
    )
    lines.append(f"{_ts(4)} {end_marker}")
    return lines


def _writer_phase(
    *,
    tool_uses: list[str],
    duration_ms: int = 80000,
    turns: int = 8,
    input_tokens: int = 800,
    output_tokens: int = 1500,
    cache_read: int = 7000,
    cache_creation: int = 50,
    cost: float = 0.04,
    attempts: int = 1,
) -> list[str]:
    lines = [f"{_ts(10)} writer stage starting"]
    for n in range(1, attempts + 1):
        lines.append(f"{_ts(10 + n)} writer attempt {n}")
    for tool in tool_uses:
        lines.append(f"{_ts(11)} worker tool_use {tool} input={{}}")
    lines.append(
        f"{_ts(12)} worker result subtype=success ms={duration_ms} turns={turns} "
        f"input_tokens={input_tokens} output_tokens={output_tokens} "
        f"cache_read_tokens={cache_read} cache_creation_tokens={cache_creation} "
        f"cost_usd={cost}"
    )
    lines.append(f"{_ts(13)} writer produced artifact: bytes=4096")
    return lines


def _mining_phase_orchestration_only() -> list[str]:
    return [
        f"{_ts(5)} mining stage starting: bundles=3 concurrency=4",
        f"{_ts(6)} bundle succeeded: foo records=10",
        f"{_ts(7)} bundle succeeded: bar records=12",
        f"{_ts(8)} bundle succeeded: baz records=8",
        f"{_ts(9)} mining stage complete: succeeded=3 skipped=0",
    ]


def _miner_log(
    bundle_label: str,
    *,
    tool_uses: list[str],
    duration_ms: int = 60000,
    turns: int = 15,
    input_tokens: int = 1000,
    output_tokens: int = 2000,
    cache_read: int = 8000,
    cache_creation: int = 30,
    cost: float = 0.03,
    attempts: int = 1,
    succeeded: bool = True,
) -> list[str]:
    lines = []
    for n in range(1, attempts + 1):
        lines.append(f"{_ts(n)} miner attempt {n}: bundle={bundle_label} paths=5")
    for tool in tool_uses:
        lines.append(f"{_ts(2)} worker tool_use {tool} input={{}}")
    if succeeded:
        lines.append(
            f"{_ts(3)} worker result subtype=success ms={duration_ms} turns={turns} "
            f"input_tokens={input_tokens} output_tokens={output_tokens} "
            f"cache_read_tokens={cache_read} cache_creation_tokens={cache_creation} "
            f"cost_usd={cost}"
        )
    return lines


def _build_run(tmp_path: Path, orchestrator_lines: list[str], bundle_logs: dict[str, list[str]]) -> Path:
    """Materialize a synthetic run folder under tmp_path."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "orchestrator.log").write_text("\n".join(orchestrator_lines), encoding="utf-8")
    bundles_root = run_dir / "bundles"
    bundles_root.mkdir()
    for label, lines in bundle_logs.items():
        bdir = bundles_root / label
        bdir.mkdir()
        (bdir / f"{label}-miner.log").write_text("\n".join(lines), encoding="utf-8")
    return run_dir


# --- _parse_call_stats unit tests -----------------------------------------

class TestParseCallStats:
    def test_empty_lines_returns_zeroed_stats(self):
        result = _parse_call_stats([])
        assert result == CallStats()

    def test_counts_tool_uses_by_name(self):
        result = _parse_call_stats([
            "worker tool_use Read input={}",
            "worker tool_use Read input={}",
            "worker tool_use Grep input={}",
            "worker tool_use Bash input={}",
        ])
        assert result.tool_uses == {"Read": 2, "Grep": 1, "Bash": 1}
        assert result.total_tool_uses == 4

    def test_picks_up_attempt_number(self):
        result = _parse_call_stats([
            "miner attempt 1: bundle=foo paths=5",
            "miner attempt 2: bundle=foo paths=5",
        ])
        assert result.attempts == 2

    def test_parses_result_with_full_token_metadata(self):
        result = _parse_call_stats([
            "worker result subtype=success ms=12345 turns=10 "
            "input_tokens=500 output_tokens=1000 "
            "cache_read_tokens=8000 cache_creation_tokens=200 "
            "cost_usd=0.0234",
        ])
        assert result.duration_ms == 12345
        assert result.num_turns == 10
        assert result.input_tokens == 500
        assert result.output_tokens == 1000
        assert result.cache_read_tokens == 8000
        assert result.cache_creation_tokens == 200
        assert result.cost_usd == pytest.approx(0.0234)

    def test_parses_old_format_result_without_tokens(self):
        """Pre-token-capture logs still parse — token fields default to 0."""
        result = _parse_call_stats([
            "worker result subtype=success ms=1000 turns=5",
        ])
        assert result.duration_ms == 1000
        assert result.num_turns == 5
        assert result.input_tokens == 0
        assert result.cost_usd == 0.0

    def test_sums_across_retries(self):
        """Two attempts means two `worker result` events; cost sums."""
        result = _parse_call_stats([
            "miner attempt 1: bundle=foo paths=5",
            "worker tool_use Read input={}",
            "worker result subtype=success ms=500 turns=2 "
            "input_tokens=100 output_tokens=200 "
            "cache_read_tokens=1000 cache_creation_tokens=10 cost_usd=0.01",
            "miner attempt 2: bundle=foo paths=5",
            "worker tool_use Read input={}",
            "worker result subtype=success ms=600 turns=3 "
            "input_tokens=110 output_tokens=210 "
            "cache_read_tokens=1100 cache_creation_tokens=11 cost_usd=0.011",
        ])
        assert result.attempts == 2
        assert result.duration_ms == 1100
        assert result.num_turns == 5
        assert result.input_tokens == 210
        assert result.output_tokens == 410
        assert result.cost_usd == pytest.approx(0.021)
        assert result.tool_uses == {"Read": 2}

    def test_skipped_bundle_with_no_result_event(self):
        """Bundle whose retries all failed has tool_uses but no `worker result`."""
        result = _parse_call_stats([
            "miner attempt 1: bundle=foo paths=5",
            "worker tool_use Read input={}",
            "miner attempt 2: bundle=foo paths=5",
            "worker tool_use Read input={}",
            "retry failed; bundle skipped: foo err=...",
        ])
        assert result.attempts == 2
        assert result.duration_ms == 0
        assert result.num_turns == 0
        assert result.tool_uses == {"Read": 2}
        assert result.cost_usd == 0.0


# --- collect_stats integration tests --------------------------------------

class TestCollectStats:
    def test_full_run_with_explorer_miners_writer(self, tmp_path):
        orch = (
            _explorer_phase(tool_uses=["Read", "Read", "Grep"])
            + _mining_phase_orchestration_only()
            + _writer_phase(tool_uses=["Read"])
        )
        bundle_logs = {
            "foo": _miner_log("foo", tool_uses=["Read"] * 5),
            "bar": _miner_log("bar", tool_uses=["Read"] * 7 + ["Grep"]),
        }
        run_dir = _build_run(tmp_path, orch, bundle_logs)

        stats = collect_stats(run_dir)

        assert stats.explorer is not None
        assert stats.explorer.label == "explorer"
        assert stats.explorer.call.tool_uses == {"Read": 2, "Grep": 1}
        assert stats.explorer.call.duration_ms == 100000

        assert len(stats.miners) == 2
        labels = {m.label for m in stats.miners}
        assert labels == {"foo", "bar"}
        miners_by_label = {m.label: m for m in stats.miners}
        assert miners_by_label["foo"].call.tool_uses == {"Read": 5}
        assert miners_by_label["bar"].call.tool_uses == {"Read": 7, "Grep": 1}

        assert stats.writer is not None
        assert stats.writer.label == "writer"
        assert stats.writer.call.tool_uses == {"Read": 1}

    def test_explorer_only_run_no_writer_yet(self, tmp_path):
        """A run halted after Explorer (e.g., Denial) parses with writer=None."""
        orch = _explorer_phase(
            tool_uses=["Read"],
            end_marker="explorer produced Denial: reason='vault too thin'",
        )
        run_dir = _build_run(tmp_path, orch, {})
        stats = collect_stats(run_dir)
        assert stats.explorer is not None
        assert stats.writer is None
        assert stats.miners == []

    def test_explorer_then_miners_no_writer(self, tmp_path):
        """A run completed through Mining but before Writer exists."""
        orch = _explorer_phase(tool_uses=["Read"]) + _mining_phase_orchestration_only()
        bundle_logs = {"foo": _miner_log("foo", tool_uses=["Read", "Read"])}
        run_dir = _build_run(tmp_path, orch, bundle_logs)
        stats = collect_stats(run_dir)
        assert stats.explorer is not None
        assert len(stats.miners) == 1
        assert stats.writer is None

    def test_missing_orchestrator_log(self, tmp_path):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        stats = collect_stats(run_dir)
        assert stats.explorer is None
        assert stats.writer is None
        assert stats.miners == []

    def test_skipped_bundle_appears_with_zero_duration(self, tmp_path):
        """A bundle whose retries all failed appears in stats with 0 duration."""
        orch = _explorer_phase(tool_uses=["Read"]) + _mining_phase_orchestration_only()
        bundle_logs = {
            "ok": _miner_log("ok", tool_uses=["Read"] * 3),
            "skipped": _miner_log(
                "skipped", tool_uses=["Read"] * 2, attempts=2, succeeded=False,
            ),
        }
        run_dir = _build_run(tmp_path, orch, bundle_logs)
        stats = collect_stats(run_dir)
        miners = {m.label: m for m in stats.miners}
        assert miners["skipped"].call.attempts == 2
        assert miners["skipped"].call.duration_ms == 0
        assert miners["skipped"].call.tool_uses == {"Read": 2}

    def test_run_stats_aggregates_across_stages(self, tmp_path):
        orch = (
            _explorer_phase(
                tool_uses=["Read"] * 3,
                duration_ms=10000, input_tokens=100, output_tokens=200,
                cache_read=1000, cache_creation=10, cost=0.01,
            )
            + _mining_phase_orchestration_only()
            + _writer_phase(
                tool_uses=["Read"] * 2,
                duration_ms=20000, input_tokens=300, output_tokens=400,
                cache_read=3000, cache_creation=30, cost=0.03,
            )
        )
        bundle_logs = {
            "a": _miner_log(
                "a", tool_uses=["Read"] * 4,
                duration_ms=5000, input_tokens=50, output_tokens=80,
                cache_read=500, cache_creation=5, cost=0.005,
            ),
            "b": _miner_log(
                "b", tool_uses=["Grep"],
                duration_ms=6000, input_tokens=60, output_tokens=90,
                cache_read=600, cache_creation=6, cost=0.006,
            ),
        }
        run_dir = _build_run(tmp_path, orch, bundle_logs)
        stats = collect_stats(run_dir)

        assert stats.total_duration_ms == 10000 + 20000 + 5000 + 6000
        assert stats.total_input_tokens == 100 + 300 + 50 + 60
        assert stats.total_output_tokens == 200 + 400 + 80 + 90
        assert stats.total_cache_read_tokens == 1000 + 3000 + 500 + 600
        assert stats.total_cache_creation_tokens == 10 + 30 + 5 + 6
        assert stats.total_cost_usd == pytest.approx(0.01 + 0.03 + 0.005 + 0.006)
        # Read = 3 (explorer) + 2 (writer) + 4 (a). Grep = 1 (b).
        assert stats.total_tool_uses == {"Read": 9, "Grep": 1}

    def test_handles_old_logs_without_token_fields(self, tmp_path):
        """A run from before the runtime-token change parses cleanly."""
        orch = [
            f"{_ts(0)} explorer stage starting: direction='x'",
            f"{_ts(1)} explorer attempt 1",
            f"{_ts(2)} worker tool_use Read input={{}}",
            f"{_ts(3)} worker result subtype=success ms=1000 turns=5",
            f"{_ts(4)} explorer produced Recipe: artifact_name='Y' bundles=1",
        ]
        bundle_logs = {
            "x": [
                f"{_ts(0)} miner attempt 1: bundle=x paths=2",
                f"{_ts(1)} worker tool_use Read input={{}}",
                f"{_ts(2)} worker result subtype=success ms=2000 turns=3",
            ],
        }
        run_dir = _build_run(tmp_path, orch, bundle_logs)
        stats = collect_stats(run_dir)
        assert stats.explorer.call.duration_ms == 1000
        assert stats.explorer.call.input_tokens == 0
        assert stats.explorer.call.cost_usd == 0.0
        assert stats.miners[0].call.duration_ms == 2000
        assert stats.miners[0].call.input_tokens == 0
        assert stats.total_cost_usd == 0.0

    def test_writer_aborted_after_retry_still_collected(self, tmp_path):
        """Writer that retried then aborted still produces stats up to abort marker."""
        writer_lines = [
            f"{_ts(10)} writer stage starting",
            f"{_ts(11)} writer attempt 1",
            f"{_ts(12)} worker tool_use Read input={{}}",
            f"{_ts(13)} writer attempt 2",
            f"{_ts(14)} worker tool_use Read input={{}}",
            f"{_ts(15)} writer aborted after retry: ...",
        ]
        orch = _explorer_phase(tool_uses=["Read"]) + writer_lines
        run_dir = _build_run(tmp_path, orch, {})
        stats = collect_stats(run_dir)
        assert stats.writer is not None
        assert stats.writer.call.attempts == 2
        assert stats.writer.call.tool_uses == {"Read": 2}
        assert stats.writer.call.duration_ms == 0


class TestRunStatsHelpers:
    def test_total_tool_uses_with_no_stages(self):
        run = RunStats(explorer=None, miners=[], writer=None)
        assert run.total_tool_uses == {}
        assert run.total_duration_ms == 0
        assert run.total_cost_usd == 0.0

    def test_call_stats_total_tool_uses_property(self):
        call = CallStats(tool_uses={"Read": 3, "Grep": 1, "Bash": 2})
        assert call.total_tool_uses == 6
