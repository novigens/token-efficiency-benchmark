"""Evaluation harness.

Presents generated tasks to models, parses responses, computes per-task
correctness and cost-weighted efficiency, and writes JSONL replay records.
See ``docs/design_v2.md`` §1 and §6.
"""

from __future__ import annotations

from .consistency_scoring import parse_consistency_response, score_consistency
from .harness import evaluate_task, evaluate_tasks
from .models import (
    ConfabulatingConsistencyModel,
    ConsistencyEchoModel,
    EchoModel,
    ModelClient,
    VerboseEchoModel,
    WrongEchoModel,
)
from .scoring import (
    DEFAULT_WEIGHTS,
    aggregate_results,
    compute_efficiency,
    score_response,
)
from .tokenization import bytes_length, count_tokens

__all__ = [
    "DEFAULT_WEIGHTS",
    "ConfabulatingConsistencyModel",
    "ConsistencyEchoModel",
    "EchoModel",
    "ModelClient",
    "VerboseEchoModel",
    "WrongEchoModel",
    "aggregate_results",
    "bytes_length",
    "compute_efficiency",
    "count_tokens",
    "evaluate_task",
    "evaluate_tasks",
    "parse_consistency_response",
    "score_consistency",
    "score_response",
]
