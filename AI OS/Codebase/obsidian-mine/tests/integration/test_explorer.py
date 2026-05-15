"""Integration tests for ExplorerSubagent — real runtime, real vault.

Opt-in with `pytest -m integration`. Default `pytest` excludes these
(see pytest.ini). Each test shells out to `claude -p`, which is slow
(tens of seconds to minutes per seed), costs money, and is non-
deterministic. Validators check structure + basic semantics, not exact
content — the point is to catch regressions and hallucinated paths, not
to pin wording.

Seeds live in SEEDS below. Populate with real vault-grounded queries
before running.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from recipe import Recipe, Denial
from runtimes.claude_code import ClaudeCodeRuntime
from subagents.explorer import ExplorerSubagent


logger = logging.getLogger(__name__)


# obsidian-mine/tests/integration/test_explorer.py → My_Vault-mining-v2/
VAULT_ROOT = Path(__file__).resolve().parents[5]


# Seeds for integration runs.
#
# Each seed is a dict:
#   - id: short stable identifier (used as pytest test id)
#   - query: the direction passed to Explorer
#   - expected_kind: "recipe" | "denial" | "either"
#   - key_terms (optional): list[str]; if Recipe, at least one must appear
#     (case-insensitive) in miner_objective, artifact_description, or any
#     bundle description
#
# Seed selection recorded in P8 Working Notes (session 3). 16 seeds cover:
# well-covered topics, thin topics, creative-with-anchor, KB scope, meta
# queries (bootstrap leverage), heavy-lift syntheses, and three denial
# paths (off-vault, too-vague, empty).
SEEDS: list[dict] = [
    # Well-covered topics — Recipe expected
    {
        "id": "data-engineering-inventory",
        "query": "What do I know about data engineering?",
        "expected_kind": "recipe",
        "key_terms": ["data engineering"],
    },
    {
        "id": "homelab-knowledge-map",
        "query": "Gather all information on the home lab project and create a map of knowledge",
        "expected_kind": "recipe",
        "key_terms": ["homelab", "home lab"],
    },
    {
        "id": "obsidian-synthesis",
        "query": "Synthesize my thinking on Obsidian as a tool",
        "expected_kind": "recipe",
        "key_terms": ["obsidian"],
    },
    {
        "id": "ai-survey",
        "query": "What's the lay of the land on AI in my vault?",
        "expected_kind": "recipe",
        "key_terms": ["AI", "artificial intelligence"],
    },
    # Thin coverage — Recipe expected (EP2b: thin is fine)
    {
        "id": "networking-thin",
        "query": "Notes on networking concepts",
        "expected_kind": "recipe",
        "key_terms": ["networking"],
    },
    # KB-scoped — Recipe expected (EP4: unrestricted scope)
    {
        "id": "mining-program-architecture",
        "query": "Summarize the architecture decisions for the mining program",
        "expected_kind": "recipe",
        "key_terms": ["mining"],
    },
    # Creative + vault-anchored — Recipe expected (EP2e)
    {
        "id": "creative-obsidian-field-guide",
        "query": "Draft a personal field guide on how I use Obsidian for thinking",
        "expected_kind": "recipe",
        "key_terms": ["obsidian"],
    },
    # Denial paths
    {
        "id": "denial-off-vault-kombucha",
        "query": "How do I brew kombucha at home?",
        "expected_kind": "denial",
    },
    {
        "id": "denial-too-vague",
        "query": "data",
        "expected_kind": "denial",
    },
    {
        "id": "denial-empty",
        "query": "",
        "expected_kind": "denial",
    },
    # Meta queries — Recipe expected (leverage bootstrap data)
    {
        "id": "tag-audit-report",
        "query": (
            "Create a report of the current state of tags in the vault. "
            "Show the current existing tags and what new tags should be created"
        ),
        "expected_kind": "recipe",
        "key_terms": ["tag", "tags"],
    },
    {
        "id": "kb-structure-audit",
        "query": "Audit the structure of the knowledge base against the desired structure",
        "expected_kind": "recipe",
        "key_terms": ["structure", "knowledge base"],
    },
    # Heavy-lift syntheses — Recipe expected (stress tests)
    {
        "id": "ai-os-evolution-retro",
        "query": (
            "Trace the evolution of my thinking on the AI OS project — what it "
            "was meant to be, what I tried, what I learned, and where it stands "
            "now"
        ),
        "expected_kind": "recipe",
        "key_terms": ["AI OS", "AIOS"],
    },
    {
        "id": "agent-ecosystem-architecture",
        "query": (
            "Produce a comprehensive architectural overview of the AI agent "
            "ecosystem across my vault — how Zettel, the mining program, and "
            "the agent framework fit together, the seams between them, and the "
            "design philosophy underneath"
        ),
        "expected_kind": "recipe",
        "key_terms": ["agent", "architecture"],
    },
    {
        "id": "productivity-system-manual",
        "query": (
            "Create a comprehensive manual of my productivity system — its "
            "philosophy, the tools and workflows I use, the failure modes I've "
            "run into, and how it's evolved over time"
        ),
        "expected_kind": "recipe",
        "key_terms": ["productivity"],
    },
    {
        "id": "vault-health-assessment",
        "query": (
            "Assess the health of the vault — which topics are well-developed, "
            "which are underdeveloped, where the gaps are, what fleeting notes "
            "should be upgraded, and what areas could use more work"
        ),
        "expected_kind": "recipe",
        "key_terms": ["vault"],
    },
]


pytestmark = pytest.mark.skipif(
    not SEEDS,
    reason="SEEDS empty — populate before running integration tests",
)


_BANNED_ARTIFACT_CHARS = set(r'\/:*?"<>|')


def _assert_recipe_valid(result, seed: dict) -> None:
    """Structural + basic-semantic checks for a Recipe response."""
    assert isinstance(result, Recipe), (
        f"{seed['id']}: expected Recipe, got {type(result).__name__}"
    )
    assert result.notes_needed, f"{seed['id']}: notes_needed is empty"
    for label, bundle in result.notes_needed.items():
        assert label.strip(), f"{seed['id']}: empty bundle label"
        assert bundle.paths, f"{seed['id']}: bundle {label!r} has empty paths"
        assert bundle.description.strip(), (
            f"{seed['id']}: bundle {label!r} has empty description"
        )
        assert bundle.expected_output.strip(), (
            f"{seed['id']}: bundle {label!r} has empty expected_output"
        )
        for path in bundle.paths:
            full = VAULT_ROOT / path
            assert full.exists(), (
                f"{seed['id']}: bundle {label!r} hallucinated path "
                f"{path!r} (not found at {full})"
            )
    assert result.artifact_name.strip(), f"{seed['id']}: empty artifact_name"
    assert len(result.artifact_name) < 200, (
        f"{seed['id']}: artifact_name over 200 chars"
    )
    banned = [c for c in result.artifact_name if c in _BANNED_ARTIFACT_CHARS]
    assert not banned, (
        f"{seed['id']}: banned chars {banned!r} in artifact_name "
        f"{result.artifact_name!r}"
    )
    assert result.miner_objective.strip(), f"{seed['id']}: empty miner_objective"
    assert result.output_schema.strip(), f"{seed['id']}: empty output_schema"
    assert result.artifact_description.strip(), (
        f"{seed['id']}: empty artifact_description"
    )
    if key_terms := seed.get("key_terms"):
        haystack_parts = [
            result.miner_objective,
            result.artifact_description,
            *(b.description for b in result.notes_needed.values()),
        ]
        haystack = " ".join(haystack_parts).lower()
        assert any(t.lower() in haystack for t in key_terms), (
            f"{seed['id']}: none of {key_terms!r} appear in miner_objective, "
            f"artifact_description, or any bundle description"
        )


def _assert_denial_valid(result, seed: dict) -> None:
    assert isinstance(result, Denial), (
        f"{seed['id']}: expected Denial, got {type(result).__name__}"
    )
    assert result.reason.strip(), f"{seed['id']}: empty reason"


@pytest.fixture(scope="module")
def runtime():
    """Real ClaudeCodeRuntime pointing at the vault root."""
    return ClaudeCodeRuntime(cwd=str(VAULT_ROOT), timeout=600)


@pytest.mark.integration
@pytest.mark.parametrize("seed", SEEDS, ids=lambda s: s["id"])
def test_explorer_seed(runtime, seed):
    """Run a real Explorer invocation and validate per the seed's contract."""
    explorer = ExplorerSubagent(runtime=runtime)

    result = explorer.explore(seed["query"])

    logger.info("seed=%s query=%r result=%s", seed["id"], seed["query"], result)

    expected = seed["expected_kind"]
    if expected == "recipe":
        _assert_recipe_valid(result, seed)
    elif expected == "denial":
        _assert_denial_valid(result, seed)
    elif expected == "either":
        assert isinstance(result, (Recipe, Denial)), (
            f"{seed['id']}: expected Recipe or Denial, got {type(result).__name__}"
        )
        if isinstance(result, Recipe):
            _assert_recipe_valid(result, seed)
        else:
            _assert_denial_valid(result, seed)
    else:
        pytest.fail(f"{seed['id']}: unknown expected_kind {expected!r}")
