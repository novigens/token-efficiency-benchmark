"""Obligated tests for the arithmetic_chain family (examples_v2.md §A).

Every test asserts against an independently computed value or an
independently stated invariant — never the implementation's own output
re-read back (the test-suite honesty rule).
"""

from __future__ import annotations

import re

import pytest

from token_efficiency_benchmark.evaluation.tokenization import count_tokens
from token_efficiency_benchmark.families import ArithmeticChainFamily, DifficultyParams
from token_efficiency_benchmark.families.arithmetic_chain import recompute_truth
from token_efficiency_benchmark.serialization import task_from_dict, task_to_dict

FAMILY = ArithmeticChainFamily()


def _gen(seed: int = 7, depth: int = 4, distractors: int = 0):
    return FAMILY.generate(seed, DifficultyParams(depth=depth, distractors=distractors))


def test_chain_determinism():
    t1 = _gen(seed=101, depth=6, distractors=3)
    t2 = _gen(seed=101, depth=6, distractors=3)
    assert task_to_dict(t1) == task_to_dict(t2)


def test_chain_different_seeds_differ():
    t1 = _gen(seed=101, depth=6)
    t2 = _gen(seed=102, depth=6)
    assert t1.merged_prompt != t2.merged_prompt


def test_chain_truth_recompute():
    for seed in range(40):
        t = _gen(seed=seed, depth=5, distractors=2)
        values = recompute_truth(t.parameters)
        assert values == t.parameters["values"]
        assert str(values[-1]) == t.canonical_terminal_answer


def test_chain_no_intermediate_leak():
    for seed in range(40):
        t = _gen(seed=seed, depth=6, distractors=4)
        for v in t.parameters["values"]:
            assert not re.search(rf"(?<![\d.]){v}(?![\d.])", t.merged_prompt), (
                f"value {v} leaked (seed={seed})"
            )


def test_chain_no_decomposition_markers():
    for seed in range(20):
        t = _gen(seed=seed, depth=8, distractors=3)
        assert not re.search(
            r"\bStep\s*\d|\bStage\s*\d|sub-?problem|\bQ\d\b",
            t.merged_prompt,
            re.IGNORECASE,
        )


def test_chain_v_star():
    t = _gen(seed=3, depth=4)
    assert t.v_star_input_tokens == count_tokens(t.merged_prompt)
    assert t.v_star_output_tokens == count_tokens(t.canonical_terminal_answer)


def test_chain_distractor_invariance():
    """Distractors change the surface, never the truth."""

    for seed in range(25):
        bare = _gen(seed=seed, depth=6, distractors=0)
        noisy = _gen(seed=seed, depth=6, distractors=5)
        assert bare.canonical_terminal_answer == noisy.canonical_terminal_answer
        assert len(noisy.merged_prompt) > len(bare.merged_prompt)


def test_chain_depth_bucket_and_nodes():
    t = _gen(seed=11, depth=7)
    assert len(t.nodes) == 7
    assert t.difficulty_bucket() == "depth_7"
    # node known answers are exactly the forward values
    assert [n.item.known_answer for n in t.nodes] == t.parameters["values"]


def test_chain_serialization_round_trip():
    t = _gen(seed=13, depth=5, distractors=2)
    assert task_from_dict(task_to_dict(t)) == t


def test_chain_values_bounded_and_integral():
    for seed in range(40):
        t = _gen(seed=seed, depth=10)
        for v in t.parameters["values"]:
            assert isinstance(v, int) and 2 <= v <= 500_000


def test_chain_rejects_depth_below_two():
    with pytest.raises(ValueError):
        _gen(depth=1)
