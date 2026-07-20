# Historical results and findings

Earlier runs and write-ups, superseded by the current board in the [README](README.md) but kept for the record and the arc of the project. Every run directory under `benchmark_data/runs/` remains replayable.

## First public run: raw `$/correct` (2026-07-03, twelve configs, depths 3 and 6)

**Why raw `$/correct` alone misleads.** An earlier, shallower run (2026-07-03, twelve configs, depths 3 and 6) ranks very differently, because raw `$/correct` prices retries and assumes wrong answers are caught. The two nanos top it at 40 to 45% accuracy, which is the trap the business board fixes: with no oracle to catch them, a 40%-accurate model is not cheap, it is unusable.

| # | model (exact config) | acc | \$/correct | waste | token-eff | out-tok |
|--:|----------------------|----:|-----------:|------:|----------:|--------:|
| 🏆 | **Human** (Ideal, the `echo` fixture: the bare correct answer) | **100%** | **~\$0.0** | **0x** | **100%** | **2** |
| 1 | `openai:gpt-4.1-nano` | 45% | 🥇 \$0.00108 | 11.2x | 8.7% | 1,109 |
| 2 | `openai:gpt-5.4-nano` | 40% | \$0.00184 | 5.4x | 15.8% | 520 |
| 3 | `moonshot:kimi-k2.5#thinking=off` | 100% | \$0.00217 | 6.1x | 14.4% | 637 |
| 4 | `moonshot:kimi-k2.6#thinking=off` | 90% | \$0.00395 | 7.3x | 12.7% | 787 |
| 5 | `anthropic:claude-haiku-4-5` | 80% | \$0.00520 | 7.0x | 12.6% | 734 |
| 6 | `openai:gpt-5.4#effort=low` | 95% | \$0.00673 | 🥇 3.3x | 🥇 24.7% | 355 |
| 7 | `openai:gpt-5.4#effort=medium` | 100% | \$0.00958 | 5.6x | 16.8% | 568 |
| 8 | `anthropic:claude-opus-4-8` | 95% | \$0.01380 | 4.1x | 20.1% | 402 |
| 9 | `anthropic:claude-sonnet-5` (defaults) | 90% | \$0.01396 | 11.1x | 8.5% | 1,134 |
| 10 | `openai:gpt-5.5` | 95% | \$0.01539 | 3.8x | 21.9% | 416 |
| 11 | `moonshot:kimi-k2.6` (default thinking) | 95% | \$0.03418 | 77.8x | 1.8% | 8,015 |
| 12 | `anthropic:claude-fable-5` | 75% | \$0.03530 | 5.0x | 17.2% | 407 |

n = 20 tasks per row, ranked by `$/correct`; 🥇 = best per metric; the Human row is the V\* floor (humans do not bill for their thinking; these models do). Full run detail, evidence, and audit: [`ANALYSIS.md`](benchmark_data/runs/20260703T070656Z_098392/ANALYSIS.md).

### More from that run

**More from that run, one line each:**

- **A 33x spread on identical questions.** One correct answer costs between \$0.0011 and \$0.0353 depending on which configuration you ask.
- **Cheap-and-wrong tops retry economics, and risk pricing resolves it.** The nanos lead raw `$/correct` at 40 to 45% accuracy because that metric prices retries, which assumes wrong answers are detectable. The risk-adjusted column makes the business judgment explicit: the nanos price in the trillions of dollars per trusted answer.
- **The cheapest clean sheet is a knob, not a flagship.** `kimi-k2.5#thinking=off` scores 100% at \$0.0022 per correct. The quiet star is `gpt-5.4#effort=low`: 95% with the board's best waste (3.3x) and token efficiency (24.7%).
- **The thinking dial has vendor-specific exchange rates.** GPT-5.4 low to medium buys the last 5 accuracy points for 1.4x the money; Kimi K2.6 off to on buys the same 5 points for 8.7x, at 77.8x waste and one death against the output cap.
- **The newest, priciest flagships rank worst per dollar.** The five most recent premium releases (Opus 4.8, Sonnet 5, GPT-5.5, Kimi K2.6, Fable 5) fill the five worst `$/correct` ranks on the board.
- **Middle-school tasks, olympiad-grade models, real failures.** Every task is hand-verifiable with middle-school math, in the same season as gold-medal IMO and IOI results and beyond-PhD GPQA scores ([OpenAI](https://x.com/OpenAI/status/1946594928945148246), [DeepMind](https://deepmind.google/blog/advanced-version-of-gemini-with-deep-think-officially-achieves-gold-medal-standard-at-the-international-mathematical-olympiad/), [IOI 2025](https://the-decoder.com/openais-ai-system-wins-a-gold-medal-level-score-at-the-international-olympiad-in-informatics-2025/), [GPQA](https://openai.com/index/learning-to-reason-with-llms/)). On this board, a single 63-parcel distractor sentence took down 8 of 12 configurations, and the priciest model refused 5 of 20 tasks outright.
- **Buyers already suspected it.** Alex Karp on CNBC: these models "have been completely, irresponsibly, oversold" ([CNBC, July 2026](https://www.cnbc.com/2026/07/01/palantir-karp-open-ai-anthropic-tokens.html)). This benchmark is a measuring instrument for that claim.

### Failing configs, listed rather than hidden

**Failing configs, listed rather than hidden.** Two *default* configurations failed the shared pre-flight probe task and were excluded from the paid run; the raw API transcripts are in [`VALIDATION.md`](benchmark_data/runs/20260703T070656Z_098392/VALIDATION.md):

| excluded config | probe result | failure mode |
|-----------------|--------------|--------------|
| `moonshot:kimi-k2.5` (default, thinking on) | no answer returned | found the correct answer mid-reasoning, kept second-guessing, burned the entire output budget |
| `openai:gpt-5.4` (default, reasoning off) | wrong answer, 4 output tokens | answered instantly without reasoning at all |

Same weights as the winners above, one knob apart. Because rows were shortlisted after this probe, read the leaderboard as a cost comparison among validated-viable configs rather than a neutral census; the manifest records the selection rationale, and the excluded configs remain replayable from the same `tasks.jsonl`.
