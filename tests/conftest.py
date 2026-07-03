"""Pytest fixtures: family-generated tasks."""

from __future__ import annotations

import pytest

from token_efficiency_benchmark.families import ArithmeticChainFamily, DifficultyParams


@pytest.fixture
def linear_chain_depth_3():
    return ArithmeticChainFamily().generate(12345, DifficultyParams(depth=3))


@pytest.fixture
def linear_chain_depth_4_fixture():
    return ArithmeticChainFamily().generate(2024, DifficultyParams(depth=4))
