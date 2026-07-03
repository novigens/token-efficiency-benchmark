"""Obligated tests for the pricing layer (examples_v2.md §E)."""

from __future__ import annotations

import json

import pytest

from token_efficiency_benchmark.evaluation.pricing import (
    dollars_summary,
    load_price_sheet,
    waste_ratio,
)
from token_efficiency_benchmark.types import TaskResult


def _result(correct: bool, in_tok: int, out_tok: int, *, cost=0.0, v_star=1.0):
    return TaskResult(
        task_id="t",
        model="x:m",
        terminal_correct=correct,
        parsed_terminal="1" if correct else "0",
        expected_terminal="1",
        input_tokens=in_tok,
        output_tokens=out_tok,
        cost=cost,
        v_star=v_star,
        efficiency=1.0 if correct else None,
        response_text="",
        generator_version="2.0.0",
        weights=(1.0, 4.0),
        difficulty_bucket="depth_3",
    )


SHEET = {"x:m": {"in": 3.0, "out": 15.0}}


def test_pricing_dollars_per_correct():
    """The §E worked numbers, exactly: 10 tasks, 7 correct, 2000 in / 5000 out
    total, $3/M in, $15/M out => spend $0.081, $/correct ~= $0.011571."""

    results = [_result(i < 7, 200, 500) for i in range(10)]
    (report,) = dollars_summary(results, SHEET)
    assert report.n == 10 and report.n_correct == 7
    assert report.spend_dollars == pytest.approx(0.081)
    assert report.dollars_per_correct == pytest.approx(0.081 / 7)


def test_pricing_zero_correct():
    results = [_result(False, 200, 500) for _ in range(3)]
    (report,) = dollars_summary(results, SHEET)
    assert report.n_correct == 0
    assert report.dollars_per_correct is None  # rendered as n/a, never a crash


def test_pricing_unpriced_model_flagged():
    results = [_result(True, 200, 500)]
    (report,) = dollars_summary(results, {})
    assert report.priced is False
    assert report.dollars_per_correct is None


def test_waste_ratio():
    """§E: V*=130, actual weighted cost 1530 => waste ~= 10.77."""

    r = _result(True, 0, 0, cost=1530.0, v_star=130.0)
    assert waste_ratio(r) == pytest.approx((1530 - 130) / 130)


def test_price_sheet_reweighting(tmp_path):
    """Raw counts survive scoring: a different sheet reprices the same results."""

    results = [_result(True, 1000, 1000)]
    cheap = dollars_summary(results, {"x:m": {"in": 1.0, "out": 1.0}})[0]
    dear = dollars_summary(results, {"x:m": {"in": 10.0, "out": 10.0}})[0]
    assert dear.spend_dollars == pytest.approx(10 * cheap.spend_dollars)


def test_price_sheet_loader_skips_meta_keys(tmp_path):
    p = tmp_path / "prices.json"
    p.write_text(json.dumps({"_note": "x", "a:b": {"in": 1, "out": 2}}))
    sheet = load_price_sheet(p)
    assert sheet == {"a:b": {"in": 1.0, "out": 2.0}}
