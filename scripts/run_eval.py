"""Resumable concurrent evaluator.

Usage: python3 scripts/run_eval.py <run_dir> <model_spec> [workers=1] [timeout_s=300]

Reads <run_dir>/tasks.jsonl, skips (task, model) pairs already present in
<run_dir>/results.jsonl (resume), evaluates the rest concurrently, and
appends each result as it completes (checkpoint). Per-task failures
(timeouts, transient API errors) are logged and skipped — the task stays
pending for the next invocation. Re-run the same command until it prints
DONE.
"""

from __future__ import annotations

import contextlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from token_efficiency_benchmark.evaluation.harness import evaluate_task
from token_efficiency_benchmark.evaluation.live_models import client_for_spec
from token_efficiency_benchmark.serialization import (
    read_tasks_jsonl,
    result_to_dict,
)

DEFAULT_TIMEOUT_S = 300.0  # thinking models can legitimately take minutes

try:  # POSIX advisory lock so parallel evaluators can share results.jsonl
    import fcntl

    @contextlib.contextmanager
    def _locked(f):  # type: ignore[no-untyped-def]
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
except ImportError:  # Windows: single-writer only

    @contextlib.contextmanager
    def _locked(f):  # type: ignore[no-untyped-def]
        yield


def make_client(spec: str, timeout_s: float) -> object:
    return client_for_spec(spec, timeout_s=timeout_s)


def main() -> None:
    if len(sys.argv) < 3:
        print(
            "usage: python3 scripts/run_eval.py <run_dir> <model_spec> "
            "[workers=1] [timeout_s=300]\n"
            "hint: fewer than 2 args received — if you passed $RUN, it may be "
            "unset in this shell.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    run_dir = Path(sys.argv[1])
    spec = sys.argv[2]
    if not (run_dir / "tasks.jsonl").exists():
        print(f"error: {run_dir / 'tasks.jsonl'} not found — check <run_dir>.", file=sys.stderr)
        raise SystemExit(2)
    workers = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    timeout_s = float(sys.argv[4]) if len(sys.argv) > 4 else DEFAULT_TIMEOUT_S

    tasks = list(read_tasks_jsonl(run_dir / "tasks.jsonl"))
    results_path = run_dir / "results.jsonl"
    done_ids: set[tuple[str, str]] = set()
    if results_path.exists():
        for line in results_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                done_ids.add((rec["task_id"], rec["model"]))

    todo = [t for t in tasks if (t.task_id, spec) not in done_ids]
    print(
        f"{spec}: {len(tasks)} tasks, {len(tasks) - len(todo)} done, "
        f"{len(todo)} to go (workers={workers}, timeout={timeout_s:.0f}s)"
    )
    if not todo:
        print("DONE")
        return

    client = make_client(spec, timeout_s)
    started = time.time()
    completed = 0
    failed = 0
    pool = ThreadPoolExecutor(max_workers=workers)
    try:
        with results_path.open("a", encoding="utf-8") as f:
            futures = {pool.submit(evaluate_task, t, client): t for t in todo}  # type: ignore[arg-type]
            for fut in as_completed(futures):
                task = futures[fut]
                try:
                    r = fut.result()
                except Exception as e:  # timeout / transient API error: retry next pass
                    failed += 1
                    print(
                        f"\n[skip] {task.task_id[-16:]}: {type(e).__name__}: {e}",
                        file=sys.stderr,
                    )
                    continue
                with _locked(f):
                    f.write(json.dumps(result_to_dict(r), ensure_ascii=False) + "\n")
                    f.flush()
                completed += 1
                elapsed = time.time() - started
                rate = completed / elapsed
                eta = (len(todo) - completed - failed) / rate if rate > 0 else 0
                print(
                    f"\r{completed}/{len(todo)} done"
                    f"{f', {failed} to retry' if failed else ''}"
                    f" | {elapsed:.0f}s elapsed, ~{eta:.0f}s left ",
                    end="",
                    flush=True,
                )
    except KeyboardInterrupt:
        # Exit promptly: cancel queued work, don't wait for in-flight calls.
        print("\ninterrupted — progress is checkpointed; re-run to resume.")
        pool.shutdown(wait=False, cancel_futures=True)
        raise SystemExit(130) from None
    pool.shutdown(wait=True)
    print()
    if failed:
        print(f"{failed} task(s) failed this pass — re-run the same command to retry them.")
    else:
        print("DONE" if completed == len(todo) else "re-run to continue")


if __name__ == "__main__":
    main()
