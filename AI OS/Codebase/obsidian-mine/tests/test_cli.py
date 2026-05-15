"""Tests for cli.py — the thin command-line surface for the /mine skill.

Covers:
    - cmd_explore: Recipe path, Denial path, exception → stderr + non-zero exit.
    - cmd_mine: happy, partial-failure (bundles_skipped + errors), recipe-stage
      failure, assembly-stage failure.
    - main(): subcommand dispatch + arg parsing for both subcommands.

All tests monkeypatch the orchestrator stage helpers so no real subprocesses
are spawned. cli.py itself does nothing other than I/O routing, so tests
focus on the format of its stdout / stderr lines (the contract the skill
body parses).
"""
from __future__ import annotations

from pathlib import Path

import pytest

import cli
from orchestrator import AssemblyResult, RunResult
from recipe import Bundle, Denial, Recipe


# --- Fixtures --------------------------------------------------------

@pytest.fixture
def fake_run_dir(tmp_path: Path) -> Path:
    rd = tmp_path / "fake-run"
    rd.mkdir()
    return rd


def _sample_recipe() -> Recipe:
    return Recipe(
        artifact_name="X",
        notes_needed={
            "a": Bundle(
                paths=["Notes/A.md"], description="d", expected_output="e",
            ),
        },
        miner_objective="mo",
        output_schema="os",
        artifact_description="ad",
    )


def _sample_assembly(run_dir: Path) -> AssemblyResult:
    art_dir = run_dir / "artifact"
    return AssemblyResult(
        run_dir=run_dir,
        artifact_dir=art_dir,
        artifact_path=art_dir / "X.md",
        summary_path=art_dir / "X - Mining Summary.md",
        artifact_name="X",
        bundles_assembled=["a"],
        bundles_skipped=[],
    )


# --- cmd_explore -----------------------------------------------------

def test_explore_recipe_prints_run_dir_and_kind(monkeypatch, capsys, fake_run_dir):
    monkeypatch.setattr(cli.storage, "start_run", lambda: fake_run_dir)
    monkeypatch.setattr(cli, "run_explore", lambda d, r: _sample_recipe())

    rc = cli.cmd_explore("test direction")
    assert rc == 0
    out = capsys.readouterr().out.splitlines()
    assert f"RUN_DIR={fake_run_dir}" in out
    assert "KIND=recipe" in out


def test_explore_denial_prints_kind_denial(monkeypatch, capsys, fake_run_dir):
    monkeypatch.setattr(cli.storage, "start_run", lambda: fake_run_dir)
    monkeypatch.setattr(
        cli, "run_explore", lambda d, r: Denial(reason="no notes for that"),
    )

    rc = cli.cmd_explore("test direction")
    assert rc == 0
    out = capsys.readouterr().out.splitlines()
    assert f"RUN_DIR={fake_run_dir}" in out
    assert "KIND=denial" in out


def test_explore_exception_to_stderr(monkeypatch, capsys, fake_run_dir):
    monkeypatch.setattr(cli.storage, "start_run", lambda: fake_run_dir)

    def boom(direction, run_dir):
        raise RuntimeError("explorer broke")

    monkeypatch.setattr(cli, "run_explore", boom)

    rc = cli.cmd_explore("test")
    captured = capsys.readouterr()
    assert rc == 1
    assert f"RUN_DIR={fake_run_dir}" in captured.out
    assert "ERROR explore" in captured.err
    assert "explorer broke" in captured.err


def test_explore_unexpected_result_type(monkeypatch, capsys, fake_run_dir):
    monkeypatch.setattr(cli.storage, "start_run", lambda: fake_run_dir)
    monkeypatch.setattr(cli, "run_explore", lambda d, r: object())

    rc = cli.cmd_explore("test")
    assert rc == 1
    err = capsys.readouterr().err
    assert "ERROR explore" in err
    assert "unexpected result type" in err


# --- cmd_mine --------------------------------------------------------

def test_mine_happy_path_prints_full_envelope(monkeypatch, capsys, fake_run_dir):
    rr = RunResult(
        run_dir=fake_run_dir,
        bundles_succeeded=["bundle-a", "bundle-b"],
        bundles_skipped=[],
        errors={},
    )
    ar = _sample_assembly(fake_run_dir)
    monkeypatch.setattr(cli, "run_recipe", lambda rd: rr)
    monkeypatch.setattr(cli, "run_assembly", lambda rd: ar)
    monkeypatch.setattr(
        cli, "_topline",
        lambda rd: "1m 0s · 100 tokens · 5 tool uses · $0.10",
    )

    rc = cli.cmd_mine(fake_run_dir)
    assert rc == 0
    out = capsys.readouterr().out.splitlines()
    assert "ARTIFACT_NAME=X" in out
    assert f"ARTIFACT_PATH={ar.artifact_path}" in out
    assert f"SUMMARY_PATH={ar.summary_path}" in out
    assert "TOPLINE=1m 0s · 100 tokens · 5 tool uses · $0.10" in out
    assert "SUCCEEDED=bundle-a,bundle-b" in out
    assert "SKIPPED=" in out
    assert not any(line.startswith("ERROR ") for line in out)


def test_mine_partial_failure_emits_per_bundle_errors(monkeypatch, capsys, fake_run_dir):
    rr = RunResult(
        run_dir=fake_run_dir,
        bundles_succeeded=["bundle-a"],
        bundles_skipped=["bundle-b"],
        errors={"bundle-b": "timeout after 900s"},
    )
    ar = _sample_assembly(fake_run_dir)
    monkeypatch.setattr(cli, "run_recipe", lambda rd: rr)
    monkeypatch.setattr(cli, "run_assembly", lambda rd: ar)
    monkeypatch.setattr(cli, "_topline", lambda rd: "5s · 1 tokens · 1 tool uses · $0.01")

    rc = cli.cmd_mine(fake_run_dir)
    assert rc == 0
    out = capsys.readouterr().out.splitlines()
    assert "SUCCEEDED=bundle-a" in out
    assert "SKIPPED=bundle-b" in out
    assert "ERROR bundle-b: timeout after 900s" in out


def test_mine_recipe_stage_failure(monkeypatch, capsys, fake_run_dir):
    def boom(rd):
        raise RuntimeError("miners gone")

    monkeypatch.setattr(cli, "run_recipe", boom)
    rc = cli.cmd_mine(fake_run_dir)
    assert rc == 1
    err = capsys.readouterr().err
    assert "ERROR mine" in err
    assert "miners gone" in err


def test_mine_assembly_stage_failure(monkeypatch, capsys, fake_run_dir):
    rr = RunResult(
        run_dir=fake_run_dir, bundles_succeeded=["a"],
        bundles_skipped=[], errors={},
    )
    monkeypatch.setattr(cli, "run_recipe", lambda rd: rr)

    def boom(rd):
        raise RuntimeError("writer gone")

    monkeypatch.setattr(cli, "run_assembly", boom)

    rc = cli.cmd_mine(fake_run_dir)
    assert rc == 1
    err = capsys.readouterr().err
    assert "ERROR assemble" in err
    assert "writer gone" in err


# --- main() dispatch -------------------------------------------------

def test_main_dispatches_explore(monkeypatch):
    captured = {}

    def fake_explore(direction):
        captured["direction"] = direction
        return 0

    monkeypatch.setattr(cli, "cmd_explore", fake_explore)
    rc = cli.main(["explore", "find dormant ideas"])
    assert rc == 0
    assert captured["direction"] == "find dormant ideas"


def test_main_dispatches_mine(monkeypatch, tmp_path):
    captured = {}

    def fake_mine(run_dir):
        captured["run_dir"] = run_dir
        return 0

    monkeypatch.setattr(cli, "cmd_mine", fake_mine)
    rc = cli.main(["mine", str(tmp_path)])
    assert rc == 0
    assert captured["run_dir"] == tmp_path


def test_main_no_subcommand_errors(capsys):
    with pytest.raises(SystemExit):
        cli.main([])
