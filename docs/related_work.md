# Related Work

Updated July 2026. This benchmark sits at the intersection of three active lines of
work: economic evaluation of LLMs, reasoning-efficiency measurement, and
contamination-resistant benchmark generation. None of them individually combines
runtime task generation, an optimal-cost baseline, and provider-billed dollar
accounting; the contribution is the integration.

## Economic evaluation (cost per correct outcome)

- **Cost-of-Pass** (Erol, El, Suzgun, Yuksekgonul & Zou, 2025; arXiv:2504.13359) is the
  closest prior work: it formalizes the expected monetary cost of generating a correct
  solution and shows the frontier cost-of-pass on MATH-500 halving roughly every 2.6
  months. We share the core economic quantity (\$/correct). The differences: Cost-of-Pass
  evaluates on *static public benchmarks* (MATH-500, AIME), inheriting their
  contamination; our tasks are generated fresh at runtime and burned after each run. We
  additionally anchor every task to an explicit optimum V*, enabling the **waste
  ratio**, an absolute overspend measure that "cost relative to other models" cannot
  provide; and we take token counts from the provider's billed usage (including hidden
  reasoning tokens) rather than from visible text.
- Price-performance trend analyses (e.g., arXiv:2511.23455) track intelligence-per-dollar
  across model generations; leaderboards such as Artificial Analysis popularized the
  framing. These measure the market; they do not provide a contamination-resistant
  instrument for measuring a single model's outcome economics.

## Reasoning-efficiency and overthinking benchmarks

- **OckBench** (2025; arXiv:2511.05722) names the "Overthinking Tax" and measures
  reasoning efficiency, but conditions on problems models already solve, excluding, by
  design, hallucination-under-difficulty and confident-wrong terminations. We do not
  filter: wrong answers earn zero efficiency and inflate \$/correct.
- **Overthinking in basic math** (Srivastava et al., 2025; arXiv:2507.04023) evaluates
  53 models on dynamically generated arithmetic and defines an Overthinking Score
  (harmonic mean of accuracy and token efficiency). Kindred in spirit at depth 1; our
  compositions add hidden multi-step structure, distractor axes, and dollar pricing.
- **EffiReason-Bench** (2025; arXiv:2511.10201) and **OptimalThinkingBench** (2025)
  systematize efficient-reasoning evaluation, the latter covering both over- and
  under-thinking. Both score against curated task sets; neither prices outcomes in
  dollars nor regenerates its test distribution per run.
- The **Stop Overthinking** survey (TMLR 2025) maps the efficient-reasoning method
  space; **BudgetThinker** (2025; arXiv:2508.17196) and related budget-control methods
  are complementary: they *train or steer* models toward efficiency, whereas this
  benchmark *measures* it, and provides the selection pressure those methods optimize
  against.

## Contamination-resistant generation

- **GSM-Symbolic** (Mirzadeh et al., 2024) showed frontier accuracy drops under
  controlled variation of known items, including the single-distractor fragility our
  distractor axis generalizes.
- **LiveBench** (White et al., 2024 onward) refreshes items monthly; **FreshQA** (Vu et al.,
  2023) tracks changing facts; **ARC-AGI / ARC-AGI-2** (Chollet, 2019; 2025) keep hidden
  sets and use empirical difficulty calibrated to reference solvers.
- Our version of the property is stronger where it matters for cost measurement: no
  fixed item pool exists at all. Tasks are drawn from parameterized families at
  evaluation time, published *after* scoring for replay, and never reused.

## Verifiable multi-step evaluation

SWE-bench (execution-verified), miniF2F/PutnamBench (prover-verified), BIG-Bench-Hard
and ProcBench (curated multi-step items) established deterministic verification for
multi-step tasks over fixed test sets. Process-reward approaches (PRM800K, Lightman et
al., 2023) score intermediate reasoning text and therefore inherit the chain-of-thought
faithfulness problem; we score only emitted answers and billed tokens, so the model's
reasoning text is whatever it wants it to be (see design_v2.md §1 and §6).

## What is distinct here

Four properties in combination, each individually precedented, jointly not: (1)
**runtime generation with burn-after-reading replay**: no static set, yet every
published number independently verifiable from a seed; (2) **V*-anchored scoring**:
efficiency and waste measured against a per-task optimum, not merely across models; (3)
**billing-truth accounting**: provider-reported usage including hidden reasoning
tokens, converted to dollars under versioned price sheets; (4) **merged single-prompt
compositions** whose decomposition the model must recover, with difficulty axes
(depth, distractors) designed for an evolution loop that keeps pace with the frontier.
