"""Tests for recipe.py — Bundle, Recipe, and Denial dataclasses."""

import pytest
from dataclasses import FrozenInstanceError

from recipe import Bundle, Recipe, Denial


class TestBundle:
    def test_instantiates_with_all_fields(self):
        b = Bundle(
            paths=["Notes/A.md", "Notes/B.md"],
            description="Alpha-related notes.",
            expected_output="One per-note record per note.",
        )
        assert b.paths == ["Notes/A.md", "Notes/B.md"]
        assert b.description == "Alpha-related notes."
        assert b.expected_output == "One per-note record per note."

    def test_is_frozen(self):
        b = Bundle(paths=[], description="d", expected_output="e")
        with pytest.raises(FrozenInstanceError):
            b.description = "x"  # type: ignore[misc]


class TestRecipe:
    def test_instantiates_with_all_fields(self):
        r = Recipe(
            artifact_name="Foo Knowledge Map",
            notes_needed={
                "alpha": Bundle(
                    paths=["Notes/A.md", "Notes/B.md"],
                    description="Alpha notes.",
                    expected_output="Per-note records.",
                ),
                "beta": Bundle(
                    paths=["Notes/C.md"],
                    description="Beta note.",
                    expected_output="Per-note record.",
                ),
            },
            miner_objective="For each note, extract the core claims.",
            output_schema='{"kind": "per-note", "claims": [str]}',
            artifact_description="A practical overview of the topic.",
        )
        assert r.artifact_name == "Foo Knowledge Map"
        assert set(r.notes_needed.keys()) == {"alpha", "beta"}
        assert r.notes_needed["alpha"].paths == ["Notes/A.md", "Notes/B.md"]
        assert r.notes_needed["alpha"].description == "Alpha notes."
        assert r.notes_needed["beta"].paths == ["Notes/C.md"]
        assert r.miner_objective == "For each note, extract the core claims."
        assert r.output_schema == '{"kind": "per-note", "claims": [str]}'
        assert r.artifact_description == "A practical overview of the topic."

    def test_instantiates_with_single_bundle(self):
        """Degenerate case — direction with no natural sub-grouping."""
        r = Recipe(
            artifact_name="Solo Topic — Inventory",
            notes_needed={
                "all": Bundle(
                    paths=["Notes/X.md"],
                    description="The single topical note.",
                    expected_output="Per-note record.",
                ),
            },
            miner_objective="Extract the key claims.",
            output_schema='{"kind": "per-note", "claims": [str]}',
            artifact_description="Narrow inventory of one note.",
        )
        assert list(r.notes_needed.keys()) == ["all"]

    def test_is_frozen(self):
        r = Recipe("a", {}, "o", "s", "d")
        with pytest.raises(FrozenInstanceError):
            r.artifact_name = "b"  # type: ignore[misc]


class TestDenial:
    def test_instantiates_with_reason(self):
        d = Denial(reason="No matching notes in scope.")
        assert d.reason == "No matching notes in scope."

    def test_is_frozen(self):
        d = Denial(reason="x")
        with pytest.raises(FrozenInstanceError):
            d.reason = "y"  # type: ignore[misc]
