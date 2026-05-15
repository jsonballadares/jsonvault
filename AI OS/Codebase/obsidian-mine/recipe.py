"""Recipe data type — Explorer's contract with the Orchestrator.

A Recipe names the work for a single mining query: the artifact to produce,
the notes the Miner reads (organized into named theme-coherent bundles),
the per-note extraction objective, and the output shape the Miner returns.
Notes are grouped into Bundles — each Bundle is a subset a single Miner
call processes together, with its own description (what the bundle is) and
expected_output (what the Miner should emit for this bundle). Orchestrator
may sub-chunk a Bundle internally if context size demands it; that
decomposition is invisible to Explorer and to the Miner's per-bundle
contract.

Explorer's return type is `Recipe | Denial` — never a list. One query, one
artifact.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Bundle:
    """A theme-coherent subset of notes the Miner processes in a single call.

    `paths` — relative vault paths (e.g., "Notes/Homelab MOC.md").
    `description` — what this bundle is; frames the Miner's extraction.
    `expected_output` — what shapes the Miner should emit for this bundle
        (per-note records, a bundle summary, multiple themed summaries, or
        a mix); must reference kinds declared in Recipe.output_schema.
    """

    paths: list[str]
    description: str
    expected_output: str


@dataclass(frozen=True)
class Recipe:
    artifact_name: str
    notes_needed: dict[str, Bundle]
    miner_objective: str
    output_schema: str
    artifact_description: str


@dataclass(frozen=True)
class Denial:
    reason: str


@dataclass(frozen=True)
class BundleResult:
    """A bundle's contribution at assembly time — what the Miner produced.

    Passed to WriterSubagent.write as part of the input packet (W2). The
    Writer sees `description` (theme framing) and `expected_output` (what
    was asked for) alongside the actual `records` so it can mirror or
    transcend bundle structure as `artifact_description` calls for.

    `paths` carries the bundle's source paths so the Writer's Read-scope
    rule (W3 — "Read only paths in one of the bundles") is enforceable
    inline by the prompt and verifiable in tests.
    """
    paths: list[str]
    description: str
    expected_output: str
    records: list[dict]
