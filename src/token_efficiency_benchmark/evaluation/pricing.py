"""Pricing layer: dollars per correct outcome and waste ratio.

Implements design_v2.md §6 / examples_v2.md §E. A price sheet is a versioned
JSON file mapping result-model identifiers (e.g. ``moonshot:kimi-k2.5``) to
dollars per **million** tokens::

    {
      "moonshot:kimi-k2.5": {"in": 0.60, "out": 3.00},
      ...
    }

Raw token counts always survive in the results file, so any other sheet can
re-price the same run retrospectively.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ..types import TaskResult

_M = 1_000_000.0


def load_price_sheet(path: Path) -> dict[str, dict[str, float]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        model: {"in": float(p["in"]), "out": float(p["out"])}
        for model, p in data.items()
        if not model.startswith("_")
    }


@dataclass(frozen=True)
class DollarsReport:
    """Per-model dollar economics for one run."""

    model: str
    n: int
    n_correct: int
    accuracy: float
    spend_dollars: float
    dollars_per_correct: float | None  # None when n_correct == 0
    mean_waste_ratio: float | None  # None when no correct tasks
    priced: bool  # False => model missing from the sheet, spend not computed


def waste_ratio(result: TaskResult) -> float:
    """(actual weighted cost - V*) / V*: the per-task overspend factor."""

    if result.v_star <= 0:
        return 0.0
    return (result.cost - result.v_star) / result.v_star


def dollars_summary(
    results: Iterable[TaskResult],
    sheet: dict[str, dict[str, float]],
) -> list[DollarsReport]:
    by_model: dict[str, list[TaskResult]] = defaultdict(list)
    for r in results:
        by_model[r.model].append(r)

    reports: list[DollarsReport] = []
    for model, group in sorted(by_model.items()):
        n = len(group)
        correct = [r for r in group if r.terminal_correct]
        n_correct = len(correct)
        prices = sheet.get(model)
        if prices is None:
            spend = 0.0
            per_correct = None
            priced = False
        else:
            spend = sum(
                r.input_tokens * prices["in"] / _M + r.output_tokens * prices["out"] / _M
                for r in group
            )
            per_correct = (spend / n_correct) if n_correct else None
            priced = True
        wastes = [waste_ratio(r) for r in correct]
        mean_waste = (sum(wastes) / len(wastes)) if wastes else None
        reports.append(
            DollarsReport(
                model=model,
                n=n,
                n_correct=n_correct,
                accuracy=n_correct / n if n else 0.0,
                spend_dollars=spend,
                dollars_per_correct=per_correct,
                mean_waste_ratio=mean_waste,
                priced=priced,
            )
        )
    return reports


def format_dollars_table(reports: list[DollarsReport]) -> str:
    if not reports:
        return "(no results)\n"
    header = f"{'model':<28} {'n':>5} {'acc':>6} {'spend $':>10} {'$/correct':>11} {'waste x':>8}\n"
    lines = [header, "-" * len(header) + "\n"]
    for r in reports:
        spend = f"{r.spend_dollars:.4f}" if r.priced else "unpriced"
        per_c = (
            f"{r.dollars_per_correct:.5f}"
            if r.dollars_per_correct is not None
            else ("n/a" if r.priced else "unpriced")
        )
        waste = f"{r.mean_waste_ratio:.2f}" if r.mean_waste_ratio is not None else "n/a"
        lines.append(
            f"{r.model:<28} {r.n:>5d} {r.accuracy:>6.3f} {spend:>10} {per_c:>11} {waste:>8}\n"
        )
    return "".join(lines)
