"""Depth-ladder experiment with early stopping.

Rungs at depths 3, 6, 9, ... up to 30, five tasks per rung, distractors fixed at 2
so depth is the only axis that varies. The configs climb the ladder together, one
rung at a time, cheapest first within each rung. openai:gpt-5.4 with reasoning off,
which failed the original pre-flight probe, is included on purpose: the pruning
rules bound its spend, and its exit rung is itself a measurement. Moonshot configs
are excluded from the ladder for practical latency (slow to serve from the US);
any Moonshot rows already recorded in a resumed run are kept and reported.

Early stopping (the rules are pre-registered here, in code):
- A config is pruned at a rung if its accuracy there is <= STOP_ACCURACY (1 of 5):
  too wrong to keep paying for.
- A config is pruned at a rung if its mean efficiency on correct answers there is
  < STOP_EFFICIENCY: too wasteful to keep waiting for, whatever its accuracy.
- The whole climb stops when more than STOP_MAJORITY of the configs that started
  the rung are pruned at it: past that point deeper rungs mostly measure nothing.

Usage:
    python3 scripts/run_depth_ladder.py                      # fresh independent ladder
    python3 scripts/run_depth_ladder.py --paired             # fresh PAIRED ladder
    python3 scripts/run_depth_ladder.py [--paired] <run_dir> # resume either kind

Paired mode: each of the five groups is ONE underlying problem extended across
all rungs (same program, same table, same distractors, chain ops prefixed), so
depth is isolated per item; see families/paired_ladder.py for the invariants.

Fully resumable and safe to interrupt: results append per task, and on resume the
prune and stop decisions are recomputed from the recorded results, so an existing
ladder run picks up new configs and new rules without re-spending on finished work.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import re
import secrets
import statistics
import subprocess
import sys
from pathlib import Path

from token_efficiency_benchmark.evaluation.harness import evaluate_task
from token_efficiency_benchmark.evaluation.live_models import client_for_spec
from token_efficiency_benchmark.families.paired_ladder import (
    PAIRED_VERSION,
    generate_paired_ladder,
)
from token_efficiency_benchmark.serialization import (
    read_tasks_jsonl,
    result_to_dict,
    task_to_dict,
)

DEPTHS = list(range(3, 31, 3))
N_PER_CELL = 5
DISTRACTORS = 2
STOP_ACCURACY = 0.20
STOP_EFFICIENCY = 0.05
STOP_MAJORITY = 0.5
TIMEOUT_S = 300.0

MODELS = [  # cheapest first
    "openai:gpt-4.1-nano",
    "openai:gpt-5.4-nano",
    "anthropic:claude-haiku-4-5",
    "openai:gpt-5.4#effort=low",
    "openai:gpt-5.4",
    "openai:gpt-5.4#effort=medium",
    "anthropic:claude-opus-4-8",
    "anthropic:claude-sonnet-5",
    "openai:gpt-5.5",
    "anthropic:claude-fable-5",
]
TEB = [sys.executable, "-m", "token_efficiency_benchmark.cli"]


def create_run() -> str:
    cmd = [
        *TEB,
        "run",
        "--model",
        "echo",
        "--pricing",
        "pricing/prices.json",
        "--n",
        str(N_PER_CELL),
    ]
    for d in DEPTHS:
        cmd += ["--cell", f"{d}:{DISTRACTORS}"]
    out = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    print(out)
    m = re.search(r"benchmark_data/runs/\S+", out)
    if not m:
        raise SystemExit("could not find the run directory in teb output")
    return m.group(0).rstrip(".,")


def create_paired_run(run_seed: int | None) -> str:
    run_seed = run_seed if run_seed is not None else secrets.randbits(48)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = Path(f"benchmark_data/runs/{stamp}_{run_seed % 1_000_000:06d}-paired")
    run_dir.mkdir(parents=True, exist_ok=False)
    tasks = []
    for i in range(N_PER_CELL):
        h = hashlib.sha256(f"{run_seed}|group|{i}".encode())
        tasks.extend(
            generate_paired_ladder(int.from_bytes(h.digest()[:8], "big"), DEPTHS, DISTRACTORS)
        )
    with (run_dir / "tasks.jsonl").open("w", encoding="utf-8") as f:
        for t in tasks:
            f.write(json.dumps(task_to_dict(t), ensure_ascii=False) + "\n")
    manifest = {
        "run_id": run_dir.name,
        "paired": True,
        "family_version": PAIRED_VERSION,
        "run_seed": run_seed,
        "depths": DEPTHS,
        "groups": N_PER_CELL,
        "distractors": DISTRACTORS,
        "task_count": len(tasks),
        "replay": f"python3 scripts/run_depth_ladder.py --paired --run-seed {run_seed}",
        "note": "No echo fixture rows; the ideal floor is derivable from each task's v_star fields.",
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        f"Paired run {run_dir.name}: {len(tasks)} tasks ({N_PER_CELL} groups x {len(DEPTHS)} rungs)"
    )
    return str(run_dir)


def task_depth(task) -> int:  # type: ignore[no-untyped-def]
    return int(task.parameters["recipe"]["per_segment_difficulty"]["depth"])


def main() -> None:
    argv = sys.argv[1:]
    paired = "--paired" in argv
    if paired:
        argv.remove("--paired")
    run_seed: int | None = None
    if "--run-seed" in argv:
        i = argv.index("--run-seed")
        run_seed = int(argv[i + 1])
        del argv[i : i + 2]
    if argv:
        run_dir = Path(argv[0])
    else:
        run_dir = Path(create_paired_run(run_seed) if paired else create_run())
    tasks = list(read_tasks_jsonl(run_dir / "tasks.jsonl"))
    results_path = run_dir / "results.jsonl"
    print(f"== depth ladder: {run_dir} | rungs {DEPTHS} | {len(tasks)} tasks ==")

    done: dict[tuple[str, str], tuple[bool, float | None]] = {}
    if results_path.exists():
        for line in results_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                done[(rec["task_id"], rec["model"])] = (
                    bool(rec["terminal_correct"]),
                    rec.get("efficiency"),
                )

    clients: dict[str, object] = {}
    alive = list(MODELS)
    for depth in DEPTHS:
        rung = [t for t in tasks if task_depth(t) == depth]
        if not rung:
            continue
        print(f"\n==== rung depth={depth} | {len(alive)} configs alive ====", flush=True)
        acc: dict[str, float] = {}
        eff: dict[str, float | None] = {}
        for spec in alive:
            correct = total = 0
            effs: list[float] = []
            for task in rung:
                key = (task.task_id, spec)
                if key not in done:
                    client = clients.setdefault(spec, client_for_spec(spec, timeout_s=TIMEOUT_S))
                    try:
                        r = evaluate_task(task, client)  # type: ignore[arg-type]
                    except Exception as e:  # transient API error: retry on resume
                        print(
                            f"[skip] {spec} {task.task_id[-12:]}: {type(e).__name__}",
                            file=sys.stderr,
                        )
                        continue
                    with results_path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(result_to_dict(r), ensure_ascii=False) + "\n")
                    done[key] = (r.terminal_correct, r.efficiency)
                ok, e = done[key]
                correct += ok
                total += 1
                if e is not None:
                    effs.append(e)
            acc[spec] = correct / total if total else 0.0
            eff[spec] = statistics.fmean(effs) if effs else None
            eff_s = f"{eff[spec]:.3f}" if eff[spec] is not None else "n/a"
            print(f"  {spec:38s} acc@d{depth} = {acc[spec]:.2f}  eff = {eff_s}")

        pruned: dict[str, str] = {}
        for m in alive:
            if acc.get(m, 0.0) <= STOP_ACCURACY:
                pruned[m] = f"accuracy {acc.get(m, 0.0):.2f} <= {STOP_ACCURACY}"
            elif eff.get(m) is not None and eff[m] < STOP_EFFICIENCY:  # type: ignore[operator]
                pruned[m] = f"efficiency {eff[m]:.3f} < {STOP_EFFICIENCY}"
        for m, why in pruned.items():
            print(f"  [prune] {m}: {why}, dropped from deeper rungs")
        if len(pruned) / max(len(alive), 1) > STOP_MAJORITY:
            print(f"\n==== EARLY STOP after depth {depth}: {len(pruned)}/{len(alive)} pruned ====")
            break
        alive = [m for m in alive if m not in pruned]
        if not alive:
            print(f"\n==== EARLY STOP after depth {depth}: no configs alive ====")
            break

    subprocess.run(
        [*TEB, "compare", "--results", str(results_path), "--pricing", "pricing/prices.json"]
    )


if __name__ == "__main__":
    main()
