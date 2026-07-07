"""Provider-reported usage is billing truth (examples_v2.md §F,
test_provider_token_counts)."""

from __future__ import annotations

from token_efficiency_benchmark.evaluation.harness import evaluate_task
from token_efficiency_benchmark.evaluation.live_models import (
    MoonshotClient,
    StubResponse,
)
from token_efficiency_benchmark.families import ArithmeticChainFamily, DifficultyParams


def _task():
    return ArithmeticChainFamily().generate(5, DifficultyParams(depth=3))


def test_provider_counts_enter_the_metric():
    """A stub that reports provider usage (simulating hidden reasoning tokens)
    must override local tokenization: 900 output tokens of hidden reasoning
    are billed even though the visible text is one integer."""

    task = _task()
    stub = StubResponse(text=task.canonical_terminal_answer, input_tokens=180, output_tokens=900)
    client = MoonshotClient(model="kimi-test", http_call=stub)
    result = evaluate_task(task, client)
    assert result.terminal_correct
    assert result.input_tokens == 180
    assert result.output_tokens == 900  # not count_tokens("<integer>")
    assert result.efficiency is not None and result.efficiency < 0.2


def test_local_fallback_when_no_usage():
    task = _task()
    stub = StubResponse(text=task.canonical_terminal_answer)  # no usage fields
    client = MoonshotClient(model="kimi-test", http_call=stub)
    result = evaluate_task(task, client)
    assert result.terminal_correct
    # falls back to local tokenizer: tiny output count
    assert result.output_tokens <= 3


def test_moonshot_client_name_prefix():
    client = MoonshotClient(model="kimi-k2.5", http_call=StubResponse(text="1"))
    assert client.name == "moonshot:kimi-k2.5"


def test_response_extra_evidence_persisted():
    """Provider extras (reasoning text, finish reason) land in the result
    record and survive serialization — the audit-evidence contract."""

    from token_efficiency_benchmark.serialization import (
        result_from_dict,
        result_to_dict,
    )

    task = _task()
    stub = StubResponse(
        text=task.canonical_terminal_answer,
        input_tokens=100,
        output_tokens=4096,
        metadata={
            "finish_reason": "length",
            "reasoning_content": "…found the answer, kept second-guessing…",
            "reasoning_tokens": 4096,
        },
    )
    result = evaluate_task(task, MoonshotClient(model="kimi-test", http_call=stub))
    assert result.response_extra["finish_reason"] == "length"
    assert "second-guessing" in result.response_extra["reasoning_content"]
    round_tripped = result_from_dict(result_to_dict(result))
    assert round_tripped == result


def test_response_extra_backward_compatible_read():
    """Old results files without response_extra still deserialize."""

    from token_efficiency_benchmark.serialization import (
        result_from_dict,
        result_to_dict,
    )

    task = _task()
    stub = StubResponse(text=task.canonical_terminal_answer)
    result = evaluate_task(task, MoonshotClient(model="kimi-test", http_call=stub))
    record = result_to_dict(result)
    del record["response_extra"]  # simulate a pre-2.0.0-evidence row
    assert result_from_dict(record).response_extra == {}


def test_client_for_spec_effort_parsing():
    """provider:model#effort=X yields a distinct row name and sets the knob."""

    from token_efficiency_benchmark.evaluation.live_models import client_for_spec

    stub = StubResponse(text="1")
    c = client_for_spec("openai:gpt-5.4#effort=medium", http_call=stub)
    assert c.name == "openai:gpt-5.4#effort=medium"
    assert c._reasoning_effort == "medium"
    plain = client_for_spec("moonshot:kimi-k2.5", http_call=stub)
    assert plain.name == "moonshot:kimi-k2.5"
    import pytest as _pytest

    with _pytest.raises(ValueError):
        client_for_spec("moonshot:kimi-k2.5#effort=high", http_call=stub)
    with _pytest.raises(ValueError):
        client_for_spec("openai:gpt-5.4#effort=maximal", http_call=stub)


def test_client_for_spec_thinking_off():
    from token_efficiency_benchmark.evaluation.live_models import client_for_spec

    stub = StubResponse(text="1")
    c = client_for_spec("moonshot:kimi-k2.5#thinking=off", http_call=stub)
    assert c.name == "moonshot:kimi-k2.5#thinking=off"
    assert c._thinking_disabled is True
    import pytest as _pytest

    with _pytest.raises(ValueError):
        client_for_spec("openai:gpt-5.4#thinking=off", http_call=stub)


def test_moonshot_stream_env_preserves_model_name(monkeypatch):
    from token_efficiency_benchmark.evaluation.live_models import client_for_spec

    monkeypatch.setenv("TEB_MOONSHOT_STREAM", "1")
    monkeypatch.setenv("TEB_MOONSHOT_MAX_TOKENS", "65536")
    client = client_for_spec("moonshot:kimi-k2.5", http_call=StubResponse(text="1"))
    assert client.name == "moonshot:kimi-k2.5"
    assert client._stream is True
    assert client._max_output_tokens == 65536
