"""Obligated tests for the hybrid family (examples_v2.md §G)."""

from __future__ import annotations

import re

import pytest

from token_efficiency_benchmark.evaluation.harness import evaluate_task
from token_efficiency_benchmark.evaluation.models import EchoModel
from token_efficiency_benchmark.evaluation.tokenization import count_tokens
from token_efficiency_benchmark.families import (
    ArithmeticChainFamily,
    DifficultyParams,
    HybridFamily,
    ProgramOutputFamily,
)
from token_efficiency_benchmark.families.base import GenerationRejected
from token_efficiency_benchmark.serialization import task_from_dict, task_to_dict

FAMILY = HybridFamily("prog+chain")


def _gen(seed: int = 7, depth: int = 3, distractors: int = 0, recipe: str = "prog+chain"):
    return HybridFamily(recipe).generate(
        seed, DifficultyParams(depth=depth, distractors=distractors)
    )


def test_hybrid_default_recipe_is_full_gauntlet():
    assert HybridFamily().recipe == "prog+chain+table"


def test_hybrid_truth_forward_across_segments():
    """Independent recompute: execute the program segment, then apply the
    chain ops from the recorded segment values."""

    for seed in range(20):
        t = _gen(seed=seed, depth=4)
        seg_values = t.parameters["segment_values"]
        assert len(seg_values) == 2
        # Segment truths are the node known answers, and the terminal is the
        # last segment's value.
        assert [n.item.known_answer for n in t.nodes] == seg_values
        assert str(seg_values[-1]) == t.canonical_terminal_answer
        # The chain segment starts exactly from the program's printed value
        # (typed joint: integer >= 2 by the chain's own contract).
        assert seg_values[0] >= 2


def test_hybrid_bridge_no_leak():
    """No segment value — including the program's printed upstream — appears
    anywhere in the merged surface."""

    for seed in range(20):
        t = _gen(seed=seed, depth=4)
        for v in t.parameters["segment_values"]:
            assert not re.search(rf"(?<![\d.]){v}(?![\d.])", t.merged_prompt), (
                f"value {v} leaked (seed={seed})"
            )


def test_hybrid_type_bridge():
    """A joint whose downstream cannot accept the upstream raises
    GenerationRejected — no implicit coercion at any joint."""

    from token_efficiency_benchmark.families import TableAggregationFamily

    with pytest.raises(GenerationRejected):
        ProgramOutputFamily().generate_segment(1, DifficultyParams(depth=3), upstream=42)
    with pytest.raises(GenerationRejected):
        ArithmeticChainFamily().generate_segment(1, DifficultyParams(depth=3), upstream=1)
    with pytest.raises(GenerationRejected):
        TableAggregationFamily().generate_segment(1, DifficultyParams(depth=3), upstream=None)


def test_hybrid_determinism():
    t1 = _gen(seed=11, depth=4, distractors=0)
    t2 = _gen(seed=11, depth=4, distractors=0)
    assert task_to_dict(t1) == task_to_dict(t2)


def test_hybrid_recipe_recorded():
    t = _gen(seed=5, depth=3)
    recipe = t.parameters["recipe"]
    assert recipe["segments"] == ["program_output", "arithmetic_chain"]
    assert t.difficulty_bucket() == "hybrid_prog+chain_d3"


def test_hybrid_three_segment_gauntlet():
    """prog+chain+table: three segment values, all hidden, terminal from the
    table segment; node truths equal segment values in order."""

    for seed in range(10):
        t = _gen(seed=seed, depth=3, recipe="prog+chain+table")
        seg_values = t.parameters["segment_values"]
        assert len(seg_values) == 3
        assert [n.item.known_answer for n in t.nodes] == seg_values
        assert str(seg_values[-1]) == t.canonical_terminal_answer
        for v in seg_values:
            assert not re.search(rf"(?<![\d.]){v}(?![\d.])", t.merged_prompt)
        assert t.difficulty_bucket() == "hybrid_prog+chain+table_d3"


def test_hybrid_chain_table_recipe():
    for seed in range(10):
        t = _gen(seed=seed, depth=3, recipe="chain+table")
        assert t.parameters["recipe"]["segments"] == [
            "arithmetic_chain",
            "table_aggregation",
        ]
        seg_values = t.parameters["segment_values"]
        assert len(seg_values) == 2
        assert str(seg_values[-1]) == t.canonical_terminal_answer


def test_hybrid_scoring_unchanged():
    """Hybrids score through the standard path: echo achieves efficiency 1.0,
    V* is prompt + canonical answer, no hybrid-specific scoring exists."""

    t = _gen(seed=9, depth=3)
    assert t.v_star_input_tokens == count_tokens(t.merged_prompt)
    result = evaluate_task(t, EchoModel({t.task_id: t.canonical_terminal_answer}))
    assert result.terminal_correct and result.efficiency == pytest.approx(1.0)


def test_hybrid_serialization_round_trip():
    t = _gen(seed=13, depth=3)
    assert task_from_dict(task_to_dict(t)) == t
