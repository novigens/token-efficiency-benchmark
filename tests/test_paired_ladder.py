"""Paired-ladder invariants: depth isolated per item.

The paired mode's whole value is a set of guarantees about what does NOT
change between rungs of a group. Each guarantee gets a test.
"""

from __future__ import annotations

import re

from token_efficiency_benchmark.families.arithmetic_chain import _OPS
from token_efficiency_benchmark.families.paired_ladder import (
    PAIRED_VERSION,
    generate_paired_ladder,
)
from token_efficiency_benchmark.families.table_aggregation import recompute_truth
from token_efficiency_benchmark.serialization import task_to_dict

RUNGS = [3, 6, 9]


def _ladder(seed: int = 11):
    return generate_paired_ladder(seed, RUNGS, distractors=2)


def test_paired_determinism():
    a = [task_to_dict(t) for t in _ladder()]
    b = [task_to_dict(t) for t in _ladder()]
    assert a == b


def test_paired_group_shape_and_version():
    tasks = _ladder()
    assert [t.parameters["paired"]["rung"] for t in tasks] == RUNGS
    assert len({t.task_id for t in tasks}) == len(RUNGS)
    for t in tasks:
        assert t.generator_version == PAIRED_VERSION
        assert t.parameters["bucket"] == f"hybrid-paired_d{t.parameters['paired']['rung']}"


def test_paired_program_identical_across_rungs():
    tasks = _ladder()
    programs = {t.parameters["program_text"] for t in tasks}
    assert len(programs) == 1
    for t in tasks:
        assert t.merged_prompt.startswith(t.parameters["program_text"].rstrip())


def test_paired_chain_is_prefix_of_deepest():
    tasks = _ladder()
    deepest = tasks[-1]
    for t in tasks:
        d = t.parameters["paired"]["rung"]
        assert t.parameters["paired"]["ops"] == deepest.parameters["paired"]["ops"][:d]
        assert t.parameters["chain_values"] == deepest.parameters["chain_values"][: d + 1]


def test_paired_chain_truth_recomputes():
    op_by_name = {op.name: op for op in _OPS}
    for t in _ladder():
        v = t.parameters["segment_values"][0]
        for rec in t.parameters["paired"]["ops"]:
            v = op_by_name[rec["name"]].compute(v, rec["k"])
        assert v == t.parameters["segment_values"][1]
        assert v == t.parameters["chain_values"][-1]


def test_paired_table_identical_except_injected_cell():
    tasks = _ladder()
    base_cells = tasks[0].parameters["cells"]
    groups = list(base_cells.keys())
    first = groups[0]
    for t in tasks:
        cells = t.parameters["cells"]
        assert list(cells.keys()) == groups
        for g in groups[1:]:
            assert cells[g] == base_cells[g]
        assert cells[first][1:] == base_cells[first][1:]
        assert cells[first][0] == t.parameters["segment_values"][1]  # injected chain value


def test_paired_distractors_identical_across_rungs():
    tasks = _ladder()
    dvals = tasks[0].parameters["distractor_values"]
    assert len(dvals) == 2
    for t in tasks:
        assert t.parameters["distractor_values"] == dvals
        for dv in dvals:
            assert re.search(rf"(?<![\d.]){dv}(?![\d.])", t.merged_prompt)


def test_paired_terminal_matches_table_recompute_and_stays_hidden():
    for t in _ladder():
        assert str(recompute_truth(t.parameters["cells"])) == t.canonical_terminal_answer
        assert not re.search(rf"(?<![\d.]){t.canonical_terminal_answer}(?![\d.])", t.merged_prompt)


def test_paired_prompts_strictly_grow_with_depth():
    tasks = _ladder()
    lengths = [len(t.merged_prompt) for t in tasks]
    assert lengths == sorted(lengths) and len(set(lengths)) == len(lengths)
