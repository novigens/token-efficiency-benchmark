"""Evaluation harness.

Drives the model client across a stream of generated tasks, parses responses,
counts tokens, and emits per-task replay records (§10.6) plus aggregated
reports (§6.2).

Token counts: if the client returns a :class:`ModelOutput` with
provider-reported usage, those counts are the billing truth and enter the
metric (design_v2.md §6 — reasoning/thinking tokens are billed as output but
invisible in the text, so local tokenization would undercount). The local
tokenizer is the fallback for fixtures and providers that omit usage.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..types import CompositeTask, ModelResponse, TaskResult
from .consistency_scoring import score_consistency
from .live_models import ModelOutput
from .models import ModelClient
from .scoring import DEFAULT_WEIGHTS, score_response
from .tokenization import count_tokens


def evaluate_task(
    task: CompositeTask,
    model: ModelClient,
    *,
    weights: tuple[float, float] = DEFAULT_WEIGHTS,
) -> TaskResult:
    """Run one task against one model and return its scored result."""

    # Models that need the task id to look up their pre-registered response
    # implement ``generate_for_task``; others use the generic ``generate``.
    if hasattr(model, "generate_for_task"):
        raw = model.generate_for_task(task.task_id, task.merged_prompt)
    else:
        raw = model.generate(task.merged_prompt)

    output = raw if isinstance(raw, ModelOutput) else ModelOutput(str(raw))

    input_tokens = (
        output.input_tokens if output.input_tokens is not None else count_tokens(task.merged_prompt)
    )
    output_tokens = (
        output.output_tokens if output.output_tokens is not None else count_tokens(output.text)
    )

    response = ModelResponse(
        task_id=task.task_id,
        model=model.name,
        response_text=output.text,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        response_metadata=dict(output.metadata),
    )
    if task.template_id == "consistency":
        return score_consistency(task, response, weights=weights)
    return score_response(task, response, weights=weights)


def evaluate_tasks(
    tasks: Iterable[CompositeTask],
    model: ModelClient,
    *,
    weights: tuple[float, float] = DEFAULT_WEIGHTS,
) -> list[TaskResult]:
    """Run a batch of tasks against one model. Sequential at v2."""

    return [evaluate_task(task, model, weights=weights) for task in tasks]
