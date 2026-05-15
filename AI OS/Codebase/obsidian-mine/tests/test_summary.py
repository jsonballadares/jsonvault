"""Tests for summary.py — Mining Summary template renderer."""
from __future__ import annotations

from pathlib import Path

import pytest

from stats import CallStats, RunStats, StageStats
from summary import (
    BundleOutcome,
    format_cost,
    format_duration,
    format_tokens,
    render_summary,
)


# --- Format helpers --------------------------------------------------------

class TestFormatDuration:
    def test_zero_returns_zero_seconds(self):
        assert format_duration(0) == "0s"

    def test_negative_returns_zero(self):
        """Defensive: negative ms should not produce weird output."""
        assert format_duration(-1) == "0s"

    def test_sub_second_returns_ms(self):
        assert format_duration(450) == "450ms"

    def test_sub_minute_returns_seconds_with_decimal(self):
        assert format_duration(1500) == "1.5s"
        assert format_duration(45000) == "45.0s"

    def test_above_minute_returns_minutes_and_seconds(self):
        assert format_duration(60000) == "1m 0s"
        assert format_duration(125000) == "2m 5s"

    def test_long_run(self):
        assert format_duration(3661000) == "61m 1s"


class TestFormatTokens:
    def test_small_returns_plain_int(self):
        assert format_tokens(0) == "0"
        assert format_tokens(500) == "500"

    def test_thousands_returns_k_suffix(self):
        assert format_tokens(1000) == "1.0k"
        assert format_tokens(12500) == "12.5k"

    def test_millions_returns_m_suffix(self):
        assert format_tokens(1234567) == "1.2M"


class TestFormatCost:
    def test_zero_returns_two_decimals(self):
        assert format_cost(0) == "$0.00"

    def test_sub_dollar_returns_four_decimals(self):
        assert format_cost(0.0234) == "$0.0234"

    def test_multi_dollar_returns_two_decimals(self):
        assert format_cost(1.5) == "$1.50"
        assert format_cost(12.34) == "$12.34"
        assert format_cost(12.345) == "$12.35"  # f-string :.2f rounds


class TestBundleOutcome:
    def test_records_count_none_means_skipped(self):
        o = BundleOutcome(label="x", paths_count=5, records_count=None)
        assert o.status == "skipped"

    def test_records_count_int_means_ok(self):
        o = BundleOutcome(label="x", paths_count=5, records_count=10)
        assert o.status == "ok"

    def test_records_count_zero_still_means_ok(self):
        """An empty bundle (no records produced) is still 'ok' if records.json exists."""
        o = BundleOutcome(label="x", paths_count=5, records_count=0)
        assert o.status == "ok"


# --- render_summary --------------------------------------------------------

def _make_stats(
    *,
    explorer: StageStats | None = None,
    miners: list[StageStats] | None = None,
    writer: StageStats | None = None,
) -> RunStats:
    return RunStats(
        explorer=explorer, miners=miners or [], writer=writer,
    )


def _call(
    *, ms=10000, attempts=1, tools=None,
    input_t=100, output_t=200, cache_r=1000, cache_c=10, cost=0.01,
) -> CallStats:
    return CallStats(
        duration_ms=ms,
        num_turns=10,
        attempts=attempts,
        tool_uses=tools or {},
        input_tokens=input_t,
        output_tokens=output_t,
        cache_read_tokens=cache_r,
        cache_creation_tokens=cache_c,
        cost_usd=cost,
    )


@pytest.fixture
def sample_run(tmp_path) -> Path:
    rd = tmp_path / "2026-04-28_12-00-00"
    rd.mkdir()
    return rd


class TestRenderSummary:
    def test_includes_kb_tree_metadata_header(self, sample_run):
        rs = _make_stats(
            explorer=StageStats(label="explorer", call=_call(tools={"Read": 1}))
        )
        md = render_summary(
            artifact_name="X", direction="d", run_dir=sample_run,
            bundle_outcomes=[], run_stats=rs,
        )
        assert md.startswith("origin:: agent\n")
        assert "type:: #vault-mining" in md
        assert "tags:: #mining-program" in md
        # No status:: per W9 KB-tree convention.
        assert "status::" not in md

    def test_header_uses_artifact_name_as_h1(self, sample_run):
        rs = _make_stats()
        md = render_summary(
            artifact_name="HomeLab Field Guide", direction="d", run_dir=sample_run,
            bundle_outcomes=[], run_stats=rs,
        )
        assert "# HomeLab Field Guide - Mining Summary" in md

    def test_top_line_includes_direction_and_aggregate_metrics(self, sample_run):
        rs = _make_stats(
            explorer=StageStats(
                label="explorer",
                call=_call(ms=60000, tools={"Read": 5}, input_t=1000, output_t=500, cost=0.05),
            ),
            writer=StageStats(
                label="writer",
                call=_call(ms=30000, tools={"Read": 2}, input_t=2000, output_t=300, cost=0.04),
            ),
        )
        md = render_summary(
            artifact_name="X", direction="my question", run_dir=sample_run,
            bundle_outcomes=[], run_stats=rs,
        )
        assert "**Direction:** my question" in md
        assert "**Run:**" in md
        assert "1m 30s" in md  # 60s + 30s
        assert "tool uses" in md
        assert "**Artifact:** [[X]]" in md

    def test_outcome_table_lists_all_bundles(self, sample_run):
        outcomes = [
            BundleOutcome(label="alpha", paths_count=5, records_count=8),
            BundleOutcome(label="beta", paths_count=12, records_count=15),
        ]
        md = render_summary(
            artifact_name="X", direction="d", run_dir=sample_run,
            bundle_outcomes=outcomes, run_stats=_make_stats(),
        )
        assert "## Bundles" in md
        assert "| `alpha` | 5 | 8 | ok |" in md
        assert "| `beta` | 12 | 15 | ok |" in md

    def test_outcome_table_marks_skipped_bundle(self, sample_run):
        outcomes = [
            BundleOutcome(label="ok-one", paths_count=5, records_count=8),
            BundleOutcome(label="failed-one", paths_count=12, records_count=None),
        ]
        md = render_summary(
            artifact_name="X", direction="d", run_dir=sample_run,
            bundle_outcomes=outcomes, run_stats=_make_stats(),
        )
        assert "| `failed-one` | 12 | — | skipped |" in md

    def test_stats_table_has_expected_columns(self, sample_run):
        rs = _make_stats(
            explorer=StageStats(
                label="explorer", call=_call(tools={"Read": 5, "Bash": 2}),
            ),
            miners=[
                StageStats(label="alpha", call=_call(tools={"Read": 12})),
            ],
            writer=StageStats(label="writer", call=_call(tools={"Read": 3})),
        )
        md = render_summary(
            artifact_name="X", direction="d", run_dir=sample_run,
            bundle_outcomes=[], run_stats=rs,
        )
        assert "## Stats" in md
        # Static canonical columns appear in order Read, Bash (Grep absent).
        # In + Out + Cache + Cost are static.
        # Stage label + Time + Att are also there.
        assert "| Stage | Time | Att |" in md
        assert "Cost |" in md

    def test_stats_table_includes_explorer_miners_writer_rows(self, sample_run):
        rs = _make_stats(
            explorer=StageStats(label="explorer", call=_call(tools={"Read": 5})),
            miners=[
                StageStats(label="alpha", call=_call(tools={"Read": 12})),
                StageStats(label="beta", call=_call(tools={"Read": 8})),
            ],
            writer=StageStats(label="writer", call=_call(tools={"Read": 3})),
        )
        md = render_summary(
            artifact_name="X", direction="d", run_dir=sample_run,
            bundle_outcomes=[], run_stats=rs,
        )
        assert "| Explorer |" in md
        assert "| Miner: `alpha` |" in md
        assert "| Miner: `beta` |" in md
        assert "| Writer |" in md
        assert "**Total**" in md

    def test_stats_table_dynamic_tool_columns(self, sample_run):
        """Tools beyond Read/Grep/Bash (e.g. Glob) get their own columns."""
        rs = _make_stats(
            explorer=StageStats(
                label="explorer", call=_call(tools={"Read": 5, "Glob": 2}),
            ),
        )
        md = render_summary(
            artifact_name="X", direction="d", run_dir=sample_run,
            bundle_outcomes=[], run_stats=rs,
        )
        # Glob is a dynamic column.
        first_line_of_stats = next(
            line for line in md.splitlines()
            if line.startswith("| Stage |")
        )
        assert "Glob" in first_line_of_stats
        assert "Read" in first_line_of_stats

    def test_stats_table_canonical_tool_order(self, sample_run):
        """Read, Grep, Bash always appear in that order before extras."""
        rs = _make_stats(
            explorer=StageStats(
                label="explorer",
                call=_call(tools={"Bash": 1, "Grep": 1, "Read": 1, "Aardvark": 1}),
            ),
        )
        md = render_summary(
            artifact_name="X", direction="d", run_dir=sample_run,
            bundle_outcomes=[], run_stats=rs,
        )
        header = next(
            line for line in md.splitlines() if line.startswith("| Stage |")
        )
        # Read appears before Grep before Bash before Aardvark.
        read_pos = header.index("| Read |")
        grep_pos = header.index("| Grep |")
        bash_pos = header.index("| Bash |")
        aardvark_pos = header.index("| Aardvark |")
        assert read_pos < grep_pos < bash_pos < aardvark_pos

    def test_total_row_aggregates_across_stages(self, sample_run):
        rs = _make_stats(
            explorer=StageStats(
                label="explorer",
                call=_call(ms=60000, tools={"Read": 5}, input_t=100, output_t=200, cost=0.01),
            ),
            miners=[
                StageStats(
                    label="alpha",
                    call=_call(ms=30000, tools={"Read": 10}, input_t=200, output_t=400, cost=0.02),
                ),
            ],
        )
        md = render_summary(
            artifact_name="X", direction="d", run_dir=sample_run,
            bundle_outcomes=[], run_stats=rs,
        )
        total_row = next(line for line in md.splitlines() if "**Total**" in line)
        assert "1m 30s" in total_row     # 60s + 30s
        assert " 15 " in total_row        # 5 + 10 reads
        assert "$0.0300" in total_row     # cost summed (under $1, four decimals)

    def test_errors_section_omitted_when_no_skipped(self, sample_run):
        outcomes = [
            BundleOutcome(label="alpha", paths_count=5, records_count=8),
        ]
        md = render_summary(
            artifact_name="X", direction="d", run_dir=sample_run,
            bundle_outcomes=outcomes, run_stats=_make_stats(),
        )
        assert "## Errors" not in md

    def test_errors_section_includes_skipped_bundles(self, sample_run):
        outcomes = [
            BundleOutcome(label="ok-one", paths_count=5, records_count=8),
            BundleOutcome(
                label="failed-one", paths_count=12, records_count=None,
                error="subprocess timed out after 900s",
            ),
            BundleOutcome(
                label="failed-two", paths_count=8, records_count=None,
            ),
        ]
        md = render_summary(
            artifact_name="X", direction="d", run_dir=sample_run,
            bundle_outcomes=outcomes, run_stats=_make_stats(),
        )
        assert "## Errors" in md
        assert "`failed-one`" in md
        assert "subprocess timed out after 900s" in md
        assert "`failed-two`" in md
        assert "(no error message recovered from logs)" in md

    def test_references_point_to_run_folder(self, sample_run):
        md = render_summary(
            artifact_name="X", direction="d", run_dir=sample_run,
            bundle_outcomes=[], run_stats=_make_stats(),
        )
        assert "# References" in md
        assert "runs/2026-04-28_12-00-00/" in md
        assert "recipe.json" in md
        assert "orchestrator.log" in md

    def test_handles_missing_explorer(self, sample_run):
        """A run that hasn't reached Writer yet should still render — just no Writer row."""
        rs = _make_stats(
            explorer=None,  # impossible in practice but defensively handled
            miners=[StageStats(label="x", call=_call(tools={"Read": 2}))],
        )
        md = render_summary(
            artifact_name="X", direction="d", run_dir=sample_run,
            bundle_outcomes=[], run_stats=rs,
        )
        assert "Explorer |" not in md  # no Explorer row
        assert "Miner: `x`" in md

    def test_handles_no_stages(self, sample_run):
        """Defensive — empty stats still produces valid markdown."""
        md = render_summary(
            artifact_name="X", direction="d", run_dir=sample_run,
            bundle_outcomes=[], run_stats=_make_stats(),
        )
        assert "## Stats" in md
        assert "_No stage data._" in md

    def test_handles_no_bundles(self, sample_run):
        md = render_summary(
            artifact_name="X", direction="d", run_dir=sample_run,
            bundle_outcomes=[], run_stats=_make_stats(),
        )
        assert "_No bundles._" in md

    def test_output_ends_with_newline(self, sample_run):
        md = render_summary(
            artifact_name="X", direction="d", run_dir=sample_run,
            bundle_outcomes=[], run_stats=_make_stats(),
        )
        assert md.endswith("\n")
