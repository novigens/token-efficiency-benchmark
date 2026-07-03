"""Core type definitions used across adapters, generator, and evaluation.

These types are the stable contract between modules. They are deliberately
small and serializable: replays, task specs, and result records are all plain
JSON over instances of these classes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AnswerType(str, Enum):
    """The canonical answer type taxonomy from ``docs/phase0/answer-types.md``."""

    INTEGER = "integer"
    REAL = "real"
    BOOLEAN = "boolean"
    MC_INDEX = "mc_index"
    STRING = "string"
    TUPLE = "tuple"


@dataclass(frozen=True)
class Item:
    """A single source-benchmark item.

    The item is pure data: verification and parameter-template application
    are performed by the adapter that owns this item (looked up by ``source``).
    Items are JSON-serializable; ``known_answer`` and ``metadata`` should
    contain only JSON-compatible values.
    """

    id: str
    question: str
    known_answer: Any
    answer_type: AnswerType
    source: str
    source_version: str
    parameter_templates_supported: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ParameterTemplateSpec:
    """Specification of a parameter template applied to a node's output.

    The actual function is resolved by name via
    :func:`generator.parameter_templates.apply`. Storing only the name plus
    JSON-serializable arguments keeps task specs and replays round-trippable.
    """

    name: str
    args: dict[str, Any] = field(default_factory=dict)
    output_type: AnswerType = AnswerType.INTEGER


@dataclass(frozen=True)
class CompositeNode:
    """One node in a composite task graph."""

    item: Item
    parameter_template: ParameterTemplateSpec | None  # None on the terminal node
    instantiated_question: str  # the item.question after parameter substitution


@dataclass(frozen=True)
class CompositeTask:
    """A generated composite task ready for evaluation.

    Equivalent to the "composer view" of §12 plus the merged prompt of §13.
    A task is fully reproducible from ``generator_version``, ``template_id``,
    and ``seed``; the other fields are computed at generation time and stored
    for downstream consumers.
    """

    task_id: str
    generator_version: str
    template_id: str
    seed: int
    parameters: dict[str, Any]
    nodes: tuple[CompositeNode, ...]
    merged_prompt: str
    canonical_terminal_answer: str
    terminal_answer_type: AnswerType
    v_star_input_tokens: int
    v_star_output_tokens: int

    def difficulty_bucket(self) -> str:
        """Coarse difficulty label used for stratified reporting.

        Families may set an explicit ``parameters["bucket"]`` (hybrids encode
        their recipe there); the default is depth-of-composition.
        """

        explicit = self.parameters.get("bucket")
        if isinstance(explicit, str) and explicit:
            return explicit
        depth = len(self.nodes)
        return f"depth_{depth}"


@dataclass(frozen=True)
class ModelResponse:
    """A model's response to a single composite task."""

    task_id: str
    model: str
    response_text: str
    input_tokens: int
    output_tokens: int
    response_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TaskResult:
    """Scored outcome for one (task, model) pair."""

    task_id: str
    model: str
    terminal_correct: bool
    parsed_terminal: str | None
    expected_terminal: str
    input_tokens: int
    output_tokens: int
    cost: float
    v_star: float
    efficiency: float | None  # None if terminal incorrect
    response_text: str
    generator_version: str
    weights: tuple[float, float]
    difficulty_bucket: str
    #: Provider-reported extras kept as audit evidence: reasoning_content
    #: (when the provider exposes the thinking text), finish/stop reason,
    #: reasoning-token counts. Never used for grading.
    response_extra: dict[str, Any] = field(default_factory=dict)
