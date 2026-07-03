"""JSON(L) serialization for tasks and results.

The benchmark's replay contract (§10.6) requires that every emitted task and
every per-task result be fully recoverable from its JSON record. This module
implements bidirectional conversion between the dataclasses in
:mod:`.types` and plain JSON-compatible dicts.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

from .types import (
    AnswerType,
    CompositeNode,
    CompositeTask,
    Item,
    ParameterTemplateSpec,
    TaskResult,
)


def task_to_dict(task: CompositeTask) -> dict[str, Any]:
    """Serialize a :class:`CompositeTask` to a JSON-ready dict."""

    return {
        "task_id": task.task_id,
        "generator_version": task.generator_version,
        "template_id": task.template_id,
        "seed": task.seed,
        "parameters": task.parameters,
        "nodes": [
            {
                "item": _item_to_dict(node.item),
                "parameter_template": (
                    _ptspec_to_dict(node.parameter_template) if node.parameter_template else None
                ),
                "instantiated_question": node.instantiated_question,
            }
            for node in task.nodes
        ],
        "merged_prompt": task.merged_prompt,
        "canonical_terminal_answer": task.canonical_terminal_answer,
        "terminal_answer_type": task.terminal_answer_type.value,
        "v_star_input_tokens": task.v_star_input_tokens,
        "v_star_output_tokens": task.v_star_output_tokens,
    }


def task_from_dict(data: dict[str, Any]) -> CompositeTask:
    nodes = tuple(
        CompositeNode(
            item=_item_from_dict(node_data["item"]),
            parameter_template=(
                _ptspec_from_dict(node_data["parameter_template"])
                if node_data["parameter_template"]
                else None
            ),
            instantiated_question=node_data["instantiated_question"],
        )
        for node_data in data["nodes"]
    )
    return CompositeTask(
        task_id=data["task_id"],
        generator_version=data["generator_version"],
        template_id=data["template_id"],
        seed=data["seed"],
        parameters=data["parameters"],
        nodes=nodes,
        merged_prompt=data["merged_prompt"],
        canonical_terminal_answer=data["canonical_terminal_answer"],
        terminal_answer_type=AnswerType(data["terminal_answer_type"]),
        v_star_input_tokens=data["v_star_input_tokens"],
        v_star_output_tokens=data["v_star_output_tokens"],
    )


def result_to_dict(result: TaskResult) -> dict[str, Any]:
    return {
        "task_id": result.task_id,
        "model": result.model,
        "terminal_correct": result.terminal_correct,
        "parsed_terminal": result.parsed_terminal,
        "expected_terminal": result.expected_terminal,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "cost": result.cost,
        "v_star": result.v_star,
        "efficiency": result.efficiency,
        "response_text": result.response_text,
        "generator_version": result.generator_version,
        "weights": list(result.weights),
        "difficulty_bucket": result.difficulty_bucket,
        "response_extra": result.response_extra,
    }


def result_from_dict(data: dict[str, Any]) -> TaskResult:
    return TaskResult(
        task_id=data["task_id"],
        model=data["model"],
        terminal_correct=data["terminal_correct"],
        parsed_terminal=data["parsed_terminal"],
        expected_terminal=data["expected_terminal"],
        input_tokens=data["input_tokens"],
        output_tokens=data["output_tokens"],
        cost=data["cost"],
        v_star=data["v_star"],
        efficiency=data["efficiency"],
        response_text=data["response_text"],
        generator_version=data["generator_version"],
        weights=tuple(data["weights"]),
        difficulty_bucket=data["difficulty_bucket"],
        response_extra=data.get("response_extra") or {},
    )


def write_tasks_jsonl(tasks: Iterable[CompositeTask], path: Path) -> int:
    """Write tasks as JSONL. Returns the count written."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task_to_dict(task), ensure_ascii=False))
            f.write("\n")
            n += 1
    return n


def read_tasks_jsonl(path: Path) -> Iterator[CompositeTask]:
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield task_from_dict(json.loads(line))


def write_results_jsonl(results: Iterable[TaskResult], path: Path) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for result in results:
            f.write(json.dumps(result_to_dict(result), ensure_ascii=False))
            f.write("\n")
            n += 1
    return n


def read_results_jsonl(path: Path) -> Iterator[TaskResult]:
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield result_from_dict(json.loads(line))


# ----------------------------------------------------------------------
# Helpers


def _item_to_dict(item: Item) -> dict[str, Any]:
    return {
        "id": item.id,
        "question": item.question,
        "known_answer": item.known_answer,
        "answer_type": item.answer_type.value,
        "source": item.source,
        "source_version": item.source_version,
        "parameter_templates_supported": list(item.parameter_templates_supported),
        "metadata": item.metadata,
    }


def _item_from_dict(data: dict[str, Any]) -> Item:
    return Item(
        id=data["id"],
        question=data["question"],
        known_answer=data["known_answer"],
        answer_type=AnswerType(data["answer_type"]),
        source=data["source"],
        source_version=data["source_version"],
        parameter_templates_supported=tuple(data.get("parameter_templates_supported") or ()),
        metadata=data.get("metadata") or {},
    )


def _ptspec_to_dict(spec: ParameterTemplateSpec) -> dict[str, Any]:
    return {
        "name": spec.name,
        "args": spec.args,
        "output_type": spec.output_type.value,
    }


def _ptspec_from_dict(data: dict[str, Any]) -> ParameterTemplateSpec:
    return ParameterTemplateSpec(
        name=data["name"],
        args=data.get("args") or {},
        output_type=AnswerType(data["output_type"]),
    )
