"""Tests for storage.py — path helpers, run lifecycle, write-guard.

All write tests redirect both tree roots into tmp_path so nothing lands
on disk outside the test sandbox.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import storage


# --- Tree roots ---

class TestTreeRoots:
    def test_runs_root_lives_under_obsidian_mine(self):
        root = storage.runs_root()
        assert root.name == "runs"
        assert root.parent.name == "obsidian-mine"

    def test_artifacts_root_lives_under_kb_sources(self):
        root = storage.artifacts_root()
        assert root.name == "Vault-Mining"
        assert root.parent.name == "Sources"
        assert root.parent.parent.name == "Knowledge Base"

    def test_runs_and_artifacts_roots_are_distinct(self):
        assert storage.runs_root() != storage.artifacts_root()


# --- Run lifecycle ---

class TestStartRun:
    def test_start_run_creates_directory(self, monkeypatch, tmp_path):
        monkeypatch.setattr(storage, "runs_root", lambda: tmp_path / "runs")
        run_dir = storage.start_run()
        assert run_dir.exists()
        assert run_dir.is_dir()

    def test_start_run_lives_under_runs_root(self, monkeypatch, tmp_path):
        runs = tmp_path / "runs"
        monkeypatch.setattr(storage, "runs_root", lambda: runs)
        run_dir = storage.start_run()
        assert run_dir.parent == runs

    def test_start_run_uses_utc_timestamp_format(self, monkeypatch, tmp_path):
        monkeypatch.setattr(storage, "runs_root", lambda: tmp_path / "runs")
        run_dir = storage.start_run()
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", run_dir.name)


# --- Run-folder paths (codebase side) ---

class TestRunFolderPaths:
    def test_orchestrator_log_path(self, tmp_path):
        run_dir = tmp_path / "run"
        assert storage.orchestrator_log_path(run_dir) == run_dir / "orchestrator.log"

    def test_recipe_path(self, tmp_path):
        run_dir = tmp_path / "run"
        assert storage.recipe_path(run_dir) == run_dir / "recipe.json"

    def test_bundle_dir_nested_under_bundles(self, tmp_path):
        run_dir = tmp_path / "run"
        assert (
            storage.bundle_dir(run_dir, "homelab-philosophy")
            == run_dir / "bundles" / "homelab-philosophy"
        )

    def test_records_path(self, tmp_path):
        run_dir = tmp_path / "run"
        assert (
            storage.records_path(run_dir, "homelab-philosophy")
            == run_dir / "bundles" / "homelab-philosophy" / "records.json"
        )

    def test_miner_log_path_self_identifying(self, tmp_path):
        """Per O5/Conventions: log filename embeds the bundle label."""
        run_dir = tmp_path / "run"
        assert (
            storage.miner_log_path(run_dir, "homelab-philosophy")
            == run_dir / "bundles" / "homelab-philosophy"
            / "homelab-philosophy-miner.log"
        )


# --- Artifact paths (KB side) ---

class TestArtifactPaths:
    def test_artifact_dir_with_explicit_date(self, monkeypatch, tmp_path):
        monkeypatch.setattr(storage, "artifacts_root", lambda: tmp_path / "vm")
        out = storage.artifact_dir("HomeLab Field Guide", date="2026-04-27")
        assert out == tmp_path / "vm" / "2026-04-27 - HomeLab Field Guide"

    def test_artifact_dir_defaults_to_today(self, monkeypatch, tmp_path):
        monkeypatch.setattr(storage, "artifacts_root", lambda: tmp_path / "vm")
        out = storage.artifact_dir("Anything")
        # Date prefix matches YYYY-MM-DD, separator is " - "
        assert re.fullmatch(
            r"\d{4}-\d{2}-\d{2} - Anything", out.name,
        )

    def test_artifact_path(self, tmp_path):
        out = storage.artifact_path(tmp_path, "HomeLab Field Guide")
        assert out == tmp_path / "HomeLab Field Guide.md"

    def test_summary_path_self_identifying(self, tmp_path):
        """Summary filename includes the artifact name (parallels miner-log convention)."""
        out = storage.summary_path(tmp_path, "HomeLab Field Guide")
        assert out == tmp_path / "HomeLab Field Guide - Mining Summary.md"


# --- Write-guard ---

@pytest.fixture
def fake_trees(monkeypatch, tmp_path):
    runs = tmp_path / "runs"
    artifacts = tmp_path / "artifacts"
    runs.mkdir()
    artifacts.mkdir()
    monkeypatch.setattr(storage, "runs_root", lambda: runs)
    monkeypatch.setattr(storage, "artifacts_root", lambda: artifacts)
    return runs, artifacts


class TestSafeWriteAllowed:
    def test_allows_writes_inside_runs_root(self, fake_trees):
        runs, _ = fake_trees
        target = runs / "2026-04-27_12-00-00" / "recipe.json"
        storage.safe_write(target, "{}")
        assert target.read_text(encoding="utf-8") == "{}"

    def test_allows_writes_inside_artifacts_root(self, fake_trees):
        _, artifacts = fake_trees
        target = artifacts / "2026-04-27 - Test" / "Test.md"
        storage.safe_write(target, "# Test\n")
        assert target.read_text(encoding="utf-8") == "# Test\n"

    def test_creates_parent_directories(self, fake_trees):
        runs, _ = fake_trees
        target = runs / "stamp" / "bundles" / "label" / "records.json"
        storage.safe_write(target, '{"records": []}')
        assert target.exists()

    def test_overwrites_existing_file(self, fake_trees):
        runs, _ = fake_trees
        target = runs / "stamp" / "recipe.json"
        storage.safe_write(target, "old")
        storage.safe_write(target, "new")
        assert target.read_text(encoding="utf-8") == "new"


class TestSafeWriteRefuses:
    def test_refuses_path_outside_both_trees(self, fake_trees, tmp_path):
        oops = tmp_path / "outside" / "oops.md"
        with pytest.raises(ValueError, match="outside the mining write trees"):
            storage.safe_write(oops, "x")
        assert not oops.exists()

    def test_refuses_traversal_escape(self, fake_trees):
        runs, _ = fake_trees
        # Path syntactically under runs but resolving outside of it.
        escape = runs / ".." / "escape.md"
        with pytest.raises(ValueError, match="outside the mining write trees"):
            storage.safe_write(escape, "x")

    def test_refuses_at_runs_root_sibling(self, fake_trees, tmp_path):
        # tmp_path is the parent of both trees; anything directly in tmp_path is outside.
        target = tmp_path / "stray.md"
        with pytest.raises(ValueError, match="outside the mining write trees"):
            storage.safe_write(target, "x")
