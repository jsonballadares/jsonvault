"""Path helpers and write-guard for the obsidian-mine program.

Storage owns:
    - The shape of the two trees mining writes to:
        * runs/                            — codebase-side debug/audit
        * Sources/Vault-Mining/             — KB-side artifacts (user-facing)
    - The write-guard primitive (`safe_write`) that ensures every write
      stays inside one of those trees.
    - Run folder lifecycle (`start_run`).

Storage does NOT own:
    - Logging configuration (orchestrator.py owns that).
    - Rendering, assembly, or any content production.
    - Reading or parsing files.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


# Module layout: <vault>/AI OS/Codebase/obsidian-mine/storage.py
# parents[0] = obsidian-mine/, parents[1] = Codebase/, parents[2] = AI OS/.
_OBSIDIAN_MINE_ROOT = Path(__file__).resolve().parent
_AI_OS_ROOT = _OBSIDIAN_MINE_ROOT.parent.parent


# --- Tree roots ---

def runs_root() -> Path:
    """Codebase-side mining tree: <obsidian-mine>/runs/"""
    return _OBSIDIAN_MINE_ROOT / "runs"


def artifacts_root() -> Path:
    """KB-side mining tree: <vault>/AI OS/Knowledge Base/Sources/Vault-Mining/"""
    return _AI_OS_ROOT / "Knowledge Base" / "Sources" / "Vault-Mining"


# --- Run lifecycle ---

def start_run() -> Path:
    """Create runs_root()/<UTC YYYY-MM-DD_HH-MM-SS>/ and return the path."""
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = runs_root() / stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


# --- Run folder paths (codebase side) ---

def orchestrator_log_path(run_dir: Path) -> Path:
    """<run_dir>/orchestrator.log — unified Orchestrator narrative across all stages."""
    return run_dir / "orchestrator.log"


def recipe_path(run_dir: Path) -> Path:
    """<run_dir>/recipe.json — Explorer's output, with top-level kind discriminator."""
    return run_dir / "recipe.json"


def bundle_dir(run_dir: Path, label: str) -> Path:
    """<run_dir>/bundles/<label>/ — per-Miner working subdirectory."""
    return run_dir / "bundles" / label


def records_path(run_dir: Path, label: str) -> Path:
    """<bundle_dir>/records.json — one Miner instance's parsed output."""
    return bundle_dir(run_dir, label) / "records.json"


def miner_log_path(run_dir: Path, label: str) -> Path:
    """<bundle_dir>/<label>-miner.log — one Miner instance's detailed trace."""
    return bundle_dir(run_dir, label) / f"{label}-miner.log"


# --- Artifact paths (KB side) ---

def artifact_dir(artifact_name: str, date: str | None = None) -> Path:
    """<artifacts_root>/<YYYY-MM-DD> - <artifact_name>/. Default `date` is today (UTC)."""
    if date is None:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return artifacts_root() / f"{date} - {artifact_name}"


def artifact_path(artifact_dir: Path, artifact_name: str) -> Path:
    """<artifact_dir>/<artifact_name>.md — the deliverable."""
    return artifact_dir / f"{artifact_name}.md"


def summary_path(artifact_dir: Path, artifact_name: str) -> Path:
    """<artifact_dir>/<artifact_name> - Mining Summary.md — the process overview."""
    return artifact_dir / f"{artifact_name} - Mining Summary.md"


# --- Write-guard ---

def safe_write(path: Path, content: str) -> None:
    """Write `content` to `path`. Raises ValueError unless path.resolve() is a
    descendant of runs_root() or artifacts_root(). Existing files are overwritten.
    """
    resolved = Path(path).resolve()
    runs = runs_root().resolve()
    artifacts = artifacts_root().resolve()
    if not (resolved.is_relative_to(runs) or resolved.is_relative_to(artifacts)):
        raise ValueError(
            f"safe_write refused: {path} is outside the mining write trees "
            f"({runs}, {artifacts})"
        )
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(content, encoding="utf-8")
