"""Stats collection by parsing run logs.

The runtime emits everything we need as INFO log lines, so stats fall out
of `<run_dir>/orchestrator.log` + each `<run_dir>/bundles/<label>/<label>-miner.log`
without any in-process accumulation.

Lines we look for:
    worker tool_use <Tool> input=...
    worker result subtype=... ms=... turns=...
                  [input_tokens=... output_tokens=...
                   cache_read_tokens=... cache_creation_tokens=... cost_usd=...]
    explorer|miner|writer attempt N
    explorer stage starting / explorer produced ... / explorer aborted ...
    writer stage starting / writer produced ... / writer aborted ...

Per-stage aggregation sums tool uses + tokens + cost across all attempts —
retries cost real money, so include them. `duration_ms` and `num_turns` also
sum (a retried stage took longer; the user should see that). `attempts`
captures the highest attempt number seen.

Old-format logs (pre-token-capture) parse to zero token/cost fields. A
bundle whose retries all failed has no `worker result` line and aggregates
to zero duration with attempts=2 and the tool_uses it managed to make.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import storage


_TOOL_USE_RE = re.compile(r"worker tool_use (\w+)")
_RESULT_RE = re.compile(
    r"worker result "
    r"subtype=(?P<subtype>\S+) "
    r"ms=(?P<ms>\d+) "
    r"turns=(?P<turns>\d+)"
    r"(?: input_tokens=(?P<input>\d+) "
    r"output_tokens=(?P<output>\d+) "
    r"cache_read_tokens=(?P<cache_read>\d+) "
    r"cache_creation_tokens=(?P<cache_creation>\d+) "
    r"cost_usd=(?P<cost>[\d.]+))?"
)
_ATTEMPT_RE = re.compile(r"(?:explorer|miner|writer) attempt (\d+)")
_EXPLORER_START_RE = re.compile(r"explorer stage starting")
_EXPLORER_END_RE = re.compile(
    r"explorer produced Recipe|explorer produced Denial|explorer aborted"
)
_WRITER_START_RE = re.compile(r"writer stage starting")
_WRITER_END_RE = re.compile(r"writer produced|writer aborted")


@dataclass(frozen=True)
class CallStats:
    duration_ms: int = 0
    num_turns: int = 0
    attempts: int = 0
    tool_uses: dict[str, int] = field(default_factory=dict)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    cost_usd: float = 0.0

    @property
    def total_tool_uses(self) -> int:
        return sum(self.tool_uses.values())


@dataclass(frozen=True)
class StageStats:
    label: str
    call: CallStats


@dataclass(frozen=True)
class RunStats:
    explorer: StageStats | None
    miners: list[StageStats]
    writer: StageStats | None

    @property
    def total_duration_ms(self) -> int:
        return self._sum_int("duration_ms")

    @property
    def total_input_tokens(self) -> int:
        return self._sum_int("input_tokens")

    @property
    def total_output_tokens(self) -> int:
        return self._sum_int("output_tokens")

    @property
    def total_cache_read_tokens(self) -> int:
        return self._sum_int("cache_read_tokens")

    @property
    def total_cache_creation_tokens(self) -> int:
        return self._sum_int("cache_creation_tokens")

    @property
    def total_cost_usd(self) -> float:
        return float(self._sum("cost_usd"))

    @property
    def total_tool_uses(self) -> dict[str, int]:
        agg: dict[str, int] = {}
        for stage in self._all_stages():
            for tool, count in stage.call.tool_uses.items():
                agg[tool] = agg.get(tool, 0) + count
        return agg

    def _all_stages(self) -> list[StageStats]:
        stages: list[StageStats] = []
        if self.explorer is not None:
            stages.append(self.explorer)
        stages.extend(self.miners)
        if self.writer is not None:
            stages.append(self.writer)
        return stages

    def _sum(self, attr: str) -> float:
        return sum(getattr(s.call, attr) for s in self._all_stages())

    def _sum_int(self, attr: str) -> int:
        return int(self._sum(attr))


def collect_stats(run_dir: Path) -> RunStats:
    """Parse all logs under `run_dir` into a RunStats object.

    Missing logs / missing stages return None for that stage. A run that
    hasn't reached the writer phase yet still parses cleanly with
    writer=None.
    """
    orchestrator_log = storage.orchestrator_log_path(run_dir)
    explorer = _slice_orchestrator(
        orchestrator_log, _EXPLORER_START_RE, _EXPLORER_END_RE, "explorer"
    )
    writer = _slice_orchestrator(
        orchestrator_log, _WRITER_START_RE, _WRITER_END_RE, "writer"
    )
    miners = _collect_miner_stats(run_dir)
    return RunStats(explorer=explorer, miners=miners, writer=writer)


def _slice_orchestrator(
    log_path: Path,
    start_re: re.Pattern[str],
    end_re: re.Pattern[str],
    label: str,
) -> StageStats | None:
    if not log_path.exists():
        return None
    lines = log_path.read_text(encoding="utf-8").splitlines()
    in_stage = False
    slice_lines: list[str] = []
    for line in lines:
        if start_re.search(line):
            in_stage = True
            slice_lines.append(line)
            continue
        if in_stage:
            slice_lines.append(line)
            if end_re.search(line):
                break
    if not slice_lines:
        return None
    return StageStats(label=label, call=_parse_call_stats(slice_lines))


def _collect_miner_stats(run_dir: Path) -> list[StageStats]:
    bundles_root = run_dir / "bundles"
    if not bundles_root.exists():
        return []
    out: list[StageStats] = []
    for bundle_dir in sorted(bundles_root.iterdir()):
        if not bundle_dir.is_dir():
            continue
        label = bundle_dir.name
        log_path = bundle_dir / f"{label}-miner.log"
        if not log_path.exists():
            continue
        lines = log_path.read_text(encoding="utf-8").splitlines()
        out.append(StageStats(label=label, call=_parse_call_stats(lines)))
    return out


def _parse_call_stats(lines: list[str]) -> CallStats:
    tool_uses: dict[str, int] = {}
    input_tokens = output_tokens = 0
    cache_read = cache_creation = 0
    cost_usd = 0.0
    duration_ms = num_turns = 0
    attempts = 0
    for line in lines:
        m = _TOOL_USE_RE.search(line)
        if m:
            tool = m.group(1)
            tool_uses[tool] = tool_uses.get(tool, 0) + 1
            continue
        m = _ATTEMPT_RE.search(line)
        if m:
            attempts = max(attempts, int(m.group(1)))
            continue
        m = _RESULT_RE.search(line)
        if m:
            duration_ms += int(m.group("ms"))
            num_turns += int(m.group("turns"))
            if m.group("input") is not None:
                input_tokens += int(m.group("input"))
                output_tokens += int(m.group("output"))
                cache_read += int(m.group("cache_read"))
                cache_creation += int(m.group("cache_creation"))
                cost_usd += float(m.group("cost"))
    return CallStats(
        duration_ms=duration_ms,
        num_turns=num_turns,
        attempts=attempts,
        tool_uses=tool_uses,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read,
        cache_creation_tokens=cache_creation,
        cost_usd=cost_usd,
    )
