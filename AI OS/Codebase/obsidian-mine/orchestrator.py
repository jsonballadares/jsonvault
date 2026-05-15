"""Pipeline orchestration helpers for the obsidian-mine program.

The /mine skill is the Orchestrator (per the Component Map's
Orchestrator-as-skill-session model). This module exposes the helpers the
skill calls — file I/O, retry, concurrency, log routing — so the skill
body stays focused on glue between stages.

Three stage helpers, one per pipeline stage:
    - run_explore(direction, run_dir): calls Explorer, persists recipe.json,
      returns the parsed object.
    - run_recipe(run_dir, concurrency): reads recipe.json, dispatches Miners
      in parallel, persists one records.json per succeeded bundle, returns
      a RunResult summary.
    - run_assembly(run_dir): reads recipe.json + each bundle's records.json,
      calls WriterSubagent to produce the artifact markdown, parses logs
      for stats, renders the Mining Summary mechanically, writes both
      files via storage.safe_write. Returns an AssemblyResult.

The "stage-handoff via file" project-wide pattern: each stage writes its
output to a durable file in the run folder; the next stage reads from
disk, not memory. The run folder is a complete audit/replay surface;
the LLM-in-the-skill does not carry stage outputs in its conversation.

Sketch of the skill flow (illustrative, not exhaustive):
    run_dir = storage.start_run()
    result  = run_explore(direction, run_dir)
    if isinstance(result, Denial):
        # surface result.reason to the user; stop
        ...
    rr = run_recipe(run_dir)            # default concurrency=4
    ar = run_assembly(run_dir)          # writes artifact + summary
"""
from __future__ import annotations

import concurrent.futures
import dataclasses
import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import stats
import storage
import summary
from recipe import Bundle, BundleResult, Denial, Recipe
from runtimes.claude_code import ClaudeCodeRuntime
from subagents.explorer import ExplorerSubagent
from subagents.miner import MinerSubagent
from subagents.writer import WriterSubagent


_EXPLORER_TIMEOUT = 600
_MINER_TIMEOUT = 900
_WRITER_TIMEOUT = 900
_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

# Errors we treat as transient / retryable. Anything else propagates.
_RETRYABLE = (subprocess.SubprocessError, ValueError, json.JSONDecodeError)


# --- Result type ---

@dataclass
class RunResult:
    """Returned by run_recipe.

    The skill consumes this to decide what to surface to the user. Per-bundle
    error messages live in `errors` AND in the per-bundle log file, so the
    skill can render them inline without grepping logs.
    """
    run_dir: Path
    bundles_succeeded: list[str] = field(default_factory=list)
    bundles_skipped: list[str] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class AssemblyResult:
    """Returned by run_assembly.

    Carries the on-disk locations of the artifact and Mining Summary so
    the skill can surface them to the user (or open them) without
    re-deriving paths. `bundles_assembled` and `bundles_skipped` reflect
    what landed in the artifact's records — a bundle whose Miner failed
    during run_recipe (no records.json on disk) is excluded from
    assembly and listed here for transparency.
    """
    run_dir: Path
    artifact_dir: Path
    artifact_path: Path
    summary_path: Path
    artifact_name: str
    bundles_assembled: list[str] = field(default_factory=list)
    bundles_skipped: list[str] = field(default_factory=list)


# --- Logger setup ---

def _setup_run_logger(run_dir: Path) -> logging.Logger:
    """Run-level logger writing to <run_dir>/orchestrator.log.

    Idempotent — calling twice for the same run_dir does not duplicate
    handlers. Uses propagate=False so records don't bubble up to the root
    logger and pollute pytest's caplog or any parent-configured handlers.
    """
    name = f"obsidian-mine.run.{run_dir.name}"
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    log.propagate = False
    log_path = storage.orchestrator_log_path(run_dir)
    if not _has_file_handler(log, log_path):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        log.addHandler(handler)
    return log


def _setup_bundle_logger(run_dir: Path, label: str) -> logging.Logger:
    """Per-bundle logger writing to <bundle_dir>/<label>-miner.log.

    propagate=False keeps the detailed worker trace from bleeding into the
    top-level orchestrator.log (per O8).
    """
    name = f"obsidian-mine.bundle.{run_dir.name}.{label}"
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)
    log.propagate = False
    log_path = storage.miner_log_path(run_dir, label)
    if not _has_file_handler(log, log_path):
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        log.addHandler(handler)
    return log


def _has_file_handler(log: logging.Logger, path: Path) -> bool:
    target = str(Path(path).resolve())
    for h in log.handlers:
        if isinstance(h, logging.FileHandler) and Path(h.baseFilename).resolve() == Path(target):
            return True
    return False


# --- Recipe persistence ---

def _serialize_recipe(result: Recipe | Denial) -> str:
    """Serialize a Recipe or Denial to JSON with top-level 'kind'."""
    if isinstance(result, Recipe):
        payload = {"kind": "recipe", **dataclasses.asdict(result)}
    elif isinstance(result, Denial):
        payload = {"kind": "denial", **dataclasses.asdict(result)}
    else:
        raise TypeError(
            f"Expected Recipe or Denial, got {type(result).__name__}"
        )
    return json.dumps(payload, indent=2)


def _deserialize_recipe(text: str) -> Recipe | Denial:
    data = json.loads(text)
    kind = data.get("kind")
    if kind == "recipe":
        notes_needed = {
            label: Bundle(
                paths=list(b["paths"]),
                description=b["description"],
                expected_output=b["expected_output"],
            )
            for label, b in data["notes_needed"].items()
        }
        return Recipe(
            artifact_name=data["artifact_name"],
            notes_needed=notes_needed,
            miner_objective=data["miner_objective"],
            output_schema=data["output_schema"],
            artifact_description=data["artifact_description"],
        )
    if kind == "denial":
        return Denial(reason=data["reason"])
    raise ValueError(
        f"recipe.json kind must be 'recipe' or 'denial', got {kind!r}"
    )


# --- Subagent construction seam ---
# Tests monkeypatch these to inject fakes that don't spawn real subprocesses.

def _make_explorer() -> ExplorerSubagent:
    return ExplorerSubagent(ClaudeCodeRuntime(timeout=_EXPLORER_TIMEOUT))


def _make_miner() -> MinerSubagent:
    return MinerSubagent(ClaudeCodeRuntime(timeout=_MINER_TIMEOUT))


def _make_writer() -> WriterSubagent:
    return WriterSubagent(ClaudeCodeRuntime(timeout=_WRITER_TIMEOUT))


# --- Stage helpers ---

def run_explore(direction: str, run_dir: Path) -> Recipe | Denial:
    """Call Explorer, persist its output to <run_dir>/recipe.json, return the parsed object.

    Failure handling: retry once on subprocess crash, parse failure, or timeout
    (600s, matching the manual runner). If the retry also fails, raises — the
    run cannot proceed without a Recipe; the skill surfaces the error and the
    user re-runs `/mine`.

    Side effects:
        - Writes <run_dir>/recipe.json (top-level "kind": "recipe" | "denial").
        - Appends Explorer-phase events to <run_dir>/orchestrator.log.
    """
    log = _setup_run_logger(run_dir)
    log.info("explorer stage starting: direction=%r", direction)
    explorer = _make_explorer()

    last_error: Exception | None = None
    result: Recipe | Denial | None = None
    for attempt in (1, 2):
        try:
            log.info("explorer attempt %d", attempt)
            result = explorer.explore(direction, logger=log)
            break
        except _RETRYABLE as e:
            log.warning("explorer attempt %d failed: %s", attempt, e)
            last_error = e
    if result is None:
        log.error("explorer aborted after retry: %s", last_error)
        raise RuntimeError(
            f"Explorer failed after retry: {last_error}"
        ) from last_error

    storage.safe_write(storage.recipe_path(run_dir), _serialize_recipe(result))

    if isinstance(result, Recipe):
        log.info(
            "explorer produced Recipe: artifact_name=%r bundles=%d",
            result.artifact_name, len(result.notes_needed),
        )
    else:
        log.info("explorer produced Denial: reason=%r", result.reason)

    return result


def run_recipe(run_dir: Path, concurrency: int = 4) -> RunResult:
    """Read <run_dir>/recipe.json and dispatch one Miner per bundle in parallel.

    Concurrency is bounded by `concurrency` via concurrent.futures.ThreadPoolExecutor;
    set to 1 for sequential. Failure handling per bundle: retry once on subprocess
    crash, parse failure, or timeout (900s). If the retry also fails the bundle
    is recorded in `bundles_skipped` + `errors`, an explicit "retry failed; bundle
    skipped" entry is logged to orchestrator.log, and the run continues with the
    remaining bundles.

    Side effects:
        - Creates <run_dir>/bundles/<label>/ per bundle.
        - Writes <run_dir>/bundles/<label>/records.json for each succeeded bundle.
        - Writes <run_dir>/bundles/<label>/<label>-miner.log per bundle (detailed
          per-Miner trace; the per-bundle logger uses propagate=False so its
          content does not bleed into orchestrator.log).
        - Appends high-level dispatch events to <run_dir>/orchestrator.log.
    """
    log = _setup_run_logger(run_dir)
    text = storage.recipe_path(run_dir).read_text(encoding="utf-8")
    parsed = _deserialize_recipe(text)
    if not isinstance(parsed, Recipe):
        raise ValueError(
            "Cannot run recipe stage: recipe.json contains a Denial, not a Recipe"
        )
    recipe = parsed

    log.info(
        "mining stage starting: bundles=%d concurrency=%d",
        len(recipe.notes_needed), concurrency,
    )

    miner = _make_miner()
    result = RunResult(run_dir=run_dir)

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = {
            ex.submit(
                _process_bundle, miner, run_dir, label, bundle,
                recipe.miner_objective, recipe.output_schema,
            ): label
            for label, bundle in recipe.notes_needed.items()
        }
        for future in concurrent.futures.as_completed(futures):
            label, outcome = future.result()
            if isinstance(outcome, Exception):
                log.error("retry failed; bundle skipped: %s err=%s", label, outcome)
                result.bundles_skipped.append(label)
                result.errors[label] = str(outcome)
            else:
                records = outcome
                storage.safe_write(
                    storage.records_path(run_dir, label),
                    json.dumps({"records": records}, indent=2),
                )
                log.info(
                    "bundle succeeded: %s records=%d", label, len(records),
                )
                result.bundles_succeeded.append(label)

    log.info(
        "mining stage complete: succeeded=%d skipped=%d",
        len(result.bundles_succeeded), len(result.bundles_skipped),
    )
    return result


def _process_bundle(
    miner: MinerSubagent,
    run_dir: Path,
    label: str,
    bundle: Bundle,
    miner_objective: str,
    output_schema: str,
) -> tuple[str, list[dict] | Exception]:
    bundle_log = _setup_bundle_logger(run_dir, label)
    last_error: Exception | None = None
    for attempt in (1, 2):
        try:
            bundle_log.info(
                "miner attempt %d: bundle=%s paths=%d",
                attempt, label, len(bundle.paths),
            )
            records = miner.mine(
                bundle=bundle,
                bundle_label=label,
                miner_objective=miner_objective,
                output_schema=output_schema,
                logger=bundle_log,
            )
            return label, records
        except _RETRYABLE as e:
            bundle_log.warning("miner attempt %d failed: %s", attempt, e)
            last_error = e
    bundle_log.error("retry failed; bundle skipped: %s", last_error)
    return label, last_error  # type: ignore[return-value]


# --- Assembly stage ---

_DIRECTION_RE = re.compile(r"direction='([^']*)'")
_BUNDLE_SKIP_RE = re.compile(
    r"retry failed; bundle skipped: (?P<label>\S+) err=(?P<err>.+)$"
)


def run_assembly(run_dir: Path) -> AssemblyResult:
    """Read recipe.json + each bundle's records.json, call Writer, render summary, write both files.

    Failure handling: retry the Writer once on subprocess crash, parse
    failure, or timeout. If the retry also fails, raise — the run cannot
    produce an artifact and the user can re-run just this stage from the
    same run folder (W5).

    A bundle whose Miner failed during run_recipe (no records.json on
    disk) is excluded from the Writer's input packet. The summary's
    Errors section lists it. If *all* bundles are skipped, run_assembly
    aborts — there is nothing to assemble.

    Side effects:
        - Reads <run_dir>/recipe.json and each <run_dir>/bundles/<label>/records.json.
        - Appends Writer-phase events to <run_dir>/orchestrator.log.
        - Writes the artifact to <artifacts_root>/<date> - <name>/<name>.md.
        - Writes the Mining Summary to <artifacts_root>/<date> - <name>/<name> - Mining Summary.md.
    """
    log = _setup_run_logger(run_dir)
    log.info("writer stage starting")

    text = storage.recipe_path(run_dir).read_text(encoding="utf-8")
    parsed = _deserialize_recipe(text)
    if not isinstance(parsed, Recipe):
        raise ValueError(
            "Cannot run assembly stage: recipe.json contains a Denial, not a Recipe"
        )
    recipe = parsed

    bundles, skipped_labels = _load_bundle_results(recipe, run_dir, log)
    if not bundles:
        log.error("writer aborted: no bundle records to assemble")
        raise RuntimeError(
            "Cannot run assembly stage: no bundle records on disk "
            "(all bundles skipped during mining)"
        )

    writer = _make_writer()
    last_error: Exception | None = None
    markdown: str | None = None
    for attempt in (1, 2):
        try:
            log.info("writer attempt %d", attempt)
            markdown = writer.write(
                artifact_name=recipe.artifact_name,
                artifact_description=recipe.artifact_description,
                output_schema=recipe.output_schema,
                bundles=bundles,
                logger=log,
            )
            break
        except _RETRYABLE as e:
            log.warning("writer attempt %d failed: %s", attempt, e)
            last_error = e
    if markdown is None:
        log.error("writer aborted after retry: %s", last_error)
        raise RuntimeError(
            f"Writer failed after retry: {last_error}"
        ) from last_error

    log.info(
        "writer produced artifact: %s bytes=%d",
        recipe.artifact_name, len(markdown),
    )

    # Stats parsing happens AFTER the writer's "produced" line is logged
    # so the writer phase has a clean end marker for stats.collect_stats.
    run_stats = stats.collect_stats(run_dir)
    direction = _extract_direction(run_dir)
    bundle_outcomes = _bundle_outcomes(recipe, run_dir)
    summary_md = summary.render_summary(
        artifact_name=recipe.artifact_name,
        direction=direction,
        run_dir=run_dir,
        bundle_outcomes=bundle_outcomes,
        run_stats=run_stats,
    )

    artifact_dir = storage.artifact_dir(recipe.artifact_name)
    artifact_path = storage.artifact_path(artifact_dir, recipe.artifact_name)
    summary_path = storage.summary_path(artifact_dir, recipe.artifact_name)
    storage.safe_write(artifact_path, markdown)
    storage.safe_write(summary_path, summary_md)

    return AssemblyResult(
        run_dir=run_dir,
        artifact_dir=artifact_dir,
        artifact_path=artifact_path,
        summary_path=summary_path,
        artifact_name=recipe.artifact_name,
        bundles_assembled=list(bundles.keys()),
        bundles_skipped=skipped_labels,
    )


def _load_bundle_results(
    recipe: Recipe, run_dir: Path, log: logging.Logger,
) -> tuple[dict[str, BundleResult], list[str]]:
    """Reconstruct BundleResult per bundle from recipe + records.json on disk."""
    bundles: dict[str, BundleResult] = {}
    skipped: list[str] = []
    for label, bundle in recipe.notes_needed.items():
        records_file = storage.records_path(run_dir, label)
        if not records_file.exists():
            log.warning(
                "bundle %s has no records.json (skipped during mining); "
                "excluding from assembly",
                label,
            )
            skipped.append(label)
            continue
        records_data = json.loads(records_file.read_text(encoding="utf-8"))
        bundles[label] = BundleResult(
            paths=list(bundle.paths),
            description=bundle.description,
            expected_output=bundle.expected_output,
            records=list(records_data.get("records", [])),
        )
    return bundles, skipped


def _extract_direction(run_dir: Path) -> str:
    """Pull the original direction string out of orchestrator.log's first line."""
    log_path = storage.orchestrator_log_path(run_dir)
    if not log_path.exists():
        return "(unknown)"
    text = log_path.read_text(encoding="utf-8")
    m = _DIRECTION_RE.search(text)
    return m.group(1) if m else "(unknown)"


def _bundle_outcomes(recipe: Recipe, run_dir: Path) -> list[summary.BundleOutcome]:
    """Build per-bundle outcome rows from disk + log state."""
    errors_by_label = _extract_skip_errors(run_dir)
    out: list[summary.BundleOutcome] = []
    for label, bundle in recipe.notes_needed.items():
        records_file = storage.records_path(run_dir, label)
        if records_file.exists():
            try:
                data = json.loads(records_file.read_text(encoding="utf-8"))
                count = len(data.get("records", []))
            except json.JSONDecodeError:
                count = 0
            out.append(summary.BundleOutcome(
                label=label,
                paths_count=len(bundle.paths),
                records_count=count,
            ))
        else:
            out.append(summary.BundleOutcome(
                label=label,
                paths_count=len(bundle.paths),
                records_count=None,
                error=errors_by_label.get(label),
            ))
    return out


def _extract_skip_errors(run_dir: Path) -> dict[str, str]:
    """Best-effort: parse 'retry failed; bundle skipped: <label> err=<msg>' from orchestrator.log."""
    log_path = storage.orchestrator_log_path(run_dir)
    if not log_path.exists():
        return {}
    out: dict[str, str] = {}
    for line in log_path.read_text(encoding="utf-8").splitlines():
        m = _BUNDLE_SKIP_RE.search(line)
        if m:
            out[m.group("label")] = m.group("err")
    return out
