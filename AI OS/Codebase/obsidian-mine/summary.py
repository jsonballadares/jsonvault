"""Mining Summary template — mechanically rendered Python.

W1 = C: the Mining Summary is not produced by the Writer subagent. It is
rendered by this module from the Recipe + per-bundle outcomes + the
RunStats parsed from logs. No LLM call.

The summary follows the KB-tree convention (origin/type/tags inline
Dataview, no status::) and lands at
`Sources/Vault-Mining/<date> - <Artifact Name>/<Artifact Name> - Mining Summary.md`.

Layout (W8):
    1. Top-line aggregate — one scannable line with totals.
    2. Outcome table — per-bundle paths/records/status.
    3. Stats table — per-call stage breakdown plus a Total footer row.
    4. Errors section — only if any bundles were skipped.
    5. References — pointers to the run folder for drilldown.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from stats import RunStats, StageStats


@dataclass(frozen=True)
class BundleOutcome:
    """One bundle's row in the summary's outcome table."""
    label: str
    paths_count: int
    records_count: int | None  # None = bundle was skipped (no records.json)
    error: str | None = None   # set when skipped, if extractable from logs

    @property
    def status(self) -> str:
        return "ok" if self.records_count is not None else "skipped"


def render_summary(
    *,
    artifact_name: str,
    direction: str,
    run_dir: Path,
    bundle_outcomes: list[BundleOutcome],
    run_stats: RunStats,
) -> str:
    """Render the Mining Summary markdown for one run.

    All inputs are explicit; no filesystem reads (the orchestrator
    pre-computed bundle_outcomes and run_stats and passes them in). The
    return value is the full markdown string ready for safe_write.
    """
    lines: list[str] = []
    lines.extend(_render_metadata())
    lines.append("")
    lines.append("---")
    lines.append(f"# {artifact_name} - Mining Summary")
    lines.append("")
    lines.extend(_render_top_line(artifact_name, direction, run_dir, run_stats))
    lines.append("")
    lines.append("## Bundles")
    lines.append("")
    lines.extend(_render_outcome_table(bundle_outcomes))
    lines.append("")
    lines.append("## Stats")
    lines.append("")
    lines.extend(_render_stats_table(run_stats))
    skipped = [b for b in bundle_outcomes if b.records_count is None]
    if skipped:
        lines.append("")
        lines.append("## Errors")
        lines.append("")
        lines.extend(_render_errors(skipped))
    lines.append("")
    lines.append("---")
    lines.append("# References")
    lines.append("")
    lines.extend(_render_references(run_dir))
    return "\n".join(lines) + "\n"


# --- Section renderers ---

def _render_metadata() -> list[str]:
    return [
        "origin:: agent",
        "type:: #vault-mining",
        "tags:: #mining-program",
    ]


def _render_top_line(
    artifact_name: str,
    direction: str,
    run_dir: Path,
    run_stats: RunStats,
) -> list[str]:
    total_tools = sum(run_stats.total_tool_uses.values())
    total_tokens = (
        run_stats.total_input_tokens
        + run_stats.total_output_tokens
        + run_stats.total_cache_read_tokens
        + run_stats.total_cache_creation_tokens
    )
    return [
        f"**Direction:** {direction}",
        f"**Run:** `{run_dir.name}` · "
        f"{format_duration(run_stats.total_duration_ms)} · "
        f"{format_tokens(total_tokens)} tokens · "
        f"{total_tools} tool uses · "
        f"{format_cost(run_stats.total_cost_usd)}",
        f"**Artifact:** [[{artifact_name}]]",
    ]


def _render_outcome_table(outcomes: list[BundleOutcome]) -> list[str]:
    if not outcomes:
        return ["_No bundles._"]
    lines = [
        "| Bundle | Paths | Records | Outcome |",
        "|---|---|---|---|",
    ]
    for o in outcomes:
        records_cell = "—" if o.records_count is None else str(o.records_count)
        lines.append(
            f"| `{o.label}` | {o.paths_count} | {records_cell} | {o.status} |"
        )
    return lines


def _render_stats_table(run_stats: RunStats) -> list[str]:
    stages = _ordered_stages(run_stats)
    if not stages:
        return ["_No stage data._"]

    tools = _all_tools_seen(stages)
    headers = ["Stage", "Time", "Att"] + tools + ["In", "Out", "Cache", "Cost"]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] * len(headers)) + "|",
    ]
    for label, call in stages:
        row = [
            label,
            format_duration(call.duration_ms),
            str(call.attempts) if call.attempts else "—",
        ]
        for tool in tools:
            row.append(str(call.tool_uses.get(tool, 0)))
        row.extend([
            format_tokens(call.input_tokens),
            format_tokens(call.output_tokens),
            format_tokens(call.cache_read_tokens),
            format_cost(call.cost_usd),
        ])
        lines.append("| " + " | ".join(row) + " |")

    # Total footer row.
    total_row = [
        "**Total**",
        format_duration(run_stats.total_duration_ms),
        "",
    ]
    for tool in tools:
        total_row.append(str(run_stats.total_tool_uses.get(tool, 0)))
    total_row.extend([
        format_tokens(run_stats.total_input_tokens),
        format_tokens(run_stats.total_output_tokens),
        format_tokens(run_stats.total_cache_read_tokens),
        format_cost(run_stats.total_cost_usd),
    ])
    lines.append("| " + " | ".join(total_row) + " |")
    return lines


def _render_errors(skipped: list[BundleOutcome]) -> list[str]:
    out: list[str] = []
    for o in skipped:
        msg = o.error if o.error else "(no error message recovered from logs)"
        out.append(f"- `{o.label}`: {msg}")
    return out


def _render_references(run_dir: Path) -> list[str]:
    stamp = run_dir.name
    return [
        f"- Run folder: `runs/{stamp}/`",
        f"- Recipe: `runs/{stamp}/recipe.json`",
        f"- Orchestrator log: `runs/{stamp}/orchestrator.log`",
        f"- Per-bundle logs and records: `runs/{stamp}/bundles/<label>/`",
    ]


# --- Stage ordering ---

def _ordered_stages(run_stats: RunStats) -> list[tuple[str, "StageCall"]]:
    """(label_for_table, CallStats) pairs in display order: Explorer, Miners, Writer."""
    rows: list = []
    if run_stats.explorer is not None:
        rows.append(("Explorer", run_stats.explorer.call))
    for m in run_stats.miners:
        rows.append((f"Miner: `{m.label}`", m.call))
    if run_stats.writer is not None:
        rows.append(("Writer", run_stats.writer.call))
    return rows


def _all_tools_seen(stages: list) -> list[str]:
    """Tool columns in stable order: Read, Grep, Bash if used, then alphabetic extras."""
    seen: set[str] = set()
    for _label, call in stages:
        seen.update(call.tool_uses.keys())
    canonical = ["Read", "Grep", "Bash"]
    used_canonical = [t for t in canonical if t in seen]
    extras = sorted(seen - set(canonical))
    return used_canonical + extras


# --- Formatting helpers (public for testability) ---

def format_duration(ms: int) -> str:
    """1234 -> '1.2s', 67890 -> '1m 8s', 600000 -> '10m 0s'."""
    if ms <= 0:
        return "0s"
    if ms < 1000:
        return f"{ms}ms"
    seconds = ms / 1000
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    remaining = int(seconds - minutes * 60)
    return f"{minutes}m {remaining}s"


def format_tokens(n: int) -> str:
    """500 -> '500', 12500 -> '12.5k', 1234567 -> '1.2M'."""
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1000:.1f}k"
    return f"{n / 1_000_000:.1f}M"


def format_cost(usd: float) -> str:
    """0.0234 -> '$0.0234', 1.50 -> '$1.50', 0.0 -> '$0.00'."""
    if usd <= 0:
        return "$0.00"
    if usd < 1:
        return f"${usd:.4f}"
    return f"${usd:.2f}"
