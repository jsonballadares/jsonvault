"""Command-line surface for the /mine skill.

Two subcommands map the three pipeline stages onto two user-visible
steps. `explore` runs Explorer alone — the user reviews the Recipe
before authorizing Miner + Writer cost. `mine` then runs `run_recipe`
and `run_assembly` back-to-back against the same run folder; nothing
between those two stages needs user input.

stdout is line-oriented `KEY=value` (or `ERROR <label>: <msg>` for
per-bundle errors) so the skill body parses it without depending on
JSON-in-markdown. Errors land on stderr; non-zero exit on failure.

The CLI is intentionally thin — it does no Recipe rendering. The
skill body reads recipe.json directly to render the compact form
(Q3) so the formatting lives in the markdown that's easy to iterate.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import stats
import storage
import summary
from orchestrator import run_assembly, run_explore, run_recipe
from recipe import Denial, Recipe


def cmd_explore(direction: str) -> int:
    """Start a run, call Explorer, persist recipe.json. Print run_dir + kind."""
    run_dir = storage.start_run()
    print(f"RUN_DIR={run_dir}")
    try:
        result = run_explore(direction, run_dir)
    except Exception as e:
        print(f"ERROR explore: {e}", file=sys.stderr)
        return 1
    if isinstance(result, Recipe):
        print("KIND=recipe")
    elif isinstance(result, Denial):
        print("KIND=denial")
    else:
        print(
            f"ERROR explore: unexpected result type {type(result).__name__}",
            file=sys.stderr,
        )
        return 1
    return 0


def cmd_mine(run_dir: Path) -> int:
    """Run Miners + Writer against an existing run folder. Print outcome lines."""
    try:
        rr = run_recipe(run_dir)
    except Exception as e:
        print(f"ERROR mine: {e}", file=sys.stderr)
        return 1
    try:
        ar = run_assembly(run_dir)
    except Exception as e:
        print(f"ERROR assemble: {e}", file=sys.stderr)
        return 1

    print(f"ARTIFACT_NAME={ar.artifact_name}")
    print(f"ARTIFACT_PATH={ar.artifact_path}")
    print(f"SUMMARY_PATH={ar.summary_path}")
    print(f"TOPLINE={_topline(run_dir)}")
    print(f"SUCCEEDED={','.join(rr.bundles_succeeded)}")
    print(f"SKIPPED={','.join(rr.bundles_skipped)}")
    for label, msg in rr.errors.items():
        print(f"ERROR {label}: {msg}")
    return 0


def _topline(run_dir: Path) -> str:
    """One-line aggregate matching the Mining Summary's top-line shape."""
    rs = stats.collect_stats(run_dir)
    total_tools = sum(rs.total_tool_uses.values())
    total_tokens = (
        rs.total_input_tokens
        + rs.total_output_tokens
        + rs.total_cache_read_tokens
        + rs.total_cache_creation_tokens
    )
    return (
        f"{summary.format_duration(rs.total_duration_ms)} · "
        f"{summary.format_tokens(total_tokens)} tokens · "
        f"{total_tools} tool uses · "
        f"{summary.format_cost(rs.total_cost_usd)}"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_explore = sub.add_parser("explore", help="Run Explorer for one direction")
    p_explore.add_argument("direction", help="What to mine (free text)")

    p_mine = sub.add_parser(
        "mine", help="Run Miners + Writer against an existing run folder",
    )
    p_mine.add_argument(
        "run_dir", type=Path, help="Run folder produced by `explore`",
    )

    args = parser.parse_args(argv)
    if args.cmd == "explore":
        return cmd_explore(args.direction)
    if args.cmd == "mine":
        return cmd_mine(args.run_dir)
    parser.error(f"unknown command: {args.cmd}")
    return 2  # unreachable, keeps mypy happy


if __name__ == "__main__":
    sys.exit(main())
