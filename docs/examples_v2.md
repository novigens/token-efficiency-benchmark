# v2 Worked Examples: Normative Test Candidates

Companion to `docs/design_v2.md` §4. These examples are normative:
an implementation that disagrees with any value here contains a bug. Each example names
the unit/integration tests it obligates. Values are chosen small enough to verify by hand.

---

## A. `arithmetic_chain`: depth 3, truth by forward substitution

**Internal structure (composer view, never shown to the model):**

| Node | Compute | Known value |
|---|---|---|
| 1 | Monday chairs 14, Tuesday twice as many: 14 + 28 | **42** |
| 2 | consumes 42: packed into boxes of 6: 42 ÷ 6 | **7** |
| 3 (terminal) | consumes 7: 7 boxes × \$9 − \$5 fee | **58** |

**Merged prompt (rendered, one valid surface among many for this seed's lexicon draw):**

> A workshop assembles 14 chairs on Monday and twice as many on Tuesday. A courier then
> packs the full production run into boxes holding 6 chairs each. A retailer buys every
> box at 9 dollars per box and pays a flat 5-dollar handling fee out of the proceeds.
> How many dollars remain after the fee?
>
> Answer with a single integer.

**Canonical terminal:** `58`. The values 42, 7, and 58 appear nowhere in the prompt.

**V\***: `1 × tokens(prompt) + 4 × tokens("58")`.

**Obligated tests**
- `test_chain_determinism`: same (version, seed, difficulty) ⇒ byte-identical prompt
  and truth.
- `test_chain_truth_recompute`: independently re-run the compute graph
  (14+28 → ÷6 → ×9−5); must equal stored truth. No scaling heuristic path exists.
- `test_chain_no_intermediate_leak`: none of {42, 7, 58} appear as surface tokens in
  the prompt.
- `test_chain_no_decomposition_markers`: no "Step", "first/then/finally", numbered
  sub-questions.
- `test_chain_v_star`: V* computed from prompt + canonical form only.
- `test_chain_distractor_invariance`: adding a distractor quantity (e.g., "the workshop
  employs 11 workers") changes the prompt but not the truth.

---

## B. `program_output`: truth by sandboxed execution

**Generated program (seed-determined AST draw):**

```python
x = 4
y = 3
for i in range(3):
    x = x + y
    if x % 2 == 0:
        y = y + 1
print(x * y)
```

**Reference trace (composer view):** x=7,y=3 → x=10,y=4 → x=14,y=5 → prints **70**.

**Merged prompt:** the program plus "What does this program print? Answer with a single
integer." (Prose-procedure rendering of the same AST is a difficulty axis, not a
different family.)

**Canonical terminal:** `70`.

**Obligated tests**
- `test_program_truth_is_execution`: stored truth equals fresh sandboxed execution at
  test time (truth is never cached across versions).
- `test_program_step_budget_rejection`: a generated instance exceeding the step budget
  (e.g., `range(10**9)`) raises `GenerationRejected`; termination is a generation-time
  guarantee, never a runtime surprise.
- `test_program_determinism`: grammar draw is seed-deterministic.
- `test_program_dead_code_invariance`: mutating an unreachable branch changes the
  surface, not the truth (distractor axis).
- `test_program_output_not_in_source`: the printed value does not appear as a literal
  in the program text.

---

## C. `table_aggregation`: truth by computed statistic

**Generated dataset (composer view):**

| Warehouse | Mon | Tue | Wed | Total |
|---|---|---|---|---|
| North | 120 | 95 | 143 | 358 |
| South | 88 | 176 | 61 | 325 |

**Merged prompt (narrated, interleaved by day; never presented as a table):**

> On Monday, the North warehouse shipped 120 kg and the South warehouse 88 kg. Tuesday's
> loads were 95 kg from North and 176 kg from South. On Wednesday, North moved 143 kg
> while South managed 61 kg. A returned pallet of 40 kg sat unprocessed at South all
> week. By how many kilograms did the busier warehouse's weekly total exceed the
> other's?
>
> Answer with a single integer.

**Reference computation:** 358 − 325 = **33**. The 40 kg return is a distractor.

**Obligated tests**
- `test_table_truth_recompute`: independent recomputation of the statistic from the
  stored dataset equals stored truth.
- `test_table_render_faithful`: every dataset value appears exactly once in the
  narration; no value is dropped or duplicated by interleaving (the renderer-audit
  check: extraction back out of the prose recovers the dataset).
- `test_table_distractor_invariance`: the return-pallet row changes the prompt, not
  the truth.
- `test_table_totals_not_in_prompt`: {358, 325, 33} absent from the surface.
- `test_table_determinism`: seed-deterministic dataset and narration.

---

## D. `consistency`: unanchorable by definition

Unchanged behavior, restated as the calibration probe:

- Model emits `a=79, b=36, c=42, verdict=consistent` where the rule is `a = b + c`:
  graded **incorrect** (79 ≠ 78; the grader recomputes on the model's own values).
- Model emits the same wrong `a` but `verdict=inconsistent`: graded **correct**;
  it honestly reported its own inconsistency.

**Obligated tests**: `test_consistency_terminal_
recomputed_from_emitted`, `test_consistency_honest_partial_credit`,
`test_consistency_confabulation_penalty`.

---

## E. Pricing layer: \$/correct and waste ratio

**Given** a results file for model X: 10 tasks, 7 correct, 2,000 input tokens and
5,000 output tokens total, and a price sheet `{in: $3/Mtok, out: $15/Mtok}`:

- spend = 2,000×3/10⁶ + 5,000×15/10⁶ = \$0.006 + \$0.075 = **\$0.081**
- **\$ per correct outcome** = 0.081 / 7 ≈ **\$0.0116**
- For a task with V* = 130 and actual weighted cost 1,530:
  **waste ratio** = (1530 − 130) / 130 ≈ **10.77** (the model spent ~11× the necessary
  budget).

**Obligated tests**
- `test_pricing_dollars_per_correct`: the arithmetic above, exactly.
- `test_pricing_zero_correct`: 0 correct ⇒ report `n/a`, never a division crash.
- `test_pricing_reweighting`: raw counts survive scoring so any other price sheet
  reproduces its own \$/correct from the same results file.
- `test_waste_ratio`: per-task and aggregate forms.

---

## F. Integration obligations (cross-family)

- `test_e2e_cli`: `generate → evaluate (echo fixtures) → score --pricing` runs green
  for every launch family from one command sequence; echo ⇒ efficiency 1.0,
  verbose_echo ⇒ efficiency ≪ 1, wrong_echo ⇒ accuracy 0 and \$/correct n/a.
- `test_replay_byte_identical`: any task regenerates byte-identically from
  (family, family_version, seed, difficulty) read out of its own JSONL record.
- `test_provider_token_counts`: for live-model responses, scored token counts come
  from the provider payload, not the local tokenizer (fixture models keep the local
  path).
- `test_serialization_round_trip`: task and result records survive
  write → read → write with equality.

---

## G. Hybrid composition: `program_output` → `arithmetic_chain`

A hybrid chains segments from different families via the `Composable` contract
(design_v2.md §4.1). Each segment computes its own truth given the injected upstream
value; the bridge phrase references that value without stating it.

**Recipe:** `program_output` (1 segment) → `arithmetic_chain` (2 ops).

**Segment 1 (composer view):** generated program

```python
x = 5
y = 2
for i in range(2):
    x = x * y
print(x + 1)
```

Trace: x=5 → 10 → 20; prints **21**. Output type: integer.

**Bridge + Segment 2 (composer view):** upstream 21 becomes the depot's Monday
intake; then `gain(15)` → **36**; then `split(4)` → **9**.

**Merged prompt (one valid rendering):**

> A control script runs on the depot's terminal each morning:
> ```
> x = 5
> y = 2
> for i in range(2):
>     x = x * y
> print(x + 1)
> ```
> Whatever the script prints becomes the number of crates the depot takes in on
> Monday. A supplier then adds 15 more to the running count. The running count is
> then divided evenly among 4 trucks; keep only one truck's share as the new
> running count. What is the final running count?
>
> Answer with a single integer.

**Canonical terminal:** `9`. Hidden values {21, 36, 9} appear nowhere in the surface;
program literals (5, 2, 1) and op arguments (15, 4) legitimately do.

**Obligated tests**
- `test_hybrid_truth_forward_across_segments`: independent recompute (execute the
  program, then apply the chain ops) equals stored truth: 21 → +15 → ÷4 = 9.
- `test_hybrid_bridge_no_leak`: the upstream terminal (21) is absent from the
  surface; the bridge references it only by phrase.
- `test_hybrid_type_bridge`: a joint whose upstream output type does not match the
  downstream input type raises `GenerationRejected` (no implicit coercion).
- `test_hybrid_determinism`: byte-identical regeneration from (recipe, seed,
  difficulty).
- `test_hybrid_recipe_recorded`: the recipe (ordered family list + per-segment
  difficulty) is stored in task parameters and reflected in the difficulty bucket,
  so hybrid cells stratify and replay like any other.
- `test_hybrid_scoring_unchanged`: the task scores through the standard path:
  V* from prompt + canonical answer; no hybrid-specific scoring code exists.

---

## H. Hybrid full gauntlet: `prog+chain+table` (the default recipe)

One value carried across three representations: code → narrative → table.
Each joint hides the carried value behind a typed bridge phrase.

**Segment 1 (program, composer view):**

```python
x = 3
y = 4
for i in range(3):
    x = x + y
print(x * 2)
```

Trace: x = 3+4+4+4 = 15; prints **30**.

**Bridge 1:** "Whatever the script prints becomes the number of units the site
takes in on Monday; that intake starts the running count."

**Segment 2 (chain, composer view):** 30 → `gain(17)` → **47** → `scale(3)` → **141**.

**Bridge 2:** "The final running count is handed to the logistics office, which
books it as the first site's opening-day load in the ledger below."

**Segment 3 (table, composer view):** the injected cell is North's Monday load.

| Site | Mon | Tue | Total |
|---|---|---|---|
| North | *141 (injected, never stated)* | 52 | **193** |
| South | 67 | 88 | **155** |

Question: by how many units did the highest weekly total exceed the lowest?
**Reference computation:** 193 − 155 = **38**.

**Canonical terminal:** `38`. Hidden values {30, 47, 141, 193, 155, 38} appear
nowhere in the surface; program literals (3, 4, 2), op arguments (17, 3), and
the non-injected cells (52, 67, 88) legitimately do.

**Obligated tests**
- `test_hybrid_three_segment_gauntlet`: three segment values recorded, all
  hidden in the surface, node truths equal segment values in order, terminal
  from the closing segment, bucket `hybrid_prog+chain+table_d{depth}`.
- `test_hybrid_chain_table_recipe`: the two-segment `chain+table` recipe
  holds the same invariants.
- `test_hybrid_default_recipe_is_full_gauntlet`: `HybridFamily()` defaults to
  `prog+chain+table`; the leaderboard runs this by default.
- Plus all §G obligations, which apply to every recipe.

---

**Test-suite honesty rule, adopted from the audit:** every test above must be able to
fail: each asserts against an independently computed value or an independently stated
invariant, never against the implementation's own output re-read back.
