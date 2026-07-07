"""Scoring.

Implements the cost-weighted token-efficiency metric (§10.5) and the
aggregated reporting (§6.2).

The headline metric:

    cost = w_in * input_tokens + w_out * output_tokens
    v_star = w_in * v_star_input + w_out * v_star_output
    efficiency = v_star / cost   if terminal_correct else None

Aggregation reports accuracy, mean efficiency (conditional on correctness),
overall expected-value ratio (accuracy x mean efficiency), variance, and
difficulty-stratified curves.
"""

from __future__ import annotations

import re
import statistics
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

from .. import GENERATOR_VERSION
from ..types import CompositeTask, ModelResponse, TaskResult

#: Default cost weights matching common provider pricing (w_out is ~4x w_in).
DEFAULT_WEIGHTS: tuple[float, float] = (1.0, 4.0)

_INT_PATTERN = re.compile(r"-?(?:\d{1,3}(?:[,\uff0c\u00a0\u202f]\d{3})+|\d+)")
_INTEGER_GROUP_SEPARATORS = str.maketrans({"\uff0c": "", ",": "", "\u00a0": "", "\u202f": ""})


def parse_integer_answer(response_text: str) -> str | None:
    """Extract a canonical integer answer from a free-form model response.

    Strategy: find the *last* integer in the response. Models typically place
    the final answer at the end of their reasoning trace, and the last-integer
    heuristic is robust to in-text references to other numbers (years,
    intermediate values). Returns the canonical decimal string or None if no
    integer is found.
    """

    matches = _INT_PATTERN.findall(response_text)
    if not matches:
        return None
    return str(int(matches[-1].translate(_INTEGER_GROUP_SEPARATORS)))


def compute_efficiency(
    *,
    v_star_input_tokens: int,
    v_star_output_tokens: int,
    actual_input_tokens: int,
    actual_output_tokens: int,
    weights: tuple[float, float] = DEFAULT_WEIGHTS,
) -> float:
    """Return the efficiency ratio V* / actual_cost.

    Bounded in (0, 1] when the model is correct. Returns 0 if the actual cost
    is 0 (degenerate case; should not occur in practice).
    """

    w_in, w_out = weights
    v_star = w_in * v_star_input_tokens + w_out * v_star_output_tokens
    actual = w_in * actual_input_tokens + w_out * actual_output_tokens
    if actual <= 0:
        return 0.0
    return v_star / actual


def score_response(
    task: CompositeTask,
    response: ModelResponse,
    *,
    weights: tuple[float, float] = DEFAULT_WEIGHTS,
) -> TaskResult:
    """Score a single (task, response) pair and return a :class:`TaskResult`."""

    parsed = parse_integer_answer(response.response_text)
    expected = task.canonical_terminal_answer
    correct = parsed is not None and parsed == expected

    w_in, w_out = weights
    cost = w_in * response.input_tokens + w_out * response.output_tokens
    v_star = w_in * task.v_star_input_tokens + w_out * task.v_star_output_tokens

    efficiency: float | None
    if correct:
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
        terminal_correct=correct,
        parsed_terminal=parsed,
        expected_terminal=expected,
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


@dataclass(frozen=True)
class AggregateReport:
    """Aggregated metrics for one (model, difficulty) cell."""

    model: str
    difficulty_bucket: str
    n: int
    accuracy: float
    mean_efficiency_when_correct: float
    expected_value_ratio: float  # accuracy * mean_efficiency
    efficiency_stddev: float
    mean_input_tokens: float
    mean_output_tokens: float


def aggregate_results(results: Iterable[TaskResult]) -> list[AggregateReport]:
    """Aggregate per-task results into per-(model, difficulty) reports."""

    buckets: dict[tuple[str, str], list[TaskResult]] = defaultdict(list)
    for r in results:
        buckets[(r.model, r.difficulty_bucket)].append(r)

    reports: list[AggregateReport] = []
    for (model, bucket), group in sorted(buckets.items()):
        n = len(group)
        n_correct = sum(1 for r in group if r.terminal_correct)
        accuracy = n_correct / n if n else 0.0
        eff_values = [r.efficiency for r in group if r.efficiency is not None]
        mean_eff = statistics.fmean(eff_values) if eff_values else 0.0
        stddev_eff = statistics.stdev(eff_values) if len(eff_values) >= 2 else 0.0
        evr = accuracy * mean_eff
        mean_in = statistics.fmean(r.input_tokens for r in group) if n else 0.0
        mean_out = statistics.fmean(r.output_tokens for r in group) if n else 0.0
        reports.append(
            AggregateReport(
                model=model,
                difficulty_bucket=bucket,
                n=n,
                accuracy=accuracy,
                mean_efficiency_when_correct=mean_eff,
                expected_value_ratio=evr,
                efficiency_stddev=stddev_eff,
                mean_input_tokens=mean_in,
                mean_output_tokens=mean_out,
            )
        )
    return reports


def format_report_table(reports: list[AggregateReport]) -> str:
    """Render an aggregate report list as a fixed-width table for the CLI."""

    if not reports:
        return "(no results)\n"

    header = (
        f"{'model':<24} {'difficulty':<12} {'n':>5} "
        f"{'acc':>6} {'eff':>6} {'EVR':>6} {'sd_eff':>6} "
        f"{'in_tok':>8} {'out_tok':>8}\n"
    )
    sep = "-" * len(header) + "\n"
    lines = [header, sep]
    for r in reports:
        lines.append(
            f"{r.model:<24} {r.difficulty_bucket:<12} {r.n:>5d} "
            f"{r.accuracy:>6.3f} {r.mean_efficiency_when_correct:>6.3f} "
            f"{r.expected_value_ratio:>6.3f} {r.efficiency_stddev:>6.3f} "
            f"{r.mean_input_tokens:>8.1f} {r.mean_output_tokens:>8.1f}\n"
        )
    lines.append(f"\ngenerator_version: {GENERATOR_VERSION}\n")
    return "".join(lines)
