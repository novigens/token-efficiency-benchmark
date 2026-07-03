"""Task families (v2 architecture).

A family owns its ground-truth computation and its surface rendering.
See ``docs/design_v2.md`` §3.1 and ``docs/examples_v2.md``.
"""

from __future__ import annotations

from .arithmetic_chain import ArithmeticChainFamily
from .base import (
    Composable,
    DifficultyParams,
    GenerationRejected,
    Segment,
    TaskFamily,
)
from .hybrid import HybridFamily
from .program_output import ProgramOutputFamily
from .table_aggregation import TableAggregationFamily

FAMILIES: dict[str, type[TaskFamily]] = {
    "arithmetic_chain": ArithmeticChainFamily,
    "program_output": ProgramOutputFamily,
    "table_aggregation": TableAggregationFamily,
    "hybrid": HybridFamily,
}

__all__ = [
    "FAMILIES",
    "ArithmeticChainFamily",
    "Composable",
    "DifficultyParams",
    "GenerationRejected",
    "HybridFamily",
    "ProgramOutputFamily",
    "Segment",
    "TableAggregationFamily",
    "TaskFamily",
]
