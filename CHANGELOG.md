# Changelog

## Unreleased

- Paired ladder mode (`families/paired_ladder.py`, version namespace `2.0.0+paired`):
  one underlying problem extended across depth rungs (same program, same table, same
  distractors, chain ops prefixed), isolating depth per item. Regular generation
  streams and published replays are untouched.
- Depth-ladder orchestrator (`scripts/run_depth_ladder.py`): rungs 3..30, accuracy and
  efficiency pruning, majority early stop, resumable; `--paired` for the paired mode.

## 2.0.0 - 2026-07-02

Initial public release.

- **TaskFamily architecture**: procedurally generated task distributions with
  ground truth computed by construction or execution: no solvers, no LLM
  judges, no heuristics. Families ship with orthogonal difficulty axes (depth × distractor
  difficulty axes, orthogonal by design).
- **Burn-after-reading protocol**: `teb run` generates fresh questions from an
  entropy-drawn seed at runtime; every run directory is self-documenting
  (manifest with replay command, exact tasks, raw results).
- **Provider-usage billing truth**: token counts from the provider's usage
  field (includes billed-but-hidden reasoning tokens); local tokenizer only
  as fixture fallback. Clients for Moonshot (Kimi), OpenAI, and Anthropic;
  any OpenAI-compatible endpoint works via `base_url`.
- **Dollar economics**: versioned price sheets; `$ per correct outcome` and
  waste ratio via `teb score --pricing`; `teb compare` leaderboard,
  model × difficulty pivots, and cost decomposition (base + per-step tokens).
- **Four task families with hybrid as the default**: `arithmetic_chain`,
  `program_output` (truth by interpreting generated programs under a hard
  step budget), `table_aggregation` (computed-statistic truth over narrated
  datasets), and `hybrid`, cross-family chains via the `Composable` segment
  contract with typed bridge joints. The default recipe `prog+chain+table`
  carries one value across three representations (code → narrative → table);
  no hybrid-specific scoring code exists.
- **Audit evidence in every result row**: provider extras (exposed reasoning
  text, finish/stop reason, reasoning-token counts) are persisted as
  `response_extra`; never used for grading, always available for review.
- **68 offline tests**, every one asserting an independently computed value.
- First smoke run (Kimi K2.5): 100% accuracy, 28× mean waste ratio, waste
  highest on the shallowest tasks; see
  `benchmark_data/runs/20260702T183746Z_346427/ANALYSIS.md`.
