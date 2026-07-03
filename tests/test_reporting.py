"""Reporting formatter regressions.

The first public run exposed two formatter bugs: bucket labels like
``hybrid_prog+chain+table_d6`` defeated the old ``rsplit("_")`` depth parser
(silencing the cost decomposition), and 31-character model specs overflowed
the fixed 28-column name field. These tests pin the fixes.
"""

from __future__ import annotations

from token_efficiency_benchmark.evaluation.reporting import (
    _bucket_order,
    format_comparison,
)
from token_efficiency_benchmark.types import TaskResult


def _result(model: str, bucket: str, out_tok: int, correct: bool = True) -> TaskResult:
    cost = 300 + 4.0 * out_tok
    return TaskResult(
        task_id=f"t::{bucket}::{out_tok}",
        model=model,
        terminal_correct=correct,
        parsed_terminal="1" if correct else "2",
        expected_terminal="1",
        input_tokens=300,
        output_tokens=out_tok,
        cost=cost,
        v_star=310.0,
        efficiency=(310.0 / cost) if correct else None,
        response_text="1",
        generator_version="2.0.0",
        weights=(1.0, 4.0),
        difficulty_bucket=bucket,
    )


def test_bucket_order_parses_hybrid_and_plain_labels():
    assert _bucket_order("depth_6") == 6
    assert _bucket_order("hybrid_prog+chain+table_d3") == 3
    assert _bucket_order("hybrid_prog+chain+table_d12") == 12
    assert _bucket_order("no_digits_here") == 0


def test_cost_decomposition_fits_across_hybrid_buckets():
    rows = [
        _result("m", "hybrid_prog+chain+table_d3", 400),
        _result("m", "hybrid_prog+chain+table_d6", 700),
    ]
    out = format_comparison(rows, {"m": {"in": 1.0, "out": 4.0}})
    assert "(needs >=2 depths)" not in out
    # slope (700-400)/(6-3) = 100.0/step; intercept 400 - 3*100 = 100
    decomposition = out.split("Cost decomposition")[1]
    assert "100.0" in decomposition


def test_long_spec_names_do_not_collide_with_columns():
    long_name = "moonshot:kimi-k2.5#thinking=off"
    rows = [
        _result(long_name, "hybrid_prog+chain+table_d3", 500),
        _result(long_name, "hybrid_prog+chain+table_d6", 800),
    ]
    out = format_comparison(rows, {long_name: {"in": 0.6, "out": 3.0}})
    for line in out.splitlines():
        if line.startswith(long_name):
            # the name field is always padded — never fused into the next column
            assert line[len(long_name)] == " "
