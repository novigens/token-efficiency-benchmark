"""Scoring path for Template D (consistency verification).

The terminal is graded by recomputing the consistency rule on the model's
emitted sub-answers, *not* by matching against a fixed canonical. This
implements §12.4: a confabulating model is caught, an honest "I got it wrong"
model is credited.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..types import CompositeTask, ModelResponse, TaskResult
from .scoring import DEFAULT_WEIGHTS, compute_efficiency


@dataclass(frozen=True)
class ConsistencyParse:
    """Parsed model output for a consistency task."""

    a: int | None
    b: int | None
    c: int | None
    verdict: str | None  # "consistent" / "inconsistent" / None

    def fully_parsed(self) -> bool:
        return all(v is not None for v in (self.a, self.b, self.c, self.verdict))


_A_RE = re.compile(r"a\s*=\s*(-?\d+)", re.IGNORECASE)
_B_RE = re.compile(r"b\s*=\s*(-?\d+)", re.IGNORECASE)
_C_RE = re.compile(r"c\s*=\s*(-?\d+)", re.IGNORECASE)
_VERDICT_RE = re.compile(r"verdict\s*=\s*(consistent|inconsistent)", re.IGNORECASE)


def parse_consistency_response(response_text: str) -> ConsistencyParse:
    """Extract a, b, c, and verdict from a model response."""

    a = _A_RE.search(response_text)
    b = _B_RE.search(response_text)
    c = _C_RE.search(response_text)
    v = _VERDICT_RE.search(response_text)
    return ConsistencyParse(
        a=int(a.group(1)) if a else None,
        b=int(b.group(1)) if b else None,
        c=int(c.group(1)) if c else None,
        verdict=v.group(1).lower() if v else None,
    )


def score_consistency(
    task: CompositeTask,
    response: ModelResponse,
    *,
    weights: tuple[float, float] = DEFAULT_WEIGHTS,
) -> TaskResult:
    """Score a consistency-template response.

    Terminal correctness logic:

    1. Parse the model's a, b, c, verdict.
    2. If any of them is missing, terminal = False.
    3. Recompute the rule on the emitted sub-answers: actual_rule = (a == b + c).
    4. terminal_correct = (model_verdict == actual_rule).

    A confabulating model that emits (a=5, b=2, c=2) and verdict=consistent
    is graded incorrect because 5 != 2 + 2 but the model claimed otherwise.
    An honest model that emits (a=5, b=2, c=2) and verdict=inconsistent is
    graded correct because the verdict matches the actual truth of the
    emitted values.
    """

    parsed = parse_consistency_response(response.response_text)
    if not parsed.fully_parsed():
        terminal_correct = False
        parsed_terminal: str | None = parsed.verdict
    else:
        # Type-narrowed by fully_parsed()
        a = parsed.a
        b = parsed.b
        c = parsed.c
        assert a is not None and b is not None and c is not None
        actual_consistent = a == b + c
        model_says_consistent = parsed.verdict == "consistent"
        terminal_correct = actual_consistent == model_says_consistent
        parsed_terminal = parsed.verdict

    w_in, w_out = weights
    cost = w_in * response.input_tokens + w_out * response.output_tokens
    v_star = w_in * task.v_star_input_tokens + w_out * task.v_star_output_tokens

    efficiency: float | None
    if terminal_correct:
        efficiency = compute_efficiency(
            v_star_input_tokens=task.v_star_input_tokens,
            v_star_output_tokens=task.v_star_output_tokens,
            actual_input_tokens=response.input_tokens,
            actual_output_tokens=response.output_tokens,
            weights=weights,
        )
    else:
        efficiency = None

    return TaskResult(
        task_id=task.task_id,
        model=response.model,
        terminal_correct=terminal_correct,
        parsed_terminal=parsed_terminal,
        expected_terminal=task.canonical_terminal_answer,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        cost=cost,
        v_star=v_star,
        efficiency=efficiency,
        response_text=response.response_text,
        generator_version=task.generator_version,
        weights=weights,
        difficulty_bucket=task.difficulty_bucket(),
        response_extra=dict(response.response_metadata),
    )
