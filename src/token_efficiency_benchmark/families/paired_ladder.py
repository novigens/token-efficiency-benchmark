"""Paired depth-ladder generation for the hybrid gauntlet.

All rungs of one paired group share a single underlying problem: the same
program, the same bridge phrases, the same base table, the same distractor
sentences, and one op-sequence whose depth-d prefix is rung d's chain. The
only differences between rung d and rung d+3 are the extra chain sentences
and the value the (otherwise identical) table absorbs. Depth is therefore
isolated per item: any accuracy or cost change between rungs of the same
group is attributable to depth alone.

Contrast with the regular hybrid ladder, where each rung is an independent
draw (no cross-rung leakage, but rung-to-rung comparisons mix the depth
effect with task-draw luck). The two designs are complementary.

Version namespace: PAIRED_VERSION seeds every RNG scope here, so the regular
generation streams (and byte-for-byte replay of published runs) are untouched.

Invariants, enforced by generation and pinned by tests:
- program text identical across rungs of a group;
- rung d's chain ops are exactly the first d ops of the deepest rung;
- table cells identical across rungs except the injected first cell;
- distractor sentences and their positions identical across rungs (values are
  drawn once against the union of every rung's hidden and surface values);
- every rung passes the standard hidden-value and decomposition-marker checks,
  and any rung failing regenerates the whole group (attempt increments).
"""

from __future__ import annotations

import hashlib
import random

from ..evaluation.tokenization import count_tokens
from ..types import AnswerType, CompositeNode, CompositeTask, Item
from .arithmetic_chain import _SCENARIOS, _build_ops
from .base import (
    DifficultyParams,
    GenerationRejected,
    Segment,
    check_no_decomposition_markers,
    check_values_hidden,
)
from .hybrid import _BRIDGES, _INSTRUCTION
from .program_output import ProgramOutputFamily
from .table_aggregation import _DISTRACTORS as _TABLE_DISTRACTORS
from .table_aggregation import _build as _build_table
from .table_aggregation import _Built

FAMILY_NAME = "hybrid"
PAIRED_VERSION = "2.0.0+paired"
RECIPE = "prog+chain+table"
_MAX_ATTEMPTS = 25
_REF_PROGRAM = DifficultyParams(depth=3, distractors=2)
_REF_TABLE = DifficultyParams(depth=3, distractors=0)  # distractors drawn by the group


def generate_paired_ladder(
    seed: int, depths: list[int], distractors: int = 2
) -> list[CompositeTask]:
    """One paired group: a task per depth in ``depths``, sharing one problem."""

    rungs = sorted(set(depths))
    if not rungs or rungs[0] < 2:
        raise ValueError("paired ladder requires depths >= 2")
    last: GenerationRejected | None = None
    for attempt in range(_MAX_ATTEMPTS):
        try:
            return _generate_once(seed, attempt, rungs, distractors)
        except GenerationRejected as e:
            last = e
    raise GenerationRejected(
        f"no valid paired ladder after {_MAX_ATTEMPTS} attempts (seed={seed}): {last}"
    )


def _generate_once(
    seed: int, attempt: int, rungs: list[int], distractors: int
) -> list[CompositeTask]:
    max_depth = rungs[-1]

    # --- program segment: fixed shape, shared by every rung
    program: Segment = ProgramOutputFamily().generate_segment(
        _dseed(seed, attempt, "program"), _REF_PROGRAM, None
    )
    if program.value < 2:
        raise GenerationRejected("program value < 2 cannot open a chain")

    # --- one op-sequence to max depth; rung d uses the prefix ops[:d]
    crng = random.Random(_dseed(seed, attempt, "chain"))
    _place, items = crng.choice(_SCENARIOS)
    chain_sents, chain_vals, chain_ops, _args = _build_ops(crng, program.value, max_depth, items)

    # --- bridges: chosen once, shared by every rung
    brng = random.Random(_dseed(seed, attempt, "bridges"))
    bridge_pc = brng.choice(_BRIDGES[("program_output", "arithmetic_chain")])
    bridge_ct = brng.choice(_BRIDGES[("arithmetic_chain", "table_aggregation")])

    # --- base tables: same (seed, attempt, shape) so all draws are identical
    # across rungs; only the injected first cell differs (the rung's chain value)
    builts: dict[int, _Built] = {}
    for d in rungs:
        builts[d] = _build_table(seed, attempt, PAIRED_VERSION, _REF_TABLE, chain_vals[d])
    base = builts[rungs[0]]
    for d in rungs[1:]:
        bt = builts[d]
        if bt.groups != base.groups or bt.units != base.units or bt.site != base.site:
            raise GenerationRejected("paired tables diverged in shape")

    # --- distractors: drawn once against the union of every rung's forbidden set
    forbidden: set[int] = set(chain_vals) | set(program.hidden_values)
    forbidden |= set(program.surface_numbers)
    for bt in builts.values():
        forbidden |= set(bt.hidden) | set(bt.surface)
    drng = random.Random(_dseed(seed, attempt, f"distractors|{distractors}"))
    day_sentence_count = _REF_TABLE.depth
    inserts: list[tuple[int, str]] = []  # (position, sentence), applied in order
    dvalues: list[int] = []
    for i in range(distractors):
        for _try in range(60):
            dv = drng.randint(3, 250)
            if dv not in forbidden and dv not in dvalues:
                break
        else:
            raise GenerationRejected("could not draw a non-colliding paired distractor")
        dvalues.append(dv)
        g = drng.choice(base.groups)
        template = drng.choice(_TABLE_DISTRACTORS)
        sentence = template.format(d=dv, g=g, units=base.units, site=base.site)
        inserts.append((drng.randint(1, day_sentence_count + i), sentence))

    # --- assemble one task per rung
    tasks: list[CompositeTask] = []
    for d in rungs:
        bt = builts[d]
        sentences = _split_sentences(bt.narration)
        for pos, sentence in inserts:
            sentences.insert(pos, sentence)
        table_text = " ".join(sentences)
        chain_text = " ".join(chain_sents[:d])
        prompt = (
            "\n\n".join([program.text.rstrip(), bridge_pc, chain_text, bridge_ct, table_text])
            + "\n\n"
            + bt.question
            + _INSTRUCTION
        )
        terminal = str(bt.diff)

        hidden = [*program.hidden_values, *chain_vals[: d + 1], *bt.hidden]
        check_no_decomposition_markers(prompt)
        check_values_hidden(prompt, hidden)

        difficulty_dict = {"depth": d, "distractors": distractors}
        task_id = _task_id(seed, difficulty_dict, prompt, terminal)
        segment_values = [program.value, chain_vals[d], bt.diff]
        nodes = tuple(
            CompositeNode(
                item=Item(
                    id=f"{FAMILY_NAME}::{task_id[-12:]}::seg{i}",
                    question="",
                    known_answer=value,
                    answer_type=AnswerType.INTEGER,
                    source=name,
                    source_version=PAIRED_VERSION,
                    metadata={},
                ),
                parameter_template=None,
                instantiated_question="",
            )
            for i, (name, value) in enumerate(
                zip(
                    ("program_output", "arithmetic_chain", "table_aggregation"),
                    segment_values,
                    strict=True,
                )
            )
        )
        tasks.append(
            CompositeTask(
                task_id=task_id,
                generator_version=PAIRED_VERSION,
                template_id=FAMILY_NAME,
                seed=seed,
                parameters={
                    "family": FAMILY_NAME,
                    "family_version": PAIRED_VERSION,
                    "recipe": {
                        "name": RECIPE,
                        "segments": ["program_output", "arithmetic_chain", "table_aggregation"],
                        "per_segment_difficulty": difficulty_dict,
                    },
                    "paired": {
                        "group_seed": seed,
                        "rung": d,
                        "rungs": rungs,
                        "max_depth": max_depth,
                        "ops": chain_ops[:d],
                    },
                    "program_text": program.text,
                    "chain_values": chain_vals[: d + 1],
                    "cells": bt.cells,
                    "totals": dict(bt.totals),
                    "distractor_values": dvalues,
                    "segment_values": segment_values,
                    "bucket": f"hybrid-paired_d{d}",
                },
                nodes=nodes,
                merged_prompt=prompt,
                canonical_terminal_answer=terminal,
                terminal_answer_type=AnswerType.INTEGER,
                v_star_input_tokens=count_tokens(prompt),
                v_star_output_tokens=count_tokens(terminal),
            )
        )
    return tasks


def _split_sentences(narration: str) -> list[str]:
    """Split a distractor-free table narration back into its day sentences."""

    parts = narration.split(". ")
    return [p if p.endswith(".") else p + "." for p in parts]


def _dseed(seed: int, attempt: int, scope: str) -> int:
    h = hashlib.sha256(f"{seed}|{attempt}|{PAIRED_VERSION}|{scope}".encode())
    return int.from_bytes(h.digest()[:8], "big")


def _task_id(seed: int, difficulty: dict[str, int], prompt: str, terminal: str) -> str:
    h = hashlib.sha256()
    for part in (
        FAMILY_NAME,
        PAIRED_VERSION,
        str(seed),
        repr(sorted(difficulty.items())),
        prompt,
        terminal,
    ):
        h.update(part.encode("utf-8"))
    return f"{FAMILY_NAME}::{PAIRED_VERSION}::{h.hexdigest()[:12]}"


__all__ = ["PAIRED_VERSION", "generate_paired_ladder"]
