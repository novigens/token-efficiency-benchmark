"""Model client interfaces.

The v0 release ships a small set of deterministic model clients used for
test fixtures and the dry-run path. Real-LLM integrations (OpenAI, Anthropic,
local servers) land in v0.1 behind optional extras.

Every client implements :class:`ModelClient`, which exposes a single
``generate(prompt) -> response_text`` method. Token counting is handled by
the harness; the client returns only the raw response text and any
provider-side metadata it wishes to expose.
"""

from __future__ import annotations

from typing import Protocol


class ModelClient(Protocol):
    """Protocol for a model client.

    ``name`` is a stable identifier used in result files. ``generate`` is the
    only required method. Clients should be cheap to instantiate and stateless
    across calls so the harness can parallelize freely.
    """

    name: str

    def generate(self, prompt: str) -> str: ...


class EchoModel:
    """Returns the canonical answer that would have been computed.

    Used in tests as a "perfect" model: it knows the task spec and emits the
    canonical terminal answer in minimal form. The harness wires this up by
    passing the expected canonical answer as the prompt-postfix marker; see
    :func:`evaluate_task` for how the harness signals the expected answer.

    Because real models do not know the expected answer, this class is a
    test-only fixture. It exists so we can verify the metric responds
    correctly to a fully-correct, fully-efficient model.

    For consistency-template tasks, callers can register a special-format
    answer via :meth:`register_consistency_answer` that emits the four-field
    structured response the consistency grader expects.
    """

    name: str = "echo_model"

    def __init__(self, answer_lookup: dict[str, str]):
        self.answer_lookup = answer_lookup

    def generate(self, prompt: str) -> str:
        # The harness invokes this via :meth:`generate_for_task` to thread the
        # task_id through; the bare protocol method is implemented as a no-op
        # so static checkers see a uniform signature.
        raise NotImplementedError(
            "EchoModel must be invoked via generate_for_task(task_id, prompt)"
        )

    def generate_for_task(self, task_id: str, prompt: str) -> str:
        answer = self.answer_lookup.get(task_id)
        if answer is None:
            raise KeyError(f"EchoModel has no answer registered for task {task_id}")
        return answer


class ConsistencyEchoModel(EchoModel):
    """Echo model that emits the structured consistency-task response format.

    Expects ``answer_lookup`` values to be dicts with keys
    ``{"a", "b", "c", "verdict"}``. The model emits a response like:
    ``"a=10, b=4, c=6, verdict=consistent"``.

    For inducing confabulation (a wrong sub-answer with verdict=consistent
    anyway), see :class:`ConfabulatingConsistencyModel`.
    """

    name: str = "consistency_echo_model"

    def generate_for_task(self, task_id: str, prompt: str) -> str:
        payload = self.answer_lookup.get(task_id)
        if payload is None:
            raise KeyError(f"ConsistencyEchoModel has no answer registered for task {task_id}")
        # payload is a dict-like serialized as a string by the registrar; we
        # accept either a dict (for in-process use) or a pre-formatted string.
        if isinstance(payload, str):
            return payload
        return f"a={payload['a']}, b={payload['b']}, c={payload['c']}, verdict={payload['verdict']}"


class ConfabulatingConsistencyModel:
    """Always emits the truthful a, b, c but claims verdict=consistent.

    Used to verify §12.4 test 3: a confabulating model that emits a wrong
    sub-answer and claims consistency is graded terminally incorrect.
    """

    name: str = "confabulating_consistency_model"

    def __init__(self, answer_lookup: dict[str, dict[str, int | str]]):
        self.answer_lookup = answer_lookup

    def generate(self, prompt: str) -> str:
        raise NotImplementedError("Use generate_for_task")

    def generate_for_task(self, task_id: str, prompt: str) -> str:
        payload = self.answer_lookup[task_id]
        # Force a wrong 'a' value (off by 1) but claim consistent.
        wrong_a = int(payload["a"]) + 1
        return f"a={wrong_a}, b={payload['b']}, c={payload['c']}, verdict=consistent"


class VerboseEchoModel(EchoModel):
    """Like :class:`EchoModel` but pads the response with chain-of-thought text.

    Used to verify the efficiency metric responds to verbosity: a correct but
    verbose response should score lower than the canonical-form echo.
    """

    name: str = "verbose_echo_model"

    def __init__(self, answer_lookup: dict[str, str], padding_tokens: int = 200):
        super().__init__(answer_lookup)
        self.padding_tokens = padding_tokens

    def generate_for_task(self, task_id: str, prompt: str) -> str:
        answer = self.answer_lookup[task_id]
        padding = "Let me think step by step about this problem. " * max(
            1, self.padding_tokens // 10
        )
        return f"{padding}\nThe answer is {answer}"


class WrongEchoModel:
    """Always returns a wrong answer.

    Used to verify that zero correctness produces zero efficiency in the
    scoring pipeline.
    """

    name: str = "wrong_echo_model"

    def generate(self, prompt: str) -> str:
        return "0"

    def generate_for_task(self, task_id: str, prompt: str) -> str:
        return "0"
