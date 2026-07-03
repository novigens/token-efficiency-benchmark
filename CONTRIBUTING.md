# Contributing to the Token Efficiency Benchmark

Thank you for your interest in contributing. This benchmark is meant to be a community-maintained piece of evaluation infrastructure, not a one-off academic artifact, and contributions from outside the original author group are explicitly welcomed.

This document covers the kinds of contribution that are most valuable, how to set up a development environment, the bar for code and tests, and the process for proposing larger design changes.

## What we are most interested in

The highest-value contributions, in roughly descending order:

**New task families.** Each family is a procedurally generated task distribution with ground truth computed by construction or execution, never approximated and never judged by an LLM. The contract is `families/base.py`; the acceptance gate is a hand-verifiable worked example with named test obligations in [`docs/examples_v2.md`](docs/examples_v2.md). Currently shipping: `arithmetic_chain`, `program_output`, `table_aggregation`, and the `hybrid` cross-family composer (default). Wanted next: the `consistency` family port, logic grids, graph/scheduling problems, new hybrid recipes and bridge types.

**New model providers and price sheets.** Any OpenAI-compatible endpoint works via `OpenAICompatClient(base_url=...)`; other providers need a small client returning `ModelOutput` with provider-reported token counts (the billing truth). Price-sheet updates to `pricing/prices.json` should cite the provider's price page and date.

**Surface-rendering improvements.** Each family owns its prose rendering; wider lexicons and more phrase variants shrink the "detectably synthetic" surface while staying seed-deterministic. Pull requests that add rendering variety without breaking the hidden-value validity checks are very welcome.

**Independent re-runs and replays.** Reproducibility is a first-class property. If you run the benchmark on a model and your aggregate score differs from a published number, please open an issue and attach the JSONL replay file. We will diff your trajectories against ours and resolve the discrepancy publicly.

**Documentation and worked examples.** The more hand-verifiable end-to-end examples we have (see [`docs/examples_v2.md`](docs/examples_v2.md)), the easier the benchmark is for new contributors to reason about.

## What we are *not* looking for

- Hand-curated test items that bypass the procedural generator. The contamination-resistance property requires that no specific question is fixed at release time; even small fixed sets undermine that.
- Families without verifiable unique answers (free-form generation, open-ended QA without a canonical key, judgment items).
- Score-tuning changes (alternative weightings, alternative aggregations) that are not configurable. The cost-weighted efficiency default is the headline metric; alternative weights belong in the configuration layer, not as replacements.
- LLM-as-judge anywhere in the scoring pipeline. The benchmark's reliability comes from deterministic grading against known answers; introducing a judge model reintroduces the failure modes the design is meant to remove.

## Development setup

```bash
git clone https://github.com/novigens/token-efficiency-benchmark.git
cd token-efficiency-benchmark
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
pytest tests/ -v
```

Python 3.10+ is required. The codebase has a small dependency footprint by design (`tiktoken`, `pydantic`, `click`, `pytest`); we will push back on PRs that add heavyweight dependencies for marginal convenience.

## Code style

- Formatting: `ruff format` (configured in `pyproject.toml`).
- Linting: `ruff check`.
- Type-checking: `mypy --strict` for the `src/` tree. New code should pass.
- Tests: `pytest`. Coverage target is "every public function in `src/` has at least one test"; we are not chasing a specific percentage.

A pre-commit hook runs ruff and mypy on staged files; please install it.

## The bar for new task families

A pull request adding a task family is accepted when:

1. It implements the `TaskFamily` protocol in `src/token_efficiency_benchmark/families/base.py` and is deterministic in (family version, seed, difficulty).
2. Ground truth is computed by construction or execution inside the family (no solver, no LLM judge, no approximation), and invalid instances raise `GenerationRejected` rather than emitting.
3. Rendered prompts pass the shared validity checks: no hidden value appears in the surface form, and no decomposition markers ("Step 1," numbered sub-questions, stage labels).
4. It declares its difficulty axes so the evolution loop can mutate them.
5. A hand-verifiable worked example lands in [`docs/examples_v2.md`](docs/examples_v2.md) first, and every named test obligation from that example passes.

## Design changes

The design is settled on a number of properties (see [`docs/design_v2.md`](docs/design_v2.md) §1 to §3). PRs that reverse a settled property need to ship with explicit reasoning about why the property no longer holds, not just a different preference. In particular:

- The terminal-only response contract is settled: the model produces one answer; everything else it emits counts against efficiency.
- Cost-weighted token efficiency with the `(w_in=1, w_out=4)` default is settled. Alternative weights are configurable; changing the default requires an RFC.
- Ground truth by construction or execution is settled. No solver, CAS, or constraint engine in the generator.
- No LLM-as-judge anywhere in scoring is settled.
- Provider-reported token usage as billing truth is settled.

For substantive design changes, open an issue tagged `rfc` with the proposed change, the failure mode it addresses, and the affected sections of `docs/design_v2.md`. Discussion happens in the issue before any code is written.

## Reporting bugs

A good bug report includes:

- The generator version (`teb --version`).
- The seed and parameters that reproduce the issue.
- For evaluation bugs, the JSONL result file for the affected tasks.
- The expected vs. actual behavior.

Generator bugs (failing validity checks, malformed merged prompts) are highest priority because they affect benchmark correctness. Please tag them `generator-bug`.

## Releases and versioning

The generator is versioned independently from the package. Major generator version changes (new source benchmarks, new templates, changed difficulty parameterization) reset comparability of historical scores. Minor changes (bug fixes, validity-check improvements) are forward-compatible and re-scoring older replays under the new minor version is valid.

Package releases follow semver. Generator version is recorded in every result file.

## Code of conduct

See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md). The short version: be reasonable, be precise, and assume good faith from other contributors.

## Questions

For benchmark methodology questions, open an issue with the `question` tag. For implementation-only questions, our preference is to discuss them in the relevant PR rather than over a separate channel, so the design rationale stays attached to the code.
