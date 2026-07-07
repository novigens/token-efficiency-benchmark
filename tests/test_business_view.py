"""Business view: risk-adjusted $/correct with gates.

Pins the formula (beta**(k^2) with k normalized per 20 tasks), the gate
behavior, and the ordering contract: gated and unusable rows are listed at
the bottom with reasons, never dropped.
"""

from __future__ import annotations

from token_efficiency_benchmark.evaluation.reporting import format_business_view
from token_efficiency_benchmark.types import TaskResult


def _result(model: str, correct: bool, out_tok: int = 500) -> TaskResult:
    cost = 300 + 4.0 * out_tok
    return TaskResult(
        task_id=f"t::{model}::{out_tok}::{correct}",
        model=model,
        terminal_correct=correct,
        parsed_terminal="1" if correct else "2",
        expected_terminal="1",
        input_tokens=300,
        output_tokens=out_tok,
        cost=cost,
        v_star=304.0,
        efficiency=(304.0 / cost) if correct else None,
        response_text="1",
        generator_version="2.0.0",
        weights=(1.0, 4.0),
        difficulty_bucket="hybrid_d3",
    )


def _rows(model: str, n_correct: int, n_wrong: int, out_tok: int = 500) -> list[TaskResult]:
    rows = [_result(model, True, out_tok) for _ in range(n_correct)]
    rows += [_result(model, False, out_tok + i + 1) for i in range(n_wrong)]  # unique ids
    return rows


SHEET = {"a:clean": {"in": 1.0, "out": 4.0}, "a:one-wrong": {"in": 1.0, "out": 4.0}}


def test_clean_sheet_is_unpenalized_and_ranked_first():
    results = _rows("a:clean", 20, 0) + _rows("a:one-wrong", 19, 1)
    out = format_business_view(results, SHEET)
    lines = [ln for ln in out.splitlines() if ln.strip() and ln.lstrip()[0].isdigit()]
    assert "a:clean" in lines[0] and "a:one-wrong" in lines[1]


def test_penalty_is_beta_to_k_squared():
    sheet = {"m:x": {"in": 1.0, "out": 4.0}}
    two_wrong = _rows("m:x", 18, 2)
    out = format_business_view(two_wrong, sheet, beta=0.8)
    # $/correct for 20 rows of identical spend s: dpc = 20s/18; risk = dpc / 0.8**4
    row = next(ln for ln in out.splitlines() if "m:x" in ln)
    dpc = float(row.split()[6])
    risk = float(row.split()[7])
    assert abs(risk - dpc / 0.8**4) < 5e-5  # both columns print at 5 decimals


def test_k_is_normalized_per_20_tasks():
    sheet = {"m:x": {"in": 1.0, "out": 4.0}}
    # 1 wrong of 10 tasks == 2 wrong per 20 => k=2, penalty beta**4
    out = format_business_view(_rows("m:x", 9, 1), sheet, beta=0.8)
    row = next(ln for ln in out.splitlines() if "m:x" in ln)
    dpc, risk = float(row.split()[6]), float(row.split()[7])
    assert abs(risk - dpc / 0.8**4) < 5e-5


def test_efficiency_gate_pushes_to_bottom_with_reason():
    sheet = {"m:fast": {"in": 1.0, "out": 4.0}, "m:slow": {"in": 1.0, "out": 4.0}}
    slow = _rows("m:slow", 20, 0, out_tok=16000)  # efficiency ~ 304/64300 << 5%
    fast = _rows("m:fast", 18, 2, out_tok=500)  # worse risk-adj, but ungated
    out = format_business_view(slow + fast, sheet)
    lines = out.splitlines()
    slow_i = next(i for i, ln in enumerate(lines) if "m:slow" in ln)
    fast_i = next(i for i, ln in enumerate(lines) if "m:fast" in ln)
    assert slow_i > fast_i, "gated row must sort below ungated rows"
    assert "gated: efficiency" in lines[slow_i]


def test_hopeless_config_prices_astronomically_but_stays_listed():
    """No hard cutoff: the exponential penalty is the verdict. A 40%-accurate
    config is listed with an absurd compact-notation price, not hidden."""

    sheet = {"m:bad": {"in": 1.0, "out": 4.0}, "m:good": {"in": 1.0, "out": 4.0}}
    out = format_business_view(_rows("m:bad", 8, 12) + _rows("m:good", 20, 0), sheet)
    lines = out.splitlines()
    bad_i = next(i for i, ln in enumerate(lines) if "m:bad" in ln)
    good_i = next(i for i, ln in enumerate(lines) if "m:good" in ln)
    assert bad_i > good_i
    assert "e+" in lines[bad_i]  # compact notation for an economically absurd price


def test_borderline_gate_reads_truthfully_at_two_decimals():
    """A config just under the floor (~4.97%) must gate on the true float value
    and display two decimals so the verdict reads '4.97% below 5%', never a
    self-contradictory '5.0% below 5%'."""

    sheet = {"m:border": {"in": 1.0, "out": 4.0}}
    borderline = [_result("m:border", True, out_tok=1453) for _ in range(20)]
    eff = borderline[0].efficiency
    assert eff is not None and 0.049 < eff < 0.05  # genuinely below the 5% floor
    out = format_business_view(borderline, sheet, eff_gate=0.05)
    row = next(ln for ln in out.splitlines() if "m:border" in ln)
    assert "gated: efficiency 4.9" in row and "below 5%" in row


def test_truly_slow_config_still_gates():
    sheet = {"m:slow": {"in": 1.0, "out": 4.0}}
    out = format_business_view(_rows("m:slow", 20, 0, out_tok=16000), sheet, eff_gate=0.05)
    row = next(ln for ln in out.splitlines() if "m:slow" in ln)
    assert "gated: efficiency" in row and "below 5%" in row


def test_above_floor_config_is_not_gated():
    sheet = {"m:ok": {"in": 1.0, "out": 4.0}}
    out = format_business_view(_rows("m:ok", 20, 0, out_tok=500), sheet, eff_gate=0.05)
    row = next(ln for ln in out.splitlines() if "m:ok" in ln)
    assert "gated" not in row


def test_no_correct_answers_is_labelled():
    sheet = {"m:zero": {"in": 1.0, "out": 4.0}}
    out = format_business_view(_rows("m:zero", 0, 5), sheet)
    row = next(ln for ln in out.splitlines() if "m:zero" in ln)
    assert "no correct answers in 5" in row


def test_fixture_models_without_prices_are_excluded():
    results = _rows("a:clean", 20, 0) + _rows("echo_model", 20, 0)
    out = format_business_view(results, {"a:clean": {"in": 1.0, "out": 4.0}})
    assert "echo_model" not in out
