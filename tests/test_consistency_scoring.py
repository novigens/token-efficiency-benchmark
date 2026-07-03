"""Obligated tests for the consistency grader (examples_v2.md §D).

The grader recomputes the rule (a == b + c) on the model's own emitted
values; there is no fixed answer to memorize. Tasks are built by hand here —
the grader's contract is independent of any generating family.
"""

from __future__ import annotations

from token_efficiency_benchmark.evaluation.consistency_scoring import score_consistency
from token_efficiency_benchmark.types import (
    AnswerType,
    CompositeTask,
    ModelResponse,
)


def _task() -> CompositeTask:
    return CompositeTask(
        task_id="consistency::test::0001",
        generator_version="2.0.0",
        template_id="consistency",
        seed=1,
        parameters={"rule": "a == b + c"},
        nodes=(),
        merged_prompt="(prompt text irrelevant to grader contract)",
        canonical_terminal_answer="consistent",
        terminal_answer_type=AnswerType.STRING,
        v_star_input_tokens=50,
        v_star_output_tokens=12,
    )


def _resp(text: str) -> ModelResponse:
    return ModelResponse(
        task_id="consistency::test::0001",
        model="stub",
        response_text=text,
        input_tokens=50,
        output_tokens=20,
    )


def test_consistency_terminal_recomputed_from_emitted():
    """Correct values + honest verdict: 78 = 36 + 42, verdict consistent."""

    r = score_consistency(_task(), _resp("a=78, b=36, c=42, verdict=consistent"))
    assert r.terminal_correct and r.efficiency is not None


def test_consistency_honest_partial_credit():
    """Wrong a (79 != 36+42) but honestly reported inconsistent => credited."""

    r = score_consistency(_task(), _resp("a=79, b=36, c=42, verdict=inconsistent"))
    assert r.terminal_correct


def test_consistency_confabulation_penalty():
    """Wrong a and a false 'consistent' claim => terminally incorrect."""

    r = score_consistency(_task(), _resp("a=79, b=36, c=42, verdict=consistent"))
    assert not r.terminal_correct and r.efficiency is None


def test_consistency_unparseable_is_incorrect():
    r = score_consistency(_task(), _resp("the answer is definitely fine"))
    assert not r.terminal_correct
