"""Multi-model comparison reporting.

Three views (in order of audience):

1. Leaderboard — one row per model, sorted by $/correct (unpriced models
   last, by EVR). The buyer's decision table.
2. Model x difficulty pivots — degradation curves read left-to-right.
   One matrix per metric: accuracy, efficiency, $/correct.
3. Cost decomposition — least-squares fit of output tokens vs depth per
   model: fixed thinking overhead (intercept) + marginal per-step cost
   (slope). Two numbers that characterize a model's cost behavior.

Dollars are the only cross-provider unit: token counts are not comparable
across tokenizers, but each provider's tokens x its own prices normalize.
"""

from __future__ import annotations

import re
import statistics
from collections import defaultdict
from collections.abc import Iterable

from ..types import TaskResult
from .pricing import waste_ratio

_M = 1_000_000.0


def _bucket_order(bucket: str) -> int:
    """Trailing integer of the bucket label (``depth_6`` -> 6, ``..._d3`` -> 3)."""

    m = re.search(r"(\d+)$", bucket)
    return int(m.group(1)) if m else 0


def _spend(r: TaskResult, prices: dict[str, float]) -> float:
    return r.input_tokens * prices["in"] / _M + r.output_tokens * prices["out"] / _M


def format_leaderboard(
    results: Iterable[TaskResult],
    sheet: dict[str, dict[str, float]] | None = None,
) -> str:
    sheet = sheet or {}
    by_model: dict[str, list[TaskResult]] = defaultdict(list)
    for r in results:
        by_model[r.model].append(r)

    rows = []
    for model, group in by_model.items():
        n = len(group)
        correct = [r for r in group if r.terminal_correct]
        acc = len(correct) / n
        effs = [r.efficiency for r in group if r.efficiency is not None]
        eff = statistics.fmean(effs) if effs else 0.0
        waste = statistics.fmean(waste_ratio(r) for r in correct) if correct else None
        out_tok = statistics.fmean(r.output_tokens for r in group)
        prices = sheet.get(model)
        if prices and correct:
            per_correct = sum(_spend(r, prices) for r in group) / len(correct)
        else:
            per_correct = None
        rows.append((model, n, acc, eff, per_correct, waste, out_tok))

    # priced models first sorted by $/correct, then unpriced by EVR desc
    rows.sort(key=lambda r: (r[4] is None, r[4] if r[4] is not None else -(r[2] * r[3])))
    name_w = max([len("model"), *(len(m) for m in by_model)]) + 2
    header = (
        f"{'model':<{name_w}} {'n':>5} {'acc':>6} {'$/correct':>11} "
        f"{'waste x':>8} {'eff':>6} {'out_tok':>8}\n"
    )
    lines = ["== Leaderboard (sorted by $/correct) ==\n", header, "-" * len(header) + "\n"]
    for model, n, acc, eff, per_correct, waste, out_tok in rows:
        pc = f"{per_correct:.5f}" if per_correct is not None else "unpriced"
        wa = f"{waste:.1f}" if waste is not None else "n/a"
        lines.append(
            f"{model:<{name_w}} {n:>5d} {acc:>6.3f} {pc:>11} {wa:>8} {eff:>6.3f} {out_tok:>8.0f}\n"
        )
    return "".join(lines)


def format_pivots(
    results: Iterable[TaskResult],
    sheet: dict[str, dict[str, float]] | None = None,
) -> str:
    sheet = sheet or {}
    results = list(results)
    buckets = sorted({r.difficulty_bucket for r in results}, key=_bucket_order)
    models = sorted({r.model for r in results})
    cell: dict[tuple[str, str], list[TaskResult]] = defaultdict(list)
    for r in results:
        cell[(r.model, r.difficulty_bucket)].append(r)

    def metric_value(metric: str, group: list[TaskResult], model: str) -> str:
        if not group:
            return "-"
        if metric == "accuracy":
            return f"{sum(r.terminal_correct for r in group) / len(group):.3f}"
        if metric == "efficiency":
            effs = [r.efficiency for r in group if r.efficiency is not None]
            return f"{statistics.fmean(effs):.3f}" if effs else "n/a"
        if metric == "$/correct":
            prices = sheet.get(model)
            n_correct = sum(r.terminal_correct for r in group)
            if not prices or not n_correct:
                return "n/a"
            return f"{sum(_spend(r, prices) for r in group) / n_correct:.5f}"
        raise ValueError(metric)

    metrics = ["accuracy", "efficiency"] + (["$/correct"] if sheet else [])
    out: list[str] = []
    width = max((len(m) for m in models), default=10) + 2
    col_w = max([11, *(len(b) + 2 for b in buckets)])
    for metric in metrics:
        out.append(f"\n== {metric} by difficulty ==\n")
        out.append(f"{'model':<{width}}" + "".join(f"{b:>{col_w}}" for b in buckets) + "\n")
        for model in models:
            row = [f"{model:<{width}}"]
            for b in buckets:
                row.append(f"{metric_value(metric, cell[(model, b)], model):>{col_w}}")
            out.append("".join(row) + "\n")
    return "".join(out)


def format_cost_decomposition(results: Iterable[TaskResult]) -> str:
    """Per model: out_tokens ~= base + rate * depth (least squares over tasks)."""

    by_model: dict[str, list[TaskResult]] = defaultdict(list)
    for r in results:
        by_model[r.model].append(r)

    name_w = max([len("model"), *(len(m) for m in by_model)]) + 2
    header = f"{'model':<{name_w}} {'base out_tok':>13} {'per-step':>9} {'n':>5}\n"
    lines = [
        "\n== Cost decomposition: out_tok = base + rate x depth ==\n",
        header,
        "-" * len(header) + "\n",
    ]
    for model, group in sorted(by_model.items()):
        pts = [(_bucket_order(r.difficulty_bucket), r.output_tokens) for r in group]
        depths = {d for d, _ in pts}
        if len(depths) < 2:
            lines.append(f"{model:<{name_w}} {'(needs >=2 depths)':>13}\n")
            continue
        n = len(pts)
        mx = sum(d for d, _ in pts) / n
        my = sum(t for _, t in pts) / n
        sxx = sum((d - mx) ** 2 for d, _ in pts)
        sxy = sum((d - mx) * (t - my) for d, t in pts)
        rate = sxy / sxx if sxx else 0.0
        base = my - rate * mx
        lines.append(f"{model:<{name_w}} {base:>13.0f} {rate:>9.1f} {n:>5d}\n")
    return "".join(lines)


def format_comparison(
    results: Iterable[TaskResult],
    sheet: dict[str, dict[str, float]] | None = None,
) -> str:
    results = list(results)
    return (
        format_leaderboard(results, sheet)
        + format_pivots(results, sheet)
        + format_cost_decomposition(results)
    )
