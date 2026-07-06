"""Command-line interface.

Five subcommands:

- ``teb run`` — burn-after-reading evaluation: fresh questions, manifest,
  results, scores (the primary entry point; default family: hybrid).
- ``teb generate`` — emit tasks to a JSONL file.
- ``teb evaluate`` — run a model over a task file (fixtures or
  moonshot:/openai:/anthropic: live clients).
- ``teb score`` — aggregate results; ``--pricing`` adds $/correct and waste.
- ``teb compare`` — leaderboard, difficulty pivots, cost decomposition.
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from . import GENERATOR_VERSION, __version__
from .evaluation.harness import evaluate_tasks
from .evaluation.models import EchoModel, VerboseEchoModel, WrongEchoModel
from .evaluation.scoring import aggregate_results, format_report_table
from .serialization import (
    read_results_jsonl,
    read_tasks_jsonl,
    write_results_jsonl,
    write_tasks_jsonl,
)


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Token Efficiency Benchmark CLI."""


@main.command()
@click.option(
    "--family",
    type=click.Choice(
        ["hybrid", "arithmetic_chain", "program_output", "table_aggregation"],
        case_sensitive=False,
    ),
    default="hybrid",
    show_default=True,
    help="Task family.",
)
@click.option(
    "--recipe",
    type=str,
    default="prog+chain+table",
    show_default=True,
    help="Hybrid recipe (hybrid family only).",
)
@click.option("--depth", type=int, required=True, help="Chain depth (>= 2).")
@click.option(
    "--distractors",
    type=int,
    default=0,
    show_default=True,
    help="Irrelevant numeric sentences per task.",
)
@click.option("--n", type=int, required=True, help="Number of tasks to generate.")
@click.option("--seed", type=int, default=42, show_default=True)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    required=True,
    help="Output JSONL path.",
)
def generate(
    family: str,
    recipe: str,
    depth: int,
    distractors: int,
    n: int,
    seed: int,
    out: Path,
) -> None:
    """Generate composite tasks and write them to a JSONL file."""

    from .families import FAMILIES, DifficultyParams, HybridFamily

    fam = HybridFamily(recipe=recipe) if family.lower() == "hybrid" else FAMILIES[family.lower()]()
    difficulty = DifficultyParams(depth=depth, distractors=distractors)
    tasks = (fam.generate(seed + i * 2027, difficulty) for i in range(n))
    count = write_tasks_jsonl(tasks, out)
    click.echo(
        f"Generated {count} tasks (family={family} v{fam.version}, "
        f"depth={depth}, distractors={distractors}, seed={seed}) → {out}"
    )


@main.command()
@click.option(
    "--tasks",
    type=click.Path(path_type=Path, exists=True),
    required=True,
    help="Task JSONL produced by `teb generate`.",
)
@click.option(
    "--model",
    type=str,
    default="echo",
    show_default=True,
    help=(
        "Fixture: echo | verbose_echo | wrong_echo. "
        "Live: moonshot:<id> | openai:<id> | anthropic:<id>. "
        "Live clients need the provider package installed and the matching "
        "MOONSHOT_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY in the environment."
    ),
)
@click.option(
    "--out",
    type=click.Path(path_type=Path),
    required=True,
    help="Output results JSONL path.",
)
def evaluate(tasks: Path, model: str, out: Path) -> None:
    """Run a model over generated tasks and write per-task results."""

    task_list = list(read_tasks_jsonl(tasks))
    answer_lookup = {t.task_id: t.canonical_terminal_answer for t in task_list}

    client: object
    if model == "echo":
        client = EchoModel(answer_lookup)
    elif model == "verbose_echo":
        client = VerboseEchoModel(answer_lookup, padding_tokens=200)
    elif model == "wrong_echo":
        client = WrongEchoModel()
    elif model.startswith("openai:"):
        from .evaluation.live_models import OpenAIClient

        client = OpenAIClient(model=model.split(":", 1)[1])
    elif model.startswith("anthropic:"):
        from .evaluation.live_models import AnthropicClient

        client = AnthropicClient(model=model.split(":", 1)[1])
    elif model.startswith("moonshot:"):
        from .evaluation.live_models import MoonshotClient

        client = MoonshotClient(model=model.split(":", 1)[1])
    else:
        raise click.BadParameter(
            f"unknown model '{model}'. Use echo | verbose_echo | wrong_echo "
            "| openai:<id> | anthropic:<id> | moonshot:<id>."
        )

    results = evaluate_tasks(task_list, client)  # type: ignore[arg-type]
    count = write_results_jsonl(results, out)
    click.echo(f"Evaluated {count} tasks with model '{model}' → {out}")


@main.command()
@click.option(
    "--results",
    type=click.Path(path_type=Path, exists=True),
    required=True,
    help="Results JSONL produced by `teb evaluate`.",
)
@click.option(
    "--pricing",
    type=click.Path(path_type=Path, exists=True),
    default=None,
    help="Price-sheet JSON ($/Mtok); adds the $/correct + waste table.",
)
@click.option(
    "--json",
    "json_out",
    is_flag=True,
    default=False,
    help="Emit aggregated reports as JSON instead of the table view.",
)
def score(results: Path, pricing: Path | None, json_out: bool) -> None:
    """Aggregate per-task results into a summary."""

    result_list = list(read_results_jsonl(results))
    reports = aggregate_results(result_list)
    if pricing is not None and not json_out:
        from .evaluation.pricing import (
            dollars_summary,
            format_dollars_table,
            load_price_sheet,
        )

        sheet = load_price_sheet(pricing)
        click.echo(format_dollars_table(dollars_summary(result_list, sheet)))
    if json_out:
        click.echo(
            json.dumps(
                [
                    {
                        "model": r.model,
                        "difficulty_bucket": r.difficulty_bucket,
                        "n": r.n,
                        "accuracy": r.accuracy,
                        "mean_efficiency_when_correct": r.mean_efficiency_when_correct,
                        "expected_value_ratio": r.expected_value_ratio,
                        "efficiency_stddev": r.efficiency_stddev,
                        "mean_input_tokens": r.mean_input_tokens,
                        "mean_output_tokens": r.mean_output_tokens,
                        "generator_version": GENERATOR_VERSION,
                    }
                    for r in reports
                ],
                indent=2,
            )
        )
    else:
        click.echo(format_report_table(reports))


@main.command()
@click.option(
    "--results",
    "results_paths",
    type=click.Path(path_type=Path, exists=True),
    multiple=True,
    required=True,
    help="Results JSONL file(s); pass multiple to merge runs/models.",
)
@click.option(
    "--pricing",
    type=click.Path(path_type=Path, exists=True),
    default=None,
    help="Price-sheet JSON; enables the $/correct views.",
)
@click.option(
    "--business",
    is_flag=True,
    default=False,
    help="Append the business view: risk-adjusted $/correct with gates (needs --pricing).",
)
@click.option(
    "--beta",
    type=float,
    default=0.8,
    show_default=True,
    help="Business-view penalty base: multiplier is beta**(k^2), k = wrong per 20 tasks.",
)
@click.option(
    "--eff-gate",
    type=float,
    default=0.05,
    show_default=True,
    help="Business-view efficiency gate: configs below this mean efficiency are flagged.",
)
def compare(
    results_paths: tuple[Path, ...],
    pricing: Path | None,
    business: bool,
    beta: float,
    eff_gate: float,
) -> None:
    """Model-vs-model comparison: leaderboard, difficulty pivots, cost decomposition."""

    from .evaluation.pricing import load_price_sheet
    from .evaluation.reporting import format_comparison
    from .types import TaskResult

    results: list[TaskResult] = []
    for p in results_paths:
        results.extend(read_results_jsonl(p))
    sheet = load_price_sheet(pricing) if pricing else None
    click.echo(format_comparison(results, sheet, business=business, beta=beta, eff_gate=eff_gate))


@main.command()
@click.option(
    "--model",
    "models",
    type=str,
    multiple=True,
    required=True,
    help="Model spec, repeatable (echo | moonshot:<id> | openai:<id> | anthropic:<id>).",
)
@click.option(
    "--cell",
    "cells",
    type=str,
    multiple=True,
    default=("3:1", "6:3"),
    show_default=True,
    help="depth:distractors, repeatable. Default is the starter ladder; "
    "the full ladder for publication runs is 3:0 6:2 10:2 14:5 with --n 25.",
)
@click.option("--n", type=int, default=10, show_default=True, help="Tasks per cell.")
@click.option(
    "--family",
    type=click.Choice(
        ["hybrid", "arithmetic_chain", "program_output", "table_aggregation"],
        case_sensitive=False,
    ),
    default="hybrid",
    show_default=True,
    help="Task family for the run.",
)
@click.option(
    "--recipe",
    type=str,
    default="prog+chain+table",
    show_default=True,
    help="Hybrid recipe (hybrid family only).",
)
@click.option(
    "--run-seed",
    type=int,
    default=None,
    help="Only for replaying a documented run. Omit for a fresh entropy draw.",
)
@click.option(
    "--pricing",
    type=click.Path(path_type=Path, exists=True),
    default=None,
    help="Price-sheet JSON for the $/correct table.",
)
@click.option(
    "--out-dir",
    type=click.Path(path_type=Path),
    default=Path("benchmark_data/runs"),
    show_default=True,
)
def run(
    models: tuple[str, ...],
    cells: tuple[str, ...],
    n: int,
    family: str,
    recipe: str,
    run_seed: int | None,
    pricing: Path | None,
    out_dir: Path,
) -> None:
    """Burn-after-reading evaluation run (design_v2.md §1.2).

    Tasks are regenerated at runtime from a fresh entropy-drawn seed, so every
    run gets different questions. The run directory documents everything
    needed for third-party replay: manifest (family version, run seed, cells),
    the exact tasks, and the raw results.
    """

    import datetime
    import secrets

    from .evaluation.scoring import DEFAULT_WEIGHTS
    from .families import FAMILIES, DifficultyParams, HybridFamily

    fam = HybridFamily(recipe=recipe) if family.lower() == "hybrid" else FAMILIES[family.lower()]()
    fresh = run_seed is None
    seed0: int = secrets.randbits(48) if run_seed is None else run_seed
    stamp = datetime.datetime.now(datetime.timezone.utc)
    run_id = f"{stamp.strftime('%Y%m%dT%H%M%SZ')}_{seed0 % 1_000_000:06d}"
    run_dir = Path(out_dir) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    parsed_cells = []
    for spec in cells:
        depth_s, dist_s = spec.split(":")
        parsed_cells.append((int(depth_s), int(dist_s)))

    # Generate fresh tasks at runtime
    tasks = []
    for c_idx, (depth, distractors) in enumerate(parsed_cells):
        difficulty = DifficultyParams(depth=depth, distractors=distractors)
        for i in range(n):
            task_seed = seed0 + c_idx * 100_003 + i * 2_027
            tasks.append(fam.generate(task_seed, difficulty))
    write_tasks_jsonl(tasks, run_dir / "tasks.jsonl")

    manifest = {
        "run_id": run_id,
        "created_at": stamp.isoformat(),
        "family": fam.name,
        "family_version": fam.version,
        "run_seed": seed0,
        "seed_was_fresh_entropy": fresh,
        "cells": [{"depth": d, "distractors": k} for d, k in parsed_cells],
        "n_per_cell": n,
        "recipe": recipe if family.lower() == "hybrid" else None,
        "models": list(models),
        "weights": list(DEFAULT_WEIGHTS),
        "task_count": len(tasks),
        "replay": (
            f"teb run --family {fam.name} --run-seed {seed0} "
            + " ".join(f"--cell {d}:{k}" for d, k in parsed_cells)
            + f" --n {n} "
            + " ".join(f"--model {m}" for m in models)
        ),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    click.echo(f"Run {run_id}: {len(tasks)} fresh tasks → {run_dir}")

    # Evaluate each model
    all_results = []
    answer_lookup = {t.task_id: t.canonical_terminal_answer for t in tasks}
    for model in models:
        if model == "echo":
            client: object = EchoModel(answer_lookup)
        elif model == "verbose_echo":
            client = VerboseEchoModel(answer_lookup, padding_tokens=200)
        elif model == "wrong_echo":
            client = WrongEchoModel()
        elif model.startswith("openai:"):
            from .evaluation.live_models import OpenAIClient

            client = OpenAIClient(model=model.split(":", 1)[1])
        elif model.startswith("anthropic:"):
            from .evaluation.live_models import AnthropicClient

            client = AnthropicClient(model=model.split(":", 1)[1])
        elif model.startswith("moonshot:"):
            from .evaluation.live_models import MoonshotClient

            client = MoonshotClient(model=model.split(":", 1)[1])
        else:
            raise click.BadParameter(f"unknown model '{model}'")
        click.echo(f"Evaluating {model} ...")
        results = evaluate_tasks(tasks, client)  # type: ignore[arg-type]
        all_results.extend(results)

    write_results_jsonl(all_results, run_dir / "results.jsonl")
    click.echo(format_report_table(aggregate_results(all_results)))
    if pricing is not None:
        from .evaluation.pricing import (
            dollars_summary,
            format_dollars_table,
            load_price_sheet,
        )

        sheet = load_price_sheet(pricing)
        click.echo(format_dollars_table(dollars_summary(all_results, sheet)))


if __name__ == "__main__":  # pragma: no cover
    main()
