"""Tests for replay round-tripping (§10.6)."""

from __future__ import annotations

from pathlib import Path

from token_efficiency_benchmark.evaluation.harness import evaluate_task
from token_efficiency_benchmark.evaluation.models import EchoModel
from token_efficiency_benchmark.serialization import (
    read_results_jsonl,
    read_tasks_jsonl,
    result_from_dict,
    result_to_dict,
    task_from_dict,
    task_to_dict,
    write_results_jsonl,
    write_tasks_jsonl,
)


def test_task_round_trip_through_dict(linear_chain_depth_3):
    data = task_to_dict(linear_chain_depth_3)
    restored = task_from_dict(data)
    assert restored.task_id == linear_chain_depth_3.task_id
    assert restored.merged_prompt == linear_chain_depth_3.merged_prompt
    assert restored.canonical_terminal_answer == linear_chain_depth_3.canonical_terminal_answer
    assert len(restored.nodes) == len(linear_chain_depth_3.nodes)


def test_result_round_trip_through_dict(linear_chain_depth_3):
    task = linear_chain_depth_3
    result = evaluate_task(task, EchoModel({task.task_id: task.canonical_terminal_answer}))
    data = result_to_dict(result)
    restored = result_from_dict(data)
    assert restored == result


def test_jsonl_round_trip_tasks_and_results(linear_chain_depth_3, tmp_path: Path):
    task = linear_chain_depth_3
    tasks_path = tmp_path / "tasks.jsonl"
    results_path = tmp_path / "results.jsonl"

    n = write_tasks_jsonl([task], tasks_path)
    assert n == 1
    restored_task = next(read_tasks_jsonl(tasks_path))
    assert restored_task.task_id == task.task_id

    result = evaluate_task(task, EchoModel({task.task_id: task.canonical_terminal_answer}))
    n = write_results_jsonl([result], results_path)
    assert n == 1
    restored_result = next(read_results_jsonl(results_path))
    assert restored_result.terminal_correct == result.terminal_correct
    assert restored_result.efficiency == result.efficiency
