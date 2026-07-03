# Run 20260703T070656Z_098392: Analysis

**Date:** 2026-07-03 · **Tasks:** 20 hybrid `prog+chain+table` (10 × depth 3 / 1 distractor, 10 × depth 6 / 3 distractors) · **Workers:** 1 · **Output cap:** 16,384 · **Prices:** `pricing/prices.json` `2026-07-02.roster-v1`

Roster and exact per-row API parameters: `manifest.json`. Pre-flight probes that selected this roster (and disqualified two default configs): `VALIDATION.md`.

## Final tables (`teb compare`)

```
== Leaderboard (sorted by $/correct) ==
model                                 n    acc   $/correct  waste x    eff  out_tok
------------------------------------------------------------------------------------
moonshot:kimi-k2.5#thinking=off      20  1.000     0.00217      6.1  0.144      637
openai:gpt-5.4#effort=medium         20  1.000     0.00958      5.6  0.168      568
anthropic:claude-sonnet-5            20  0.900     0.01396     11.1  0.085     1134
echo_model                           20  1.000    unpriced      0.0  1.000        2

== $/correct by difficulty ==
model                              hybrid_prog+chain+table_d3  hybrid_prog+chain+table_d6
anthropic:claude-sonnet-5                             0.00929                     0.01979
moonshot:kimi-k2.5#thinking=off                       0.00169                     0.00264
openai:gpt-5.4#effort=medium                          0.00855                     0.01061

== Cost decomposition: out_tok = base + rate x depth ==
model                              base out_tok  per-step     n
----------------------------------------------------------------
anthropic:claude-sonnet-5                   257     194.8    20
echo_model                                    2       0.0    20
moonshot:kimi-k2.5#thinking=off             239      88.5    20
openai:gpt-5.4#effort=medium                423      32.1    20
```

## Verification (independent of the harness)

- **Dollars recomputed from raw rows × price sheet**: kimi \$0.00217, gpt \$0.00958, sonnet \$0.01396 per correct; exact match with the leaderboard.
- **Row inventory**: 80 rows = 20 `echo_model` + 20 × 3 live configs. No truncations: every finish is `stop` / `end_turn`.
- **Knob evidence**: all 20 Kimi rows carry empty `reasoning_content` (thinking really off); GPT rows carry 243 to 1,186 reasoning tokens, mean 555 (effort really on); Sonnet rows carry 227 to 1,035 thinking tokens, mean 582 (default thinking active).

## Sonnet-5 miss autopsy (2/20, both depth-6)

| task (suffix) | canonical | answered | stop | out_tok | thinking_tok |
|---------------|----------:|---------:|------|--------:|-------------:|
| …6a6b9c5f542e | 1079 | 1066 | end_turn | 1,692 | 854 |
| …15d2686d73da | 929 | 1020 | end_turn | 1,263 | 774 |

Both are clean, confident completions: distractors correctly identified, arithmetic slip mid-chain, wrong final total. Not parser artifacts, not truncation: genuine accuracy failures, billed in full (which is precisely what \$/correct is designed to capture).

## Reading

Three spending strategies on identical questions. Kimi-instant reasons entirely in the open (mean 637 output tokens, all visible). GPT-5.4-medium reasons almost entirely in hiding (~555 hidden + ~13 visible). Sonnet-5 defaults do both (~582 hidden + ~552 visible = 1,134), and they pay the highest unit price for it. Token-efficiency and dollar-efficiency disagree on the winner: GPT is the most token-lean (eff 0.168), yet Kimi is 4.4× cheaper per correct outcome; unit price dominates verbosity, which is the benchmark's core thesis. Depth scaling: GPT's high fixed tax but 32-token marginal step suggests it would close the gap on much deeper tasks; Sonnet's 195-token step rate widens its gap with depth (7.5× Kimi's \$/correct at depth 6).

Selection caveat: rows were shortlisted after a validation probe (see `VALIDATION.md`), so this is a cost comparison among validated-viable configs, not a neutral census of defaults.

## Excluded configs (failed the probe)

| config | probe result |
|--------|--------------|
| `moonshot:kimi-k2.5` (default, thinking on) | burned the full output budget, returned no answer |
| `openai:gpt-5.4` (default, reasoning off) | instant wrong answer, 4 output tokens |

Both remain replayable against this run's `tasks.jsonl`; transcripts in `VALIDATION.md`.
