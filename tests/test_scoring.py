"""Tests for the scoring pipeline (§10.5, §6.2)."""

from __future__ import annotations

from token_efficiency_benchmark.evaluation.harness import evaluate_task
from token_efficiency_benchmark.evaluation.models import (
    EchoModel,
    VerboseEchoModel,
    WrongEchoModel,
)
from token_efficiency_benchmark.evaluation.scoring import (
    aggregate_results,
    compute_efficiency,
    parse_integer_answer,
)


def test_parse_integer_answer_picks_last_integer():
    assert parse_integer_answer("The year 1947 and the answer is 12") == "12"
    assert parse_integer_answer("answer: 42") == "42"
    assert parse_integer_answer("no number here") is None
    assert parse_integer_answer("") is None
    assert parse_integer_answer("step 1, step 2, result 7") == "7"


def test_parse_integer_answer_accepts_grouped_final_answer():
    assert parse_integer_answer("Difference: 463,949") == "463949"
    assert parse_integer_answer("Difference: 463\uff0c949") == "463949"
    assert parse_integer_answer("Difference: 185\u202f805") == "185805"
    assert parse_integer_answer("Difference: 185\u00a0805") == "185805"


def test_compute_efficiency_bounded_in_zero_one():
    eff = compute_efficiency(
        v_star_input_tokens=100,
        v_star_output_tokens=1,
        actual_input_tokens=100,
        actual_output_tokens=1,
    )
    assert eff == 1.0

    eff = compute_efficiency(
        v_star_input_tokens=100,
        v_star_output_tokens=1,
        actual_input_tokens=200,
        actual_output_tokens=10,
    )
    assert 0 < eff < 1


def test_compute_efficiency_zero_on_zero_actual():
    assert (
        compute_efficiency(
            v_star_input_tokens=10,
            v_star_output_tokens=1,
            actual_input_tokens=0,
            actual_output_tokens=0,
        )
        == 0.0
    )


def test_echo_model_is_terminally_correct(linear_chain_depth_3):
    task = linear_chain_depth_3
    model = EchoModel({task.task_id: task.canonical_terminal_answer})
    result = evaluate_task(task, model)
    assert result.terminal_correct
    assert result.parsed_terminal == task.canonical_terminal_answer
    assert result.efficiency is not None
    assert 0 < result.efficiency <= 1.0001  # allow tiny rounding slack


def test_verbose_echo_is_correct_but_less_efficient(linear_chain_depth_3):
    task = linear_chain_depth_3
    echo = EchoModel({task.task_id: task.canonical_terminal_answer})
    verbose = VerboseEchoModel({task.task_id: task.canonical_terminal_answer}, padding_tokens=400)
    echo_result = evaluate_task(task, echo)
    verbose_result = evaluate_task(task, verbose)
    assert echo_result.terminal_correct
    assert verbose_result.terminal_correct
    assert echo_result.efficiency is not None
    assert verbose_result.efficiency is not None
    assert verbose_result.efficiency < echo_result.efficiency


def test_wrong_echo_is_incorrect_and_has_no_efficiency(linear_chain_depth_3):
    task = linear_chain_depth_3
    # Ensure the canonical answer is not literally "0" — almost always true,
    # but guard the assertion if it ever happens to be.
    if task.canonical_terminal_answer == "0":
        return
    result = evaluate_task(task, WrongEchoModel())
    assert not result.terminal_correct
    assert result.efficiency is None


def test_aggregate_results_groups_by_model_and_difficulty(linear_chain_depth_3):
    task = linear_chain_depth_3
    correct = evaluate_task(task, EchoModel({task.task_id: task.canonical_terminal_answer}))
    wrong = evaluate_task(task, WrongEchoModel())
    reports = aggregate_results([correct, wrong])
    by_model = {r.model: r for r in reports}
    assert by_model["echo_model"].accuracy == 1.0
    if task.canonical_terminal_answer != "0":
        assert by_model["wrong_echo_model"].accuracy == 0.0
    assert by_model["echo_model"].difficulty_bucket == "depth_3"
