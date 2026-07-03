"""Hybrid family: cross-family segment composition (design_v2.md §4.1,
examples_v2.md §G).

A hybrid task chains segments from different Composable families. Each
segment computes its own truth given the injected upstream value, so ground
truth remains by construction/execution end to end. Typed bridge phrases
reference the upstream value without stating it; a joint whose downstream
cannot accept the upstream raises :class:`GenerationRejected` (no implicit
coercion). Scoring is entirely standard — no hybrid-specific scoring code
exists, by design.

2.0.0 recipes:

- ``prog+chain``: program's printed value opens a narrative chain.
- ``chain+table``: a chain's final count becomes a hidden cell in a narrated
  dataset that must then be aggregated.
- ``prog+chain+table`` (default): the full gauntlet — code → narrative →
  table, one value carried across three representations.
"""

from __future__ import annotations

import hashlib
import random

from ..evaluation.tokenization import count_tokens
from ..types import AnswerType, CompositeNode, CompositeTask, Item
from .arithmetic_chain import ArithmeticChainFamily
from .base import (
    Composable,
    DifficultyParams,
    GenerationRejected,
    Segment,
    TaskFamily,
    check_no_decomposition_markers,
    check_values_hidden,
)
from .program_output import ProgramOutputFamily
from .table_aggregation import TableAggregationFamily

FAMILY_NAME = "hybrid"
FAMILY_VERSION = "2.0.0"
_MAX_ATTEMPTS = 25

_RECIPES: dict[str, tuple[str, ...]] = {
    "prog+chain": ("program_output", "arithmetic_chain"),
    "chain+table": ("arithmetic_chain", "table_aggregation"),
    "prog+chain+table": ("program_output", "arithmetic_chain", "table_aggregation"),
}

DEFAULT_RECIPE = "prog+chain+table"

_SEGMENT_FAMILIES: dict[str, Composable] = {
    "program_output": ProgramOutputFamily(),
    "arithmetic_chain": ArithmeticChainFamily(),
    "table_aggregation": TableAggregationFamily(),
}

# Typed bridge phrases per (source, target). The bridge references the
# upstream value by description only — never by literal.
_BRIDGES: dict[tuple[str, str], tuple[str, ...]] = {
    ("program_output", "arithmetic_chain"): (
        "Whatever the script prints becomes the number of units the site "
        "takes in on Monday; that intake starts the running count.",
        "The script's printed value is recorded as Monday's intake and "
        "becomes the initial running count.",
    ),
    ("arithmetic_chain", "table_aggregation"): (
        "The final running count is handed to the logistics office, which "
        "books it as the first site's opening-day load in the ledger below.",
        "That closing running count becomes the very first load entered in "
        "the week's shipping ledger.",
    ),
}

_INSTRUCTION = "\n\nAnswer with a single integer."


class HybridFamily(TaskFamily):
    """Chains Composable segments per a named recipe."""

    name = FAMILY_NAME
    version = FAMILY_VERSION

    def __init__(self, recipe: str = DEFAULT_RECIPE) -> None:
        if recipe not in _RECIPES:
            raise ValueError(f"unknown recipe '{recipe}'; available: {sorted(_RECIPES)}")
        self.recipe = recipe

    def difficulty_axes(self) -> dict[str, str]:
        return {
            "depth": "ops in the consuming chain segment (>= 2)",
            "distractors": "irrelevant numeric sentences (chain segment axis)",
            "recipe": f"segment composition ({sorted(_RECIPES)}; fixed set in 2.0.0)",
        }

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
            f"no valid hybrid after {_MAX_ATTEMPTS} attempts (seed={seed}): {last}"
        )

    # ------------------------------------------------------------------

    def _generate_once(
        self, seed: int, attempt: int, difficulty: DifficultyParams
    ) -> CompositeTask:
        family_names = _RECIPES[self.recipe]
        bridge_rng = random.Random(
            _derive_seed(seed, attempt, self.version, f"bridge|{self.recipe}")
        )

        segments: list[Segment] = []
        upstream: int | None = None
        for idx, fam_name in enumerate(family_names):
            fam = _SEGMENT_FAMILIES[fam_name]
            seg_seed = _derive_seed(seed, attempt, self.version, f"segment{idx}|{fam_name}")
            # Type check at the joint happens inside generate_segment
            # (GenerationRejected on mismatch — no implicit coercion).
            segment = fam.generate_segment(seg_seed, difficulty, upstream)
            segments.append(segment)
            upstream = segment.value

        # Assemble: segment texts joined by bridge phrases; final question.
        parts: list[str] = []
        for idx, segment in enumerate(segments):
            parts.append(segment.text.rstrip())
            if idx < len(segments) - 1:
                pair = (family_names[idx], family_names[idx + 1])
                bridge_options = _BRIDGES.get(pair)
                if bridge_options is None:
                    raise GenerationRejected(f"no bridge template for joint {pair}")
                parts.append(bridge_rng.choice(bridge_options))
        terminal_question = segments[-1].question
        if not terminal_question:
            raise GenerationRejected("closing segment provided no question form")
        prompt = "\n\n".join(parts) + "\n\n" + terminal_question + _INSTRUCTION
        terminal_value = segments[-1].value
        terminal = str(terminal_value)

        # Cross-segment validity: every hidden value from every segment must
        # be absent from the entire merged surface (bridge included).
        hidden: list[int] = []
        for segment in segments:
            hidden.extend(segment.hidden_values)
        check_no_decomposition_markers(prompt)
        check_values_hidden(prompt, hidden)

        difficulty_dict = {
            "depth": difficulty.depth,
            "distractors": difficulty.distractors,
        }
        task_id = _task_id(self.recipe, seed, difficulty_dict, prompt, terminal)

        nodes = tuple(
            CompositeNode(
                item=Item(
                    id=f"{FAMILY_NAME}::{task_id[-12:]}::seg{idx}",
                    question="",
                    known_answer=segment.value,
                    answer_type=AnswerType.INTEGER,
                    source=family_names[idx],
                    source_version=FAMILY_VERSION,
                    metadata={},
                ),
                parameter_template=None,
                instantiated_question="",
            )
            for idx, segment in enumerate(segments)
        )

        return CompositeTask(
            task_id=task_id,
            generator_version=FAMILY_VERSION,
            template_id=FAMILY_NAME,
            seed=seed,
            parameters={
                "family": FAMILY_NAME,
                "family_version": FAMILY_VERSION,
                "recipe": {
                    "name": self.recipe,
                    "segments": list(family_names),
                    "per_segment_difficulty": difficulty_dict,
                },
                "segment_values": [s.value for s in segments],
                "difficulty": difficulty_dict,
                "bucket": f"hybrid_{self.recipe}_d{difficulty.depth}",
            },
            nodes=nodes,
            merged_prompt=prompt,
            canonical_terminal_answer=terminal,
            terminal_answer_type=AnswerType.INTEGER,
            v_star_input_tokens=count_tokens(prompt),
            v_star_output_tokens=count_tokens(terminal),
        )


def _derive_seed(seed: int, attempt: int, version: str, scope: str) -> int:
    h = hashlib.sha256(f"{seed}|{attempt}|{version}|{scope}".encode())
    return int.from_bytes(h.digest()[:8], "big")


def _task_id(recipe: str, seed: int, difficulty: dict[str, int], prompt: str, terminal: str) -> str:
    h = hashlib.sha256()
    for part in (
        FAMILY_NAME,
        FAMILY_VERSION,
        recipe,
        str(seed),
        repr(sorted(difficulty.items())),
        prompt,
        terminal,
    ):
        h.update(part.encode("utf-8"))
    return f"{FAMILY_NAME}::{FAMILY_VERSION}::{h.hexdigest()[:12]}"
