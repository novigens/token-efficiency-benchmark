"""TaskFamily interface and shared validity checks (design_v2.md §3.1).

A family must produce ground truth by construction or execution — never by a
solver, an LLM judge, or a heuristic. Rendering is family-owned and
seed-deterministic. A family raises :class:`GenerationRejected` instead of
emitting a task that violates any validity obligation.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..types import CompositeTask


class GenerationRejected(Exception):  # noqa: N818 - public API name, used throughout docs
    """Raised when a candidate instance fails a validity obligation."""


@dataclass(frozen=True)
class DifficultyParams:
    """Difficulty dials shared across families; families may ignore axes
    they do not implement and extend via ``extra``."""

    depth: int = 4
    distractors: int = 0
    extra: dict[str, object] = field(default_factory=dict)


class TaskFamily(ABC):
    """One procedurally generated task distribution."""

    name: str
    version: str

    @abstractmethod
    def generate(self, seed: int, difficulty: DifficultyParams) -> CompositeTask:
        """Deterministic in (version, seed, difficulty)."""

    @abstractmethod
    def difficulty_axes(self) -> dict[str, str]:
        """Human-readable description of the dials the evolution loop may mutate."""


@dataclass(frozen=True)
class Segment:
    """One hybrid-composition segment (design_v2.md §4.1).

    ``text`` is statement-form prose (no question). ``value`` is the segment's
    computed terminal, hidden from the surface. ``hidden_values`` lists every
    value (intermediates included) that must not appear in the merged prompt.
    ``surface_numbers`` lists literals that legitimately appear, so the hybrid
    composer can reject cross-segment collisions with hidden values.
    """

    text: str
    value: int
    output_type: str  # AnswerType.value of the terminal
    hidden_values: tuple[int, ...]
    surface_numbers: tuple[int, ...]
    question: str | None = None  # terminal question form, if this segment closes the task
    meta: dict[str, object] = field(default_factory=dict)


class Composable(ABC):
    """Optional family extension: can produce hybrid segments.

    ``upstream=None`` means the segment opens the task; a non-None upstream is
    the previous segment's terminal, injected as this segment's starting
    value. A family that cannot consume an upstream raises
    :class:`GenerationRejected` — the hybrid composer treats that as a type
    mismatch at the joint (no implicit coercion, ever).
    """

    @abstractmethod
    def generate_segment(
        self, seed: int, difficulty: DifficultyParams, upstream: int | None
    ) -> Segment:
        """Deterministic in (version, seed, difficulty, upstream)."""


# ----------------------------------------------------------------------
# Shared validity checks (the subset generation can guarantee)

_DECOMPOSITION_MARKERS = re.compile(
    r"\bStep\s*\d|\bStage\s*\d|sub-?problem|\bPart\s+[A-Z0-9]\b|\bQ\d\b",
    re.IGNORECASE,
)


def check_no_decomposition_markers(prompt: str) -> None:
    if _DECOMPOSITION_MARKERS.search(prompt):
        raise GenerationRejected("decomposition marker present in surface form")


def check_values_hidden(prompt: str, hidden_values: list[int]) -> None:
    """Every intermediate and the terminal must be absent as standalone integers."""

    for v in hidden_values:
        if re.search(rf"(?<![\d.]){v}(?![\d.])", prompt):
            raise GenerationRejected(f"hidden value {v} leaks into surface form")
