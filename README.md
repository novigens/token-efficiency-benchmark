# Token Efficiency Benchmark

[![CI](https://github.com/novigens/token-efficiency-benchmark/actions/workflows/ci.yml/badge.svg)](https://github.com/novigens/token-efficiency-benchmark/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

**What does a correct answer actually cost an enterprise on each LLM?**

Providers bill you per token. What you actually buy is *correct outcomes*, and a wrong one is not free: it flows downstream into a report or an invoice, and someone has to catch and fix it. This benchmark prices the thing that matters, the cost of a **trusted** answer.

**One concrete example.** Say you automate 1 million back-office workflows a month, each about 20 short steps a person could do on a computer: read a ledger, do the arithmetic, tabulate a total.

- **Opus 4.8** gets 92% right, at about **\$0.016 per correct answer**.
- **Haiku 4.5** looks half the price at **\$0.007 per correct answer**, but only gets 74% right.

The sticker says Haiku is cheaper. Reality: Haiku's wrong answers do not announce themselves. Each one lands in a report someone must catch and redo, and one bad number in a financial close costs far more than the pennies saved. Once you price that cleanup in, for the same million workflows **Opus costs about \$29K a month and Haiku about \$2.9M a month**, 100x more, for looking "cheaper." (The board's actual leaders, Kimi K3 and GPT-5.6 Sol, land near \$10K.)

That gap is what this benchmark measures: not the price per token, but the dollar cost of a trusted answer at scale.

**Recommendation.** The two newest frontier models are in a statistical dead heat at the top, both a generational leap over everything else (including their own vendors' prior releases):

- **`moonshot:kimi-k3`** (co-#1): 98% accuracy, the lowest cost per trusted answer, ~\$9.4K per million workflows a month.
- **`openai:gpt-5.6-sol#effort=medium`** (co-#1): the only 100% on the board, US-hosted, ~\$10.4K.

They finish within ~\$1K a month per million workflows, closer than a single run can resolve, so reliability, hosting, and data-residency decide it, not price: Sol for zero-defect runs, K3 for the lowest bill. `anthropic:claude-opus-4-8` is a solid third at 92%. Treat this as a shortlist, then run your own workload; the harness makes that cheap. Full board and method: [Leaderboard](#leaderboard).

## Leaderboard

### Business ranking, risk-adjusted `$/correct` (paired depth ladder run 2026-07-06, models through 2026-07-09)

| # | model (exact config) | acc | eff | `$/correct` | risk-adj `$/correct` | **cost / 1M workflows / mo** | note |
|--:|----------------------|----:|-----:|------------:|---------------------:|-----------------------------:|------|
| 🏆 | **Human** (Ideal: the bare correct answer) | **100%** | **100%** | **~\$0.0** | **~\$0.0** | **~\$0** | the V\* floor |
| 1 | `moonshot:kimi-k3` | 98% | 23.39% | \$0.00908 | **\$0.00941** | **\$9.4K** | co-leader · cheapest per trusted answer |
| 1 | `openai:gpt-5.6-sol#effort=medium` | **100%** | 36.57% | \$0.01042 | **\$0.01042** | **\$10.4K** | co-leader · only 100% on the board |
| 3 | `anthropic:claude-opus-4-8` | 92% | 21.87% | \$0.01617 | \$0.02862 | \$28.6K | |
| 4 | `moonshot:kimi-k3#thinking=off` | 88% | 20.97% | \$0.01113 | \$0.04026 | \$40.3K | |
| 5 | `anthropic:claude-fable-5` | 86% | 17.43% | \$0.04085 | \$0.235 | \$234.9K | |
| 6 | `openai:gpt-5.6-terra#effort=medium` | 78% | 38.23% | \$0.00641 | \$0.482 | \$482.3K | most efficient, but lower accuracy |
| 7 | `openai:gpt-5.5` | 80% | 22.14% | \$0.02628 | \$0.933 | \$933.5K | last gen, same price as Sol |
| 8 | `anthropic:claude-sonnet-5` | 78% | 10.60% | \$0.01710 | \$1.286 | \$1.29M | |
| 9 | `openai:gpt-5.4#effort=medium` | 76% | 18.29% | \$0.01580 | \$2.701 | \$2.70M | |
| 10 | `anthropic:claude-haiku-4-5` | 74% | 13.09% | \$0.00686 | \$2.862 | \$2.86M | |
| 11 | `openai:gpt-5.4#effort=low` | 70% | 28.33% | \$0.00993 | \$30.59 | \$30.6M | |
| 12 | `openai:gpt-5.6-luna` | 48% | 24.42% | \$0.00670 | \$2.0e+08 | unusable | cheap tier, too many wrong |
| 13 | `openai:gpt-5.4-nano` | 33% | 14.60% | \$0.00232 | \$3.9e+14 | unusable | pruned at depth 9 |
| 14 | `openai:gpt-4.1-nano` | 20% | 7.31% | \$0.00409 | \$2.6e+22 | unusable | pruned at depth 6 |
| - | `deepseek:deepseek-v4-pro` | 76% | 4.97% | \$0.00391 | (\$0.668) | (\$668.3K) | gated: 4.97% efficiency, just under the 5% floor |
| - | `moonshot:kimi-k2.5` (default thinking) | 76% | 1.46% | \$0.04021 | (\$6.87) | (\$6.9M) | gated: last-gen overthinking |
| - | `moonshot:kimi-k2.6` (default thinking) | 72% | 1.83% | \$0.05359 | (\$58.6) | (\$58.6M) | gated: last-gen overthinking |
| - | `openai:gpt-5.4` (default, reasoning off) | 0% | - | n/a | n/a | n/a | no correct answers; pruned at depth 3 |

The two newest frontier models, `kimi-k3` and `gpt-5.6-sol`, are co-ranked #1: their risk-adjusted costs sit within ~10% of each other, closer than the margin of error of a single 50-task run, so we call it a tie rather than split hairs (K3 the lowest bill, Sol the only 100%). Both are a generational leap ahead of everything else, including their own vendors' prior models. **cost / 1M workflows / mo** = risk-adj `$/correct` × 1,000,000: the monthly bill to run a million of these workflows, cleanup of wrong answers priced in. The cleanest illustration is within one vendor: OpenAI's GPT-5.6 Sol and GPT-5.5 are priced identically per token, yet Sol runs a million workflows for **\$10.4K** at 100% and GPT-5.5 for **\$933.5K** at 80%, a ~90x gap, one generation apart. Read the board as a make-or-buy line too: these are workflows a back-office team could process and validate with ordinary computer tools, no LLM in the loop (the Human row), so if staffing that team costs *less* than the cheapest reliable model here (~\$9.4K a month), keep the human-plus-computer workflow or go hybrid. Method, formula, gates, and full per-row counts: [`ANALYSIS.md`](benchmark_data/runs/20260706T222112Z_412022-paired/ANALYSIS.md).

![Accuracy and cost per correct answer versus depth 3 to 30 on the paired ladder, with the ideal V* floor marked](benchmark_data/runs/20260706T222112Z_412022-paired/depth_scaling_paired.png)

How depth separates them, now with real curves (paired ladder, 2026-07-06): through depth 30 the frontier tier shows no accuracy cliff, and the flat 80% lines are one bait-broken group, not depth. The weak tier collapses and is pruned on schedule. On the cost side nobody approaches the ideal floor at any depth: waste is a flat-rate tax, sitting 20 to 60x above V* from depth 3 all the way to depth 30. Full curves, the 77-parcel exhibit, and the honest outcome of our pre-registered depth prediction: [paired `ANALYSIS.md`](benchmark_data/runs/20260706T222112Z_412022-paired/ANALYSIS.md).

> **Reproducibility disclaimer.** These are single-run numbers, five shared problems per depth: directional, not definitive. The two co-leaders finish within ~10% on cost, well inside the margin of error of a 50-task run, so read them as tied, not ordered. LLM outputs also vary run to run: the same Fable 5 refused 5 of 20 tasks (25%) on the earlier 2026-07-03 board yet refused none here, which alone can swing a ranking. Kimi K3 and GPT-5.6 were both released in July 2026 and evaluated on the existing task set, so they had no more exposure to it than any other model, but they are the freshest and least-sampled rows. Numbers this close need repeated sampling before they are repeatable. Treat this board as a shortlist and a method, not a verdict, and reproduce with your own sample size before you procure.

Rows for Gemini, Grok, Qwen, DeepSeek, and the rest of the field are welcome through the same client (see [Extending](#extending)), provided each ships its full run directory as evidence; scaling the sample count is a community-sized job the harness makes cheap.

## The three metrics

**Efficiency (0 to 1]** measures how close the model came to the theoretical minimum cost, called `V*` ("V-star"). V* is the cost of simply reading the prompt and emitting the shortest correct answer. A model at efficiency 1.0 wasted nothing; a model at 0.05 spent 20× the minimum. Wrong answers get no efficiency score at all, because being cheap and wrong is worth nothing.

**\$/correct** is the total dollars spent across all tasks, divided by the number of correct answers. This is the number a buyer cares about. Wrong answers make it worse automatically: you paid for them and got nothing back. Its business variant, **risk-adjusted `$/correct`**, divides by 0.8^(k²) with k = wrong answers per 20 tasks, so unreliability compounds the price the way it compounds in deployed workflows (one wrong keeps 80% of value, two keep 41%, three 13%, four 3%); the 2026-07-06 board ranks by it.

**Waste ratio** counts how many multiples of the minimum the model overspent: `(actual cost − V*) / V*`. A waste ratio of 28 means the model spent 29× the necessary budget. It is the "token tax" in a single number.

![Benchmark pipeline: a family library feeds a generator; the question drops into the model spine while the exact answer goes straight to the grader, ending in scores and a leaderboard](docs/pipeline.svg)

One picture, the whole protocol: a generator chains interchangeable task families around one hidden value, hands the question to the model and the exact answer to the grader, and every response is priced in dollars per correct outcome.

## How it works, in plain terms

1. **Fresh questions at runtime, every run.** Task families are recipes that can mint millions of distinct multi-step problems, and a brand-new question set is one `teb run` away. Memorizing a test set, or distilling its answers into model weights, buys nothing: the next run simply is not that test.

2. **The right answer is known before any model answers.** Questions are built *forward* from known values, or by executing generated code. No human graders, no "LLM judge" whose own biases contaminate the score.

3. **Correctness and cost are scored together.** A wrong answer earns zero, no matter how cheap. A correct answer is scored against the minimum possible cost: read the question, state the answer.

4. **Everything converts to dollars.** Provider-reported token counts (the number you are billed for, hidden "thinking" tokens included) times the provider's own prices. Dollars are the only fair unit across providers.

## A worked example, end to end

The default benchmark family is the **hybrid gauntlet** (`prog+chain+table`): one value is carried across three representations (code → narrative → table), and the model must follow it the whole way without ever being told the value. Here is a real depth-2 gauntlet task, exactly as the model sees it:

> A control script runs on the site's terminal each morning:
>
> ```
> x = 3
> y = 4
> for i in range(3):
>     x = x + y
> print(x * 2)
> ```
>
> Whatever the script prints becomes the number of units the site takes in on Monday; that intake starts the running count.
>
> A supplier then adds 17 more to the running count. A wholesaler then orders 3 times the running count, and that order becomes the new running count.
>
> The final running count is handed to the logistics office, which books it as the first site's opening-day load in the ledger below.
>
> On Monday, the North depot logged a load equal to the running count, while the South depot logged 67 kilograms. On Tuesday, the North depot logged 52 kilograms, while the South depot logged 88 kilograms.
>
> By how many kilograms did the highest weekly total among the depots exceed the lowest?
>
> Answer with a single integer.

The generator built this forward, so it already knows every hidden value: the script prints **30** (x becomes 3+4+4+4=15, then 15×2); the running count goes 30 + 17 = **47**, then 47 × 3 = **141**; the ledger totals are North 141 + 52 = **193** and South 67 + 88 = **155**; the answer is 193 − 155 = **38**. None of those five numbers appear anywhere in the prompt. The model must execute the code, thread the result through the narrative, and aggregate the table. That triple representational shift is what single-family benchmarks can't test.

**Step 1: compute V\*, the optimal cost.** Say the prompt is 270 tokens and the canonical answer `38` is 1 token. With the default cost weights (input ×1, output ×4, mirroring the fact that providers charge roughly 4 to 5× more for output):

```
V* = 1×270 + 4×1 = 274 cost-weighted units
```

That's the price of a perfect performance: read the question, say the answer.

**Step 2: the model answers, and the provider reports what you'd be billed.** Say we run Kimi K2.5 and the API's usage field reports 270 input tokens and 1,200 output tokens (nearly all internal reasoning we never see, but all billed). The model's visible reply is `38`, which is correct.

**Step 3: score it.**

```
actual cost = 1×270 + 4×1,200 = 5,070
efficiency  = V* / cost = 274 / 5,070 = 0.054
waste ratio = (5,070 − 274) / 274 = 17.5×
```

Correct answer, 5% efficiency: the model spent seventeen times the necessary budget.

**Step 4: convert to dollars** using the provider's price sheet (K2.5: \$0.60 per million input tokens, \$3.00 per million output):

```
spend = 270×0.60/1M + 1,200×3.00/1M = $0.003762
```

Now compare a terse model that solved the same gauntlet with 25 output tokens: cost = 270 + 4×25 = 370, efficiency = 274/370 = **0.74**, spend ≈ **\$0.00024**. Same accuracy. **~16× cheaper.** And a model that confidently answered `40` after 6 tokens? Efficiency: none. It contributed to the bill and nothing to the numerator of \$/correct. That's the whole scoring philosophy: *there is no partial credit for being cheaply wrong or expensively right-adjacent.*

Aggregate those three behaviors over hundreds of fresh tasks per difficulty level, and luck washes out. What remains is each model's real cost-of-correctness curve.

**This isn't hypothetical.** Our first smoke run (July 2026, single-family arithmetic chains) put Kimi K2.5 at 100% accuracy with a **28× average waste ratio**, and the waste was *highest on the easiest questions* (38× at depth 3 vs 17× at depth 14), because the model carries a fixed thinking overhead of roughly 540 tokens no matter how trivial the task. Most enterprise queries are trivial. That's the finding accuracy leaderboards structurally cannot produce.

## Findings and evidence

The full audit, autopsies, and commentary live in the run's `ANALYSIS.md`. The current highlights, each with its caveat:

- **The two newest frontier models are tied at the top, a generation ahead of the rest.** Kimi K3 (Moonshot, 98%, ~\$9.4K per million workflows) and GPT-5.6 Sol (OpenAI, the only 100%, ~\$10.4K) finish within ~10% of each other and far ahead of everything else. Read that as a photo finish, not an ordering: at a single 50-task run the gap is inside the margin of error, and one flipped task would swap them. The story is generational, not national: both crush their own vendors' prior models (GPT-5.5 fell to mid-pack; the last-gen Kimi K2.5/K2.6 remain gated for overthinking), and the previous "board" had a Claude model on top. Fresh releases move fast; this is why the board is a living measurement, not a verdict.
- **The efficiency turnaround is real.** Last generation's default-thinking Kimis were gated at 1.5 to 1.8% efficiency (rumination). K3 reasons at 23% and GPT-5.6 Sol at 37%, the highest of any correct model, on a few hundred tokens per answer. Whatever changed in these training recipes, it priced thinking far better; the benchmark measures exactly that.
- **Everyone is still far from the human floor, and the cheapest tokens still rank worst.** Even the co-leaders run at 3 to 4x the ideal token cost, and none is perfectly reliable across depth. Meanwhile the lowest-per-token tiers failed regardless of vendor: OpenAI's `gpt-4.1-nano` (cheapest on the sheet) and its new `gpt-5.6-luna`, plus DeepSeek and last-gen Kimi, all landed unusable or gated. Cheap tokens did not buy cheap outcomes. And the benchmark is not partial to any lab: a Claude model (Fable 5) refused a quarter of its tasks on the shallow board, and the current #1 and #2 are not Claude at all.

*Dear frontier labs: we believe you about the olympiad golds. Now please first solve the simple analytical questions any human can easily get right, as efficiently as a human does.*

Earlier runs, the raw-`$/correct` board that motivates the risk adjustment, and the full finding history are in [`HISTORICAL.md`](HISTORICAL.md).

## Why this exists (for the technically curious)

- **Business:** choosing a model is a three-part decision: is it accurate enough, what does a correct answer cost, and was it tested on anything resembling your actual work? In our runs, the most expensive models matched cheaper ones on accuracy while costing several times more per correct answer, and popular benchmarks rarely test the kind of multi-step work enterprises actually run.
- **Theory:** today's reasoning models train on verifiable rewards, a sound idea shipped in its most degenerate form: one pass or fail signal per whole attempt, nothing teaching the model which step went wrong, nothing pricing its thinking. The remedies are textbook, step-level credit assignment (Bellman, Sutton) and the value of computation (Russell and Wefald, 1991), yet shipped models behave as if none of it exists. Add pay-per-token billing with hidden reasoning, where revenue rises with waste the buyer cannot inspect, and the conflict is structural, no intent required. This benchmark makes that waste measurable.

This benchmark is built to expose exactly those weaknesses, on freshly generated tasks no model can have memorized. And it will keep exposing them until a frontier lab solves reasoning properly, with step-level credit assignment and priced computation rather than patches around them. The proof is simple and open to anyone: ship a model whose cost scales like state tracking, and top this board. The full argument, pinned to evidence rows and references: [`docs/motivation.md`](docs/motivation.md).

**What about guardrails and agentic loops?** A fair objection: production systems add validators, retries, and step-by-step checks. But self-correction does not leave this cost-of-risk frontier, it moves along it. The critic is usually the same class of model with the same error rate, so it catches mistakes imperfectly, and every extra validation or retry pass is more tokens and more dollars. You buy accuracy with spend, which is exactly the trade `risk-adjusted $/correct` prices. So measure the whole loop as one unit: point the harness at your agent and read its risk-adjusted `$/correct` on the same board. The single-shot number is the primitive the loop is built from. The one genuine escape is a cheap deterministic verifier (unit tests, recomputable arithmetic); where you have one, use it and accuracy rises cheaply, but where the check is itself the hard judgment, as in most business decisions, the loop's checker is just another fallible call.

## Quick start

```bash
git clone https://github.com/novigens/token-efficiency-benchmark.git
cd token-efficiency-benchmark

# Use a virtual environment (or your equivalent: conda, uv, poetry)
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e ".[dev]"

# Offline sanity check: no API key needed, uses built-in reference fixtures.
# Runs the default family, the hybrid gauntlet (code -> narrative -> table).
teb run --model echo --model verbose_echo --n 5
# expect: echo => efficiency 1.000; verbose_echo => efficiency ~0.1, waste ~10x
```

## Run a leaderboard (real models)

The leaderboard workflow has one rule: **generate the questions once, then every model answers the same questions.** The run directory holds the shared question set. You can evaluate providers days apart, or only the ones you have keys for, and results merge into one file.

**Step 1: install provider packages and add keys** (same activated venv as above):

```bash
pip install -e ".[all]"          # provider SDKs, into the ACTIVATED venv
                                 # (the openai package also covers Moonshot/Kimi
                                 # and any OpenAI-compatible endpoint)

# Keys go in .env (gitignored), one line per provider you use:
#   MOONSHOT_API_KEY=sk-...
#   OPENAI_API_KEY=sk-...
#   ANTHROPIC_API_KEY=sk-...
set -a; source .env; set +a
```

**Step 2: create the run.** Fresh hybrid-gauntlet questions from an entropy-drawn seed, plus the `echo` fixture as the efficiency-1.000 reference row. This takes seconds and costs nothing:

```bash
teb run --model echo --pricing pricing/prices.json
# prints: Run <run_id>: 20 fresh tasks -> benchmark_data/runs/<run_id>
```

The default is the **starter ladder**: 2 cells (`3:1`, `6:3`) × 10 tasks = 20 questions. It is cheap (~\$0.10 per thinking model) and fast (~30 min per model at 1 worker), yet it keeps every difficulty axis active. For a publication-grade run, scale up: `--cell 3:0 --cell 6:2 --cell 10:2 --cell 14:5 --n 25`.

Each `--cell depth:distractors` is a difficulty setting (`10:2` means 10-step tasks with 2 irrelevant numeric sentences mixed in); `--n` is questions per cell. The default family is `hybrid` (`prog+chain+table`); single-representation families are available via `--family`: `arithmetic_chain`, `program_output`, `table_aggregation`.

**Step 3: evaluate each model against the same questions.** The evaluator runs requests concurrently, checkpoints every result, and skips finished work. It is safe to interrupt and re-run, and safe to come back to next week with new keys:

```bash
RUN=benchmark_data/runs/<run_id>   # paste the id Step 2 printed

python3 scripts/run_eval.py $RUN "moonshot:kimi-k2.5#thinking=off"
python3 scripts/run_eval.py $RUN anthropic:claude-sonnet-5
python3 scripts/run_eval.py $RUN "openai:gpt-5.4#effort=medium"
python3 scripts/run_eval.py $RUN openai:gpt-5.4-nano
# ...any subset, any order; adjust ids to what your provider's /models exposes.
# Knob fragments are distinct leaderboard rows: #thinking=off (Moonshot),
# #effort=low|medium|high (OpenAI). Always QUOTE a spec containing '#':
# unquoted, the shell treats everything after '#' as a comment and drops it.
# Defaults: 1 worker, 300s timeout. Raise carefully (`... 4 600`) only if your
# provider tier tolerates concurrency; thinking models are slow but steady.
```

**Step 4: the leaderboard.**

```bash
teb compare --results $RUN/results.jsonl --pricing pricing/prices.json
```

You get three tables: a **leaderboard** sorted by \$/correct (the buying decision), **model × difficulty pivots** so degradation curves read left-to-right (the diagnosis), and a **cost decomposition** that splits each model's spending into a fixed "thinking tax" plus a per-step rate (the explanation). Add `--business` for the risk-adjusted buyer view described under the leaderboard. In the first public run, GPT-5.4-medium decomposed to ~423 base + 32 tokens per step, while Sonnet 5 scaled at ~195 per step (see [Leaderboard](#leaderboard)).

**Common pitfalls.** Every one of these caught us during the first public run:

- **Fresh terminal, empty environment.** API keys and `RUN` are per-shell: run `set -a; source .env; set +a` and re-set `RUN` in every new terminal. If `run_eval.py` prints its usage line, `$RUN` expanded to nothing.
- **Unquoted `#` in a model spec.** `... $RUN moonshot:kimi-k2.5#thinking=off` without quotes silently becomes `moonshot:kimi-k2.5`, because the shell eats everything from `#` on. Quote it.
- **Provider SDK outside the venv.** If every task prints `[skip] ...: anthropic is not installed`, the SDK went to a different Python. Run `pip install -e ".[all]"` inside the activated venv, then re-run the same command; the evaluator resumes exactly where it left off.
- **Discarding bad rows.** `results.jsonl` is one row per (task, model). Deleting offending lines is safe and surgical, and the next run re-evaluates only what's missing.

**Replicating someone else's leaderboard.** Their run directory's `manifest.json` contains the seed and a ready-to-paste replay command that regenerates the identical questions byte-for-byte; their `results.jsonl` carries every raw response and provider-reported token count for re-grading and re-pricing. For a quick one-shot evaluation instead of the full workflow, `teb run --model moonshot:kimi-k2.5 ...` generates and evaluates in a single command (sequential, so slower for thinking-heavy models).

## Reproducibility: fresh questions, verifiable results

Every `teb run` draws a fresh random seed, generates its questions on the spot, and then documents everything:

```
benchmark_data/runs/<run_id>/
  manifest.json    # family version, run seed, difficulty cells, ready-to-paste replay command
  tasks.jsonl      # the exact questions this run saw
  results.jsonl    # raw model responses + provider-reported token counts
```

To verify someone's published run, paste the replay command from their manifest: `teb run --run-seed <seed> ...` regenerates the identical questions byte-for-byte, and grading of the recorded responses is fully deterministic. (The model's *own* responses may differ if you re-query the API; that is the model's nondeterminism, not the benchmark's, which is why raw responses ship with every run.) Raw token counts are always preserved, so anyone can re-price a run under their own cost structure (different provider discounts, batch rates, self-hosting) without spending a cent re-running it.

Two scores are comparable only when they share the same family version and difficulty cell.

## Extending

**Add a model.** Any OpenAI-compatible endpoint works without new code: instantiate `OpenAICompatClient(model=..., base_url=..., api_key_env=...)`. For anything else, implement a client returning `ModelOutput` (text + provider token counts) in `evaluation/live_models.py`.

**Add prices.** Edit `pricing/prices.json`: dollars per million tokens, keyed by `provider:model`. Please verify against the provider's live price page before publishing results.

**Add a task family.** Implement the `TaskFamily` protocol in `families/base.py`: `generate(seed, difficulty) -> task`, deterministic given (version, seed, difficulty), with ground truth computed by construction or execution, never approximated and never judged by an LLM. Write the worked example with hand-checkable numbers in [`docs/examples_v2.md`](docs/examples_v2.md) first; its named test obligations are the acceptance gate.

Design deep-dives: [`docs/design_v2.md`](docs/design_v2.md) (architecture, why the forward/backward asymmetry makes this work, the difficulty-evolution loop) and [`docs/examples_v2.md`](docs/examples_v2.md) (the normative worked examples).

## Project layout

```
src/token_efficiency_benchmark/
  families/           # arithmetic_chain, program_output, table_aggregation, hybrid
  evaluation/         # harness, scoring, pricing, reporting, model clients
  serialization.py    # replay-grade JSONL round-tripping
  cli.py              # teb: generate | evaluate | score | run | compare
pricing/prices.json   # versioned $/Mtok price sheet
scripts/run_eval.py   # resumable concurrent evaluator
docs/                 # design docs and worked examples
tests/                # offline test suite (ruff + mypy strict + pytest in CI)
```

## Future work

- **More families and recipes**: a consistency family (the same hidden fact probed through different surface forms), additional hybrid recipes and bridge types, and PSPACE-flavored interactive tasks beyond the current P/NP range.
- **Difficulty evolution**: when models saturate a difficulty region, automatically push the dials (depth, distractors, structure) until they separate again, so difficulty tracks the frontier instead of decaying with it.
- **Real-workload validation**: synthetic families prove contamination resistance, not real-world transfer. Pairing benchmark scores against measured costs on actual enterprise workloads is the study that closes that loop.
- **Agentic and tool-use tasks**: extending cost accounting to tool calls and multi-turn trajectories.
- **Verifiable-only scope, for now**: open-ended judgment and writing quality need different instruments; we'd rather do the verifiable slice rigorously than everything loosely.

## Citing this work

If you use this benchmark in your research or product evaluations, please cite it. A [`CITATION.cff`](CITATION.cff) file is included (GitHub renders a "Cite this repository" button from it), or use the BibTeX below:

```bibtex
@software{token_efficiency_benchmark_2026,
  author  = {Quah, K.H.},
  title   = {Token Efficiency Benchmark: Measuring the Cost of Correct
             Outcomes in Large Language Models},
  year    = {2026},
  month   = {7},
  version = {2.0.0},
  license = {MIT},
  url     = {https://github.com/novigens/token-efficiency-benchmark}
}
```

When citing results produced with the benchmark, please also state the family version, difficulty cells, and run seed from the run's `manifest.json`; that is what makes your numbers independently verifiable.

## License

MIT. See [LICENSE](LICENSE).
