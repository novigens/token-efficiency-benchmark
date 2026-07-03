"""Arithmetic-chain family (design_v2.md §4.1, examples_v2.md §A).

A single evolving quantity ("the running count") is transformed through
``depth`` steps. Ground truth is forward substitution through the ops'
compute functions — there is no scaling heuristic and no solver. Distractor
sentences carry numbers that are irrelevant to the chain; validity guarantees
they never collide with hidden values.

Difficulty axes: depth, distractor density, value magnitude, lexicon breadth.
"""

from __future__ import annotations

import hashlib
import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

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

FAMILY_NAME = "arithmetic_chain"
FAMILY_VERSION = "2.0.0"

_VALUE_CAP = 500_000
_MAX_ATTEMPTS = 25

_SCENARIOS: tuple[tuple[str, str], ...] = (
    ("workshop", "chairs"),
    ("bakery", "loaves"),
    ("depot", "crates"),
    ("farm", "egg cartons"),
    ("print shop", "posters"),
    ("nursery", "saplings"),
    ("assembly plant", "gadgets"),
    ("studio", "picture frames"),
)

# First step: two concrete seed values produce the initial running count.
# (template, compute(a, b) -> v0)
_FIRST_STEPS: tuple[tuple[str, Callable[[int, int], int]], ...] = (
    (
        "A {place} produces {a} {items} in the morning and {b} more in the afternoon.",
        lambda a, b: a + b,
    ),
    (
        "Two crews at a {place} turn out {a} and {b} {items} respectively.",
        lambda a, b: a + b,
    ),
    (
        "A {place} finishes {a} {items} on Monday and twice as many on Tuesday.",
        lambda a, b: a + 2 * a,
    ),
)


@dataclass(frozen=True)
class _Op:
    name: str
    phrases: tuple[str, ...]
    # sample_arg returns a valid arg for current value v, or None if inapplicable
    sample_arg: Callable[[random.Random, int], int | None]
    compute: Callable[[int, int], int]


def _sample_gain(rng: random.Random, v: int) -> int | None:
    if v + 96 > _VALUE_CAP:
        return None
    return rng.randint(13, 96)


def _sample_loss(rng: random.Random, v: int) -> int | None:
    hi = min(96, v - 2)
    if hi < 7:
        return None
    return rng.randint(7, hi)


def _sample_scale(rng: random.Random, v: int) -> int | None:
    ks = [k for k in range(2, 10) if v * k <= _VALUE_CAP]
    return rng.choice(ks) if ks else None


def _sample_split(rng: random.Random, v: int) -> int | None:
    divisors = [k for k in range(2, 13) if v % k == 0 and v // k >= 2]
    return rng.choice(divisors) if divisors else None


_OPS: tuple[_Op, ...] = (
    _Op(
        name="gain",
        phrases=(
            "A supplier then adds {k} more to the running count.",
            "An overnight delivery then raises the running count by {k}.",
            "Later, {k} additional {items} join the running count.",
        ),
        sample_arg=_sample_gain,
        compute=lambda v, k: v + k,
    ),
    _Op(
        name="loss",
        phrases=(
            "Quality control then removes {k} from the running count.",
            "Then {k} are pulled from the running count as rejects.",
            "Shipping damage then costs the running count {k}.",
        ),
        sample_arg=_sample_loss,
        compute=lambda v, k: v - k,
    ),
    _Op(
        name="scale",
        phrases=(
            "A wholesaler then orders {k} times the running count, and that order becomes the new running count.",
            "The next cycle turns out {k} times the running count, which replaces it.",
        ),
        sample_arg=_sample_scale,
        compute=lambda v, k: v * k,
    ),
    _Op(
        name="split",
        phrases=(
            "The running count is then divided evenly among {k} trucks; keep only one truck's share as the new running count.",
            "Workers then split the running count into {k} equal lots; only a single lot moves on as the running count.",
        ),
        sample_arg=_sample_split,
        compute=lambda v, k: v // k,
    ),
)

_DISTRACTOR_TEMPLATES: tuple[str, ...] = (
    "The {place} employs {d} workers year-round.",
    "Each of the {items} weighs about {d} grams.",
    "The site was founded {d} years ago.",
    "Inspectors visit the {place} {d} times per season.",
    "The main hall spans {d} meters end to end.",
    "A nearby competitor advertises {d} product lines.",
)

_TERMINAL_QUESTION = "What is the final running count?"
_INSTRUCTION = "\n\nAnswer with a single integer."


class ArithmeticChainFamily(TaskFamily, Composable):
    name = FAMILY_NAME
    version = FAMILY_VERSION

    def generate_segment(
        self, seed: int, difficulty: DifficultyParams, upstream: int | None
    ) -> Segment:
        """Chain segment: consuming (upstream >= 2, ops-only continuation) or
        opening (upstream None, first step + ops, statement form).

        ``difficulty.depth`` is the number of chained ops in the segment."""

        if upstream is not None and upstream < 2:
            raise GenerationRejected("arithmetic_chain segment requires an integer upstream >= 2")
        last: GenerationRejected | None = None
        for attempt in range(_MAX_ATTEMPTS):
            rng = random.Random(
                _derive_rng_seed(
                    seed, attempt, self.version, f"segment|{difficulty.depth}|{upstream}"
                )
            )
            place, items = rng.choice(_SCENARIOS)
            try:
                if upstream is None:
                    first_template, first_compute = rng.choice(_FIRST_STEPS)
                    a = rng.randint(12, 89)
                    b = rng.randint(11, 88)
                    start = first_compute(a, b)
                    opening = [
                        first_template.format(place=place, items=items, a=a, b=b),
                        "The combined output starts the running count.",
                    ]
                    seg_args = {a, b}
                else:
                    start = upstream
                    opening = []
                    seg_args = set()
                sentences, values, ops_record, op_args = _build_ops(
                    rng, start, difficulty.depth, items
                )
            except GenerationRejected as e:
                last = e
                continue
            return Segment(
                text=" ".join(opening + sentences),
                value=values[-1],
                output_type=AnswerType.INTEGER.value,
                hidden_values=tuple(values),  # includes the start value
                surface_numbers=tuple(sorted(seg_args | op_args)),
                question=_TERMINAL_QUESTION,
                meta={"ops": ops_record},
            )
        raise GenerationRejected(
            f"no valid segment after {_MAX_ATTEMPTS} attempts (seed={seed}): {last}"
        )

    def difficulty_axes(self) -> dict[str, str]:
        return {
            "depth": "number of chained transformations (>= 2)",
            "distractors": "count of irrelevant numeric sentences interleaved",
            "value_magnitude": f"values bounded by {_VALUE_CAP} (fixed in 2.0.0)",
            "lexicon": f"{len(_SCENARIOS)} scenarios x phrase variants (fixed in 2.0.0)",
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
            f"no valid instance after {_MAX_ATTEMPTS} attempts (seed={seed}): {last}"
        )

    # ------------------------------------------------------------------

    def _generate_once(
        self, seed: int, attempt: int, difficulty: DifficultyParams
    ) -> CompositeTask:
        # Chain RNG must not depend on the distractor count, so that the
        # distractor axis is orthogonal: same (seed, depth) => same chain and
        # same truth at any distractor density (test_chain_distractor_invariance).
        rng = random.Random(
            _derive_rng_seed(seed, attempt, self.version, f"chain|{difficulty.depth}")
        )
        distractor_rng = random.Random(
            _derive_rng_seed(
                seed,
                attempt,
                self.version,
                f"distractors|{difficulty.depth}|{difficulty.distractors}",
            )
        )
        place, items = rng.choice(_SCENARIOS)

        # --- first step
        first_template, first_compute = rng.choice(_FIRST_STEPS)
        a = rng.randint(12, 89)
        b = rng.randint(11, 88)
        v = first_compute(a, b)
        first_sentence = first_template.format(place=place, items=items, a=a, b=b)

        # --- chained ops (depth - 1 transformations after the opening step)
        op_sentences, op_values, op_records, _op_args = _build_ops(
            rng, v, difficulty.depth - 1, items
        )
        sentences: list[str] = [first_sentence, *op_sentences]
        values: list[int] = op_values  # includes v at index 0
        ops_record: list[dict[str, Any]] = [
            {"name": "first", "template": first_template, "a": a, "b": b},
            *op_records,
        ]

        # --- distractors: numbers that must never collide with hidden values
        hidden = set(values)
        distractor_values: list[int] = []
        for _ in range(difficulty.distractors):
            for _try in range(50):
                d = distractor_rng.randint(3, 97)
                if d not in hidden and d not in distractor_values:
                    break
            else:
                raise GenerationRejected("could not draw a non-colliding distractor")
            template = distractor_rng.choice(_DISTRACTOR_TEMPLATES)
            sentence = template.format(place=place, items=items, d=d)
            # insert anywhere after the opening sentence, before the question
            pos = distractor_rng.randint(1, len(sentences))
            sentences.insert(pos, sentence)
            distractor_values.append(d)

        body = " ".join([*sentences, _TERMINAL_QUESTION])
        prompt = body + _INSTRUCTION
        terminal = str(values[-1])

        # --- validity obligations (reject, never emit)
        check_no_decomposition_markers(prompt)
        check_values_hidden(prompt, values)

        # --- assemble
        input_tokens = count_tokens(prompt)
        output_tokens = count_tokens(terminal)
        difficulty_dict = {
            "depth": difficulty.depth,
            "distractors": difficulty.distractors,
        }
        task_id = _task_id(seed, difficulty_dict, prompt, terminal)

        nodes = tuple(
            CompositeNode(
                item=Item(
                    id=f"{FAMILY_NAME}::{task_id[-12:]}::step{i}",
                    question=sentences[0] if i == 0 else "",
                    known_answer=values[i],
                    answer_type=AnswerType.INTEGER,
                    source=FAMILY_NAME,
                    source_version=FAMILY_VERSION,
                    metadata={"op": ops_record[i]},
                ),
                parameter_template=None,
                instantiated_question="",
            )
            for i in range(len(values))
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
                "scenario": {"place": place, "items": items},
                "ops": ops_record,
                "values": values,
                "distractor_values": distractor_values,
            },
            nodes=nodes,
            merged_prompt=prompt,
            canonical_terminal_answer=terminal,
            terminal_answer_type=AnswerType.INTEGER,
            v_star_input_tokens=input_tokens,
            v_star_output_tokens=output_tokens,
        )


def _build_ops(
    rng: random.Random, start_value: int, n_ops: int, items: str
) -> tuple[list[str], list[int], list[dict[str, Any]], set[int]]:
    """Draw ``n_ops`` chained transformations from ``start_value``.

    Returns (sentences, values, ops_record, surface_args) where ``values``
    includes ``start_value`` at index 0. Shared by standalone generation and
    hybrid segments so truth propagation has exactly one implementation.
    """

    v = start_value
    sentences: list[str] = []
    values: list[int] = [v]
    ops_record: list[dict[str, Any]] = []
    surface_args: set[int] = set()
    for _ in range(n_ops):
        candidates = list(_OPS)
        rng.shuffle(candidates)
        placed = False
        for op in candidates:
            k = op.sample_arg(rng, v)
            if k is None:
                continue
            nxt = op.compute(v, k)
            if not (2 <= nxt <= _VALUE_CAP):
                continue
            sentences.append(rng.choice(op.phrases).format(k=k, items=items))
            ops_record.append({"name": op.name, "k": k})
            surface_args.add(k)
            v = nxt
            values.append(v)
            placed = True
            break
        if not placed:
            raise GenerationRejected("no applicable op for current value")
    return sentences, values, ops_record, surface_args


def recompute_truth(parameters: dict[str, Any]) -> list[int]:
    """Independent forward recomputation from the recorded op list.

    Used by tests and by replay verification: must reproduce
    ``parameters['values']`` exactly. Raises KeyError/ValueError on malformed
    records rather than guessing.
    """

    ops = parameters["ops"]
    first = ops[0]
    template = first["template"]
    compute = next(c for t, c in _FIRST_STEPS if t == template)
    v = compute(first["a"], first["b"])
    values = [v]
    op_by_name = {op.name: op for op in _OPS}
    for rec in ops[1:]:
        v = op_by_name[rec["name"]].compute(v, rec["k"])
        values.append(v)
    return values


def _derive_rng_seed(seed: int, attempt: int, version: str, scope: str) -> int:
    """Stable integer seed (never Python's salted hash())."""

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
