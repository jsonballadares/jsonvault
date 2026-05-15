# obsidian-mine

The runtime behind the `/mine` skill. Given a free-text direction (e.g. "contrast my HomeLab vs Data Engineering notes"), it runs an Explorer subagent to draft a Recipe, then — after user approval — runs Miner subagents in parallel and a Writer subagent to assemble a single Knowledge Base artifact anchored to source notes via wiki-links.

## Prerequisites

- **Python 3.10+**
- **[Claude Code CLI](https://docs.claude.com/claude-code)** installed and authenticated. The runtime shells out to `claude -p` for every subagent invocation; no Python SDK or API key is used directly.

## Setup

From this directory:

```
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

That installs `pytest` (the only third-party dep — the runtime itself is pure stdlib).

Verify:

```
venv/bin/python cli.py --help
venv/bin/python -m pytest          # unit tests, fast
venv/bin/python -m pytest -m integration   # opt-in, calls real `claude -p`
```

## Layout

| Path | Role |
|---|---|
| `cli.py` | Two-subcommand entry point (`explore`, `mine`). Read by the `/mine` skill body. |
| `orchestrator.py` | Pipeline glue — `run_explore`, `run_recipe`, `run_assembly`. |
| `recipe.py` | Recipe / Denial dataclasses + JSON shape. |
| `storage.py` | Run-folder layout under `runs/<stamp>/`. |
| `stats.py`, `summary.py` | Token / cost / duration accounting and Mining Summary rendering. |
| `prompts/` | Subagent system prompts (`explorer.md`, `miner.md`, `writer.md`). |
| `subagents/` | Subagent driver classes. |
| `runtimes/` | Runtime backends — `claude_code.py` is the production one (subprocess to `claude -p`). |
| `tests/` | Unit + integration tests. Integration tests are opt-in via `-m integration`. |

## Run artifacts

Each invocation creates `runs/<stamp>/` containing the Recipe, miner outputs, the assembled artifact, and stats. Run folders are gitignored — they're per-machine working state. Inspect them when debugging a failed run.

The final artifact is written into the vault's Knowledge Base under `AI OS/Knowledge Base/Sources/Vault-Mining/<date> - <name>/`, alongside a Mining Summary.
