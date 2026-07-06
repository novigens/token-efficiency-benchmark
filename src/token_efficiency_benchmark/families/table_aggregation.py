"""Table-aggregation family (design_v2.md §4.3, examples_v2.md §C).

A synthetic dataset (groups x days) is narrated as interleaved prose — never
shown as a table. The question asks for a derived statistic: by how much the
highest weekly total exceeds the lowest. Ground truth is computed from the
dataset. This is the enterprise-document-workflow shape: extract → structure
→ aggregate.

Composable: as a consuming segment, the upstream value silently becomes the
first group's first-day load ("a load equal to the running count"), so the
model must carry a value from a different representation into the aggregation.
"""

from __future__ import annotations

import hashlib
import random

from ..evaluation.tokenization import count_tokens
from ..types import AnswerType, CompositeNode, CompositeTask, Item
from .base import (
    Composable,
    DifficultyParams,
    GenerationRejected,
    Segment,
    TaskFamily,
    check_no_decomposition_markers,
    check_values_hidden,
)

FAMILY_NAME = "table_aggregation"
FAMILY_VERSION = "2.0.0"
_MAX_ATTEMPTS = 25

_GROUPS = ("North", "South", "East", "West")
_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

_UNITS = ("kilograms", "crates", "parcels")
_SITE = ("depot", "warehouse", "hub")

_DAY_TEMPLATES = (
    "On {day}, the {entries}.",
    "{day}'s ledger shows the {entries}.",
)

_DISTRACTORS = (
    "A returned pallet of {d} {units} sat unprocessed at the {g} {site} all week.",
    "The {g} {site} employs {d} staff across two shifts.",
    "Insurance values the {g} {site}'s forklift fleet at {d} thousand dollars.",
)

_QUESTION = "By how many {units} did the highest weekly total among the {sites} exceed the lowest?"
_INSTRUCTION = "\n\nAnswer with a single integer."


class TableAggregationFamily(TaskFamily, Composable):
    name = FAMILY_NAME
    version = FAMILY_VERSION

    def difficulty_axes(self) -> dict[str, str]:
        return {
            "depth": "number of days narrated per group (>= 2)",
            "distractors": "irrelevant numeric sentences interleaved",
            "groups": "2-3 groups (drawn per seed; fixed range in 2.0.0)",
        }

    # ------------------------------------------------------------- TaskFamily

    def generate(self, seed: int, difficulty: DifficultyParams) -> CompositeTask:
        if difficulty.depth < 2:
            raise ValueError("depth must be >= 2")
        last: GenerationRejected | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                return self._generate_once(seed, attempt, difficulty)
            except GenerationRejected as e:
                last = e
        raise GenerationRejected(
            f"no valid instance after {_MAX_ATTEMPTS} attempts (seed={seed}): {last}"
        )

    # ------------------------------------------------------------- Composable

    def generate_segment(
        self, seed: int, difficulty: DifficultyParams, upstream: int | None
    ) -> Segment:
        if upstream is None or upstream < 2:
            raise GenerationRejected("table_aggregation segment requires an integer upstream >= 2")
        last: GenerationRejected | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                built = _build(seed, attempt, self.version, difficulty, upstream)
            except GenerationRejected as e:
                last = e
                continue
            return Segment(
                text=built.narration,
                value=built.diff,
                output_type=AnswerType.INTEGER.value,
                hidden_values=built.hidden,
                surface_numbers=built.surface,
                question=built.question,
                meta={"cells": built.cells, "groups": list(built.groups)},
            )
        raise GenerationRejected(
            f"no valid segment after {_MAX_ATTEMPTS} attempts (seed={seed}): {last}"
        )

    # ---------------------------------------------------------------- internal

    def _generate_once(
        self, seed: int, attempt: int, difficulty: DifficultyParams
    ) -> CompositeTask:
        built = _build(seed, attempt, self.version, difficulty, upstream=None)
        prompt = built.narration + "\n\n" + built.question + _INSTRUCTION
        terminal = str(built.diff)

        check_no_decomposition_markers(prompt)
        check_values_hidden(prompt, list(built.hidden))

        difficulty_dict = {
            "depth": difficulty.depth,
            "distractors": difficulty.distractors,
        }
        task_id = _task_id(seed, difficulty_dict, prompt, terminal)
        nodes = tuple(
            CompositeNode(
                item=Item(
                    id=f"{FAMILY_NAME}::{task_id[-12:]}::{group}",
                    question="",
                    known_answer=total,
                    answer_type=AnswerType.INTEGER,
                    source=FAMILY_NAME,
                    source_version=FAMILY_VERSION,
                    metadata={"group": group},
                ),
                parameter_template=None,
                instantiated_question="",
            )
            for group, total in built.totals.items()
        )
        return CompositeTask(
            task_id=task_id,
            generator_version=FAMILY_VERSION,
            template_id=FAMILY_NAME,
            seed=seed,
            parameters={
                "family": FAMILY_NAME,
                "family_version": FAMILY_VERSION,
                "difficulty": difficulty_dict,
                "cells": built.cells,
                "totals": dict(built.totals),
                "distractor_values": list(built.distractor_values),
                "bucket": f"table_d{difficulty.depth}",
            },
            nodes=nodes,
            merged_prompt=prompt,
            canonical_terminal_answer=terminal,
            terminal_answer_type=AnswerType.INTEGER,
            v_star_input_tokens=count_tokens(prompt),
            v_star_output_tokens=count_tokens(terminal),
        )


class _Built:
    def __init__(
        self,
        narration: str,
        question: str,
        cells: dict[str, list[int]],
        totals: dict[str, int],
        diff: int,
        hidden: tuple[int, ...],
        surface: tuple[int, ...],
        groups: tuple[str, ...],
        distractor_values: tuple[int, ...],
        units: str = "",
        site: str = "",
    ) -> None:
        self.narration = narration
        self.question = question
        self.cells = cells
        self.totals = totals
        self.diff = diff
        self.hidden = hidden
        self.surface = surface
        self.groups = groups
        self.distractor_values = distractor_values
        self.units = units
        self.site = site


def recompute_truth(cells: dict[str, list[int]]) -> int:
    """Independent recomputation: highest weekly total minus lowest."""

    totals = [sum(v) for v in cells.values()]
    return max(totals) - min(totals)


def _build(
    seed: int,
    attempt: int,
    version: str,
    difficulty: DifficultyParams,
    upstream: int | None,
) -> _Built:
    scope = f"table|{difficulty.depth}|{'seg' if upstream is not None else 'solo'}"
    rng = random.Random(_derive_seed(seed, attempt, version, scope))
    distractor_rng = random.Random(
        _derive_seed(seed, attempt, version, f"{scope}|dist|{difficulty.distractors}")
    )

    n_groups = rng.choice((2, 3))
    groups = tuple(rng.sample(_GROUPS, n_groups))
    days = _DAYS[: difficulty.depth]
    units = rng.choice(_UNITS)
    site = rng.choice(_SITE)

    # Draw distinct cell values so the render-faithful check is exact.
    n_cells = n_groups * len(days)
    values = rng.sample(range(41, 197), n_cells)
    cells: dict[str, list[int]] = {
        g: values[i * len(days) : (i + 1) * len(days)] for i, g in enumerate(groups)
    }
    if upstream is not None:
        cells[groups[0]][0] = upstream  # the injected cell, referenced by phrase

    totals = {g: sum(v) for g, v in cells.items()}
    ordered = sorted(totals.values())
    if len(set(ordered)) != len(ordered):
        raise GenerationRejected("tie in group totals (ambiguous max/min)")
    diff = ordered[-1] - ordered[0]
    if diff < 2:
        raise GenerationRejected("degenerate difference")

    surface_cells = [
        v
        for g in groups
        for idx, v in enumerate(cells[g])
        if not (upstream is not None and g == groups[0] and idx == 0)
    ]
    hidden = set(totals.values()) | {diff}
    if upstream is not None:
        hidden.add(upstream)
    if hidden & set(surface_cells):
        raise GenerationRejected("hidden value collides with a surface cell")

    # Narration, interleaved by day.
    sentences: list[str] = []
    for d_idx, day in enumerate(days):
        parts = []
        for g in groups:
            if upstream is not None and g == groups[0] and d_idx == 0:
                parts.append(f"{g} {site} logged a load equal to the running count")
            else:
                parts.append(f"{g} {site} logged {cells[g][d_idx]} {units}")
        entries = ", the ".join(parts[:-1]) + (
            f", while the {parts[-1]}" if len(parts) > 1 else parts[0]
        )
        template = rng.choice(_DAY_TEMPLATES)
        sentences.append(template.format(day=day, entries=entries))

    # Distractors (values must not collide with anything meaningful).
    distractor_values: list[int] = []
    forbidden = hidden | set(surface_cells)
    for _ in range(difficulty.distractors):
        for _try in range(60):
            d = distractor_rng.randint(3, 250)
            if d not in forbidden and d not in distractor_values:
                break
        else:
            raise GenerationRejected("could not draw a non-colliding distractor")
        distractor_values.append(d)
        g = distractor_rng.choice(groups)
        template = distractor_rng.choice(_DISTRACTORS)
        sentence = template.format(d=d, g=g, units=units, site=site)
        sentences.insert(distractor_rng.randint(1, len(sentences)), sentence)

    question = _QUESTION.format(units=units, sites=f"{site}s")
    return _Built(
        narration=" ".join(sentences),
        question=question,
        cells=cells,
        totals=totals,
        diff=diff,
        hidden=tuple(sorted(hidden)),
        surface=tuple(sorted(set(surface_cells) | set(distractor_values))),
        groups=groups,
        distractor_values=tuple(distractor_values),
        units=units,
        site=site,
    )


def _derive_seed(seed: int, attempt: int, version: str, scope: str) -> int:
    h = hashlib.sha256(f"{seed}|{attempt}|{version}|{scope}".encode())
    return int.from_bytes(h.digest()[:8], "big")


def _task_id(seed: int, difficulty: dict[str, int], prompt: str, terminal: str) -> str:
    h = hashlib.sha256()
    for part in (
        FAMILY_NAME,
        FAMILY_VERSION,
        str(seed),
        repr(sorted(difficulty.items())),
        prompt,
        terminal,
    ):
        h.update(part.encode("utf-8"))
    return f"{FAMILY_NAME}::{FAMILY_VERSION}::{h.hexdigest()[:12]}"
