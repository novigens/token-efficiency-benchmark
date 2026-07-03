"""Program-output family (design_v2.md §4.2, examples_v2.md §B).

Generates a small integer program from a restricted grammar (assignments,
bounded ``for`` loops, parity conditionals, one final ``print``), renders it
as source text, and computes ground truth by **interpreting the program**
under a hard step budget. The step budget makes termination a generation-time
guarantee: an instance that exceeds it raises :class:`GenerationRejected`.

The family is P-complete territory by design: there is no shortcut around
effectively simulating the computation, so required internal work scales with
program size (design_v2.md §2).

Composable: a program segment can open a hybrid task; it cannot consume an
upstream value in 2.x (raises GenerationRejected — the typed-joint rule).
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

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

FAMILY_NAME = "program_output"
FAMILY_VERSION = "2.0.0"

_VALUE_CAP = 10_000_000
_STEP_BUDGET = 10_000
_MAX_ATTEMPTS = 25

_VARS = ("x", "y", "z")
_OPS = ("+", "-", "*")


# ----------------------------------------------------------------------
# Program representation (tiny AST, interpreted directly — never exec()ed)


@dataclass(frozen=True)
class _Stmt:
    target: str
    op: str  # + - *
    operand_var: str | None  # None => constant operand
    operand_const: int
    guard_even: str | None = None  # if set: run only when var is even
    dead: bool = False  # rendered under an unreachable guard


@dataclass(frozen=True)
class _Loop:
    count: int
    body: tuple[_Stmt, ...]


@dataclass(frozen=True)
class _Program:
    inits: tuple[tuple[str, int], ...]
    loops: tuple[_Loop, ...]
    final_op: str
    final_left: str
    final_const: int


def execute_program(program: _Program, budget: int = _STEP_BUDGET) -> int:
    """Interpret the program with a hard step budget (§B obligation)."""

    env = dict(program.inits)
    steps = 0

    def run_stmt(stmt: _Stmt) -> None:
        nonlocal steps
        steps += 1
        if steps > budget:
            raise GenerationRejected(f"step budget {budget} exceeded during execution")
        if stmt.dead:
            return  # unreachable guard: rendered but never executed
        if stmt.guard_even is not None and env[stmt.guard_even] % 2 != 0:
            return
        operand = env[stmt.operand_var] if stmt.operand_var is not None else stmt.operand_const
        v = env[stmt.target]
        if stmt.op == "+":
            v = v + operand
        elif stmt.op == "-":
            v = v - operand
        else:
            v = v * operand
        if abs(v) > _VALUE_CAP:
            raise GenerationRejected("value overflow during execution")
        env[stmt.target] = v

    for loop in program.loops:
        if loop.count > budget:
            raise GenerationRejected(f"loop bound {loop.count} exceeds step budget {budget}")
        for _ in range(loop.count):
            for stmt in loop.body:
                run_stmt(stmt)

    left = env[program.final_left]
    if program.final_op == "+":
        return left + program.final_const
    if program.final_op == "-":
        return left - program.final_const
    return left * program.final_const


def render_source(program: _Program) -> str:
    lines: list[str] = [f"{v} = {k}" for v, k in program.inits]
    for loop in program.loops:
        lines.append(f"for i in range({loop.count}):")
        for stmt in loop.body:
            operand = stmt.operand_var if stmt.operand_var is not None else str(stmt.operand_const)
            body_line = f"{stmt.target} = {stmt.target} {stmt.op} {operand}"
            if stmt.dead:
                lines.append("    if 0 > 1:")
                lines.append(f"        {body_line}")
            elif stmt.guard_even is not None:
                lines.append(f"    if {stmt.guard_even} % 2 == 0:")
                lines.append(f"        {body_line}")
            else:
                lines.append(f"    {body_line}")
    lines.append(f"print({program.final_left} {program.final_op} {program.final_const})")
    return "\n".join(lines)


def _source_literals(program: _Program) -> set[int]:
    lits = {v for _, v in program.inits}
    for loop in program.loops:
        lits.add(loop.count)
        for stmt in loop.body:
            if stmt.operand_var is None:
                lits.add(stmt.operand_const)
            if stmt.dead:
                lits.update({0, 1})
            if stmt.guard_even is not None:
                lits.update({2, 0})
    lits.add(program.final_const)
    return lits


_PROMPT_TEMPLATE = (
    "Consider this program:\n\n```\n{src}\n```\n\n"
    "What does this program print?\n\nAnswer with a single integer."
)


class ProgramOutputFamily(TaskFamily, Composable):
    name = FAMILY_NAME
    version = FAMILY_VERSION

    def difficulty_axes(self) -> dict[str, str]:
        return {
            "depth": "number of loop-body statements across all loops (>= 2)",
            "distractors": "dead-code statements rendered under unreachable guards",
            "step_budget": f"hard interpreter budget ({_STEP_BUDGET}, fixed in 2.0.0)",
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
        if upstream is not None:
            raise GenerationRejected(
                "program_output cannot consume an upstream value in 2.x "
                "(typed-joint rule: no implicit coercion)"
            )
        program, printed = self._draw_valid_program(seed, difficulty)
        src = render_source(program)
        text = f"A control script runs on the site's terminal each morning:\n\n```\n{src}\n```\n"
        return Segment(
            text=text,
            value=printed,
            output_type=AnswerType.INTEGER.value,
            hidden_values=(printed,),
            surface_numbers=tuple(sorted(_source_literals(program))),
            question="What does the script print?",
            meta={"source": src},
        )

    # ---------------------------------------------------------------- internal

    def _draw_valid_program(self, seed: int, difficulty: DifficultyParams) -> tuple[_Program, int]:
        last: GenerationRejected | None = None
        for attempt in range(_MAX_ATTEMPTS):
            program = _draw_program(seed, attempt, self.version, difficulty)
            try:
                printed = execute_program(program)
            except GenerationRejected as e:
                last = e
                continue
            if abs(printed) > _VALUE_CAP:
                last = GenerationRejected("printed value overflow")
                continue
            if printed in _source_literals(program):
                # §B: the printed value must not appear as a literal in source
                last = GenerationRejected("printed value collides with source literal")
                continue
            return program, printed
        raise GenerationRejected(
            f"no valid program after {_MAX_ATTEMPTS} attempts (seed={seed}): {last}"
        )

    def _generate_once(
        self, seed: int, attempt: int, difficulty: DifficultyParams
    ) -> CompositeTask:
        program, printed = self._draw_valid_program(seed + attempt * 1009, difficulty)
        src = render_source(program)
        prompt = _PROMPT_TEMPLATE.format(src=src)
        terminal = str(printed)

        check_no_decomposition_markers(prompt)
        check_values_hidden(prompt, [printed])

        difficulty_dict = {
            "depth": difficulty.depth,
            "distractors": difficulty.distractors,
        }
        task_id = _task_id(seed, difficulty_dict, prompt, terminal)
        node = CompositeNode(
            item=Item(
                id=f"{FAMILY_NAME}::{task_id[-12:]}::program",
                question=src,
                known_answer=printed,
                answer_type=AnswerType.INTEGER,
                source=FAMILY_NAME,
                source_version=FAMILY_VERSION,
                metadata={},
            ),
            parameter_template=None,
            instantiated_question="",
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
                "source": src,
                "printed": printed,
                "bucket": f"prog_d{difficulty.depth}",
            },
            nodes=(node,),
            merged_prompt=prompt,
            canonical_terminal_answer=terminal,
            terminal_answer_type=AnswerType.INTEGER,
            v_star_input_tokens=count_tokens(prompt),
            v_star_output_tokens=count_tokens(terminal),
        )


def _draw_program(seed: int, attempt: int, version: str, difficulty: DifficultyParams) -> _Program:
    # Program-shape RNG excludes distractors so the dead-code axis is orthogonal.
    rng = random.Random(_derive_seed(seed, attempt, version, f"prog|{difficulty.depth}"))
    dead_rng = random.Random(
        _derive_seed(
            seed,
            attempt,
            version,
            f"dead|{difficulty.depth}|{difficulty.distractors}",
        )
    )

    n_vars = rng.choice((2, 3))
    variables = _VARS[:n_vars]
    inits = tuple((v, rng.randint(2, 9)) for v in variables)

    remaining = difficulty.depth
    loops: list[_Loop] = []
    while remaining > 0:
        body_n = min(remaining, rng.choice((1, 2)))
        remaining -= body_n
        body: list[_Stmt] = []
        for _ in range(body_n):
            target = rng.choice(variables)
            op = rng.choice(_OPS)
            if op == "*":
                operand_var, operand_const = None, rng.randint(2, 3)
            elif rng.random() < 0.5:
                operand_var = rng.choice([v for v in variables if v != target])
                operand_const = 0
            else:
                operand_var, operand_const = None, rng.randint(2, 9)
            guard = rng.choice(variables) if rng.random() < 0.35 else None
            body.append(
                _Stmt(
                    target=target,
                    op=op,
                    operand_var=operand_var,
                    operand_const=operand_const,
                    guard_even=guard,
                )
            )
        loops.append(_Loop(count=rng.randint(2, 4), body=tuple(body)))

    # Dead-code distractors: appended into random loops, never executed.
    for _ in range(difficulty.distractors):
        idx = dead_rng.randrange(len(loops))
        loop = loops[idx]
        dead = _Stmt(
            target=dead_rng.choice(variables),
            op=dead_rng.choice(_OPS),
            operand_var=None,
            operand_const=dead_rng.randint(2, 9),
            dead=True,
        )
        loops[idx] = _Loop(count=loop.count, body=(*loop.body, dead))

    final_left = rng.choice(variables)
    return _Program(
        inits=inits,
        loops=tuple(loops),
        final_op=rng.choice(("+", "-", "*")),
        final_left=final_left,
        final_const=rng.randint(1, 9),
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


__all__ = [
    "ProgramOutputFamily",
    "execute_program",
    "render_source",
]
