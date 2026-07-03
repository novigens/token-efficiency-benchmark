"""Tests for the live-model client scaffolding (Phase 4.5).

These tests verify the client contract using stubbed HTTP calls; no real
provider API is touched. Real-API integration tests live behind the
``[openai]`` / ``[anthropic]`` extras and are gated by env-var presence.
"""

from __future__ import annotations

import pytest

from token_efficiency_benchmark.evaluation.harness import evaluate_task
from token_efficiency_benchmark.evaluation.live_models import (
    AnthropicClient,
    OpenAIClient,
    StubResponse,
)
from token_efficiency_benchmark.families import ArithmeticChainFamily, DifficultyParams


def _make_task(seed: int = 100):
    return ArithmeticChainFamily().generate(seed, DifficultyParams(depth=2))


def test_openai_client_requires_key_or_http_call():
    """Without an API key and without http_call injection, construction
    should raise.
    """

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIClient(model="gpt-4o-mini", api_key=None)


def test_anthropic_client_requires_key_or_http_call():
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        AnthropicClient(model="claude-3-haiku", api_key=None)


def test_openai_client_with_stub_returns_canonical_answer():
    task = _make_task()
    canonical = task.canonical_terminal_answer
    stub = StubResponse(text=canonical)
    client = OpenAIClient(model="gpt-4o-mini", http_call=stub)
    result = evaluate_task(task, client)
    assert result.terminal_correct
    assert result.model == "openai:gpt-4o-mini"


def test_anthropic_client_with_stub_returns_canonical_answer():
    task = _make_task(seed=200)
    canonical = task.canonical_terminal_answer
    stub = StubResponse(text=canonical)
    client = AnthropicClient(model="claude-3-haiku-20240307", http_call=stub)
    result = evaluate_task(task, client)
    assert result.terminal_correct
    assert result.model == "anthropic:claude-3-haiku-20240307"


def test_openai_client_with_wrong_stub_is_terminally_incorrect():
    task = _make_task(seed=300)
    canonical = task.canonical_terminal_answer
    wrong = str(int(canonical) + 1)
    stub = StubResponse(text=wrong)
    client = OpenAIClient(model="gpt-4o-mini", http_call=stub)
    result = evaluate_task(task, client)
    assert not result.terminal_correct
    assert result.efficiency is None


def test_live_client_response_text_recorded():
    task = _make_task(seed=400)
    canonical = task.canonical_terminal_answer
    stub_text = f"Let me think... the answer is {canonical}."
    stub = StubResponse(text=stub_text)
    client = OpenAIClient(model="gpt-4o-mini", http_call=stub)
    result = evaluate_task(task, client)
    # The response text is preserved in the replay record.
    assert stub_text in result.response_text
    assert result.terminal_correct
