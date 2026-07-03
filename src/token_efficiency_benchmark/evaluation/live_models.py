"""Live-model clients: OpenAI, Anthropic, Moonshot (Kimi).

Each client returns a :class:`ModelOutput` carrying the response text **and
the provider-reported token usage** — the billing truth (design_v2.md §6).
Reasoning/thinking tokens are billed as output tokens by all three providers
and are included in the provider's output count even though the reasoning
text is not returned; a local tokenizer over visible text would therefore
undercount real cost, sometimes massively. The harness uses provider counts
when present and falls back to the local tokenizer only for fixtures.

Moonshot's API is OpenAI-compatible (https://api.moonshot.ai/v1), so
:class:`MoonshotClient` is the OpenAI client pointed at that base URL with
its own env var and name prefix.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

MOONSHOT_BASE_URL = "https://api.moonshot.ai/v1"


@dataclass(frozen=True)
class ModelOutput:
    """Response text plus provider-reported usage (None => unknown)."""

    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class OpenAICompatClient:
    """Chat-Completions client for OpenAI and OpenAI-compatible providers."""

    def __init__(
        self,
        *,
        model: str,
        name_prefix: str = "openai",
        api_key: str | None = None,
        api_key_env: str = "OPENAI_API_KEY",
        base_url: str | None = None,
        temperature: float | None = None,  # None => provider default (some models require it)
        max_output_tokens: int = 16384,
        token_param: str = "max_tokens",  # OpenAI reasoning models need "max_completion_tokens"
        reasoning_effort: str | None = None,  # OpenAI: enable thinking (low/medium/high)
        thinking_disabled: bool = False,  # Moonshot: instant mode (thinking off)
        timeout_s: float = 300.0,
        http_call: Any = None,
    ) -> None:
        self.name = f"{name_prefix}:{model}"
        self._model = model
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._token_param = token_param
        self._reasoning_effort = reasoning_effort
        self._thinking_disabled = thinking_disabled
        self._timeout_s = timeout_s
        self._api_key = api_key or os.environ.get(api_key_env)
        self._base_url = base_url
        self._http_call = http_call  # test injection: prompt -> ModelOutput|str
        if self._http_call is None and self._api_key is None:
            raise RuntimeError(
                f"{type(self).__name__} requires {api_key_env} in the "
                "environment or http_call injection for tests."
            )

    def generate(self, prompt: str) -> ModelOutput:
        if self._http_call is not None:
            out = self._http_call(prompt)
            return out if isinstance(out, ModelOutput) else ModelOutput(str(out))
        try:
            from openai import OpenAI
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "openai is not installed. Install with `pip install "
                "token-efficiency-benchmark[openai]`."
            ) from e

        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        kwargs: dict[str, Any] = {self._token_param: self._max_output_tokens}
        if self._temperature is not None:
            kwargs["temperature"] = self._temperature
        if self._reasoning_effort is not None:
            kwargs["reasoning_effort"] = self._reasoning_effort
        if self._thinking_disabled:
            kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
        completion = client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            timeout=self._timeout_s,
            **kwargs,
        )
        message = completion.choices[0].message
        text = message.content or ""
        usage = getattr(completion, "usage", None)
        in_tok = getattr(usage, "prompt_tokens", None) if usage else None
        out_tok = getattr(usage, "completion_tokens", None) if usage else None
        details = getattr(usage, "completion_tokens_details", None) if usage else None
        reasoning = getattr(details, "reasoning_tokens", None) if details else None
        return ModelOutput(
            text=text,
            input_tokens=in_tok,
            output_tokens=out_tok,
            metadata={
                "provider_usage": True,
                "reasoning_tokens": reasoning,
                "finish_reason": completion.choices[0].finish_reason,
                "reasoning_content": getattr(message, "reasoning_content", None),
            },
        )


class OpenAIClient(OpenAICompatClient):
    def __init__(self, *, model: str, **kwargs: Any) -> None:
        kwargs.setdefault("token_param", "max_completion_tokens")
        super().__init__(model=model, name_prefix="openai", **kwargs)


class MoonshotClient(OpenAICompatClient):
    """Moonshot (Kimi) — OpenAI-compatible endpoint, MOONSHOT_API_KEY."""

    def __init__(self, *, model: str, **kwargs: Any) -> None:
        kwargs.setdefault("base_url", MOONSHOT_BASE_URL)
        kwargs.setdefault("api_key_env", "MOONSHOT_API_KEY")
        super().__init__(model=model, name_prefix="moonshot", **kwargs)


class AnthropicClient:
    """Anthropic Messages-API client."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        max_output_tokens: int = 16384,
        timeout_s: float = 300.0,
        http_call: Any = None,
    ) -> None:
        self.name = f"anthropic:{model}"
        self._model = model
        self._max_output_tokens = max_output_tokens
        self._timeout_s = timeout_s
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._http_call = http_call
        if self._http_call is None and self._api_key is None:
            raise RuntimeError(
                "AnthropicClient requires ANTHROPIC_API_KEY in the environment "
                "or http_call injection for tests."
            )

    def generate(self, prompt: str) -> ModelOutput:
        if self._http_call is not None:
            out = self._http_call(prompt)
            return out if isinstance(out, ModelOutput) else ModelOutput(str(out))
        try:
            from anthropic import Anthropic
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "anthropic is not installed. Install with `pip install "
                "token-efficiency-benchmark[anthropic]`."
            ) from e

        client = Anthropic(api_key=self._api_key)
        message = client.messages.create(
            model=self._model,
            max_tokens=self._max_output_tokens,
            messages=[{"role": "user", "content": prompt}],
            timeout=self._timeout_s,
        )
        parts: list[str] = []
        thinking_parts: list[str] = []
        for block in message.content:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
            thinking = getattr(block, "thinking", None)
            if isinstance(thinking, str) and thinking:
                thinking_parts.append(thinking)
        usage = getattr(message, "usage", None)
        details = getattr(usage, "output_tokens_details", None) if usage else None
        return ModelOutput(
            text="".join(parts),
            input_tokens=getattr(usage, "input_tokens", None) if usage else None,
            output_tokens=getattr(usage, "output_tokens", None) if usage else None,
            metadata={
                "provider_usage": True,
                "stop_reason": getattr(message, "stop_reason", None),
                "thinking_tokens": getattr(details, "thinking_tokens", None),
                "thinking_content": "".join(thinking_parts) or None,
            },
        )


@dataclass(frozen=True)
class StubResponse:
    """Stub http_call for tests: returns fixed text and optional usage."""

    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __call__(self, prompt: str) -> ModelOutput:
        return ModelOutput(
            text=self.text,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            metadata=dict(self.metadata),
        )


def client_for_spec(spec: str, *, timeout_s: float | None = None, **kwargs: Any) -> Any:
    """Build a live client from a spec string.

    Format: ``provider:model[#effort=low|medium|high]`` with provider in
    {moonshot, openai, anthropic}. The effort fragment (OpenAI only) enables
    reasoning and yields a distinct leaderboard row; the client's ``name`` is
    always the full spec so results and price-sheet keys line up exactly.
    """

    provider, _, rest = spec.partition(":")
    model, _, frag = rest.partition("#")
    if frag:
        key, _, value = frag.partition("=")
        if key == "effort" and value in ("low", "medium", "high"):
            if provider != "openai":
                raise ValueError(f"#effort= is only supported for openai specs, got '{spec}'")
            kwargs["reasoning_effort"] = value
        elif key == "thinking" and value == "off":
            if provider != "moonshot":
                raise ValueError(
                    f"#thinking=off is only supported for moonshot specs, got '{spec}'"
                )
            kwargs["thinking_disabled"] = True
        else:
            raise ValueError(f"unsupported spec fragment '#{frag}' in '{spec}'")
    if timeout_s is not None:
        kwargs["timeout_s"] = timeout_s
    classes = {
        "moonshot": MoonshotClient,
        "openai": OpenAIClient,
        "anthropic": AnthropicClient,
    }
    if provider not in classes:
        raise ValueError(f"unknown provider '{provider}' in spec '{spec}'")
    client = classes[provider](model=model, **kwargs)
    client.name = spec
    return client
