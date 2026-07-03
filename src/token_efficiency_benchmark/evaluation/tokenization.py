"""Token counting.

The benchmark uses ``tiktoken`` with the ``cl100k_base`` encoding as the
default tokenizer for V* and model-cost computation. This is the encoding
used by OpenAI's gpt-4 family; it's a reasonable proxy for a "modern BPE"
that does not advantage any one model.

We also expose UTF-8 byte length for tokenizer-independent reporting (§10.5).

If ``tiktoken`` is not installed for some reason (e.g., a constrained
environment), the module falls back to a word-based heuristic. The fallback
is logged once on first use and is not recommended for headline reporting.
"""

from __future__ import annotations

import logging
from typing import Any

_LOG = logging.getLogger(__name__)

try:
    import tiktoken

    _ENCODING: Any | None = tiktoken.get_encoding("cl100k_base")
except Exception:  # pragma: no cover - covered by manual install matrix
    _ENCODING = None
    _LOG.warning(
        "tiktoken unavailable; falling back to word-count heuristic. "
        "Install tiktoken for accurate token counts."
    )


def count_tokens(text: str) -> int:
    """Count tokens in ``text`` using the configured tokenizer.

    Returns 0 for empty input. Uses ``cl100k_base`` BPE when available; falls
    back to a whitespace-based heuristic otherwise.
    """

    if not text:
        return 0
    if _ENCODING is not None:
        return len(_ENCODING.encode(text))
    # Fallback heuristic: tokens ≈ words * 1.3
    return max(1, int(len(text.split()) * 1.3))


def bytes_length(text: str) -> int:
    """UTF-8 byte length, for tokenizer-independent efficiency reporting."""

    return len(text.encode("utf-8"))
