"""Smoke tests for the CLI."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from token_efficiency_benchmark.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "generate" in result.output
    assert "evaluate" in result.output
    assert "score" in result.output


def test_cli_end_to_end(tmp_path: Path):
    runner = CliRunner()
    tasks_path = tmp_path / "tasks.jsonl"
    results_path = tmp_path / "results.jsonl"

    gen = runner.invoke(
        main,
        [
            "generate",
            "--depth",
            "3",
            "--n",
            "5",
            "--seed",
            "100",
            "--out",
            str(tasks_path),
        ],
    )
    assert gen.exit_code == 0, gen.output
    assert tasks_path.exists()

    ev = runner.invoke(
        main,
        [
            "evaluate",
            "--tasks",
            str(tasks_path),
            "--model",
            "echo",
            "--out",
            str(results_path),
        ],
    )
    assert ev.exit_code == 0, ev.output
    assert results_path.exists()

    sc = runner.invoke(main, ["score", "--results", str(results_path)])
    assert sc.exit_code == 0, sc.output
    assert "echo_model" in sc.output
