"""Tests for orchestrator.py — pipeline stage helpers + log routing.

Covers:
    - Logger setup helpers (run + per-bundle), idempotency, propagate=False.
    - Recipe (de)serialization round-trip.
    - run_explore happy Recipe / happy Denial / retry-then-success / retry-then-abort.
    - run_recipe happy / parallel / retry-then-success / retry-then-skip /
      records.json written for succeeded bundles only / Denial recipe rejection.

All tests redirect storage roots into tmp_path and inject fake Subagents
via the `_make_explorer` / `_make_miner` seam — no real subprocesses.
"""

from __future__ import annotations

import json
import logging
import subprocess
import threading
import time

import pytest

import orchestrator
import storage
from recipe import Bundle, Denial, Recipe


# --- Fakes -------------------------------------------------------------

class FakeExplorer:
    """Stand-in for ExplorerSubagent — emits a scripted sequence of outcomes.

    `outcomes` is a list of either Recipe/Denial values (returned) or
    Exception instances (raised).
    """

    def __init__(self, outcomes: list) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict] = []

    def explore(self, direction, event_log=None, logger=None):
        self.calls.append({
            "direction": direction, "event_log": event_log, "logger": logger,
        })
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class FakeMiner:
    """Stand-in for MinerSubagent — per-bundle scripted outcomes."""

    def __init__(self, outcomes: dict[str, list]) -> None:
        # outcomes[label] is a list consumed in attempt order.
        self.outcomes = {k: list(v) for k, v in outcomes.items()}
        self.calls: list[dict] = []
        self._lock = threading.Lock()

    def mine(self, bundle, bundle_label, miner_objective, output_schema,
             event_log=None, logger=None):
        with self._lock:
            self.calls.append({
                "bundle_label": bundle_label,
                "logger": logger,
                "ts": time.monotonic(),
            })
        outcome = self.outcomes[bundle_label].pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


# --- Fixtures ----------------------------------------------------------

@pytest.fixture
def fake_trees(monkeypatch, tmp_path):
    runs = tmp_path / "runs"
    artifacts = tmp_path / "artifacts"
    runs.mkdir()
    artifacts.mkdir()
    monkeypatch.setattr(storage, "runs_root", lambda: runs)
    monkeypatch.setattr(storage, "artifacts_root", lambda: artifacts)
    return runs, artifacts


@pytest.fixture
def run_dir(fake_trees):
    runs, _ = fake_trees
    rd = runs / "2026-04-27_12-00-00"
    rd.mkdir()
    return rd


@pytest.fixture(autouse=True)
def _close_loggers():
    """Close handlers attached to obsidian-mine.* loggers between tests.

    File handlers hold the run log open; without cleanup the next test
    in the same tmp_path session can hit Windows-style file locks (and
    on macOS, leaks file descriptors across the whole session).
    """
    yield
    for name, log in list(logging.Logger.manager.loggerDict.items()):
        if not isinstance(log, logging.Logger):
            continue
        if not name.startswith("obsidian-mine."):
            continue
        for h in list(log.handlers):
            h.close()
            log.removeHandler(h)


# --- Sample data -------------------------------------------------------

SAMPLE_RECIPE = Recipe(
    artifact_name="HomeLab Field Guide",
    notes_needed={
        "philosophy": Bundle(
            paths=["Notes/HomeLab Philosophy.md"],
            description="Why I run a homelab.",
            expected_output="One per_note record.",
        ),
        "services": Bundle(
            paths=["Notes/Plex.md", "Notes/Sonarr.md"],
            description="Active services.",
            expected_output="One per_note record per note plus a bundle_summary.",
        ),
    },
    miner_objective="Capture purpose and status.",
    output_schema='per_note: {"kind": "per_note", "path": str}',
    artifact_description="A practical overview anchored to source notes.",
)

SAMPLE_DENIAL = Denial(reason="No homelab notes; populate vault first.")


def _records(label: str, n: int = 1) -> list[dict]:
    return [
        {"kind": "per_note", "path": f"Notes/{label}-{i}.md"} for i in range(n)
    ]


# --- Logger setup ------------------------------------------------------

class TestLoggerSetup:
    def test_run_logger_writes_to_orchestrator_log(self, run_dir):
        log = orchestrator._setup_run_logger(run_dir)
        log.info("hello")
        for h in log.handlers:
            h.flush()
        text = (run_dir / "orchestrator.log").read_text(encoding="utf-8")
        assert "hello" in text

    def test_run_logger_does_not_propagate(self, run_dir):
        log = orchestrator._setup_run_logger(run_dir)
        assert log.propagate is False

    def test_run_logger_idempotent(self, run_dir):
        log_a = orchestrator._setup_run_logger(run_dir)
        log_b = orchestrator._setup_run_logger(run_dir)
        assert log_a is log_b
        assert len(log_a.handlers) == 1

    def test_bundle_logger_writes_to_bundle_log(self, run_dir):
        log = orchestrator._setup_bundle_logger(run_dir, "philosophy")
        log.info("bundle event")
        for h in log.handlers:
            h.flush()
        bundle_log = run_dir / "bundles" / "philosophy" / "philosophy-miner.log"
        assert "bundle event" in bundle_log.read_text(encoding="utf-8")

    def test_bundle_logger_does_not_propagate_to_run_logger(self, run_dir):
        run_log = orchestrator._setup_run_logger(run_dir)
        bundle_log = orchestrator._setup_bundle_logger(run_dir, "philosophy")
        bundle_log.info("private to bundle")
        for h in run_log.handlers:
            h.flush()
        for h in bundle_log.handlers:
            h.flush()
        run_text = (run_dir / "orchestrator.log").read_text(encoding="utf-8")
        assert "private to bundle" not in run_text


# --- Recipe persistence round-trip ------------------------------------

class TestRecipePersistence:
    def test_recipe_round_trip(self):
        text = orchestrator._serialize_recipe(SAMPLE_RECIPE)
        parsed = orchestrator._deserialize_recipe(text)
        assert parsed == SAMPLE_RECIPE

    def test_denial_round_trip(self):
        text = orchestrator._serialize_recipe(SAMPLE_DENIAL)
        parsed = orchestrator._deserialize_recipe(text)
        assert parsed == SAMPLE_DENIAL

    def test_serialized_recipe_has_kind_discriminator(self):
        text = orchestrator._serialize_recipe(SAMPLE_RECIPE)
        assert json.loads(text)["kind"] == "recipe"

    def test_serialized_denial_has_kind_discriminator(self):
        text = orchestrator._serialize_recipe(SAMPLE_DENIAL)
        assert json.loads(text)["kind"] == "denial"

    def test_deserialize_unknown_kind_raises(self):
        bad = json.dumps({"kind": "proposal", "x": 1})
        with pytest.raises(ValueError, match="must be 'recipe' or 'denial'"):
            orchestrator._deserialize_recipe(bad)


# --- run_explore -------------------------------------------------------

class TestRunExploreHappyPath:
    def test_returns_recipe(self, monkeypatch, run_dir):
        explorer = FakeExplorer([SAMPLE_RECIPE])
        monkeypatch.setattr(orchestrator, "_make_explorer", lambda: explorer)
        result = orchestrator.run_explore("anything", run_dir)
        assert result == SAMPLE_RECIPE

    def test_persists_recipe_json(self, monkeypatch, run_dir):
        explorer = FakeExplorer([SAMPLE_RECIPE])
        monkeypatch.setattr(orchestrator, "_make_explorer", lambda: explorer)
        orchestrator.run_explore("anything", run_dir)
        text = storage.recipe_path(run_dir).read_text(encoding="utf-8")
        assert json.loads(text)["kind"] == "recipe"

    def test_returns_denial(self, monkeypatch, run_dir):
        explorer = FakeExplorer([SAMPLE_DENIAL])
        monkeypatch.setattr(orchestrator, "_make_explorer", lambda: explorer)
        result = orchestrator.run_explore("anything", run_dir)
        assert result == SAMPLE_DENIAL

    def test_persists_denial_json(self, monkeypatch, run_dir):
        explorer = FakeExplorer([SAMPLE_DENIAL])
        monkeypatch.setattr(orchestrator, "_make_explorer", lambda: explorer)
        orchestrator.run_explore("anything", run_dir)
        data = json.loads(storage.recipe_path(run_dir).read_text(encoding="utf-8"))
        assert data["kind"] == "denial"
        assert data["reason"] == SAMPLE_DENIAL.reason

    def test_passes_run_logger_to_explorer(self, monkeypatch, run_dir):
        explorer = FakeExplorer([SAMPLE_RECIPE])
        monkeypatch.setattr(orchestrator, "_make_explorer", lambda: explorer)
        orchestrator.run_explore("dir", run_dir)
        assert explorer.calls[0]["logger"] is not None
        assert explorer.calls[0]["logger"].name.endswith(run_dir.name)


class TestRunExploreRetry:
    def test_retry_then_success(self, monkeypatch, run_dir):
        flaky = ValueError("transient")
        explorer = FakeExplorer([flaky, SAMPLE_RECIPE])
        monkeypatch.setattr(orchestrator, "_make_explorer", lambda: explorer)
        result = orchestrator.run_explore("anything", run_dir)
        assert result == SAMPLE_RECIPE
        assert len(explorer.calls) == 2

    def test_retry_then_abort_raises(self, monkeypatch, run_dir):
        explorer = FakeExplorer([
            ValueError("first fail"), ValueError("second fail"),
        ])
        monkeypatch.setattr(orchestrator, "_make_explorer", lambda: explorer)
        with pytest.raises(RuntimeError, match="Explorer failed after retry"):
            orchestrator.run_explore("anything", run_dir)
        assert len(explorer.calls) == 2

    def test_retry_then_abort_does_not_persist_recipe(self, monkeypatch, run_dir):
        explorer = FakeExplorer([
            ValueError("first fail"), ValueError("second fail"),
        ])
        monkeypatch.setattr(orchestrator, "_make_explorer", lambda: explorer)
        with pytest.raises(RuntimeError):
            orchestrator.run_explore("anything", run_dir)
        assert not storage.recipe_path(run_dir).exists()


# --- run_recipe --------------------------------------------------------

class TestRunRecipeHappyPath:
    def _write_recipe(self, run_dir, recipe):
        storage.safe_write(
            storage.recipe_path(run_dir), orchestrator._serialize_recipe(recipe),
        )

    def test_dispatches_one_miner_per_bundle(self, monkeypatch, run_dir):
        self._write_recipe(run_dir, SAMPLE_RECIPE)
        miner = FakeMiner({
            "philosophy": [_records("philosophy", 1)],
            "services": [_records("services", 2)],
        })
        monkeypatch.setattr(orchestrator, "_make_miner", lambda: miner)
        result = orchestrator.run_recipe(run_dir, concurrency=2)
        assert sorted(result.bundles_succeeded) == ["philosophy", "services"]
        assert result.bundles_skipped == []
        assert result.errors == {}

    def test_writes_records_json_per_bundle(self, monkeypatch, run_dir):
        self._write_recipe(run_dir, SAMPLE_RECIPE)
        miner = FakeMiner({
            "philosophy": [_records("philosophy", 1)],
            "services": [_records("services", 2)],
        })
        monkeypatch.setattr(orchestrator, "_make_miner", lambda: miner)
        orchestrator.run_recipe(run_dir, concurrency=2)
        for label, expected_n in [("philosophy", 1), ("services", 2)]:
            data = json.loads(
                storage.records_path(run_dir, label).read_text(encoding="utf-8")
            )
            assert len(data["records"]) == expected_n

    def test_passes_per_bundle_logger_to_miner(self, monkeypatch, run_dir):
        self._write_recipe(run_dir, SAMPLE_RECIPE)
        miner = FakeMiner({
            "philosophy": [_records("philosophy", 1)],
            "services": [_records("services", 1)],
        })
        monkeypatch.setattr(orchestrator, "_make_miner", lambda: miner)
        orchestrator.run_recipe(run_dir, concurrency=2)
        loggers_seen = {c["bundle_label"]: c["logger"].name for c in miner.calls}
        assert "philosophy" in loggers_seen["philosophy"]
        assert "services" in loggers_seen["services"]

    def test_run_result_has_run_dir(self, monkeypatch, run_dir):
        self._write_recipe(run_dir, SAMPLE_RECIPE)
        miner = FakeMiner({
            "philosophy": [_records("philosophy")],
            "services": [_records("services")],
        })
        monkeypatch.setattr(orchestrator, "_make_miner", lambda: miner)
        result = orchestrator.run_recipe(run_dir, concurrency=2)
        assert result.run_dir == run_dir


class TestRunRecipeParallelism:
    def test_dispatches_concurrently(self, monkeypatch, fake_trees):
        """With concurrency=4 and 4 sleepy miners, wall time < 4×sleep."""
        runs, _ = fake_trees
        rd = runs / "stamp"
        rd.mkdir()

        recipe = Recipe(
            artifact_name="X",
            notes_needed={
                f"b{i}": Bundle(paths=[f"P{i}.md"], description="d", expected_output="o")
                for i in range(4)
            },
            miner_objective="o",
            output_schema="s",
            artifact_description="ad",
        )
        storage.safe_write(
            storage.recipe_path(rd), orchestrator._serialize_recipe(recipe),
        )

        sleep_s = 0.10

        class SleepyMiner:
            def __init__(self):
                self.calls = []
                self._lock = threading.Lock()

            def mine(self, bundle, bundle_label, miner_objective, output_schema,
                     event_log=None, logger=None):
                with self._lock:
                    self.calls.append(bundle_label)
                time.sleep(sleep_s)
                return [{"kind": "per_note", "path": f"{bundle_label}.md"}]

        miner = SleepyMiner()
        monkeypatch.setattr(orchestrator, "_make_miner", lambda: miner)

        start = time.monotonic()
        result = orchestrator.run_recipe(rd, concurrency=4)
        elapsed = time.monotonic() - start

        assert len(result.bundles_succeeded) == 4
        # Sequential would take ~4 * sleep_s = 0.40s. With concurrency=4, expect
        # well under 2 * sleep_s. Generous bound for CI jitter.
        assert elapsed < 2 * sleep_s, (
            f"expected concurrent dispatch but elapsed={elapsed:.3f}s "
            f"vs ceiling={2*sleep_s:.3f}s"
        )


class TestRunRecipeRetry:
    def _write_recipe(self, run_dir, recipe):
        storage.safe_write(
            storage.recipe_path(run_dir), orchestrator._serialize_recipe(recipe),
        )

    def test_retry_then_success(self, monkeypatch, run_dir):
        self._write_recipe(run_dir, SAMPLE_RECIPE)
        miner = FakeMiner({
            "philosophy": [ValueError("flake"), _records("philosophy", 1)],
            "services": [_records("services", 1)],
        })
        monkeypatch.setattr(orchestrator, "_make_miner", lambda: miner)
        result = orchestrator.run_recipe(run_dir, concurrency=2)
        assert sorted(result.bundles_succeeded) == ["philosophy", "services"]
        assert result.bundles_skipped == []

    def test_retry_then_skip_partial_run(self, monkeypatch, run_dir):
        self._write_recipe(run_dir, SAMPLE_RECIPE)
        miner = FakeMiner({
            "philosophy": [ValueError("hard1"), ValueError("hard2")],
            "services": [_records("services", 1)],
        })
        monkeypatch.setattr(orchestrator, "_make_miner", lambda: miner)
        result = orchestrator.run_recipe(run_dir, concurrency=2)
        assert result.bundles_succeeded == ["services"]
        assert result.bundles_skipped == ["philosophy"]
        assert "philosophy" in result.errors
        assert "hard2" in result.errors["philosophy"]

    def test_retry_then_skip_does_not_write_records(self, monkeypatch, run_dir):
        self._write_recipe(run_dir, SAMPLE_RECIPE)
        miner = FakeMiner({
            "philosophy": [ValueError("hard1"), ValueError("hard2")],
            "services": [_records("services", 1)],
        })
        monkeypatch.setattr(orchestrator, "_make_miner", lambda: miner)
        orchestrator.run_recipe(run_dir, concurrency=2)
        assert not storage.records_path(run_dir, "philosophy").exists()
        assert storage.records_path(run_dir, "services").exists()

    def test_retry_then_skip_logs_explicit_skip_message(self, monkeypatch, run_dir):
        self._write_recipe(run_dir, SAMPLE_RECIPE)
        miner = FakeMiner({
            "philosophy": [ValueError("hard1"), ValueError("hard2")],
            "services": [_records("services", 1)],
        })
        monkeypatch.setattr(orchestrator, "_make_miner", lambda: miner)
        orchestrator.run_recipe(run_dir, concurrency=2)
        for log in logging.Logger.manager.loggerDict.values():
            if isinstance(log, logging.Logger):
                for h in log.handlers:
                    h.flush()
        run_log_text = storage.orchestrator_log_path(run_dir).read_text(
            encoding="utf-8"
        )
        assert "retry failed; bundle skipped" in run_log_text
        assert "philosophy" in run_log_text


class TestRunRecipeRejectsDenial:
    def test_denial_recipe_raises(self, fake_trees):
        runs, _ = fake_trees
        rd = runs / "stamp"
        rd.mkdir()
        storage.safe_write(
            storage.recipe_path(rd), orchestrator._serialize_recipe(SAMPLE_DENIAL),
        )
        with pytest.raises(ValueError, match="contains a Denial"):
            orchestrator.run_recipe(rd)


class TestRetryOnTimeout:
    def test_subprocess_timeout_is_retryable(self, monkeypatch, run_dir):
        explorer = FakeExplorer([
            subprocess.TimeoutExpired(cmd=["x"], timeout=600),
            SAMPLE_RECIPE,
        ])
        monkeypatch.setattr(orchestrator, "_make_explorer", lambda: explorer)
        result = orchestrator.run_explore("anything", run_dir)
        assert result == SAMPLE_RECIPE

    def test_called_process_error_is_retryable(self, monkeypatch, run_dir):
        explorer = FakeExplorer([
            subprocess.CalledProcessError(returncode=1, cmd=["x"]),
            SAMPLE_RECIPE,
        ])
        monkeypatch.setattr(orchestrator, "_make_explorer", lambda: explorer)
        result = orchestrator.run_explore("anything", run_dir)
        assert result == SAMPLE_RECIPE


# --- run_assembly tests ----------------------------------------------------

class FakeWriter:
    """Stand-in for WriterSubagent — emits a scripted sequence of outcomes.

    `outcomes` is a list of either str (returned as markdown) or Exception
    instances (raised).
    """

    def __init__(self, outcomes: list) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[dict] = []

    def write(self, artifact_name, artifact_description, output_schema,
              bundles, event_log=None, logger=None):
        self.calls.append({
            "artifact_name": artifact_name,
            "artifact_description": artifact_description,
            "output_schema": output_schema,
            "bundles": bundles,
            "event_log": event_log,
            "logger": logger,
        })
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


SAMPLE_MARKDOWN = (
    "origin:: agent\n"
    "type:: #vault-mining\n"
    "tags:: #homelab\n\n"
    "---\n"
    "# HomeLab Field Guide\n\nbody.\n"
)


def _seed_run(run_dir, recipe, records_per_bundle: dict[str, list]):
    """Seed a run folder with recipe.json + records.json per bundle."""
    storage.safe_write(
        storage.recipe_path(run_dir), orchestrator._serialize_recipe(recipe),
    )
    for label, records in records_per_bundle.items():
        storage.safe_write(
            storage.records_path(run_dir, label),
            json.dumps({"records": records}, indent=2),
        )


class TestRunAssemblyHappyPath:
    def test_returns_assembly_result(self, monkeypatch, run_dir):
        _seed_run(run_dir, SAMPLE_RECIPE, {
            "philosophy": _records("philosophy", 1),
            "services": _records("services", 2),
        })
        writer = FakeWriter([SAMPLE_MARKDOWN])
        monkeypatch.setattr(orchestrator, "_make_writer", lambda: writer)

        result = orchestrator.run_assembly(run_dir)

        assert result.run_dir == run_dir
        assert result.artifact_name == "HomeLab Field Guide"
        assert sorted(result.bundles_assembled) == ["philosophy", "services"]
        assert result.bundles_skipped == []

    def test_writes_artifact_file(self, monkeypatch, run_dir):
        _seed_run(run_dir, SAMPLE_RECIPE, {
            "philosophy": _records("philosophy"),
            "services": _records("services"),
        })
        writer = FakeWriter([SAMPLE_MARKDOWN])
        monkeypatch.setattr(orchestrator, "_make_writer", lambda: writer)

        result = orchestrator.run_assembly(run_dir)

        assert result.artifact_path.exists()
        assert result.artifact_path.read_text(encoding="utf-8") == SAMPLE_MARKDOWN

    def test_writes_summary_file(self, monkeypatch, run_dir):
        _seed_run(run_dir, SAMPLE_RECIPE, {
            "philosophy": _records("philosophy"),
            "services": _records("services"),
        })
        writer = FakeWriter([SAMPLE_MARKDOWN])
        monkeypatch.setattr(orchestrator, "_make_writer", lambda: writer)

        result = orchestrator.run_assembly(run_dir)

        assert result.summary_path.exists()
        text = result.summary_path.read_text(encoding="utf-8")
        assert "HomeLab Field Guide - Mining Summary" in text
        assert "## Bundles" in text
        assert "## Stats" in text
        # Bundles should appear in the outcome table.
        assert "`philosophy`" in text
        assert "`services`" in text

    def test_writer_packet_carries_recipe_fields(self, monkeypatch, run_dir):
        _seed_run(run_dir, SAMPLE_RECIPE, {
            "philosophy": _records("philosophy", 3),
            "services": _records("services", 5),
        })
        writer = FakeWriter([SAMPLE_MARKDOWN])
        monkeypatch.setattr(orchestrator, "_make_writer", lambda: writer)

        orchestrator.run_assembly(run_dir)

        assert len(writer.calls) == 1
        call = writer.calls[0]
        assert call["artifact_name"] == SAMPLE_RECIPE.artifact_name
        assert call["artifact_description"] == SAMPLE_RECIPE.artifact_description
        assert call["output_schema"] == SAMPLE_RECIPE.output_schema
        assert set(call["bundles"].keys()) == {"philosophy", "services"}
        # BundleResult carries paths/description/expected_output/records.
        philosophy = call["bundles"]["philosophy"]
        assert philosophy.paths == ["Notes/HomeLab Philosophy.md"]
        assert philosophy.description == "Why I run a homelab."
        assert len(philosophy.records) == 3

    def test_passes_run_logger_to_writer(self, monkeypatch, run_dir):
        _seed_run(run_dir, SAMPLE_RECIPE, {
            "philosophy": _records("philosophy"),
            "services": _records("services"),
        })
        writer = FakeWriter([SAMPLE_MARKDOWN])
        monkeypatch.setattr(orchestrator, "_make_writer", lambda: writer)

        orchestrator.run_assembly(run_dir)

        passed_logger = writer.calls[0]["logger"]
        assert passed_logger is not None
        assert run_dir.name in passed_logger.name


class TestRunAssemblyPartialBundles:
    def test_skipped_bundle_excluded_from_writer_packet(self, monkeypatch, run_dir):
        """A bundle missing records.json (skipped during mining) is not in the packet."""
        _seed_run(run_dir, SAMPLE_RECIPE, {
            "services": _records("services"),  # only services has records
        })
        writer = FakeWriter([SAMPLE_MARKDOWN])
        monkeypatch.setattr(orchestrator, "_make_writer", lambda: writer)

        result = orchestrator.run_assembly(run_dir)

        call = writer.calls[0]
        assert set(call["bundles"].keys()) == {"services"}
        assert "philosophy" not in call["bundles"]
        assert result.bundles_assembled == ["services"]
        assert result.bundles_skipped == ["philosophy"]

    def test_skipped_bundle_listed_in_summary_errors(self, monkeypatch, run_dir):
        _seed_run(run_dir, SAMPLE_RECIPE, {
            "services": _records("services"),
        })
        writer = FakeWriter([SAMPLE_MARKDOWN])
        monkeypatch.setattr(orchestrator, "_make_writer", lambda: writer)

        result = orchestrator.run_assembly(run_dir)
        summary_text = result.summary_path.read_text(encoding="utf-8")

        assert "## Errors" in summary_text
        assert "`philosophy`" in summary_text

    def test_all_bundles_skipped_raises(self, monkeypatch, run_dir):
        """When no records.json files exist on disk, run_assembly aborts."""
        _seed_run(run_dir, SAMPLE_RECIPE, {})  # no bundles seeded
        writer = FakeWriter([SAMPLE_MARKDOWN])
        monkeypatch.setattr(orchestrator, "_make_writer", lambda: writer)

        with pytest.raises(RuntimeError, match="no bundle records"):
            orchestrator.run_assembly(run_dir)
        assert writer.calls == []  # writer never called


class TestRunAssemblyDenialRecipe:
    def test_denial_recipe_raises(self, fake_trees, monkeypatch):
        runs, _ = fake_trees
        rd = runs / "stamp"
        rd.mkdir()
        storage.safe_write(
            storage.recipe_path(rd), orchestrator._serialize_recipe(SAMPLE_DENIAL),
        )
        writer = FakeWriter([SAMPLE_MARKDOWN])
        monkeypatch.setattr(orchestrator, "_make_writer", lambda: writer)

        with pytest.raises(ValueError, match="contains a Denial"):
            orchestrator.run_assembly(rd)
        assert writer.calls == []


class TestRunAssemblyRetry:
    def test_retry_then_success(self, monkeypatch, run_dir):
        _seed_run(run_dir, SAMPLE_RECIPE, {
            "philosophy": _records("philosophy"),
            "services": _records("services"),
        })
        writer = FakeWriter([ValueError("flake"), SAMPLE_MARKDOWN])
        monkeypatch.setattr(orchestrator, "_make_writer", lambda: writer)

        result = orchestrator.run_assembly(run_dir)

        assert len(writer.calls) == 2
        assert result.artifact_path.exists()

    def test_retry_then_abort_raises(self, monkeypatch, run_dir):
        _seed_run(run_dir, SAMPLE_RECIPE, {
            "philosophy": _records("philosophy"),
            "services": _records("services"),
        })
        writer = FakeWriter([
            ValueError("hard1"),
            ValueError("hard2"),
        ])
        monkeypatch.setattr(orchestrator, "_make_writer", lambda: writer)

        with pytest.raises(RuntimeError, match="Writer failed after retry"):
            orchestrator.run_assembly(run_dir)

    def test_retry_then_abort_does_not_write_artifact(self, monkeypatch, run_dir):
        _seed_run(run_dir, SAMPLE_RECIPE, {
            "philosophy": _records("philosophy"),
            "services": _records("services"),
        })
        writer = FakeWriter([
            ValueError("hard1"),
            ValueError("hard2"),
        ])
        monkeypatch.setattr(orchestrator, "_make_writer", lambda: writer)

        with pytest.raises(RuntimeError):
            orchestrator.run_assembly(run_dir)

        # No artifact_dir should have been created.
        artifact_dir = storage.artifact_dir(SAMPLE_RECIPE.artifact_name)
        assert not artifact_dir.exists() or not any(artifact_dir.iterdir())

    def test_retry_then_abort_logs_writer_aborted(self, monkeypatch, run_dir):
        _seed_run(run_dir, SAMPLE_RECIPE, {
            "philosophy": _records("philosophy"),
            "services": _records("services"),
        })
        writer = FakeWriter([
            ValueError("hard1"),
            ValueError("hard2"),
        ])
        monkeypatch.setattr(orchestrator, "_make_writer", lambda: writer)

        with pytest.raises(RuntimeError):
            orchestrator.run_assembly(run_dir)

        for log in logging.Logger.manager.loggerDict.values():
            if isinstance(log, logging.Logger):
                for h in log.handlers:
                    h.flush()
        run_log_text = storage.orchestrator_log_path(run_dir).read_text(
            encoding="utf-8"
        )
        assert "writer aborted after retry" in run_log_text


class TestRunAssemblyPaths:
    def test_artifact_lands_under_artifacts_root(self, monkeypatch, fake_trees, run_dir):
        _, artifacts = fake_trees
        _seed_run(run_dir, SAMPLE_RECIPE, {
            "philosophy": _records("philosophy"),
            "services": _records("services"),
        })
        writer = FakeWriter([SAMPLE_MARKDOWN])
        monkeypatch.setattr(orchestrator, "_make_writer", lambda: writer)

        result = orchestrator.run_assembly(run_dir)

        # artifact_path should be a descendant of artifacts_root.
        assert result.artifact_path.is_relative_to(artifacts)
        # Filename should be `<Artifact Name>.md`.
        assert result.artifact_path.name == "HomeLab Field Guide.md"

    def test_summary_filename_is_self_identifying(self, monkeypatch, run_dir):
        _seed_run(run_dir, SAMPLE_RECIPE, {
            "philosophy": _records("philosophy"),
            "services": _records("services"),
        })
        writer = FakeWriter([SAMPLE_MARKDOWN])
        monkeypatch.setattr(orchestrator, "_make_writer", lambda: writer)

        result = orchestrator.run_assembly(run_dir)

        # Summary filename is `<Artifact Name> - Mining Summary.md`.
        assert result.summary_path.name == "HomeLab Field Guide - Mining Summary.md"
