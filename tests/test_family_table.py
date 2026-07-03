"""Obligated tests for the table_aggregation family (examples_v2.md §C)."""

from __future__ import annotations

import re

from token_efficiency_benchmark.families import (
    DifficultyParams,
    TableAggregationFamily,
)
from token_efficiency_benchmark.families.table_aggregation import recompute_truth
from token_efficiency_benchmark.serialization import task_from_dict, task_to_dict

FAMILY = TableAggregationFamily()


def _gen(seed: int = 7, depth: int = 3, distractors: int = 0):
    return FAMILY.generate(seed, DifficultyParams(depth=depth, distractors=distractors))


def test_table_truth_recompute():
    """Independent recomputation of the statistic from the stored dataset."""

    for seed in range(30):
        t = _gen(seed=seed, depth=4, distractors=2)
        assert str(recompute_truth(t.parameters["cells"])) == (t.canonical_terminal_answer)


def test_table_render_faithful():
    """Every dataset value appears exactly once in the narration (cells are
    drawn distinct, so extraction back out of the prose recovers the set)."""

    for seed in range(30):
        t = _gen(seed=seed, depth=3, distractors=0)
        for group_values in t.parameters["cells"].values():
            for v in group_values:
                hits = re.findall(rf"(?<![\d.]){v}(?![\d.])", t.merged_prompt)
                assert len(hits) == 1, f"value {v} appears {len(hits)}x (seed={seed})"


def test_table_distractor_invariance():
    for seed in range(20):
        bare = _gen(seed=seed, depth=3, distractors=0)
        noisy = _gen(seed=seed, depth=3, distractors=4)
        assert bare.canonical_terminal_answer == noisy.canonical_terminal_answer
        assert len(noisy.merged_prompt) > len(bare.merged_prompt)


def test_table_totals_not_in_prompt():
    """Group totals and the final difference are hidden."""

    for seed in range(30):
        t = _gen(seed=seed, depth=4)
        hidden = [
            *t.parameters["totals"].values(),
            int(t.canonical_terminal_answer),
        ]
        for v in hidden:
            assert not re.search(rf"(?<![\d.]){v}(?![\d.])", t.merged_prompt), (
                f"hidden {v} leaked (seed={seed})"
            )


def test_table_determinism():
    t1 = _gen(seed=99, depth=4, distractors=2)
    t2 = _gen(seed=99, depth=4, distractors=2)
    assert task_to_dict(t1) == task_to_dict(t2)


def test_table_serialization_round_trip():
    t = _gen(seed=13, depth=3, distractors=1)
    assert task_from_dict(task_to_dict(t)) == t


def test_table_no_total_ties():
    """Unique max/min guaranteed at generation (ambiguity is rejected)."""

    for seed in range(30):
        t = _gen(seed=seed, depth=3)
        totals = list(t.parameters["totals"].values())
        assert len(set(totals)) == len(totals)
