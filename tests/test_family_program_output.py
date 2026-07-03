"""Obligated tests for the program_output family (examples_v2.md §B)."""

from __future__ import annotations

import re

import pytest

from token_efficiency_benchmark.families import DifficultyParams, ProgramOutputFamily
from token_efficiency_benchmark.families.base import GenerationRejected
from token_efficiency_benchmark.families.program_output import (
    _Loop,
    _Program,
    _Stmt,
    execute_program,
    render_source,
)
from token_efficiency_benchmark.serialization import task_from_dict, task_to_dict

FAMILY = ProgramOutputFamily()


def _gen(seed: int = 7, depth: int = 4, distractors: int = 0):
    return FAMILY.generate(seed, DifficultyParams(depth=depth, distractors=distractors))


def test_program_truth_is_execution():
    """Stored truth equals a fresh execution of the rendered program at test
    time — verified by exec()ing the source independently of the family's
    interpreter."""

    for seed in range(25):
        t = _gen(seed=seed, depth=5)
        namespace: dict[str, object] = {}
        printed: list[str] = []
        src = t.parameters["source"]
        exec(
            src,
            {"print": lambda v, _p=printed: _p.append(str(v)), "range": range},
            namespace,
        )
        assert printed == [t.canonical_terminal_answer], f"seed={seed}\n{src}"


def test_program_step_budget_rejection():
    """A loop bound beyond the budget raises GenerationRejected — termination
    is a generation-time guarantee."""

    huge = _Program(
        inits=(("x", 2),),
        loops=(_Loop(count=10**9, body=(_Stmt("x", "+", None, 1),)),),
        final_op="+",
        final_left="x",
        final_const=1,
    )
    with pytest.raises(GenerationRejected):
        execute_program(huge)


def test_program_determinism():
    t1 = _gen(seed=99, depth=6, distractors=2)
    t2 = _gen(seed=99, depth=6, distractors=2)
    assert task_to_dict(t1) == task_to_dict(t2)


def test_program_dead_code_invariance():
    """Dead-code distractors change the surface, never the truth."""

    for seed in range(15):
        bare = _gen(seed=seed, depth=5, distractors=0)
        noisy = _gen(seed=seed, depth=5, distractors=3)
        assert bare.canonical_terminal_answer == noisy.canonical_terminal_answer
        assert len(noisy.merged_prompt) > len(bare.merged_prompt)


def test_program_output_not_in_source():
    for seed in range(25):
        t = _gen(seed=seed, depth=5)
        printed = t.canonical_terminal_answer
        assert not re.search(rf"(?<![\d.]){printed}(?![\d.])", t.parameters["source"])


def test_program_serialization_round_trip():
    t = _gen(seed=3, depth=4, distractors=1)
    assert task_from_dict(task_to_dict(t)) == t


def test_program_render_matches_interpreter():
    """render_source and execute_program agree on the §B reference shape."""

    program = _Program(
        inits=(("x", 4), ("y", 3)),
        loops=(
            _Loop(
                count=3,
                body=(
                    _Stmt("x", "+", "y", 0),
                    _Stmt("y", "+", None, 1, guard_even="x"),
                ),
            ),
        ),
        final_op="*",
        final_left="x",
        final_const=5,
    )
    # x: 7 (y stays 3), 10 (even => y=4), 14 (even => y=5); print(14*5)=70
    assert execute_program(program) == 70
    src = render_source(program)
    assert "for i in range(3):" in src and "print(x * 5)" in src
